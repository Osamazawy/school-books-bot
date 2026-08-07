from typing import List, Dict, Any
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

STAGE_PALETTES = [
    {"header_icon": "🟩", "btn_icon": "🟩"},
    {"header_icon": "🟨", "btn_icon": "🟨"},
    {"header_icon": "🟥", "btn_icon": "🟥"},
    {"header_icon": "🟪", "btn_icon": "🟪"},
    {"header_icon": "🟦", "btn_icon": "🟦"},
]


def get_stages_and_classes_keyboard(stages_with_classes: List[Dict[str, Any]], is_admin: bool = False) -> InlineKeyboardMarkup:
    """عرض الشاشة الموحدة للمراحل والصفوف بمربعات ملونة مخصصة لكل مرحلة (للطلاب والمشرفين)."""
    keyboard = []
    
    for idx, item in enumerate(stages_with_classes):
        stage = item["stage"]
        classes = item["classes"]
        palette = STAGE_PALETTES[idx % len(STAGE_PALETTES)]
        
        # عنوان المرحلة الرأسي بـ رمز واحد عن اليمين واليسار
        h_icon = palette["header_icon"]
        header_text = f"{h_icon} {stage['name']} {h_icon}"
        keyboard.append([InlineKeyboardButton(header_text, callback_data="info_noop")])
        
        # أزرار الصفوف باسم الصف فقط (للآدمن تذهب لكارت التحكم adm_view_bks_ وللطالب تذهب لصفحة الكتب user_class_)
        row = []
        for cls in classes:
            btn_text = cls['name'].strip()
            callback_data = f"adm_view_bks_{cls['id']}" if is_admin else f"user_class_{cls['id']}"
            btn = InlineKeyboardButton(btn_text, callback_data=callback_data)
            row.append(btn)
            if len(row) == 2:
                keyboard.append(row[::-1])
                row = []
        if row:
            keyboard.append(row[::-1])

    if is_admin:
        keyboard.append([InlineKeyboardButton("❇️ إضافة مرحلة جديدة", callback_data="adm_add_stage_new")])
        keyboard.append([InlineKeyboardButton("↩️ لوحة التحكم", callback_data="admin_panel")])
        
    return InlineKeyboardMarkup(keyboard)


def get_main_menu_keyboard(stages_with_classes: List[Dict[str, Any]] = None, is_admin: bool = False) -> InlineKeyboardMarkup:
    """القائمة الرئيسية المباشرة للبوت."""
    if stages_with_classes:
        return get_stages_and_classes_keyboard(stages_with_classes, is_admin=is_admin)
        
    keyboard = [
        [InlineKeyboardButton("📊 الصفوف والمناهج الدراسية", callback_data="user_stages")]
    ]
    if is_admin:
        keyboard.append([InlineKeyboardButton("⚙️ لوحة التحكم", callback_data="admin_panel")])
    return InlineKeyboardMarkup(keyboard)


