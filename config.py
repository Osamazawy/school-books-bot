import os
from typing import List

# توكن البوت من BotFather (يمكن تغييره هنا أو تعيينه كمتغير بيئة BOT_TOKEN)
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "8909138016:AAFFkhoSamtrT1L6oRCNweuM8uTTnWZdY8Q")

# قائمة معرفات المشرفين (Telegram User IDs)
# يمكن إضافة أكثر من معرف يفصل بينها فاصلة في متغير البيئة أو في القائمة أدناه مباشرة
ADMIN_IDS: List[int] = [
    int(admin_id.strip())
    for admin_id in os.getenv("ADMIN_IDS", "7245409261").split(",")
    if admin_id.strip().isdigit()
]

# مسار أو رابط قاعدة البيانات (SQLite كبديل محلي، أو DATABASE_URL لـ Supabase PostgreSQL)
DB_PATH: str = os.getenv("DB_PATH", "school_books.db")
DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres.uefbgnyzqldhscqiqsuz:7raawaWAKQSlYwyc@aws-0-eu-central-1.pooler.supabase.com:6543/postgres")

# رابط الـ Webhook الخاص بـ Vercel
WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")

# مستوى التسجيل Logging
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

