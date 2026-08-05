from contextlib import asynccontextmanager
import os
import re
import traceback
from config import DB_PATH, DATABASE_URL
from utils.logger import logger

IS_POSTGRES = bool(DATABASE_URL and ("postgres://" in DATABASE_URL or "postgresql://" in DATABASE_URL))

if IS_POSTGRES:
    import asyncpg
else:
    import aiosqlite


def get_formatted_db_url(url: str) -> str:
    """تنسيق رابط قاعدة البيانات لـ asyncpg."""
    formatted = url.replace("postgres://", "postgresql://", 1)
    # إزالة sslmode إذا كانت غير متوافقة مع asyncpg وتمرير ssl بدلاً منها
    formatted = re.sub(r"[?&]sslmode=[^&]+", "", formatted)
    return formatted


def convert_params(sql: str) -> str:
    """تحويل علامات الاستفهام ? إلى $1, $2 في PostgreSQL asyncpg."""
    pg_sql = re.sub(r"INSERT\s+OR\s+IGNORE\s+INTO", "INSERT INTO", sql, flags=re.IGNORECASE)
    if "INSERT INTO" in pg_sql.upper() and "ON CONFLICT" not in pg_sql.upper() and "IGNORE" in sql.upper():
        pg_sql = pg_sql.rstrip(";") + " ON CONFLICT DO NOTHING;"

    count = [0]
    def repl(match):
        count[0] += 1
        return f"${count[0]}"
    
    return re.sub(r"\?", repl, pg_sql)


class AsyncPGDBWrapper:
    """مغلف متوافق مع aiosqlite يغلف asyncpg لسرعة واستقرار Vercel."""

    def __init__(self, conn):
        self.conn = conn

    async def execute(self, sql: str, params: tuple = ()):
        pg_sql = convert_params(sql)
        if pg_sql.strip().upper().startswith("SELECT") or "RETURNING" in pg_sql.upper():
            rows = await self.conn.fetch(pg_sql, *params)
            return AsyncPGCursorWrapper(rows)
        else:
            status = await self.conn.execute(pg_sql, *params)
            return AsyncPGCursorWrapper([], status=status)

    async def commit(self):
        pass  # asyncpg يقوم بالتنفيذ المباشر التلقائي بدون حاجة لـ commit يدوي

    async def close(self):
        await self.conn.close()


class AsyncPGCursorWrapper:
    def __init__(self, rows, status=None):
        self.rows = [dict(row) for row in rows] if rows else []
        self.status = status
        self._index = 0

    @property
    def rowcount(self):
        if self.status:
            match = re.search(r"\d+", self.status)
            return int(match.group()) if match else 1
        return len(self.rows)

    @property
    def lastrowid(self):
        if self.rows and 'id' in self.rows[0]:
            return self.rows[0]['id']
        return None

    async def fetchone(self):
        if self.rows:
            return self.rows[0]
        return None

    async def fetchall(self):
        return self.rows

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


async def init_db():
    """إعادة تهيئة وفحص جداول قاعدة البيانات."""
    logger.info("جاري فحص وإعداد قاعدة البيانات...")

    if IS_POSTGRES:
        db_url = get_formatted_db_url(DATABASE_URL)
        try:
            conn = await asyncpg.connect(db_url, ssl="require")
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS stages (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL UNIQUE
                );
                CREATE TABLE IF NOT EXISTS classes (
                    id SERIAL PRIMARY KEY,
                    stage_id INTEGER NOT NULL REFERENCES stages(id) ON DELETE CASCADE,
                    name VARCHAR(255) NOT NULL
                );
                CREATE TABLE IF NOT EXISTS subjects (
                    id SERIAL PRIMARY KEY,
                    class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
                    name VARCHAR(255) NOT NULL
                );
                CREATE TABLE IF NOT EXISTS books (
                    id SERIAL PRIMARY KEY,
                    class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
                    subject_id INTEGER REFERENCES subjects(id) ON DELETE SET NULL,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    telegram_file_id TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    telegram_id BIGINT UNIQUE NOT NULL,
                    full_name TEXT,
                    join_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
            await conn.close()
        except Exception as e:
            logger.error(f"خطأ الاتصال بـ Supabase (asyncpg): {e}")
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("PRAGMA foreign_keys = ON;")
            await db.execute("""
                CREATE TABLE IF NOT EXISTS stages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE
                );
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS classes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stage_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    FOREIGN KEY (stage_id) REFERENCES stages (id) ON DELETE CASCADE
                );
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS subjects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    class_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    FOREIGN KEY (class_id) REFERENCES classes (id) ON DELETE CASCADE
                );
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    class_id INTEGER NOT NULL,
                    subject_id INTEGER,
                    title TEXT NOT NULL,
                    description TEXT,
                    telegram_file_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (class_id) REFERENCES classes (id) ON DELETE CASCADE,
                    FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE SET NULL
                );
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    full_name TEXT,
                    join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            await db.commit()

    logger.info("تم إعداد قاعدة البيانات بنجاح.")


@asynccontextmanager
async def get_db_connection():
    """مزود الاتصال بقاعدة البيانات لـ Vercel عبر asyncpg."""
    if IS_POSTGRES:
        db_url = get_formatted_db_url(DATABASE_URL)
        conn = await asyncpg.connect(db_url, ssl="require")
        wrapper = AsyncPGDBWrapper(conn)
        try:
            yield wrapper
        finally:
            await conn.close()
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("PRAGMA foreign_keys = ON;")
            yield db
