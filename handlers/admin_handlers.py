import asyncio
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
)
from config import ADMIN_IDS
from utils.filters import IS_ADMIN
from database import repository
from keyboards import inline
from utils.logger import logger

# حالات ConversationHandlers
ADD_STAGE_NAME = 10
ADD_CLASS_BATCH = 15
UPL_BOOK_BATCH = 20
REN_STAGE_NAME = 30
REN_CLASS_NAME = 35
REN_BOOK_TITLE = 40
WAITING_BROADCAST = 50


async def check_admin(update: Update) -> bool:
    user = update.effective_user
    is_admin = bool(user and user.id in ADMIN_IDS)
    if not is_admin:
        if update.callback_query:
            await update.callback_query.answer("❌ عذراً، هذه العملية مخصصة للمشرفين فقط.", show_alert=True)
        elif update.message:
            await update.message.reply_text("❌ عذراً، هذا الأمر مخصص للمشرفين فقط.")
    return is_admin


# ==================== لوحة التحكم الرئيسية والإحصائيات ====================

async def admin_panel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin(update):
        return

    text = "⚙️ <b>لوحة تحكم المشرفين المحترفة</b>\nاختر القسم المطلوب من الأزرار المركزية أدناه:"
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=inline.get_admin_main_keyboard()
        )
    elif update.message:
        await update.message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=inline.get_admin_main_keyboard()
        )

async def admin_stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin(update):
        return
        
    query = update.callback_query
    await query.answer()
    
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
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 لوحة التحكم", callback_data="admin_panel")]
    ])
    await query.edit_message_text(stats_text, parse_mode="HTML", reply_markup=keyboard)


# ==================== الإذاعة والإعلانات للطلاب (Broadcast) ====================

