from contextlib import asynccontextmanager
import aiosqlite
from config import DB_PATH
from utils.logger import logger

async def init_db():
    """إنشاء جداول قاعدة البيانات وفق أحدث معاير 2026."""
    logger.info("جاري فحص وإعداد قاعدة البيانات...")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        
        # 1. جدول المراحل (Stages)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS stages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );
        """)
        
        # 2. جدول الصفوف (Classes)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS classes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stage_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                FOREIGN KEY (stage_id) REFERENCES stages (id) ON DELETE CASCADE
            );
        """)
        
        # 3. جدول المواد (Subjects - اختياري)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                class_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                FOREIGN KEY (class_id) REFERENCES classes (id) ON DELETE CASCADE
            );
        """)
        
        # 4. جدول الكتب (Books)
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
        
        # 5. جدول المستخدمين (Users)
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
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON;")
        yield db
