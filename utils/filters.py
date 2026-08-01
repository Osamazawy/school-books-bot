from telegram import Update
from telegram.ext import filters
from config import ADMIN_IDS
from utils.logger import logger

class AdminFilter(filters.UpdateFilter):
    """فلتر للتحقق مما إذا كان المستخدم مشرفاً (Admin)."""
    def filter(self, update: Update) -> bool:
        user = update.effective_user
        if not user:
            return False
        is_admin = user.id in ADMIN_IDS
        if not is_admin:
            logger.warning(f"محاولة وصول غير مصرح بها من المستخدم: {user.id} ({user.full_name})")
        return is_admin

# تصدير كائن الفلتر لاستخدامه مباشرة في الـ Handlers
IS_ADMIN = AdminFilter()