async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
    if not await check_admin(update):
        return ConversationHandler.END

    users_cnt = await repository.get_users_count()
    if users_cnt == 0:
        await query.edit_message_text("❌ لا يوجد مستخدمين مسجلين في البوت بعد للإذاعة لهم.")
        return ConversationHandler.END

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("❌ إلغاء الإذاعة", callback_data="admin_panel")]])
    await query.edit_message_text(
        f"📢 <b>إذاعة / إعلان جديد للطلاب (عدد المشتركين: {users_cnt})</b>\n\n"
        "أرسل أو وِجّه الرسالة التي ترغب بنشرها لجميع المشتركين الآن (نص، صورة، ملصق، أو مستند):",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    return WAITING_BROADCAST

async def send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await check_admin(update):
        return ConversationHandler.END

    user_ids = await repository.get_all_user_ids()
    total = len(user_ids)
    
    status_msg = await update.message.reply_text(f"⏳ جاري بدء الإذاعة لـ {total} مستخدم...")
    
    success = 0
    failed = 0
    
    for uid in user_ids:
        try:
            await update.message.copy(chat_id=uid)
            success += 1
            await asyncio.sleep(0.04)
        except Exception as e:
            failed += 1
            logger.warning(f"تعذر إرسال الإذاعة للمستخدم {uid}: {e}")

    await status_msg.edit_text(
        f"🎉 <b>تمت الإذاعة بنجاح!</b>\n\n"
        f"✅ تم الإرسال إلى: <b>{success}</b> مستخدم\n"
        f"❌ تعذر الإرسال إلى: <b>{failed}</b> مستخدم",
        parse_mode="HTML",
        reply_markup=inline.get_admin_main_keyboard()
    )
    return ConversationHandler.END


# ==================== 1. المستوى الأول: إدارة المراحل (Stage Level) ====================

async def admin_manage_curriculum(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض قائمة جميع المراحل الدراسية للآدمن."""
    query = update.callback_query
    if query:
        await query.answer()
    if not await check_admin(update):
        return

    stages = await repository.get_all_stages()
    text = "🏛️ <b>إدارة المراحل والصفوف والمناهج</b>\nاختر المرحلة الدراسية لفتح كارت التحكم الخاص بها:"
    
    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=inline.get_admin_stages_list_keyboard(stages)
    )

async def view_stage_card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض كارت التحكم الخاص بـ مرحلة معينة (Stage Card)."""
    query = update.callback_query
    await query.answer()
    if not await check_admin(update):
        return

    stage_id = int(query.data.split("_")[-1])
    stage = await repository.get_stage_by_id(stage_id)
    classes = await repository.get_classes_by_stage(stage_id)
    
    if not stage:
        await query.edit_message_text("❌ المرحلة غير موجودة.")
        return

    card_text = (
        f"🏛️ <b>كارت إدارة مرحلة: {stage['name']}</b>\n\n"
        f"🎓 <b>عدد الصفوف المضافة بها:</b> {len(classes)} صف دراسي\n\n"
        "اختر الإجراء المطلوب لهذه المرحلة من الأزرار أدناه:"
    )
    await query.edit_message_text(
        card_text,
        parse_mode="HTML",
        reply_markup=inline.get_admin_stage_card_keyboard(stage_id)
    )

# --- إضافة مرحلة جديدة ---
async def start_add_stage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not await check_admin(update):
        return ConversationHandler.END
        
    await query.edit_message_text("➕ **إضافة مرحلة جديدة**\nأرسل اسم المرحلة الجديدة (مثال: المرحلة الثانوية):")
    return ADD_STAGE_NAME

async def save_add_stage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await check_admin(update):
        return ConversationHandler.END

    name = update.message.text.strip()
    if not name:
        await update.message.reply_text("⚠️ اسم غير صالح.")
        return ADD_STAGE_NAME
        
    stage_id = await repository.add_stage(name)
    await update.message.reply_text(
        f"✅ تم إضافة المرحلة **{name}** بنجاح!",
        parse_mode="Markdown",
        reply_markup=inline.get_admin_stage_card_keyboard(stage_id)
    )
    return ConversationHandler.END

# --- تعديل اسم المرحلة ---
async def start_rename_stage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    stage_id = int(query.data.split("_")[-1])
    context.user_data['ren_stage_id'] = stage_id
    stage = await repository.get_stage_by_id(stage_id)
    
    await query.edit_message_text(f"✏️ **تعديل اسم المرحلة**\nالاسم الحالي: **{stage['name']}**\n\nأرسل الاسم الجديد للمرحلة:")
    return REN_STAGE_NAME

async def save_rename_stage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_name = update.message.text.strip()
    stage_id = context.user_data.get('ren_stage_id')
    
    await repository.update_stage_name(stage_id, new_name)
    await update.message.reply_text(
        f"✅ تم تحديث اسم المرحلة إلى: **{new_name}**",
        parse_mode="Markdown",
        reply_markup=inline.get_admin_stage_card_keyboard(stage_id)
    )
    return ConversationHandler.END

# --- حذف المرحلة بالكامل ---
async def confirm_delete_stage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    stage_id = int(query.data.split("_")[-1])
    stage = await repository.get_stage_by_id(stage_id)
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚠️ نعم، احذف المرحلة بالكامل", callback_data=f"adm_del_stg_exec_{stage_id}"),
            InlineKeyboardButton("❌ إلغاء", callback_data=f"adm_stage_card_{stage_id}")
        ]
    ])
    await query.edit_message_text(
        f"⚠️ **تأكيد حذف المرحلة بالكامل!**\n\nهل أنت محدد وتأكد من حذف مرحلة **{stage['name']}**؟\n"
        "🔴 **تنبيه:** سيتم حذف كافة الصفوف وكافة الكتب التابعة لهذه المرحلة نهائياً!",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

async def exec_delete_stage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    stage_id = int(query.data.split("_")[-1])
    await repository.delete_stage(stage_id)
    
    await query.edit_message_text(
        "✅ تم حذف المرحلة بجميع صفوفها وكتبها نهائياً.",
        reply_markup=inline.get_admin_main_keyboard()
    )


# ==================== 2. المستوى الثاني: إدارة الصفوف (Class Level) ====================

async def view_classes_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض صفوف مرحلة محددة للآدمن."""
    query = update.callback_query
    await query.answer()
    
    stage_id = int(query.data.split("_")[-1])
    stage = await repository.get_stage_by_id(stage_id)
    classes = await repository.get_classes_by_stage(stage_id)
    
    text = f"🎓 **صفوف مرحلة: {stage['name']}**\nاختر الصف الدراسي لفتح كارت التحكم الخاص به:"
    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=inline.get_admin_classes_list_keyboard(classes, stage_id)
    )

async def view_class_card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض كارت التحكم الموحد الخاص بـ صف محدد (Class Control Card)."""
    query = update.callback_query
    await query.answer()
    
    class_id = int(query.data.split("_")[-1])
    cls = await repository.get_class_by_id(class_id)
    books = await repository.get_books_by_class(class_id)
    
    card_text = (
        f"🎓 **كارت إدارة صف: ({cls['stage_name']} - {cls['name']})**\n\n"
        f"📚 **إجمالي الكتب المرفوعة لهذا الصف:** {len(books)} كتاب\n\n"
        "اختر الإجراء المطلوب لهذا الصف من الأزرار المركزية أدناه:"
    )
    await query.edit_message_text(
        card_text,
        parse_mode="Markdown",
        reply_markup=inline.get_admin_class_card_keyboard(class_id, cls['stage_id'])
    )

# --- إضافة صفوف متتالية لمرحلة ---
async def start_add_class_batch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    stage_id = int(query.data.split("_")[-1])
    stage = await repository.get_stage_by_id(stage_id)
    context.user_data['active_stage_id'] = stage_id

    finish_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏁 تم الانتهاء", callback_data=f"adm_view_cls_{stage_id}")]
    ])

    await query.edit_message_text(
        f"✍️ **وضع إضافة الصفوف التتابعي مفعّل لمرحلة: ({stage['name']})**\n\n"
        "أرسل أسماء الصفوف متتالية (كل صف برسالة، أو عدة صفوف في أسطر برسالة واحدة):\n\n"
        "**مثال:**\n"
        "```text\n"
        "الأول المتوسط\n"
        "الثاني المتوسط\n"
        "الثالث المتوسط\n"
        "```\n\n"
        "عند الانتهاء اضغط زر **'🏁 تم الانتهاء'** أدناه.",
        parse_mode="Markdown",
        reply_markup=finish_keyboard
    )
    return ADD_CLASS_BATCH

