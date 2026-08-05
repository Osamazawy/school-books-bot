import asyncio
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from config import ADMIN_IDS
from utils.filters import IS_ADMIN
from database import repository
from keyboards import inline
from utils.logger import logger


async def check_admin(update: Update) -> bool:
    user = update.effective_user
    is_admin = bool(user and user.id in ADMIN_IDS)
    if not is_admin:
        if update.callback_query:
            try:
                await update.callback_query.answer("❌ عذراً، هذه العملية مخصصة للمشرفين فقط.", show_alert=True)
            except Exception:
                pass
        elif update.message:
            await update.message.reply_text("❌ عذراً، هذا الأمر مخصص للمشرفين فقط.")
    return is_admin


async def safe_edit_message(query, text: str, reply_markup=None, parse_mode: str = "HTML"):
    try:
        await query.edit_message_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
    except Exception as e:
        if "not modified" in str(e).lower():
            pass
        else:
            logger.error(f"خطأ أثناء تعديل الرسالة: {e}")


# ==================== لوحة التحكم الرئيسية والإحصائيات ====================

async def admin_panel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin(update):
        return

    context.user_data.pop('admin_action', None)
    text = "⚙️ <b>لوحة تحكم المشرفين المحترفة</b>\nاختر القسم المطلوب من الأزرار المركزية أدناه:"
    if update.callback_query:
        try:
            await update.callback_query.answer()
        except Exception:
            pass
        await safe_edit_message(update.callback_query, text, reply_markup=inline.get_admin_main_keyboard())
    elif update.message:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=inline.get_admin_main_keyboard())


async def admin_stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin(update):
        return
        
    query = update.callback_query
    if query:
        try:
            await query.answer()
        except Exception:
            pass
    
    try:
        users_cnt = await repository.get_users_count()
        stages_cnt = await repository.get_stages_count()
        classes_cnt = await repository.get_classes_count()
        books_cnt = await repository.get_books_count()
        breakdown = await repository.get_stage_breakdown()
        
        breakdown_text = ""
        for item in breakdown:
            breakdown_text += f"   • {item['stage_name']}: {item['books_cnt']} كتاب\n"

        stats_text = (
            "📊 <b>الإحصائيات الشاملة للنظام</b>\n\n"
            f"👥 <b>إجمالي المشتركين:</b> {users_cnt}\n"
            f"🏛️ <b>عدد المراحل:</b> {stages_cnt}\n"
            f"🎓 <b>عدد الصفوف:</b> {classes_cnt}\n"
            f"📚 <b>إجمالي الكتب المرفوعة:</b> {books_cnt}\n\n"
            f"📋 <b>توزيع الكتب حسب المراحل:</b>\n{breakdown_text if breakdown_text else '   لا توجد كتب حالياً.'}"
        )
    except Exception as e:
        logger.error(f"خطأ أثناء جلب الإحصائيات: {e}")
        stats_text = f"❌ <b>حدث خطأ أثناء جلب الإحصائيات:</b>\n<code>{e}</code>"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 لوحة التحكم", callback_data="admin_panel")]
    ])
    await safe_edit_message(query, stats_text, reply_markup=keyboard)


# ==================== الإذاعة والإعلانات للطلاب (Broadcast) ====================

async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin(update):
        return

    query = update.callback_query
    if query:
        try:
            await query.answer()
        except Exception:
            pass

    context.user_data['admin_action'] = 'broadcast'

    try:
        users_cnt = await repository.get_users_count()
    except Exception:
        users_cnt = 0

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 لوحة التحكم", callback_data="admin_panel")]])
    
    text = (
        f"📢 <b>إذاعة / إعلان جديد للطلاب (عدد المشتركين: {users_cnt})</b>\n\n"
        "أرسل أو وِجّه الرسالة التي ترغب بنشرها لجميع المشتركين الآن مباشرة."
    )
    if query:
        await safe_edit_message(query, text, reply_markup=keyboard)
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)


