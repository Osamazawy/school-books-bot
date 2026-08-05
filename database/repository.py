from typing import List, Dict, Any, Optional
from database.connection import get_db_connection

def _val(row, key_or_idx=0):
    """مساعد آمن لاستخراج القيمة من القاموس أو الصف الترتيبي."""
    if row is None:
        return None
    if isinstance(row, dict):
        if isinstance(key_or_idx, str) and key_or_idx in row:
            return row[key_or_idx]
        vals = list(row.values())
        return vals[0] if vals else None
    return row[key_or_idx]

def _dict(row) -> Dict[str, Any]:
    if row is None:
        return {}
    if isinstance(row, dict):
        return dict(row)
    return dict(row)

# ==================== مستخدمون (Users & Broadcast) ====================

async def add_or_update_user(telegram_id: int, full_name: str) -> None:
    async with get_db_connection() as db:
        await db.execute("""
            INSERT INTO users (telegram_id, full_name)
            VALUES (?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET full_name=EXCLUDED.full_name;
        """, (telegram_id, full_name))
        await db.commit()

async def get_all_user_ids() -> List[int]:
    """استرجاع جميع معرفات المستخدمين للإذاعة."""
    async with get_db_connection() as db:
        async with db.execute("SELECT telegram_id FROM users;") as cursor:
            rows = await cursor.fetchall()
            return [_val(row, 'telegram_id') for row in rows]

async def get_users_count() -> int:
    async with get_db_connection() as db:
        async with db.execute("SELECT COUNT(*) FROM users;") as cursor:
            row = await cursor.fetchone()
            val = _val(row, 0)
            return val if val else 0


# ==================== المراحل الدراسية (Stages) ====================

async def add_stage(name: str) -> Optional[int]:
    async with get_db_connection() as db:
        await db.execute("INSERT INTO stages (name) VALUES (?) ON CONFLICT (name) DO NOTHING;", (name.strip(),))
        await db.commit()
        async with db.execute("SELECT id FROM stages WHERE name = ?;", (name.strip(),)) as cursor:
            row = await cursor.fetchone()
            return _val(row, 'id')

async def get_all_stages() -> List[Dict[str, Any]]:
    async with get_db_connection() as db:
        async with db.execute("SELECT id, name FROM stages ORDER BY id ASC;") as cursor:
            rows = await cursor.fetchall()
            return [_dict(row) for row in rows]

async def get_stage_by_id(stage_id: int) -> Optional[Dict[str, Any]]:
    async with get_db_connection() as db:
        async with db.execute("SELECT id, name FROM stages WHERE id = ?;", (stage_id,)) as cursor:
            row = await cursor.fetchone()
            return _dict(row) if row else None

async def update_stage_name(stage_id: int, new_name: str) -> bool:
    """تعديل اسم المرحلة."""
    async with get_db_connection() as db:
        cursor = await db.execute("UPDATE stages SET name = ? WHERE id = ?;", (new_name.strip(), stage_id))
        await db.commit()
        return cursor.rowcount > 0

async def delete_stage(stage_id: int) -> bool:
    """حذف مرحلة بالكامل بجميع صفوفها وكتبها (CASCADE)."""
    async with get_db_connection() as db:
        cursor = await db.execute("DELETE FROM stages WHERE id = ?;", (stage_id,))
        await db.commit()
        return cursor.rowcount > 0

async def get_stages_count() -> int:
    async with get_db_connection() as db:
        async with db.execute("SELECT COUNT(*) FROM stages;") as cursor:
            row = await cursor.fetchone()
            val = _val(row, 0)
            return val if val else 0


# ==================== الصفوف الدراسية (Classes) ====================

async def add_class(stage_id: int, name: str) -> Optional[int]:
    async with get_db_connection() as db:
        await db.execute("INSERT INTO classes (stage_id, name) VALUES (?, ?) ON CONFLICT DO NOTHING;", (stage_id, name.strip()))
        await db.commit()
        async with db.execute("SELECT id FROM classes WHERE stage_id = ? AND name = ?;", (stage_id, name.strip())) as cursor:
            row = await cursor.fetchone()
            return _val(row, 'id')

async def get_classes_by_stage(stage_id: int) -> List[Dict[str, Any]]:
    async with get_db_connection() as db:
        async with db.execute("SELECT id, stage_id, name FROM classes WHERE stage_id = ? ORDER BY id ASC;", (stage_id,)) as cursor:
            rows = await cursor.fetchall()
            return [_dict(row) for row in rows]

async def get_class_by_id(class_id: int) -> Optional[Dict[str, Any]]:
    async with get_db_connection() as db:
        async with db.execute("""
            SELECT c.id, c.stage_id, c.name, st.name as stage_name
            FROM classes c
            JOIN stages st ON c.stage_id = st.id
            WHERE c.id = ?;
        """, (class_id,)) as cursor:
            row = await cursor.fetchone()
            return _dict(row) if row else None

async def update_class_name(class_id: int, new_name: str) -> bool:
    """تعديل اسم الصف."""
    async with get_db_connection() as db:
        cursor = await db.execute("UPDATE classes SET name = ? WHERE id = ?;", (new_name.strip(), class_id))
        await db.commit()
        return cursor.rowcount > 0

