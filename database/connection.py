from contextlib import asynccontextmanager
import os
import re
from config import DB_PATH, DATABASE_URL
from utils.logger import logger

# اختيار المكتبة المناسبة بحسب توفر DATABASE_URL
IS_POSTGRES = bool(DATABASE_URL and (DATABASE_URL.startswith("postgres://") or DATABASE_URL.startswith("postgresql://")))

if IS_POSTGRES:
    import psycopg
    from psycopg.rows import dict_row
else:
    import aiosqlite


class PostgresDBWrapper:
    """مغلف متوافق مع aiosqlite لتسهيل التعامل مع PostgreSQL (Supabase)."""

    def __init__(self, conn):
        self.conn = conn

    async def execute(self, sql: str, params: tuple = ()):
        # تحويل علاقات الإدخال من ? في SQLite إلى %s في PostgreSQL
        pg_sql = sql.replace("?", "%s")
        # تحويل INSERT OR IGNORE إلى ON CONFLICT DO NOTHING
        pg_sql = re.sub(r"INSERT\s+OR\s+IGNORE\s+INTO", "INSERT INTO", pg_sql, flags=re.IGNORECASE)
        if "INSERT INTO" in pg_sql.upper() and "ON CONFLICT" not in pg_sql.upper() and "IGNORE" in sql.upper():
            pg_sql = pg_sql.rstrip(";") + " ON CONFLICT DO NOTHING;"

        cursor = await self.conn.execute(pg_sql, params)
        return PostgresCursorWrapper(cursor)

    async def commit(self):
        await self.conn.commit()

    async def close(self):
        await self.conn.close()


class PostgresCursorWrapper:
    def __init__(self, cursor):
        self.cursor = cursor

    @property
    def rowcount(self):
        return self.cursor.rowcount

    @property
    def lastrowid(self):
        # في postgresql نحاول إرجاع المعرف إذا تم استعمال RETURNING id
        try:
            row = self.cursor.fetchone()
            if row:
                return row.get('id', row[0] if isinstance(row, (tuple, list)) else None)
        except Exception:
            pass
        return None

    async def fetchone(self):
        return await self.cursor.fetchone()

    async def fetchall(self):
        return await self.cursor.fetchall()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


async def init_db():
    """إعادة تهيئة وفحص جداول قاعدة البيانات عند التشغيل الأول."""
    logger.info("جاري فحص وإعداد قاعدة البيانات...")

    if IS_POSTGRES:
        # تعديل الرابط إذا كان يبدأ بـ postgres:// ليتوافق مع psycopg3
        db_url = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
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
            await conn.commit()
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
    """مزود الاتصال بقاعدة البيانات (يدعم SQLite المحلية أو Supabase PostgreSQL تلقائياً)."""
    if IS_POSTGRES:
        db_url = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        conn = await psycopg.AsyncConnection.connect(db_url, row_factory=dict_row)
        wrapper = PostgresDBWrapper(conn)
        try:
            yield wrapper
        finally:
            await conn.close()
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("PRAGMA foreign_keys = ON;")
            yield db
