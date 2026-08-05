import logging
import os
import sys
from config import LOG_LEVEL

def setup_logger():
    """إعداد نظام تسجيل الأحداث والأخطاء (Logging)."""
    # ضبط ترميز موجه الأوامر لدعم اللغات والأيقونات على ويندوز
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    handler_stdout = logging.StreamHandler(sys.stdout)

    handlers = [handler_stdout]
    # إضافة ملف bot.log فقط إذا كان النظام يدعم الكتابة (ليس Vercel)
    if not os.getenv("VERCEL"):
        try:
            handler_file = logging.FileHandler("bot.log", encoding="utf-8")
            handlers.append(handler_file)
        except OSError:
            pass

    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers
    )
    
    # تقليل الضجيج من مكتبات httpx و telegram
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.INFO)
    
    return logging.getLogger("SchoolBooksBot")

logger = setup_logger()