def get_stages_keyboard(stages: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """عرض عناصر المراحل للمستخدم."""
    keyboard = []
    for stage in stages:
        keyboard.append([InlineKeyboardButton(f"📊 {stage['name']}", callback_data=f"user_stage_{stage['id']}")])
    keyboard.append([InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)


def get_classes_keyboard(classes: List[Dict[str, Any]], stage_id: int) -> InlineKeyboardMarkup:
    """عرض عناصر الصفوف للمستخدم."""
    keyboard = []
    for cls in classes:
        keyboard.append([InlineKeyboardButton(f"📋 {cls['name']}", callback_data=f"user_class_{cls['id']}")])
    keyboard.append([InlineKeyboardButton("↩️ القائمة الرئيسية", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)


def get_books_keyboard(books: List[Dict[str, Any]], stage_id: int = 1) -> InlineKeyboardMarkup:
    """عرض كتب الصف للمستخدم العادي."""
    keyboard = []
    for book in books:
        keyboard.append([InlineKeyboardButton(f"📖 {book['title']}", callback_data=f"user_book_{book['id']}")])
        
    keyboard.append([InlineKeyboardButton("↩️ القائمة الرئيسية", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)


def get_book_details_keyboard(book_id: int, class_id: int) -> InlineKeyboardMarkup:
    """أزرار تفاصيل الكتاب للمستخدم بعرض كامل."""
    keyboard = [
        [InlineKeyboardButton("📥 تحميل الكتاب (PDF)", callback_data=f"dl_book_{book_id}")],
        [InlineKeyboardButton("↩️ العودة للكتب", callback_data=f"user_class_{class_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_search_results_keyboard(books: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """أزرار نتائج البحث."""
    keyboard = []
    for book in books:
        button_text = f"📖 {book['title']} ({book['class_name']} - {book['stage_name']})"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"user_book_{book['id']}")])
    keyboard.append([InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)


# ==================== لوحة التحكم وكروت المشرفين المباشرة (Direct Admin 2026) ====================

def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    """لوحة تحكم المشرف الرئيسية."""
    keyboard = [
        [InlineKeyboardButton("📚 إدارة المناهج والمراحل والصفوف", callback_data="adm_manage_curriculum")],
        [InlineKeyboardButton("📢 إذاعة للطلاب", callback_data="admin_broadcast")],
        [InlineKeyboardButton("📊 الإحصائيات الشاملة", callback_data="admin_stats")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_admin_stats_keyboard(active_tf: str = "all") -> InlineKeyboardMarkup:
    """كيبورد أزرار الفلترة الزمنية للإحصائيات للآدمن."""
    b_today = "🔘 اليوم" if active_tf == "today" else "📅 اليوم"
    b_7days = "🔘 7 أيام" if active_tf == "7days" else "🗓️ آخر 7 أيام"
    b_30days = "🔘 30 يوماً" if active_tf == "30days" else "📊 آخر 30 يوماً"
    b_all = "🔘 التجميع الكلي" if active_tf == "all" else "🌐 التجميع الكلي"
    b_custom = "🔘 مدى مخصص" if active_tf == "custom" else "🔍 مدى تاريخ مخصص"

    keyboard = [
        [
            InlineKeyboardButton(b_today, callback_data="stats_tf_today"),
            InlineKeyboardButton(b_7days, callback_data="stats_tf_7days")
        ],
        [
            InlineKeyboardButton(b_30days, callback_data="stats_tf_30days"),
            InlineKeyboardButton(b_all, callback_data="stats_tf_all")
        ],
        [
            InlineKeyboardButton(b_custom, callback_data="stats_tf_custom")
        ],
        [
            InlineKeyboardButton("↩️ لوحة التحكم", callback_data="admin_panel")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_admin_class_books_list_keyboard(books: List[Dict[str, Any]], class_id: int, stage_id: int = 1) -> InlineKeyboardMarkup:
    """عرض كتب الصف للآدمن."""
    keyboard = []
    for b in books:
        keyboard.append([InlineKeyboardButton(f"📖 {b['title']}", callback_data=f"adm_book_card_{b['id']}")])
        
    keyboard.append([InlineKeyboardButton("📤 رفع كتب جديدة لهذا الصف", callback_data=f"adm_upl_bk_{class_id}")])
    keyboard.append([InlineKeyboardButton("✏️ تعديل اسم الصف", callback_data=f"adm_ren_cls_{class_id}")])
    keyboard.append([
        InlineKeyboardButton("🗑️ حذف الكتب", callback_data=f"adm_del_all_bks_confirm_{class_id}"),
        InlineKeyboardButton("🗑️ حذف هذا الصف بالكامل", callback_data=f"adm_del_cls_confirm_{class_id}")
    ])
    keyboard.append([InlineKeyboardButton("↩️ قائمة المناهج والصفوف", callback_data="adm_manage_curriculum")])
    return InlineKeyboardMarkup(keyboard)


def get_admin_single_book_card_keyboard(book_id: int, class_id: int) -> InlineKeyboardMarkup:
    """كارت التحكم المباشر بكتاب مفرد."""
    keyboard = [
        [InlineKeyboardButton("📥 تحميل واستعراض الملف", callback_data=f"dl_book_{book_id}")],
        [
            InlineKeyboardButton("✏️ تعديل العنوان", callback_data=f"adm_ren_bk_{book_id}"),
            InlineKeyboardButton("🗑️ حذف الكتاب", callback_data=f"adm_del_bk_confirm_{book_id}")
        ],
        [InlineKeyboardButton("↩️ قائمة كتب الصف", callback_data=f"adm_view_bks_{class_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)