async def send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin(update):
        return

    try:
        user_ids = await repository.get_all_user_ids()
    except Exception as e:
        logger.error(f"خطأ الإذاعة: {e}")
        await update.message.reply_text(f"❌ تعذر استرجاع المستخدمين للإذاعة: {e}")
        return

    total = len(user_ids)
    status_msg = await update.message.reply_text(f"⏳ جاري بدء الإذاعة لـ {total} مستخدم...")
    success = 0
    failed = 0
    
    for uid in user_ids:
        try:
            await update.message.copy(chat_id=uid)
            success += 1
            await asyncio.sleep(0.04)
        except Exception:
            failed += 1

    await status_msg.edit_text(
        f"🎉 <b>تمت الإذاعة بنجاح!</b>\n\n"
        f"✅ تم الإرسال إلى: <b>{success}</b> مستخدم\n"
        f"❌ تعذر الإرسال إلى: <b>{failed}</b> مستخدم",
        parse_mode="HTML",
        reply_markup=inline.get_admin_main_keyboard()
    )


# ==================== 1. المستوى الأول: إدارة المراحل (Stage Level) ====================

async def admin_manage_curriculum(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin(update):
        return

    query = update.callback_query
    if query:
        try:
            await query.answer()
        except Exception:
            pass

    try:
        stages = await repository.get_all_stages()
        text = "🏛️ <b>إدارة المراحل والصفوف والمناهج</b>\nاختر المرحلة الدراسية للتنقل المباشر:"
        reply_markup = inline.get_admin_stages_list_keyboard(stages)
    except Exception as e:
        logger.error(f"خطأ جلب المراحل: {e}")
        text = f"❌ <b>حدث خطأ أثناء جلب المراحل:</b>\n<code>{e}</code>"
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 لوحة التحكم", callback_data="admin_panel")]])

    await safe_edit_message(query, text, reply_markup=reply_markup)


async def start_add_stage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin(update):
        return
    query = update.callback_query
    if query:
        try:
            await query.answer()
        except Exception:
            pass
    context.user_data['admin_action'] = 'add_stage'
    await safe_edit_message(query, "❇️ <b>إضافة مرحلة جديدة</b>\nأرسل اسم المرحلة الجديدة في رسالة (مثال: المرحلة الثانوية):")


async def start_rename_stage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin(update):
        return
    query = update.callback_query
    if query:
        try:
            await query.answer()
        except Exception:
            pass
    stage_id = int(query.data.split("_")[-1])
    context.user_data['admin_action'] = f'rename_stage_{stage_id}'
    stage = await repository.get_stage_by_id(stage_id)
    await safe_edit_message(query, f"✏️ <b>تعديل اسم المرحلة</b>\nالاسم الحالي: <b>{stage['name'] if stage else ''}</b>\n\nأرسل الاسم الجديد:")


async def confirm_delete_stage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin(update):
        return
    query = update.callback_query
    if query:
        try:
            await query.answer()
        except Exception:
            pass
    stage_id = int(query.data.split("_")[-1])
    stage = await repository.get_stage_by_id(stage_id)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚠️ نعم، تأكيد الحذف النهائي", callback_data=f"adm_del_stg_exec_{stage_id}")],
        [InlineKeyboardButton("❌ إلغاء", callback_data=f"adm_view_cls_{stage_id}")]
    ])
    await safe_edit_message(query, f"⚠️ <b>هل أنت تأكد من حذف مرحلة: {stage['name'] if stage else ''}؟</b>\nسيتم حذف كافة الصفوف والكتب التابعة لها أيضاً!", reply_markup=keyboard)


async def exec_delete_stage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin(update):
        return
    query = update.callback_query
    if query:
        try:
            await query.answer()
        except Exception:
            pass
    stage_id = int(query.data.split("_")[-1])
    await repository.delete_stage(stage_id)
    await safe_edit_message(query, "✅ تم حذف المرحلة وكافة محتوياتها بنجاح.", reply_markup=inline.get_admin_main_keyboard())


# ==================== 2. المستوى الثاني: إدارة الصفوف والكتب المباشرة ====================

