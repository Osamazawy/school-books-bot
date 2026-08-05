-- ============================================================
-- قاعدة بيانات بوت الكتب والمناهج الدراسية (Supabase PostgreSQL)
-- يمكنك نسخ هذا الكود ولصقه في SQL Editor في موقع Supabase
-- ============================================================

-- 1. جدول المراحل الدراسية (Stages)
CREATE TABLE IF NOT EXISTS stages (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE
);

-- 2. جدول الصفوف الدراسية (Classes)
CREATE TABLE IF NOT EXISTS classes (
    id SERIAL PRIMARY KEY,
    stage_id INTEGER NOT NULL REFERENCES stages(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    CONSTRAINT unique_stage_class UNIQUE (stage_id, name)
);

-- 3. جدول الكتب (Books)
CREATE TABLE IF NOT EXISTS books (
    id SERIAL PRIMARY KEY,
    class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    telegram_file_id TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. جدول المستخدمين (Users)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    full_name TEXT,
    join_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- إنشاء الفهارس لسرعة البحث في آلاف السجلات
CREATE INDEX IF NOT EXISTS idx_books_class_id ON books(class_id);
CREATE INDEX IF NOT EXISTS idx_classes_stage_id ON classes(stage_id);
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
