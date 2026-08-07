from typing import List, Dict, Any, Optional
import datetime
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
        async with db.execute("SELECT id, name, COALESCE(sort_order, id) as sort_order FROM stages ORDER BY sort_order ASC, id ASC;") as cursor:
            rows = await cursor.fetchall()
            return [_dict(row) for row in rows]

async def get_all_stages_with_classes() -> List[Dict[str, Any]]:
    """جلب جميع المراحل مع صفوفها التابعة لعرضها في شاشة واحدة جليلة مرتبة حسب الترتيب الصحيح."""
    async with get_db_connection() as db:
        async with db.execute("SELECT id, name, COALESCE(sort_order, id) as sort_order FROM stages ORDER BY sort_order ASC, id ASC;") as cursor:
            stage_rows = await cursor.fetchall()
            stages = [_dict(r) for r in stage_rows]
            
        result = []
        for stage in stages:
            async with db.execute("SELECT id, stage_id, name, COALESCE(sort_order, id) as sort_order FROM classes WHERE stage_id = ? ORDER BY sort_order ASC, id ASC;", (stage['id'],)) as cursor:
                class_rows = await cursor.fetchall()
                classes = [_dict(r) for r in class_rows]
            result.append({
                "stage": stage,
                "classes": classes
            })
        return result

async def get_stage_by_id(stage_id: int) -> Optional[Dict[str, Any]]:
    async with get_db_connection() as db:
        async with db.execute("SELECT id, name, COALESCE(sort_order, id) as sort_order FROM stages WHERE id = ?;", (stage_id,)) as cursor:
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
        async with db.execute("SELECT id, stage_id, name, COALESCE(sort_order, id) as sort_order FROM classes WHERE stage_id = ? ORDER BY sort_order ASC, id ASC;", (stage_id,)) as cursor:
            rows = await cursor.fetchall()
            return [_dict(row) for row in rows]

async def get_class_by_id(class_id: int) -> Optional[Dict[str, Any]]:
    async with get_db_connection() as db:
        async with db.execute("""
            SELECT c.id, c.stage_id, c.name, COALESCE(c.sort_order, c.id) as sort_order, st.name as stage_name
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
            INSERT INTO books (class_id, title, description, telegram_file_id, downloads_count)
            VALUES (?, ?, ?, ?, 0);
        """, (class_id, title.strip(), description.strip() if description else "", telegram_file_id.strip()))
        await db.commit()
        return getattr(cursor, 'lastrowid', None)

async def increment_book_download_count(book_id: int) -> None:
    """زيادة عداد تحميل الكتاب بمقدار +1."""
    async with get_db_connection() as db:
        await db.execute("UPDATE books SET downloads_count = COALESCE(downloads_count, 0) + 1 WHERE id = ?;", (book_id,))
        await db.commit()

async def get_books_by_class(class_id: int) -> List[Dict[str, Any]]:
    """استرجاع جميع كتب صف محدد."""
    async with get_db_connection() as db:
        async with db.execute("""
            SELECT id, class_id, title, description, telegram_file_id, COALESCE(downloads_count, 0) as downloads_count, created_at
            FROM books WHERE class_id = ? ORDER BY id ASC;
        """, (class_id,)) as cursor:
            rows = await cursor.fetchall()
            return [_dict(row) for row in rows]

