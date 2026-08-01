import asyncio
import sys
from telegram.ext import ApplicationBuilder, Defaults
from telegram.constants import ParseMode

from config import BOT_TOKEN
from utils.logger import logger
from database.connection import init_db
from handlers.user_handlers import register_user_handlers
from handlers.search_handlers import get_search_handler
from handlers.admin_handlers import register_admin_handlers

async def post_init(application):
    """إعادة تهيئة قاعدة البيانات عند بدء التشغيل."""
    await init_db()
    logger.info("تم البدء والاستعداد لاستقبال الطلبات.")

def main():
    """الدالة الرئيسية لتشغيل البوت."""
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("لم يتم تعيين BOT_TOKEN! يرجى تعيين التوكن الصحيح في config.py أو في متغيرات البيئة.")
        sys.exit(1)

    logger.info("جاري إعداد وتشغيل بوت المناهج والكتب الدراسية...")

    # تعيين افتراضيات البوت (مثل نمط التنسيق HTML)
    defaults = Defaults(parse_mode=ParseMode.HTML)

    # إنشاء تطبيق البوت باستخدام ApplicationBuilder
    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .defaults(defaults)
        .post_init(post_init)
        .build()
    )

    # 1. تسجيل موجه البحث أولاً (ConversationHandler)
    application.add_handler(get_search_handler())

    # 2. تسجيل موجهات لوحة تحكم المشرفين
    register_admin_handlers(application)

    # 3. تسجيل موجهات المستخدم والتصفح العادي
    register_user_handlers(application)

    # بدء الاستماع للرسائل (Polling)
    logger.info("البوت يعمل الآن بصورة ممتازة. (Press Ctrl+C to stop)")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
