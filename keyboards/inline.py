from typing import List, Dict, Any
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_main_menu_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """القائمة الرئيسية للبوت (أزرار رئيسية علوية بعرض كامل وممركزة)."""
    keyboard = [
        [InlineKeyboardButton("🏛️  المراحل الدراسية  🏛️", callback_data="user_stages")],
        [InlineKeyboardButton("🔍  البحث عن كتاب  🔍", callback_data="user_search")]
    ]
    if is_admin:
        keyboard.append([InlineKeyboardButton("⚙️  لوحة التحكم  ⚙️", callback_data="admin_panel")])
    return InlineKeyboardMarkup(keyboard)


def get_stages_keyboard(stages: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """عرض عناصر المراحل للمستخدم بعمودين محاذيين لليمين RTL، والأزرار الرئيسية بعرض كامل."""
    keyboard = []
    row = []
    for stage in stages:
        row.append(InlineKeyboardButton(f"🏛️ {stage['name']}", callback_data=f"user_stage_{stage['id']}"))
        if len(row) == 2:
            keyboard.append(row[::-1])
            row = []
    if row:
        keyboard.append(row[::-1])
        
    keyboard.append([InlineKeyboardButton("🏠  القائمة الرئيسية  🏠", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)


def get_classes_keyboard(classes: List[Dict[str, Any]], stage_id: int) -> InlineKeyboardMarkup:
    """عرض عناصر الصفوف للمستخدم بعمودين محاذيين لليمين RTL، والأزرار الرئيسية بعرض كامل."""
    keyboard = []
    row = []
    for cls in classes:
        row.append(InlineKeyboardButton(f"🎓 {cls['name']}", callback_data=f"user_class_{cls['id']}"))
        if len(row) == 2:
            keyboard.append(row[::-1])
            row = []
    if row:
        keyboard.append(row[::-1])
        
    keyboard.append([InlineKeyboardButton("🔙  العودة للمراحل  🔙", callback_data="user_stages")])
    return InlineKeyboardMarkup(keyboard)


def get_books_keyboard(books: List[Dict[str, Any]], stage_id: int) -> InlineKeyboardMarkup:
    """عرض كتب الصف للمستخدم العادي بعرض كامل وممركز."""
    keyboard = []
    for book in books:
        keyboard.append([InlineKeyboardButton(f"📘  {book['title']}  📘", callback_data=f"user_book_{book['id']}")])
        
    keyboard.append([InlineKeyboardButton("🔙  العودة للصفوف  🔙", callback_data=f"user_stage_{stage_id}")])
    return InlineKeyboardMarkup(keyboard)


def get_book_details_keyboard(book_id: int, class_id: int) -> InlineKeyboardMarkup:
    """أزرار تفاصيل الكتاب للمستخدم بعرض كامل."""
    keyboard = [
        [InlineKeyboardButton("📥  تحميل الكتاب (PDF)  📥", callback_data=f"dl_book_{book_id}")],
        [InlineKeyboardButton("🔙  العودة للكتب  🔙", callback_data=f"user_class_{class_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_search_results_keyboard(books: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """أزرار نتائج البحث بعرض كامل."""
    keyboard = []
    for book in books:
        button_text = f"📘 {book['title']} ({book['class_name']} - {book['stage_name']})"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"user_book_{book['id']}")])
    keyboard.append([InlineKeyboardButton("🏠  القائمة الرئيسية  🏠", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)


# ==================== لوحة التحكم وكروت المشرفين المباشرة (Direct Admin 2026) ====================

def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    """لوحة تحكم المشرف الرئيسية (أزرار رئيسية بعرض كامل وممركزة)."""
    keyboard = [
        [InlineKeyboardButton("🏛️  إدارة المناهج والمراحل والصفوف  🏛️", callback_data="adm_manage_curriculum")],
        [InlineKeyboardButton("📢  إذاعة للطلاب  📢", callback_data="admin_broadcast")],
        [InlineKeyboardButton("📊  الإحصائيات الشاملة  📊", callback_data="admin_stats")],
        [InlineKeyboardButton("🏠  القائمة الرئيسية  🏠", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_admin_stages_list_keyboard(stages: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """عرض عناصر المراحل للآدمن بعمودين محاذيين لليمين RTL، والأزرار الرئيسية ممركزة بعرض كامل."""
    keyboard = []
    row = []
    for s in stages:
        row.append(InlineKeyboardButton(f"🏛️ {s['name']}", callback_data=f"adm_view_cls_{s['id']}"))
        if len(row) == 2:
            keyboard.append(row[::-1])
            row = []
    if row:
        keyboard.append(row[::-1])
    keyboard.append([InlineKeyboardButton("➕  إضافة مرحلة جديدة  ➕", callback_data="adm_add_stage_new")])
    keyboard.append([InlineKeyboardButton("🔙  لوحة التحكم  🔙", callback_data="admin_panel")])
    return InlineKeyboardMarkup(keyboard)


def get_admin_classes_list_keyboard(classes: List[Dict[str, Any]], stage_id: int) -> InlineKeyboardMarkup:
    """عرض عناصر الصفوف للآدمن بعمودين محاذيين لليمين RTL، والأزرار الرئيسية ممركزة بعرض كامل."""
    keyboard = []
    row = []
    for c in classes:
        row.append(InlineKeyboardButton(f"🎓 {c['name']}", callback_data=f"adm_view_bks_{c['id']}"))
        if len(row) == 2:
            keyboard.append(row[::-1])
            row = []
    if row:
        keyboard.append(row[::-1])
        
    keyboard.append([InlineKeyboardButton("➕  إضافة صف جديد  ➕", callback_data=f"adm_add_cls_batch_{stage_id}")])
    keyboard.append([
        InlineKeyboardButton("🗑️ حذف المرحلة", callback_data=f"adm_del_stg_confirm_{stage_id}"),
        InlineKeyboardButton("✏️ تعديل الاسم", callback_data=f"adm_ren_stg_{stage_id}")
    ])
    keyboard.append([InlineKeyboardButton("🔙  قائمة المراحل  🔙", callback_data="adm_manage_curriculum")])
    return InlineKeyboardMarkup(keyboard)


def get_admin_class_books_list_keyboard(books: List[Dict[str, Any]], class_id: int, stage_id: int = 1) -> InlineKeyboardMarkup:
    """عرض كتب الصف للآدمن والأزرار الرئيسية ممركزة بعرض كامل."""
    keyboard = []
    for b in books:
        keyboard.append([InlineKeyboardButton(f"📘 {b['title']}", callback_data=f"adm_book_card_{b['id']}")])
        
    keyboard.append([InlineKeyboardButton("🚀  رفع كتب جديدة لهذا الصف  🚀", callback_data=f"adm_upl_bk_{class_id}")])
    keyboard.append([
        InlineKeyboardButton("🗑️ تفريغ الكتب", callback_data=f"adm_del_all_bks_confirm_{class_id}"),
        InlineKeyboardButton("✏️ تعديل اسم الصف", callback_data=f"adm_ren_cls_{class_id}")
    ])
    keyboard.append([InlineKeyboardButton("🗑️  حذف هذا الصف بالكامل  🗑️", callback_data=f"adm_del_cls_confirm_{class_id}")])
    keyboard.append([InlineKeyboardButton("🔙  قائمة الصفوف  🔙", callback_data=f"adm_view_cls_{stage_id}")])
    return InlineKeyboardMarkup(keyboard)


def get_admin_single_book_card_keyboard(book_id: int, class_id: int) -> InlineKeyboardMarkup:
    """كارت التحكم المباشر بكتاب مفرد."""
    keyboard = [
        [InlineKeyboardButton("📥  تحميل واستعراض الملف  📥", callback_data=f"dl_book_{book_id}")],
        [
            InlineKeyboardButton("🗑️ حذف الكتاب", callback_data=f"adm_del_bk_confirm_{book_id}"),
            InlineKeyboardButton("✏️ تعديل العنوان", callback_data=f"adm_ren_bk_{book_id}")
        ],
        [InlineKeyboardButton("🔙  قائمة كتب الصف  🔙", callback_data=f"adm_view_bks_{class_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)