async def view_classes_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin(update):
        return
    query = update.callback_query
    if query:
        try:
            await query.answer()
        except Exception:
            pass
    stage_id = int(query.data.split("_")[-1])
    stage = await repository.get_stage_by_id(stage_id)
    classes = await repository.get_classes_by_stage(stage_id)
    await safe_edit_message(query, f"🎓 <b>صفوف مرحلة: {stage['name'] if stage else ''}</b>\nاختر الصف لتصفح وإدارة كتبه مباشرة:", reply_markup=inline.get_admin_classes_list_keyboard(classes, stage_id))


async def start_add_class_batch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin(update):
        return
    query = update.callback_query
    if query:
        try:
            await query.answer()
        except Exception:
            pass
    stage_id = int(query.data.split("_")[-1])
    context.user_data['admin_action'] = f'add_class_{stage_id}'
    stage = await repository.get_stage_by_id(stage_id)
    await safe_edit_message(query, f"❇️ <b>إضافة صف جديد لمرحلة: {stage['name'] if stage else ''}</b>\nأرسل اسم الصف الجديد في رسالة:")


async def start_rename_class(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin(update):
        return
    query = update.callback_query
    if query:
        try:
            await query.answer()
        except Exception:
            pass
    class_id = int(query.data.split("_")[-1])
    context.user_data['admin_action'] = f'rename_class_{class_id}'
    cls = await repository.get_class_by_id(class_id)
    await safe_edit_message(query, f"✏️ <b>تعديل اسم الصف</b>\nالاسم الحالي: <b>{cls['name'] if cls else ''}</b>\n\nأرسل الاسم الجديد:")


async def confirm_delete_class(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin(update):
        return
    query = update.callback_query
    if query:
        try:
            await query.answer()
        except Exception:
            pass
    class_id = int(query.data.split("_")[-1])
    cls = await repository.get_class_by_id(class_id)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚠️ نعم، تأكيد الحذف النهائي", callback_data=f"adm_del_cls_exec_{class_id}")],
        [InlineKeyboardButton("❌ إلغاء", callback_data=f"adm_view_bks_{class_id}")]
    ])
    await safe_edit_message(query, f"⚠️ <b>هل أنت تأكد من حذف صف: {cls['name'] if cls else ''}؟</b>\nسيتم حذف كافة الكتب التابعة له أيضاً!", reply_markup=keyboard)


