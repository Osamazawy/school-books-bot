import logging
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
    handler_file = logging.FileHandler("bot.log", encoding="utf-8")

    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[handler_stdout, handler_file]
    )
    
    # تقليل الضجيج من مكتبات httpx و telegram
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.INFO)
    
    return logging.getLogger("SchoolBooksBot")

logger = setup_logger()
