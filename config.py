import os
from typing import List

# توكن البوت من BotFather
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "8909138016:AAFFkhoSamtrT1L6oRCNweuM8uTTnWZdY8Q").strip().strip('"').strip("'")

# قائمة معرفات المشرفين (Telegram User IDs)
raw_admins = os.getenv("ADMIN_IDS", "7245409261").strip().strip('"').strip("'")
ADMIN_IDS: List[int] = [
    int(aid.strip())
    for aid in raw_admins.split(",")
    if aid.strip().isdigit()
]
# ضمان إدراج حسابك دائماً للمشرفين حتى لو تغير متغير البيئة
if 7245409261 not in ADMIN_IDS:
    ADMIN_IDS.append(7245409261)

# مسار وقاعدة البيانات (تحويل تلقائي لـ IPv4 Pooler السريع والموثوق)
DB_PATH: str = os.getenv("DB_PATH", "school_books.db")

raw_db_url = os.getenv("DATABASE_URL", "").strip().strip('"').strip("'")
if not raw_db_url or "db.uefbgnyzqldhscqiqsuz.supabase.co" in raw_db_url:
    DATABASE_URL: str = "postgresql://postgres.uefbgnyzqldhscqiqsuz:7raawaWAKQSlYwyc@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"
else:
    DATABASE_URL: str = raw_db_url

# رابط الـ Webhook الخاص بـ Vercel
WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "https://school-books-bot-jrt8.vercel.app").strip().strip('"').strip("'")

# مستوى التسجيل Logging
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