async def save_add_class_batch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    stage_id = context.user_data.get('active_stage_id')
    
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for name in lines:
        await repository.add_class(stage_id, name)

    finish_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏁 تم الانتهاء", callback_data=f"adm_view_cls_{stage_id}")]
    ])

    formatted = "\n".join([f"• {n}" for n in lines])
    await update.message.reply_text(
        f"✅ **تم إضافة الصفوف التالية بنجاح:**\n{formatted}\n\n"
        "<i>يمكنك إرسال المزيد أو الضغط على تم الانتهاء.</i>",
        parse_mode="HTML",
        reply_markup=finish_keyboard
    )
    return ADD_CLASS_BATCH

# --- تعديل اسم الصف ---
async def start_rename_class(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    class_id = int(query.data.split("_")[-1])
    context.user_data['ren_class_id'] = class_id
    cls = await repository.get_class_by_id(class_id)
    
    await query.edit_message_text(f"✏️ **تعديل اسم الصف**\nالاسم الحالي: **{cls['name']}**\n\nأرسل الاسم الجديد للصف:")
    return REN_CLASS_NAME

async def save_rename_class(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_name = update.message.text.strip()
    class_id = context.user_data.get('ren_class_id')
    cls = await repository.get_class_by_id(class_id)
    
    await repository.update_class_name(class_id, new_name)
    await update.message.reply_text(
        f"✅ تم تحديث اسم الصف إلى: **{new_name}**",
        parse_mode="Markdown",
        reply_markup=inline.get_admin_class_card_keyboard(class_id, cls['stage_id'])
    )
    return ConversationHandler.END

# --- حذف الصف بالكامل ---
async def confirm_delete_class(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    class_id = int(query.data.split("_")[-1])
    cls = await repository.get_class_by_id(class_id)
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚠️ نعم، احذف هذا الصف بكل كتبه", callback_data=f"adm_del_cls_exec_{class_id}"),
            InlineKeyboardButton("❌ إلغاء", callback_data=f"adm_class_card_{class_id}")
        ]
    ])
    await query.edit_message_text(
        f"⚠️ **تأكيد حذف الصف بالكامل!**\n\nهل أنت متأكد من حذف صف **{cls['name']}**؟\n"
        "🔴 **تنبيه:** سيتم حذف جميع الكتب المرفوعة لهذا الصف نهائياً!",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

async def exec_delete_class(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    class_id = int(query.data.split("_")[-1])
    cls = await repository.get_class_by_id(class_id)
    stage_id = cls['stage_id'] if cls else 1

    await repository.delete_class(class_id)
    
    await query.edit_message_text(
        "✅ تم حذف الصف بجميع كتبه نهائياً.",
        reply_markup=inline.get_admin_stage_card_keyboard(stage_id)
    )


# ==================== 3. المستوى الثالث: الرفع الجماعي وإدارة كتب الصف (Books Level) ====================

# --- الرفع الجماعي المباشر للصف ---
async def start_upload_books(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    class_id = int(query.data.split("_")[-1])
    cls = await repository.get_class_by_id(class_id)
    
    context.user_data['active_class_id'] = class_id
    context.user_data['uploaded_books_count'] = 0

    finish_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏁 تم الانتهاء من الرفع", callback_data=f"adm_class_card_{class_id}")]
    ])

    await query.edit_message_text(
        f"📥 **وضع الرفع الجماعي المباشر مفعّل لصف: ({cls['stage_name']} - {cls['name']})**\n\n"
        "قم الآن **بإرسال أو سحب وإفلات جميع ملفات الـ PDF** الخاصة بهذا الصف دفعة واحدة من الكمبيوتر 📄📄📄.\n\n"
        "سيتم الحفظ والتسمية تلقائياً باسم كل ملف وتوفيره للطلاب فوراً!\n"
        "عند الانتهاء اضغط زر **'🏁 تم الانتهاء من الرفع'**.",
        parse_mode="Markdown",
        reply_markup=finish_keyboard
    )
    return UPL_BOOK_BATCH

async def save_upload_book_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    doc = update.message.document
    if not doc:
        await update.message.reply_text("⚠️ يرجى إرسال ملفات كمستندات PDF.")
        return UPL_BOOK_BATCH

    class_id = context.user_data.get('active_class_id')
    file_id = doc.file_id
    raw_name = doc.file_name or "كتاب دراسي"
    title = os.path.splitext(raw_name)[0].replace("_", " ").strip()

    await repository.add_book_for_class(class_id=class_id, title=title, description=f"ملف: {doc.file_name}", telegram_file_id=file_id)
    
    cnt = context.user_data.get('uploaded_books_count', 0) + 1
    context.user_data['uploaded_books_count'] = cnt

    finish_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏁 تم الانتهاء من الرفع", callback_data=f"adm_class_card_{class_id}")]
    ])

    await update.message.reply_text(
        f"✅ <b>[{cnt}] تم إضافة الكتاب للصف:</b> {title}\n"
        f"🆔 file_id: <code>{file_id}</code>",
        parse_mode="HTML",
        reply_markup=finish_keyboard
    )
    return UPL_BOOK_BATCH

