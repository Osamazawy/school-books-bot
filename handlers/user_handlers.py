from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from config import ADMIN_IDS
from database import repository
from keyboards import inline
from utils.logger import logger

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return

    is_admin = user.id in ADMIN_IDS
    welcome_text = (
        f"مرحباً بك يا <b>{user.first_name}</b> في بوت المناهج والكتب الدراسية 📚✨\n\n"
        "اختر <b>المراحل الدراسية</b> للتنقل بين الصفوف وتحميل المناهج بصيغة PDF فوراً."
    )
    
    if update.message:
        await update.message.reply_text(
            welcome_text,
            parse_mode="HTML",
            reply_markup=inline.get_main_menu_keyboard(is_admin=is_admin)
        )
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            welcome_text,
            parse_mode="HTML",
            reply_markup=inline.get_main_menu_keyboard(is_admin=is_admin)
        )

    try:
        await repository.add_or_update_user(telegram_id=user.id, full_name=user.full_name or "بدون اسم")
    except Exception as e:
        logger.error(f"خطأ غير مؤثر أثناء حفظ المستخدم {user.id}: {e}")

async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    is_admin = user.id in ADMIN_IDS if user else False
    
    await query.edit_message_text(
        "📚 <b>القائمة الرئيسية</b>\nيرجى اختيار القسم المطلوب من الأزرار أدناه:",
        parse_mode="HTML",
        reply_markup=inline.get_main_menu_keyboard(is_admin=is_admin)
    )

async def list_stages_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    stages = await repository.get_all_stages()
    if not stages:
        user = update.effective_user
        is_admin = user.id in ADMIN_IDS if user else False
        await query.edit_message_text(
            "⚠️ لا توجد مراحل دراسية مضافة حالياً في قاعدة البيانات.",
            reply_markup=inline.get_main_menu_keyboard(is_admin=is_admin)
        )
        return

    await query.edit_message_text(
        "🏛️ <b>المراحل الدراسية</b>\nاختر المرحلة الدراسية لعرض صفوفها المتاحة:",
        parse_mode="HTML",
        reply_markup=inline.get_stages_keyboard(stages)
    )

async def run_minimal_countdown(query, final_text: str, reply_markup=None) -> None:
    """عرض عداد تنازلي بالأرقام فقط (3️⃣ 2️⃣ 1️⃣) بسلاسة فائقة قبل فتح القسم."""
    for num in ["3️⃣", "2️⃣", "1️⃣"]:
        try:
            await query.edit_message_text(f"⏳ <b>{num}</b>", parse_mode="HTML")
            await asyncio.sleep(0.7)
        except Exception:
            break
    await query.edit_message_text(final_text, parse_mode="HTML", reply_markup=reply_markup)

async def list_classes_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    stage_id = int(query.data.split("_")[-1])
    stage = await repository.get_stage_by_id(stage_id)
    classes = await repository.get_classes_by_stage(stage_id)
    
    stage_name = stage['name'] if stage else "المرحلة"
    
    if not classes:
        await query.edit_message_text(
            f"⚠️ لا توجد صفوف مضافة لمرحلة <b>{stage_name}</b> حتى الآن.",
            parse_mode="HTML",
            reply_markup=inline.get_classes_keyboard([], stage_id)
        )
        return

    final_text = f"🎓 <b>صفوف مرحلة: {stage_name}</b>\nاختر الصف الدراسي لعرض كتبه ومناهجه:"
    await run_minimal_countdown(query, final_text, inline.get_classes_keyboard(classes, stage_id))

async def list_books_for_class_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض الكتب التابعة للصف مباشرة عند الاختيار مع عداد تنازلي بالأرقام."""
    query = update.callback_query
    await query.answer()
    
    class_id = int(query.data.split("_")[-1])
    cls = await repository.get_class_by_id(class_id)
    books = await repository.get_books_by_class(class_id)
    
    class_name = cls['name'] if cls else "الصف"
    stage_id = cls['stage_id'] if cls else 1

    if not books:
        await query.edit_message_text(
            f"⚠️ لا توجد كتب مضافة لـ <b>{class_name}</b> حتى الآن.",
            parse_mode="HTML",
            reply_markup=inline.get_books_keyboard([], stage_id)
        )
        return

    final_text = f"📘 <b>كتب ومناهج: {class_name}</b>\nاختر الكتاب المطلوب لتحميله مباشرة:"
    await run_minimal_countdown(query, final_text, inline.get_books_keyboard(books, stage_id))

async def view_book_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    book_id = int(query.data.split("_")[-1])
    book = await repository.get_book_by_id(book_id)
    
    if not book:
        await query.edit_message_text("❌ لم يتم العثور على هذا الكتاب.")
        return

    caption = (
        f"📘 <b>{book['title']}</b>\n\n"
        f"🏛️ <b>المرحلة:</b> {book['stage_name']}\n"
        f"🎓 <b>الصف:</b> {book['class_name']}\n\n"
        "اضغط على الزر أدناه لإرسال ملف الـ PDF فوراً:"
    )
    
    await run_minimal_countdown(query, caption, inline.get_book_details_keyboard(book_id, book['class_id']))

async def download_book_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer("جاري إرسال الملف... ⏳")
    
    book_id = int(query.data.split("_")[-1])
    book = await repository.get_book_by_id(book_id)
    
    if not book:
        await query.message.reply_text("❌ خطأ: هذا الكتاب غير موجود.")
        return

    caption = (
        f"📚 <b>{book['title']}</b>\n"
        f"🏛️ {book['stage_name']} - 🎓 {book['class_name']}"
    )

    try:
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=book['telegram_file_id'],
            caption=caption,
            parse_mode="HTML"
        )
        logger.info(f"تم إرسال الكتاب {book['id']} ({book['title']}) إلى {query.from_user.id}")
    except Exception as e:
        logger.error(f"خطأ إرسال الملف: {e}")
        await query.message.reply_text("❌ تعذر إرسال الملف.")

def register_user_handlers(app):
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CallbackQueryHandler(main_menu_handler, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(list_stages_handler, pattern="^(user_stages|user_grades)$"))
    app.add_handler(CallbackQueryHandler(list_classes_handler, pattern="^user_stage_\\d+$"))
    app.add_handler(CallbackQueryHandler(list_books_for_class_handler, pattern="^user_class_\\d+$"))
    app.add_handler(CallbackQueryHandler(view_book_handler, pattern="^user_book_\\d+$"))
    app.add_handler(CallbackQueryHandler(download_book_handler, pattern="^dl_book_\\d+$"))