async def get_book_by_id(book_id: int) -> Optional[Dict[str, Any]]:
    """استرجاع تفاصيل كتاب واحد بجميع تفاصيله الهيكلية."""
    async with get_db_connection() as db:
        async with db.execute("""
            SELECT b.id, b.class_id, b.title, b.description, b.telegram_file_id,
                   COALESCE(b.downloads_count, 0) as downloads_count, b.created_at,
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
                   COALESCE(b.downloads_count, 0) as downloads_count,
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

async def get_total_downloads_count() -> int:
    """إجمالي عدد التحميلات في البوت."""
    async with get_db_connection() as db:
        async with db.execute("SELECT SUM(COALESCE(downloads_count, 0)) FROM books;") as cursor:
            row = await cursor.fetchone()
            val = _val(row, 0)
            return val if val else 0

async def get_top_downloaded_books(limit: int = 5) -> List[Dict[str, Any]]:
    """أكثر الكتب تحميلاً."""
    async with get_db_connection() as db:
        async with db.execute("""
            SELECT b.id, b.title, COALESCE(b.downloads_count, 0) as downloads_count,
                   c.name as class_name, st.name as stage_name
            FROM books b
            JOIN classes c ON b.class_id = c.id
            JOIN stages st ON c.stage_id = st.id
            WHERE COALESCE(b.downloads_count, 0) > 0
            ORDER BY b.downloads_count DESC, b.id DESC LIMIT ?;
        """, (limit,)) as cursor:
            rows = await cursor.fetchall()
            return [_dict(row) for row in rows]

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

async def record_download_log(book_id: int, telegram_id: Optional[int] = None) -> None:
    """تسجيل عملية التحميل في السجل مع زيادة العداد والتدوير التلقائي للسجلات لآخر 90 يوماً."""
    async with get_db_connection() as db:
        await db.execute("UPDATE books SET downloads_count = COALESCE(downloads_count, 0) + 1 WHERE id = ?;", (book_id,))
        await db.execute("INSERT INTO download_logs (book_id, telegram_id) VALUES (?, ?);", (book_id, telegram_id))
        try:
            cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=90)).strftime("%Y-%m-%d %H:%M:%S")
            await db.execute("DELETE FROM download_logs WHERE downloaded_at < ?;", (cutoff,))
        except Exception:
            pass
        await db.commit()

async def get_filtered_stats(timeframe: str = "all", custom_start: Optional[str] = None, custom_end: Optional[str] = None) -> Dict[str, Any]:
    """استرجاع الإحصائيات الشاملة مفلترة حسب الفترة الزمنية (اليوم، 7 أيام، 30 يوماً، أو تاريخ مخصص)."""
    now = datetime.datetime.now(datetime.timezone.utc)
    start_dt = None
    end_dt = None
    
    if timeframe == "today":
        start_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif timeframe == "7days":
        start_dt = now - datetime.timedelta(days=7)
    elif timeframe == "30days":
        start_dt = now - datetime.timedelta(days=30)
    elif timeframe == "custom" and custom_start:
        try:
            start_dt = datetime.datetime.strptime(custom_start.strip(), "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
            if custom_end:
                end_dt = datetime.datetime.strptime(custom_end.strip(), "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=datetime.timezone.utc)
        except Exception:
            start_dt = None
            end_dt = None

    async with get_db_connection() as db:
        users_cnt = await get_users_count()
        stages_cnt = await get_stages_count()
        classes_cnt = await get_classes_count()
        books_cnt = await get_books_count()

        new_users_cnt = 0
        if start_dt:
            start_str = start_dt.strftime("%Y-%m-%d %H:%M:%S")
            if end_dt:
                end_str = end_dt.strftime("%Y-%m-%d %H:%M:%S")
                async with db.execute("SELECT COUNT(*) FROM users WHERE join_date >= ? AND join_date <= ?;", (start_str, end_str)) as cursor:
                    new_users_cnt = _val(await cursor.fetchone(), 0) or 0
            else:
                async with db.execute("SELECT COUNT(*) FROM users WHERE join_date >= ?;", (start_str,)) as cursor:
                    new_users_cnt = _val(await cursor.fetchone(), 0) or 0

        period_downloads = 0
        if start_dt:
            start_str = start_dt.strftime("%Y-%m-%d %H:%M:%S")
            if end_dt:
                end_str = end_dt.strftime("%Y-%m-%d %H:%M:%S")
                async with db.execute("SELECT COUNT(*) FROM download_logs WHERE downloaded_at >= ? AND downloaded_at <= ?;", (start_str, end_str)) as cursor:
                    period_downloads = _val(await cursor.fetchone(), 0) or 0
            else:
                async with db.execute("SELECT COUNT(*) FROM download_logs WHERE downloaded_at >= ?;", (start_str,)) as cursor:
                    period_downloads = _val(await cursor.fetchone(), 0) or 0
        else:
            period_downloads = await get_total_downloads_count()

        top_books = []
        if start_dt:
            start_str = start_dt.strftime("%Y-%m-%d %H:%M:%S")
            if end_dt:
                end_str = end_dt.strftime("%Y-%m-%d %H:%M:%S")
                sql = """
                    SELECT b.id, b.title, COUNT(dl.id) as downloads_count,
                           c.name as class_name, st.name as stage_name
                    FROM download_logs dl
                    JOIN books b ON dl.book_id = b.id
                    JOIN classes c ON b.class_id = c.id
                    JOIN stages st ON c.stage_id = st.id
                    WHERE dl.downloaded_at >= ? AND dl.downloaded_at <= ?
                    GROUP BY b.id, b.title, c.name, st.name
                    ORDER BY downloads_count DESC LIMIT 5;
                """
                params = (start_str, end_str)
            else:
                sql = """
                    SELECT b.id, b.title, COUNT(dl.id) as downloads_count,
                           c.name as class_name, st.name as stage_name
                    FROM download_logs dl
                    JOIN books b ON dl.book_id = b.id
                    JOIN classes c ON b.class_id = c.id
                    JOIN stages st ON c.stage_id = st.id
                    WHERE dl.downloaded_at >= ?
                    GROUP BY b.id, b.title, c.name, st.name
                    ORDER BY downloads_count DESC LIMIT 5;
                """
                params = (start_str,)
            async with db.execute(sql, params) as cursor:
                top_books = [_dict(r) for r in await cursor.fetchall()]
        else:
            top_books = await get_top_downloaded_books(limit=5)

        stage_percentages = []
        if start_dt:
            start_str = start_dt.strftime("%Y-%m-%d %H:%M:%S")
            if end_dt:
                end_str = end_dt.strftime("%Y-%m-%d %H:%M:%S")
                sql = """
                    SELECT st.name as stage_name, COUNT(dl.id) as dl_cnt
                    FROM download_logs dl
                    JOIN books b ON dl.book_id = b.id
                    JOIN classes c ON b.class_id = c.id
                    JOIN stages st ON c.stage_id = st.id
                    WHERE dl.downloaded_at >= ? AND dl.downloaded_at <= ?
                    GROUP BY st.id, st.name ORDER BY st.id ASC;
                """
                params = (start_str, end_str)
            else:
                sql = """
                    SELECT st.name as stage_name, COUNT(dl.id) as dl_cnt
                    FROM download_logs dl
                    JOIN books b ON dl.book_id = b.id
                    JOIN classes c ON b.class_id = c.id
                    JOIN stages st ON c.stage_id = st.id
                    WHERE dl.downloaded_at >= ?
                    GROUP BY st.id, st.name ORDER BY st.id ASC;
                """
                params = (start_str,)
            async with db.execute(sql, params) as cursor:
                rows = await cursor.fetchall()
                total_dl = sum([_val(r, 'dl_cnt') or 0 for r in rows])
                for r in rows:
                    cnt = _val(r, 'dl_cnt') or 0
                    pct = round((cnt / total_dl * 100), 1) if total_dl > 0 else 0
                    stage_percentages.append({
                        "stage_name": _val(r, 'stage_name'),
                        "count": cnt,
                        "pct": pct
                    })
        else:
            async with db.execute("""
                SELECT st.name as stage_name, SUM(COALESCE(b.downloads_count, 0)) as dl_cnt
                FROM stages st
                LEFT JOIN classes c ON c.stage_id = st.id
                LEFT JOIN books b ON b.class_id = c.id
                GROUP BY st.id, st.name ORDER BY st.id ASC;
            """) as cursor:
                rows = await cursor.fetchall()
                total_dl = sum([_val(r, 'dl_cnt') or 0 for r in rows])
                for r in rows:
                    cnt = _val(r, 'dl_cnt') or 0
                    pct = round((cnt / total_dl * 100), 1) if total_dl > 0 else 0
                    stage_percentages.append({
                        "stage_name": _val(r, 'stage_name'),
                        "count": cnt,
                        "pct": pct
                    })

        return {
            "users_cnt": users_cnt,
            "new_users_cnt": new_users_cnt,
            "stages_cnt": stages_cnt,
            "classes_cnt": classes_cnt,
            "books_cnt": books_cnt,
            "period_downloads": period_downloads,
            "top_books": top_books,
            "stage_percentages": stage_percentages,
            "timeframe": timeframe,
            "custom_start": custom_start,
            "custom_end": custom_end
        }