# --- عرض كتب الصف للآدمن ---
async def view_class_books(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    class_id = int(query.data.split("_")[-1])
    cls = await repository.get_class_by_id(class_id)
    books = await repository.get_books_by_class(class_id)
    
    if not books:
        await query.edit_message_text(
            f"❌ لا توجد كتب مضافة في صف **{cls['name']}** بعد.",
            reply_markup=inline.get_admin_class_card_keyboard(class_id, cls['stage_id'])
        )
        return

    text = f"📚 **كتب صف: {cls['name']}**\nاضغط على اسم الكتاب لفتح كارت التحكم المباشر به (تعديل أو حذف):"
    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=inline.get_admin_class_books_list_keyboard(books, class_id)
    )

# --- كارت الكتاب الواحد المباشر (Single Book Card) ---
async def view_single_book_card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    book_id = int(query.data.split("_")[-1])
    book = await repository.get_book_by_id(book_id)
    
    if not book:
        await query.edit_message_text("❌ الكتاب غير موجود.")
        return

    text = (
        f"📘 **كارت إدارة كتاب واحد**\n\n"
        f"📌 **اسم الكتاب:** {book['title']}\n"
        f"🏛️ **المرحلة والصف:** {book['stage_name']} - {book['class_name']}\n"
        f"🆔 **file_id:** `{book['telegram_file_id']}`\n\n"
        "اختر الإجراء لـ هذا الكتاب فقط:"
    )
    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=inline.get_admin_single_book_card_keyboard(book_id, book['class_id'])
    )