async def delete_class(class_id: int) -> bool:
    """حذف صف دراسي بالكامل بجميع كتبه (CASCADE)."""
    async with get_db_connection() as db:
        cursor = await db.execute("DELETE FROM classes WHERE id = ?;", (class_id,))
        await db.commit()
        return cursor.rowcount > 0

async def get_classes_count() -> int:
    async with get_db_connection() as db:
        async with db.execute("SELECT COUNT(*) FROM classes;") as cursor:
            row = await cursor.fetchone()
            val = _val(row, 0)
            return val if val else 0


# ==================== الكتب (Books) ====================

async def add_book_for_class(class_id: int, title: str, description: str, telegram_file_id: str) -> Optional[int]:
    """إضافة كتاب مباشرة لصف دراسي."""
    async with get_db_connection() as db:
        cursor = await db.execute("""
            INSERT INTO books (class_id, title, description, telegram_file_id)
            VALUES (?, ?, ?, ?);
        """, (class_id, title.strip(), description.strip() if description else "", telegram_file_id.strip()))
        await db.commit()
        return getattr(cursor, 'lastrowid', None)

async def get_books_by_class(class_id: int) -> List[Dict[str, Any]]:
    """استرجاع جميع كتب صف محدد."""
    async with get_db_connection() as db:
        async with db.execute("""
            SELECT id, class_id, subject_id, title, description, telegram_file_id, created_at
            FROM books WHERE class_id = ? ORDER BY id ASC;
        """, (class_id,)) as cursor:
            rows = await cursor.fetchall()
            return [_dict(row) for row in rows]

async def get_book_by_id(book_id: int) -> Optional[Dict[str, Any]]:
    """استرجاع تفاصيل كتاب واحد بجميع تفاصيله الهيكلية."""
    async with get_db_connection() as db:
        async with db.execute("""
            SELECT b.id, b.class_id, b.subject_id, b.title, b.description, b.telegram_file_id, b.created_at,
                   c.name as class_name, c.stage_id, st.name as stage_name
            FROM books b
            JOIN classes c ON b.class_id = c.id
            JOIN stages st ON c.stage_id = st.id
            WHERE b.id = ?;
        """, (book_id,)) as cursor:
            row = await cursor.fetchone()
            return _dict(row) if row else None

async def search_books(query: str) -> List[Dict[str, Any]]:
    """البحث السريع القياسي عن الكتب."""
    search_term = f"%{query.strip()}%"
    async with get_db_connection() as db:
        async with db.execute("""
            SELECT b.id, b.title, b.description, b.telegram_file_id,
                   c.name as class_name, st.name as stage_name
            FROM books b
            JOIN classes c ON b.class_id = c.id
            JOIN stages st ON c.stage_id = st.id
            WHERE LOWER(b.title) LIKE LOWER(?) OR LOWER(b.description) LIKE LOWER(?) OR LOWER(c.name) LIKE LOWER(?) OR LOWER(st.name) LIKE LOWER(?)
            ORDER BY b.id DESC LIMIT 25;
        """, (search_term, search_term, search_term, search_term)) as cursor:
            rows = await cursor.fetchall()
            return [_dict(row) for row in rows]

async def update_book_title(book_id: int, new_title: str) -> bool:
    """تعديل عنوان كتاب واحد."""
    async with get_db_connection() as db:
        cursor = await db.execute("UPDATE books SET title = ? WHERE id = ?;", (new_title.strip(), book_id))
        await db.commit()
        return cursor.rowcount > 0

async def delete_book(book_id: int) -> bool:
    """حذف كتاب واحد فقط من قاعدة البيانات."""
    async with get_db_connection() as db:
        cursor = await db.execute("DELETE FROM books WHERE id = ?;", (book_id,))
        await db.commit()
        return cursor.rowcount > 0

async def delete_all_books_by_class(class_id: int) -> int:
    """حذف جميع الكتب التابعة لصف دراسي محدد دفعة واحدة."""
    async with get_db_connection() as db:
        cursor = await db.execute("DELETE FROM books WHERE class_id = ?;", (class_id,))
        await db.commit()
        return cursor.rowcount if cursor and cursor.rowcount >= 0 else 0

async def get_books_count() -> int:
    async with get_db_connection() as db:
        async with db.execute("SELECT COUNT(*) FROM books;") as cursor:
            row = await cursor.fetchone()
            val = _val(row, 0)
            return val if val else 0

async def get_stage_breakdown() -> List[Dict[str, Any]]:
    """استرجاع توزيع عدد الكتب حسب المراحل."""
    async with get_db_connection() as db:
        async with db.execute("""
            SELECT st.name as stage_name, COUNT(b.id) as books_cnt
            FROM stages st
            LEFT JOIN classes c ON c.stage_id = st.id
            LEFT JOIN books b ON b.class_id = c.id
            GROUP BY st.id, st.name;
        """) as cursor:
            rows = await cursor.fetchall()
            return [_dict(row) for row in rows]
