import sys
import os
import asyncio

# ضمان إضافة مسار المشروع الحالي لمسارات بايثون لمنع ModuleNotFoundError
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telegram.ext import ApplicationBuilder, Defaults
from telegram.constants import ParseMode
from telegram.request import HTTPXRequest

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

    # زيادة مبيعات المهلة (Timeouts) لضمان عدم الاتقطاع على الشبكات الضعيفة
    request = HTTPXRequest(
        connect_timeout=30.0,
        read_timeout=30.0,
        write_timeout=30.0,
        pool_timeout=30.0
    )

    defaults = Defaults(parse_mode=ParseMode.HTML)

    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .request(request)
        .defaults(defaults)
        .post_init(post_init)
        .build()
    )

    application.add_handler(get_search_handler())
    register_admin_handlers(application)
    register_user_handlers(application)

    logger.info("البوت يعمل الآن بصورة ممتازة. (Press Ctrl+C to stop)")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