# --- تعديل عنوان الكتاب المفرد ---
async def start_rename_book(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    book_id = int(query.data.split("_")[-1])
    context.user_data['ren_book_id'] = book_id
    book = await repository.get_book_by_id(book_id)
    
    await query.edit_message_text(f"✏️ **تعديل عنوان الكتاب**\nالعنوان الحالي: **{book['title']}**\n\nأرسل العنوان الجديد للكتاب:")
    return REN_BOOK_TITLE

async def save_rename_book(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_title = update.message.text.strip()
    book_id = context.user_data.get('ren_book_id')
    book = await repository.get_book_by_id(book_id)

    await repository.update_book_title(book_id, new_title)
    await update.message.reply_text(
        f"✅ تم تحديث عنوان الكتاب إلى: **{new_title}**",
        parse_mode="Markdown",
        reply_markup=inline.get_admin_single_book_card_keyboard(book_id, book['class_id'])
    )
    return ConversationHandler.END

# --- حذف كتاب واحد فقط ---
async def confirm_delete_single_book(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    book_id = int(query.data.split("_")[-1])
    book = await repository.get_book_by_id(book_id)
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🗑️ نعم، احذف هذا الكتاب فقط", callback_data=f"adm_del_bk_exec_{book_id}"),
            InlineKeyboardButton("❌ إلغاء", callback_data=f"adm_book_card_{book_id}")
        ]
    ])
    await query.edit_message_text(
        f"⚠️ **تأكيد حذف كتاب مفرد**\n\nهل أنت محدد وتأكد من حذف كتاب **{book['title']}** فقط؟",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

async def exec_delete_single_book(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    book_id = int(query.data.split("_")[-1])
    book = await repository.get_book_by_id(book_id)
    class_id = book['class_id'] if book else 1

    await repository.delete_book(book_id)
    
    await query.edit_message_text(
        "✅ تم حذف الكتاب المفرد نهائياً من قاعدة البيانات.",
        reply_markup=inline.get_admin_class_card_keyboard(class_id, 1)
    )


async def cancel_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("تم الإلغاء.")
    else:
        await update.message.reply_text("تم الإلغاء.")
    return ConversationHandler.END


# ==================== تسجيل الـ Handlers الخاصين بالمشرف ====================

def register_admin_handlers(app):
    app.add_handler(CommandHandler("admin", admin_panel_handler, filters=IS_ADMIN))
    app.add_handler(CallbackQueryHandler(admin_panel_handler, pattern="^admin_panel$"))
    app.add_handler(CallbackQueryHandler(admin_stats_handler, pattern="^admin_stats$"))
    app.add_handler(CallbackQueryHandler(admin_manage_curriculum, pattern="^adm_manage_curriculum$"))

    # التنقل في كروت الإدارة
    app.add_handler(CallbackQueryHandler(view_stage_card, pattern="^adm_stage_card_\\d+$"))
    app.add_handler(CallbackQueryHandler(view_classes_list, pattern="^adm_view_cls_\\d+$"))
    app.add_handler(CallbackQueryHandler(view_class_card, pattern="^adm_class_card_\\d+$"))
    app.add_handler(CallbackQueryHandler(view_class_books, pattern="^adm_view_bks_\\d+$"))
    app.add_handler(CallbackQueryHandler(view_single_book_card, pattern="^adm_book_card_\\d+$"))

    # الحذف المباشر للـ Stage والـ Class والـ Book
    app.add_handler(CallbackQueryHandler(confirm_delete_stage, pattern="^adm_del_stg_confirm_\\d+$"))
    app.add_handler(CallbackQueryHandler(exec_delete_stage, pattern="^adm_del_stg_exec_\\d+$"))
    app.add_handler(CallbackQueryHandler(confirm_delete_class, pattern="^adm_del_cls_confirm_\\d+$"))
    app.add_handler(CallbackQueryHandler(exec_delete_class, pattern="^adm_del_cls_exec_\\d+$"))
    app.add_handler(CallbackQueryHandler(confirm_delete_single_book, pattern="^adm_del_bk_confirm_\\d+$"))
    app.add_handler(CallbackQueryHandler(exec_delete_single_book, pattern="^adm_del_bk_exec_\\d+$"))

    # Conversation الإذاعة
    broadcast_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_broadcast, pattern="^admin_broadcast$")],
        states={
            WAITING_BROADCAST: [MessageHandler(filters.ALL & ~filters.COMMAND, send_broadcast)]
        },
        fallbacks=[CommandHandler("cancel", cancel_admin_action), CallbackQueryHandler(cancel_admin_action, pattern="^admin_panel$")],
        allow_reentry=True,
        per_message=False
    )

    # Conversation إضافة مرحلة
    add_stage_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_add_stage, pattern="^adm_add_stage_new$")],
        states={
            ADD_STAGE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_add_stage)]
        },
        fallbacks=[CommandHandler("cancel", cancel_admin_action), CallbackQueryHandler(cancel_admin_action, pattern="^admin_panel$")],
        allow_reentry=True,
        per_message=False
    )

    # Conversation تعديل مرحلة
    ren_stage_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_rename_stage, pattern="^adm_ren_stg_\\d+$")],
        states={
            REN_STAGE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_rename_stage)]
        },
        fallbacks=[CommandHandler("cancel", cancel_admin_action), CallbackQueryHandler(cancel_admin_action, pattern="^admin_panel$")],
        allow_reentry=True,
        per_message=False
    )

    # Conversation إضافة صفوف متتالية
    add_class_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_add_class_batch, pattern="^adm_add_cls_batch_\\d+$")],
        states={
            ADD_CLASS_BATCH: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_add_class_batch),
                CallbackQueryHandler(admin_manage_curriculum, pattern="^adm_manage_curriculum$")
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel_admin_action), CallbackQueryHandler(cancel_admin_action, pattern="^admin_panel$")],
        allow_reentry=True,
        per_message=False
    )

    # Conversation تعديل صف
    ren_class_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_rename_class, pattern="^adm_ren_cls_\\d+$")],
        states={
            REN_CLASS_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_rename_class)]
        },
        fallbacks=[CommandHandler("cancel", cancel_admin_action), CallbackQueryHandler(cancel_admin_action, pattern="^admin_panel$")],
        allow_reentry=True,
        per_message=False
    )

    # Conversation الرفع الجماعي المباشر للصف
    upl_book_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_upload_books, pattern="^adm_upl_bk_\\d+$")],
        states={
            UPL_BOOK_BATCH: [
                MessageHandler(filters.Document.ALL, save_upload_book_file),
                CallbackQueryHandler(view_class_card, pattern="^adm_class_card_\\d+$")
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel_admin_action), CallbackQueryHandler(cancel_admin_action, pattern="^admin_panel$")],
        allow_reentry=True,
        per_message=False
    )

    # Conversation تعديل اسم كتاب مفرد
    ren_book_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_rename_book, pattern="^adm_ren_bk_\\d+$")],
        states={
            REN_BOOK_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_rename_book)]
        },
        fallbacks=[CommandHandler("cancel", cancel_admin_action), CallbackQueryHandler(cancel_admin_action, pattern="^admin_panel$")],
        allow_reentry=True,
        per_message=False
    )

    app.add_handler(broadcast_conv)
    app.add_handler(add_stage_conv)
    app.add_handler(ren_stage_conv)
    app.add_handler(add_class_conv)
    app.add_handler(ren_class_conv)
    app.add_handler(upl_book_conv)
    app.add_handler(ren_book_conv)
