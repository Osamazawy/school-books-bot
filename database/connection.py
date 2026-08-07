from contextlib import asynccontextmanager
import os
import re
import asyncio
from config import DB_PATH, DATABASE_URL
from utils.logger import logger

IS_POSTGRES = bool(DATABASE_URL and ("postgres://" in DATABASE_URL or "postgresql://" in DATABASE_URL))

if IS_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor
else:
    import aiosqlite


def get_formatted_db_url(url: str) -> str:
    """تنسيق رابط قاعدة البيانات لـ psycopg2 وتصحيح روابط Supabase Direct إلى IPv4 Pooler."""
    formatted = url.replace("postgres://", "postgresql://", 1)
    
    # تحويل رابط Direct Connection (IPv6 فقط) إلى Connection Pooler (IPv4 متوافق مع Vercel)
    if ".supabase.co" in formatted and "pooler.supabase.com" not in formatted:
        # استخراج reference من db.xxx.supabase.co
        match = re.search(r"@db\.([a-z0-9]+)\.supabase\.co", formatted)
        if match:
            ref = match.group(1)
            # تحديث اسم المستخدم والرابط لاستخدام IPv4 Pooler
            formatted = re.sub(r"postgresql://postgres:", f"postgresql://postgres.{ref}:", formatted)
            formatted = re.sub(r"@db\.[a-z0-9]+\.supabase\.co:5432", r"@aws-0-eu-central-1.pooler.supabase.com:5432", formatted)
    
    if "sslmode" not in formatted:
        separator = "&" if "?" in formatted else "?"
        formatted = f"{formatted}{separator}sslmode=require"
    return formatted


class AsyncQuery:
    """كائن استعلام متوافق مع async with و await في نفس الوقت."""
    def __init__(self, conn, sql: str, params: tuple = ()):
        self.conn = conn
        self.sql = sql
        self.params = params
        self._wrapper = None

    async def _execute(self):
        if self._wrapper is None:
            pg_sql = self.sql.replace("?", "%s")
            pg_sql = re.sub(r"INSERT\s+OR\s+IGNORE\s+INTO", "INSERT INTO", pg_sql, flags=re.IGNORECASE)
            if "INSERT INTO" in pg_sql.upper() and "ON CONFLICT" not in pg_sql.upper() and "IGNORE" in self.sql.upper():
                pg_sql = pg_sql.rstrip(";") + " ON CONFLICT DO NOTHING;"

            def _run():
                cur = self.conn.cursor(cursor_factory=RealDictCursor)
                cur.execute(pg_sql, self.params)
                return cur

            cursor = await asyncio.to_thread(_run)
            self._wrapper = SyncCursorWrapper(cursor)
        return self._wrapper

    def __await__(self):
        return self._execute().__await__()

    async def __aenter__(self):
        return await self._execute()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class SyncToAsyncPostgresWrapper:
    """مغلف تزامني متوافق لـ psycopg2 ويعمل مع asyncio لسيرفرات Vercel."""

    def __init__(self, conn):
        self.conn = conn

    def execute(self, sql: str, params: tuple = ()):
        return AsyncQuery(self.conn, sql, params)

    async def commit(self):
        await asyncio.to_thread(self.conn.commit)

    async def close(self):
        await asyncio.to_thread(self.conn.close)


class SyncCursorWrapper:
    def __init__(self, cursor):
        self.cursor = cursor

    @property
    def rowcount(self):
        return getattr(self.cursor, 'rowcount', -1)

    @property
    def lastrowid(self):
        try:
            row = self.cursor.fetchone()
            if row:
                return row.get('id', row[0] if isinstance(row, (tuple, list)) else None)
        except Exception:
            pass
        return None

    async def fetchone(self):
        def _fetch():
            try:
                return self.cursor.fetchone()
            except Exception:
                return None
        return await asyncio.to_thread(_fetch)

    async def fetchall(self):
        def _fetch_all():
            try:
                return self.cursor.fetchall()
            except Exception:
                return []
        return await asyncio.to_thread(_fetch_all)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


