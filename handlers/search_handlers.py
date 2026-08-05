from telegram import Update
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from database import repository
from keyboards import inline
from utils.logger import logger

async def initiate_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """بدء عملية البحث وطلب كلمة البحث من المستخدم."""
    query = update.callback_query
    prompt = "🔍 <b>أرسل اسم الكتاب أو المادة للبحث مباشرة:</b>"
    if query:
        await query.answer()
        await query.edit_message_text(
            prompt,
            parse_mode="HTML",
            reply_markup=inline.get_search_results_keyboard([])
        )
    else:
        await update.message.reply_text(
            prompt,
            parse_mode="HTML",
            reply_markup=inline.get_search_results_keyboard([])
        )

async def process_search_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة النص المرسل من المستخدم والبحث في قاعدة البيانات مباشرة."""
    if context.user_data.get('admin_action'):
        return

    text = update.message.text.strip() if update.message and update.message.text else ""
    if text.startswith("/search"):
        text = text.replace("/search", "", 1).strip()
    
    if not text:
        await update.message.reply_text("⚠️ يرجى إدخال اسم الكتاب أو المادة للبحث.")
        return

    logger.info(f"المستخدم {update.effective_user.id} يدير بحثاً عن: '{text}'")
    results = await repository.search_books(text)

    if not results:
        await update.message.reply_text(
            f"❌ لم يتم العثور على نتائج تطابق: <b>{text}</b>\n\nحاول البحث باسم آخر أو اختر من المراحل الدراسية.",
            parse_mode="HTML",
            reply_markup=inline.get_search_results_keyboard([])
        )
        return

    result_text = f"🔎 <b>نتائج البحث عن:</b> <code>{text}</code>\nتم العثور على {len(results)} نتيجة:"
    await update.message.reply_text(
        result_text,
        parse_mode="HTML",
        reply_markup=inline.get_search_results_keyboard(results)
    )

def register_search_handlers(app):
    app.add_handler(CallbackQueryHandler(initiate_search, pattern="^user_search$"))
    app.add_handler(CommandHandler("search", process_search_query))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_search_query))
