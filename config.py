import os
import re
from typing import List

# توكن البوت من BotFather (يمكن تغييره هنا أو تعيينه كمتغير بيئة BOT_TOKEN)
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "8909138016:AAFFkhoSamtrT1L6oRCNweuM8uTTnWZdY8Q").strip().strip('"').strip("'")

# قائمة معرفات المشرفين (Telegram User IDs)
raw_admin_env = os.getenv("ADMIN_IDS", "7245409261")
parsed_ids = [int(num) for num in re.findall(r"\d+", raw_admin_env)]
if 7245409261 not in parsed_ids:
    parsed_ids.append(7245409261)
ADMIN_IDS: List[int] = parsed_ids

# مسار أو رابط قاعدة البيانات (SQLite كبديل محلي، أو DATABASE_URL لـ Supabase PostgreSQL)
DB_PATH: str = os.getenv("DB_PATH", "school_books.db")
DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres.uefbgnyzqldhscqiqsuz:7raawaWAKQSlYwyc@aws-0-eu-central-1.pooler.supabase.com:5432/postgres")

# رابط الـ Webhook الخاص بـ Vercel
WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")

# مستوى التسجيل Logging
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