async def init_db():
    """إعادة تهيئة وفحص جداول قاعدة البيانات عند التشغيل الأول."""
    logger.info("جاري فحص وإعداد قاعدة البيانات...")

    if IS_POSTGRES:
        db_url = get_formatted_db_url(DATABASE_URL)
        try:
            def _init_pg():
                conn = psycopg2.connect(db_url)
                conn.autocommit = False
                cur = conn.cursor()

                # 1. إنشاء المراحل والصفوف أولاً
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS stages (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL UNIQUE,
                        sort_order INTEGER DEFAULT 0
                    );
                    CREATE TABLE IF NOT EXISTS classes (
                        id SERIAL PRIMARY KEY,
                        stage_id INTEGER NOT NULL REFERENCES stages(id) ON DELETE CASCADE,
                        name VARCHAR(255) NOT NULL,
                        sort_order INTEGER DEFAULT 0
                    );
                """)
                conn.commit()

                # إضافة الأعمدة الجديدة وسواقتها إن لم تكن موجودة
                try:
                    cur.execute("ALTER TABLE stages ADD COLUMN IF NOT EXISTS sort_order INTEGER DEFAULT 0;")
                    cur.execute("ALTER TABLE classes ADD COLUMN IF NOT EXISTS sort_order INTEGER DEFAULT 0;")
                    cur.execute("UPDATE stages SET sort_order = id WHERE sort_order = 0 OR sort_order IS NULL;")
                    cur.execute("UPDATE classes SET sort_order = id WHERE sort_order = 0 OR sort_order IS NULL;")
                    conn.commit()
                except Exception:
                    conn.rollback()

                # إضافة قيد التفرّد إن لم يكن موجوداً
                try:
                    cur.execute("ALTER TABLE classes ADD CONSTRAINT unique_stage_class UNIQUE (stage_id, name);")
                    conn.commit()
                except Exception:
                    conn.rollback()

                # 2. إزالة جدول subjects والعمود المرتبط به فوراً
                try:
                    cur.execute("DROP TABLE IF EXISTS subjects CASCADE;")
                    cur.execute("ALTER TABLE IF EXISTS books DROP COLUMN IF EXISTS subject_id;")
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    logger.error(f"خطأ أثناء حذف subjects: {e}")

                # 3. إنشاء جدول الكتب والمستخدمين
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS books (
                        id SERIAL PRIMARY KEY,
                        class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
                        title VARCHAR(255) NOT NULL,
                        description TEXT,
                        telegram_file_id TEXT NOT NULL,
                        downloads_count INTEGER DEFAULT 0,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        telegram_id BIGINT UNIQUE NOT NULL,
                        full_name TEXT,
                        join_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                conn.commit()

                try:
                    cur.execute("ALTER TABLE books ADD COLUMN IF NOT EXISTS downloads_count INTEGER DEFAULT 0;")
                    conn.commit()
                except Exception:
                    conn.rollback()

                # 4. إدراج المراحل والصفوف الافتراضية بأمان
                try:
                    cur.execute("INSERT INTO stages (id, name, sort_order) VALUES (1, 'المرحلة الابتدائية', 1), (2, 'المرحلة المتوسطة', 2), (3, 'المرحلة الإعدادية', 3) ON CONFLICT (id) DO NOTHING;")
                    cur.execute("""
                        INSERT INTO classes (stage_id, name, sort_order) VALUES 
                            (1, 'الأول الابتدائي', 1), (1, 'الثاني الابتدائي', 2), (1, 'الثالث الابتدائي', 3), (1, 'الرابع الابتدائي', 4), (1, 'الخامس الابتدائي', 5), (1, 'السادس الابتدائي', 6),
                            (2, 'الأول المتوسط', 1), (2, 'الثاني المتوسط', 2), (2, 'الثالث المتوسط', 3),
                            (3, 'الرابع العلمي', 1), (3, 'الرابع الأدبي', 2), (3, 'الخامس العلمي', 3), (3, 'الخامس الأدبي', 4), (3, 'السادس العلمي', 5), (3, 'السادس الأدبي', 6)
                        ON CONFLICT DO NOTHING;
                    """)
                    conn.commit()
                except Exception:
                    conn.rollback()

                conn.close()

            await asyncio.to_thread(_init_pg)
        except Exception as e:
            logger.error(f"خطأ أثناء الاتصال بـ Supabase PostgreSQL: {e}")
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("PRAGMA foreign_keys = ON;")
            await db.execute("""
                CREATE TABLE IF NOT EXISTS stages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    sort_order INTEGER DEFAULT 0
                );
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS classes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stage_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    sort_order INTEGER DEFAULT 0,
                    FOREIGN KEY (stage_id) REFERENCES stages (id) ON DELETE CASCADE,
                    UNIQUE (stage_id, name)
                );
            """)
            await db.execute("DROP TABLE IF EXISTS subjects;")
            await db.execute("""
                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    class_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    telegram_file_id TEXT NOT NULL,
                    downloads_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (class_id) REFERENCES classes (id) ON DELETE CASCADE
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

            # إضافة الأعمدة الجديدة لـ SQLite إن لم تكن موجودة
            for col_sql in [
                "ALTER TABLE stages ADD COLUMN sort_order INTEGER DEFAULT 0;",
                "ALTER TABLE classes ADD COLUMN sort_order INTEGER DEFAULT 0;",
                "ALTER TABLE books ADD COLUMN downloads_count INTEGER DEFAULT 0;"
            ]:
                try:
                    await db.execute(col_sql)
                    await db.commit()
                except Exception:
                    pass

            await db.execute("UPDATE stages SET sort_order = id WHERE sort_order = 0 OR sort_order IS NULL;")
            await db.execute("UPDATE classes SET sort_order = id WHERE sort_order = 0 OR sort_order IS NULL;")
            await db.commit()

    logger.info("تم إعداد قاعدة البيانات بنجاح.")


@asynccontextmanager
async def get_db_connection():
    """مزود الاتصال بقاعدة البيانات لـ Vercel عبر psycopg2-binary المضمونة."""
    if IS_POSTGRES:
        db_url = get_formatted_db_url(DATABASE_URL)
        conn = await asyncio.to_thread(psycopg2.connect, db_url)
        wrapper = SyncToAsyncPostgresWrapper(conn)
        try:
            yield wrapper
        finally:
            await asyncio.to_thread(conn.close)
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("PRAGMA foreign_keys = ON;")
            yield db
