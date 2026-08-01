from telegram import Update
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
)
from database import repository
from keyboards import inline
from utils.logger import logger

# حالة المحادثة الخاصة بالبحث
WAITING_SEARCH_QUERY = 1

async def initiate_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """بدء عملية البحث وطلب كلمة البحث من المستخدم."""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "🔍 **البحث عن كتاب**\n\nأرسل اسم الكتاب أو المادة أو الكلمة المفتاحية التي تبحث عنها:",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "🔍 **البحث عن كتاب**\n\nأرسل اسم الكتاب أو المادة أو الكلمة المفتاحية التي تبحث عنها:",
            parse_mode="Markdown"
        )
    return WAITING_SEARCH_QUERY

async def process_search_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة النص المرسل من المستخدم والبحث في قاعدة البيانات."""
    search_term = update.message.text.strip()
    if not search_term:
        await update.message.reply_text("⚠️ يرجى إدخال نص صحيح للبحث.")
        return WAITING_SEARCH_QUERY

    logger.info(f"المستخدم {update.effective_user.id} يدير بحثاً عن: '{search_term}'")
    results = await repository.search_books(search_term)

    if not results:
        await update.message.reply_text(
            f"❌ لم يتم العثور على نتائج تطابق: <b>{search_term}</b>\n\nحاول البحث باسم آخر أو العودة للقائمة الرئيسية.",
            parse_mode="HTML",
            reply_markup=inline.get_search_results_keyboard([])
        )
        return ConversationHandler.END

    result_text = f"🔎 **نتائج البحث عن:** `{search_term}`\nتم العثور على {len(results)} نتيجة:"
    await update.message.reply_text(
        result_text,
        parse_mode="Markdown",
        reply_markup=inline.get_search_results_keyboard(results)
    )
    return ConversationHandler.END

async def cancel_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """إلغاء البحث."""
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("تم إلغاء البحث.")
    elif update.message:
        await update.message.reply_text("تم إلغاء البحث.")
    return ConversationHandler.END

def get_search_handler() -> ConversationHandler:
    """إرجاع موجه حالة البحث (ConversationHandler)."""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(initiate_search, pattern="^user_search$"),
            CommandHandler("search", initiate_search)
        ],
        states={
            WAITING_SEARCH_QUERY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_search_query)
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_search),
            CallbackQueryHandler(cancel_search, pattern="^main_menu$")
        ],
        allow_reentry=True,
        per_message=False
    )