async def exec_delete_class(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin(update):
        return
    query = update.callback_query
    if query:
        try:
            await query.answer()
        except Exception:
            pass
    class_id = int(query.data.split("_")[-1])
    cls = await repository.get_class_by_id(class_id)
    stage_id = cls['stage_id'] if cls else 1
    await repository.delete_class(class_id)
    await safe_edit_message(query, "✅ تم حذف الصف بنجاح.", reply_markup=inline.get_admin_classes_list_keyboard([], stage_id))


# ==================== 3. المستوى الثالث: إدارة الكتب المرفوعة ====================

async def start_upload_books(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin(update):
        return
    query = update.callback_query
    if query:
        try:
            await query.answer()
        except Exception:
            pass
    class_id = int(query.data.split("_")[-1])
    context.user_data['admin_action'] = f'upload_book_{class_id}'
    cls = await repository.get_class_by_id(class_id)
    await safe_edit_message(query, f"🚀 <b>رفع كتب لصف: {cls['name'] if cls else ''}</b>\n\nأرسل ملف الكرات أو الكتب بصيغة PDF فوراً في محادثة مباشرة وسأقوم بحفظها وتنسيق اسمها تلقائياً.")


async def view_class_books(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin(update):
        return
    query = update.callback_query
    if query:
        try:
            await query.answer()
        except Exception:
            pass
    class_id = int(query.data.split("_")[-1])
    cls = await repository.get_class_by_id(class_id)
    books = await repository.get_books_by_class(class_id)
    stage_id = cls['stage_id'] if cls else 1
    
    if not books:
        await safe_edit_message(query, f"⚠️ لا توجد كتب مضافة في صف <b>{cls['name'] if cls else ''}</b> بعد.", reply_markup=inline.get_admin_class_books_list_keyboard([], class_id, stage_id))
        return
    await safe_edit_message(query, f"📚 <b>كتب صف: {cls['name'] if cls else ''}</b>\nاختر الكتاب للتحكم به أو استخدم الأدوات أدناه:", reply_markup=inline.get_admin_class_books_list_keyboard(books, class_id, stage_id))


async def view_single_book_card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin(update):
        return
    query = update.callback_query
    if query:
        try:
            await query.answer()
        except Exception:
            pass
    book_id = int(query.data.split("_")[-1])
    book = await repository.get_book_by_id(book_id)
    if not book:
        await safe_edit_message(query, "❌ الكتاب غير موجود.")
        return
    text = (
        f"📘 <b>كارت إدارة كتاب مفرد</b>\n\n"
        f"📌 <b>العنوان:</b> {book['title']}\n"
        f"🏛️ <b>المرحلة والصف:</b> {book['stage_name']} - {book['class_name']}\n"
        f"🆔 <b>file_id:</b> <code>{book['telegram_file_id']}</code>"
    )
    await safe_edit_message(query, text, reply_markup=inline.get_admin_single_book_card_keyboard(book_id, book['class_id']))


async def start_rename_book(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin(update):
        return
    query = update.callback_query
    if query:
        try:
            await query.answer()
        except Exception:
            pass
    book_id = int(query.data.split("_")[-1])
    context.user_data['admin_action'] = f'rename_book_{book_id}'
    book = await repository.get_book_by_id(book_id)
    await safe_edit_message(query, f"✏️ <b>تعديل عنوان الكتاب</b>\nالعنوان الحالي: <b>{book['title'] if book else ''}</b>\n\nأرسل العنوان الجديد:")


async def confirm_delete_single_book(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin(update):
        return
    query = update.callback_query
    if query:
        try:
            await query.answer()
        except Exception:
            pass
    book_id = int(query.data.split("_")[-1])
    book = await repository.get_book_by_id(book_id)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚠️ نعم، تأكيد الحذف", callback_data=f"adm_del_bk_exec_{book_id}")],
        [InlineKeyboardButton("❌ إلغاء", callback_data=f"adm_book_card_{book_id}")]
    ])
    await safe_edit_message(query, f"⚠️ <b>هل أنت تأكد من حذف كتاب: {book['title'] if book else ''}؟</b>", reply_markup=keyboard)


async def exec_delete_single_book(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin(update):
        return
    query = update.callback_query
    if query:
        try:
            await query.answer()
        except Exception:
            pass
    book_id = int(query.data.split("_")[-1])
    book = await repository.get_book_by_id(book_id)
    class_id = book['class_id'] if book else 1
    await repository.delete_book(book_id)
    await safe_edit_message(query, "✅ تم حذف الكتاب نهائياً.", reply_markup=inline.get_admin_class_books_list_keyboard([], class_id, 1))


async def handle_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة مدخلات المشرف النصية أو الملفات بناءً على الحالة الحالية."""
    if not update.effective_user or update.effective_user.id not in ADMIN_IDS:
        return

    action = context.user_data.get('admin_action')
    if not action:
        return

    # الإبقاء على حالة الرفع الجماعي نشطة لاستقبال كافة الملفات المرسلة دفعة واحدة
    if not action.startswith('upload_book_'):
        context.user_data.pop('admin_action', None)

    if action == 'broadcast':
        await send_broadcast(update, context)
        return

    if action == 'add_stage':
        stage_name = update.message.text.strip() if update.message and update.message.text else ""
        if stage_name:
            await repository.add_stage(stage_name)
            stages = await repository.get_all_stages()
            await update.message.reply_text(
                f"✅ تم إضافة مرحلة: <b>{stage_name}</b> بنجاح.",
                parse_mode="HTML",
                reply_markup=inline.get_admin_stages_list_keyboard(stages)
            )
        else:
            await update.message.reply_text("❌ يرجى كتابة اسم مرحلة صحيح.")
        return

    if action.startswith('rename_stage_'):
        stage_id = int(action.split('_')[-1])
        new_name = update.message.text.strip() if update.message and update.message.text else ""
        if new_name:
            await repository.update_stage_name(stage_id, new_name)
            stages = await repository.get_all_stages()
            await update.message.reply_text(
                f"✅ تم تعديل اسم المرحلة إلى: <b>{new_name}</b>.",
                parse_mode="HTML",
                reply_markup=inline.get_admin_stages_list_keyboard(stages)
            )
        return

    if action.startswith('add_class_'):
        stage_id = int(action.split('_')[-1])
        class_name = update.message.text.strip() if update.message and update.message.text else ""
        if class_name:
            await repository.add_class(stage_id, class_name)
            classes = await repository.get_classes_by_stage(stage_id)
            await update.message.reply_text(
                f"✅ تم إضافة صف: <b>{class_name}</b> بنجاح.",
                parse_mode="HTML",
                reply_markup=inline.get_admin_classes_list_keyboard(classes, stage_id)
            )
        return

    if action.startswith('rename_class_'):
        class_id = int(action.split('_')[-1])
        new_name = update.message.text.strip() if update.message and update.message.text else ""
        if new_name:
            await repository.update_class_name(class_id, new_name)
            cls = await repository.get_class_by_id(class_id)
            stage_id = cls['stage_id'] if cls else 1
            classes = await repository.get_classes_by_stage(stage_id)
            await update.message.reply_text(
                f"✅ تم تعديل اسم الصف إلى: <b>{new_name}</b>.",
                parse_mode="HTML",
                reply_markup=inline.get_admin_classes_list_keyboard(classes, stage_id)
            )
        return

    if action.startswith('upload_book_'):
        class_id = int(action.split('_')[-1])
        msg = update.message
        if msg and (msg.document or msg.audio or msg.video):
            file_obj = msg.document or msg.audio or msg.video
            file_id = file_obj.file_id
            title = file_obj.file_name or msg.caption or "كتاب دراسي"
            await repository.add_book_for_class(class_id, title, "", file_id)
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("↩️  قائمة كتب الصف", callback_data=f"adm_view_bks_{class_id}")]])
            await msg.reply_text(f"✅ تم رفع كتاب: <b>{title}</b> بنجاح!\n<i>يمكنك إرسال باقي الكتب أو الضغط على قائمة كتب الصف عند الانتهاء.</i>", parse_mode="HTML", reply_markup=keyboard)
        else:
            await msg.reply_text("⚠️ يرجى إرسال ملف الـ PDF كملف مرفق.")
        return

    if action.startswith('rename_book_'):
        book_id = int(action.split('_')[-1])
        new_title = update.message.text.strip() if update.message and update.message.text else ""
        if new_title:
            await repository.update_book_title(book_id, new_title)
            book = await repository.get_book_by_id(book_id)
            class_id = book['class_id'] if book else 1
            books = await repository.get_books_by_class(class_id)
            await update.message.reply_text(
                f"✅ تم تعديل عنوان الكتاب إلى: <b>{new_title}</b>.",
                parse_mode="HTML",
                reply_markup=inline.get_admin_class_books_list_keyboard(books, class_id)
            )
        return


async def confirm_delete_all_class_books(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin(update):
        return
    query = update.callback_query
    if query:
        try:
            await query.answer()
        except Exception:
            pass
    class_id = int(query.data.split("_")[-1])
    cls = await repository.get_class_by_id(class_id)
    books = await repository.get_books_by_class(class_id)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚠️ نعم، تفريغ وحذف كافة الكتب الآن", callback_data=f"adm_del_all_bks_exec_{class_id}")],
        [InlineKeyboardButton("❌ إلغاء", callback_data=f"adm_view_bks_{class_id}")]
    ])
    await safe_edit_message(query, f"⚠️ <b>هل أنت تأكد من حذف وتفريغ جميع الكتب ({len(books)} كتاب) التابعة لصف: {cls['name'] if cls else ''}؟</b>", reply_markup=keyboard)


async def exec_delete_all_class_books(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin(update):
        return
    query = update.callback_query
    if query:
        try:
            await query.answer()
        except Exception:
            pass
    class_id = int(query.data.split("_")[-1])
    cls = await repository.get_class_by_id(class_id)
    stage_id = cls['stage_id'] if cls else 1
    count = await repository.delete_all_books_by_class(class_id)
    books = await repository.get_books_by_class(class_id)
    await safe_edit_message(query, f"✅ تم تفريغ وحذف جميع الكتب ({count} كتاب) بنجاح لصف <b>{cls['name'] if cls else ''}</b>.", reply_markup=inline.get_admin_class_books_list_keyboard(books, class_id, stage_id))


def register_admin_handlers(app):
    app.add_handler(CommandHandler("admin", admin_panel_handler, filters=IS_ADMIN))
    app.add_handler(CallbackQueryHandler(admin_panel_handler, pattern="^admin_panel$"))
    app.add_handler(CallbackQueryHandler(admin_stats_handler, pattern="^admin_stats$"))
    app.add_handler(CallbackQueryHandler(admin_manage_curriculum, pattern="^adm_manage_curriculum$"))

    # التنقل المباشر والسريع
    app.add_handler(CallbackQueryHandler(view_classes_list, pattern="^adm_view_cls_\\d+$"))
    app.add_handler(CallbackQueryHandler(view_class_books, pattern="^adm_view_bks_\\d+$"))
    app.add_handler(CallbackQueryHandler(view_single_book_card, pattern="^adm_book_card_\\d+$"))

    # الحذف المباشر
    app.add_handler(CallbackQueryHandler(confirm_delete_stage, pattern="^adm_del_stg_confirm_\\d+$"))
    app.add_handler(CallbackQueryHandler(exec_delete_stage, pattern="^adm_del_stg_exec_\\d+$"))
    app.add_handler(CallbackQueryHandler(confirm_delete_class, pattern="^adm_del_cls_confirm_\\d+$"))
    app.add_handler(CallbackQueryHandler(exec_delete_class, pattern="^adm_del_cls_exec_\\d+$"))
    app.add_handler(CallbackQueryHandler(confirm_delete_all_class_books, pattern="^adm_del_all_bks_confirm_\\d+$"))
    app.add_handler(CallbackQueryHandler(exec_delete_all_class_books, pattern="^adm_del_all_bks_exec_\\d+$"))
    app.add_handler(CallbackQueryHandler(confirm_delete_single_book, pattern="^adm_del_bk_confirm_\\d+$"))
    app.add_handler(CallbackQueryHandler(exec_delete_single_book, pattern="^adm_del_bk_exec_\\d+$"))

    # ربط الأزرار المباشرة بدون اعتمادات الذاكرة المؤقتة
    app.add_handler(CallbackQueryHandler(start_broadcast, pattern="^admin_broadcast$"))
    app.add_handler(CallbackQueryHandler(start_add_stage, pattern="^adm_add_stage_new$"))
    app.add_handler(CallbackQueryHandler(start_rename_stage, pattern="^adm_ren_stg_\\d+$"))
    app.add_handler(CallbackQueryHandler(start_add_class_batch, pattern="^adm_add_cls_batch_\\d+$"))
    app.add_handler(CallbackQueryHandler(start_rename_class, pattern="^adm_ren_cls_\\d+$"))
    app.add_handler(CallbackQueryHandler(start_upload_books, pattern="^adm_upl_bk_\\d+$"))
    app.add_handler(CallbackQueryHandler(start_rename_book, pattern="^adm_ren_bk_\\d+$"))

    # معالج مدخلات الآدمن النصية والملفات
    app.add_handler(MessageHandler((filters.TEXT | filters.Document.ALL | filters.AUDIO | filters.VIDEO) & ~filters.COMMAND & IS_ADMIN, handle_admin_input))

