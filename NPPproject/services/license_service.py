import json
from database import get_connection
from datetime import date


AUTO_FIELD_KEYS = ["articles", "conferences", "textbooks", "methodical", "trainings"]

YEAR_FROM = lambda: date.today().year - 4

# Типи публікацій → ключ авто-поля
PUB_TYPE_MAP = {
    "article":          "articles",
    "conference_paper": "conferences",
    "textbook":         "textbooks",
    "monograph":        "methodical",
    "other":            "methodical",
    "patent":           "methodical",
}


# ── Утиліти для JSON-значень ──────────────────────────────────────────────────

def is_json_ids(val: str) -> bool:
    if not val or not val.startswith("{"):
        return False
    try:
        d = json.loads(val)
        return isinstance(d, dict) and "ids" in d
    except Exception:
        return False


def encode_ids(ids: list) -> str:
    """Список id → JSON-рядок для збереження в БД."""
    return json.dumps({"ids": ids}, ensure_ascii=False)


def decode_ids(val: str) -> list:
    """JSON-рядок → список id."""
    try:
        return json.loads(val).get("ids", [])
    except Exception:
        return []


# ── Читання публікацій/тренінгів з БД ────────────────────────────────────────

def _fetch_pub_labels(cur, teacher_id: str,
                      specific_ids: list | None,
                      last_5_years: bool) -> dict:
    """
    Повертає {field_key: "текст; текст"} для публікацій.
    specific_ids=None → всі публікації викладача (режим __DB__)
    specific_ids=[..] → тільки ці id
    В обох випадках застосовується фільтр року якщо last_5_years=True.
    """
    year_cond = f"AND (p.year >= {YEAR_FROM()} OR p.year IS NULL)" if last_5_years else ""

    if specific_ids is None:
        cur.execute(f"""
            SELECT p.id::text, p.type, p.title, p.year
            FROM publications p
            JOIN publication_authors pa ON pa.publication_id = p.id
            WHERE pa.teacher_id = %s {year_cond}
            ORDER BY p.year DESC NULLS LAST, p.title
        """, (teacher_id,))
    else:
        if not specific_ids:
            return {k: "" for k in ["articles", "conferences", "textbooks", "methodical"]}
        cur.execute(f"""
            SELECT p.id::text, p.type, p.title, p.year
            FROM publications p
            WHERE p.id = ANY(%s::uuid[]) {year_cond}
            ORDER BY p.year DESC NULLS LAST, p.title
        """, (specific_ids,))

    groups: dict[str, list] = {
        "articles": [], "conferences": [], "textbooks": [], "methodical": []}
    for pub_id, pub_type, title, year in cur.fetchall():
        key   = PUB_TYPE_MAP.get(pub_type, "methodical")
        label = f"{title} ({year})" if year else title
        groups[key].append(label)

    return {k: "; ".join(v) for k, v in groups.items()}


def _fetch_training_labels(cur, teacher_id: str,
                           specific_ids: list | None,
                           last_5_years: bool) -> str:
    """Повертає "текст; текст" для тренінгів."""
    year_cond = (
        f"AND (EXTRACT(YEAR FROM start_date) >= {YEAR_FROM()} OR start_date IS NULL)"
        if last_5_years else ""
    )

    if specific_ids is None:
        cur.execute(f"""
            SELECT title, provider, start_date, hours, ects
            FROM trainings
            WHERE teacher_id = %s {year_cond}
            ORDER BY start_date DESC NULLS LAST
        """, (teacher_id,))
    else:
        if not specific_ids:
            return ""
        cur.execute(f"""
            SELECT title, provider, start_date, hours, ects
            FROM trainings
            WHERE id = ANY(%s::uuid[]) {year_cond}
            ORDER BY start_date DESC NULLS LAST
        """, (specific_ids,))

    parts_list = []
    for title, provider, start, hours, ects in cur.fetchall():
        parts = [title]
        if provider: parts.append(provider)
        if start:    parts.append(str(start)[:7])
        if hours:    parts.append(f"{hours} год.")
        if ects:     parts.append(f"{ects} ЄКТС")
        parts_list.append(", ".join(parts))
    return "; ".join(parts_list)


def _filter_text_by_year(text: str) -> str:
    """
    Фільтрує елементи ручного тексту по роках.
    Формат елементів: "Назва (2023)" або "Назва" (без року).
    Якщо рік вказано і він старший за year_from — елемент прибирається.
    Якщо рік не вказано — залишається (не можемо визначити).
    """
    import re
    yf    = YEAR_FROM()
    parts = [p.strip() for p in text.split(";") if p.strip()]
    out   = []
    for part in parts:
        m = re.search(r"\((\d{4})\)\s*$", part)
        if m:
            if int(m.group(1)) >= yf:
                out.append(part)
        else:
            out.append(part)
    return "; ".join(out)


def _resolve_field(cur, teacher_id: str, fkey: str, raw: str,
                   last_5_years: bool) -> str:
    """
    Розкриває raw значення поля у відображуваний текст з урахуванням фільтра.
      ""        → ""
      "__DB__"  → всі записи з БД (з фільтром)
      JSON ids  → тільки обрані id (з фільтром)
    """
    if not raw:
        return ""

    if raw == "__DB__":
        if fkey == "trainings":
            return _fetch_training_labels(cur, teacher_id, None, last_5_years)
        else:
            labels = _fetch_pub_labels(cur, teacher_id, None, last_5_years)
            return labels.get(fkey, "")

    if is_json_ids(raw):
        ids = decode_ids(raw)
        if fkey == "trainings":
            return _fetch_training_labels(cur, teacher_id, ids, last_5_years)
        else:
            labels = _fetch_pub_labels(cur, teacher_id, ids, last_5_years)
            return labels.get(fkey, "")

    # Ручний текст — фільтруємо по роках
    if last_5_years:
        return _filter_text_by_year(raw)
    return raw


# ── Публічне API ─────────────────────────────────────────────────────────────

def get_disciplines_by_teacher(teacher_id: str,
                                last_5_years: bool = False) -> list:
    """
    Повертає список дисциплін з відображуваними текстами авто-полів.
    Фільтр last_5_years застосовується до __DB__ і JSON-ids.
    Кожна дисципліна також містить "_raw" версії для діалогу редагування.
    """
    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("""
        SELECT id, course_name, specialty,
               COALESCE(syllabus_url, ''),
               COALESCE(program_url, ''),
               sort_order
        FROM license_disciplines
        WHERE teacher_id = %s
        ORDER BY sort_order, id
    """, (teacher_id,))
    rows = cur.fetchall()

    if not rows:
        cur.close(); conn.close()
        return []

    disc_ids = [r[0] for r in rows]
    cur.execute("""
        SELECT discipline_id, field_key, field_value
        FROM license_auto_fields
        WHERE discipline_id = ANY(%s)
    """, (disc_ids,))
    raw_map: dict[int, dict] = {}
    for disc_id, fkey, fval in cur.fetchall():
        raw_map.setdefault(disc_id, {})[fkey] = fval or ""

    result = []
    for disc_id, course_name, specialty, syllabus_url, program_url, _ in rows:
        raw = raw_map.get(disc_id, {})
        entry = {
            "id":           disc_id,
            "course_name":  course_name  or "",
            "specialty":    specialty    or "",
            "syllabus_url": syllabus_url,
            "program_url":  program_url,
        }
        for fkey in AUTO_FIELD_KEYS:
            raw_val = raw.get(fkey, "")
            # Відображуваний текст (з фільтром)
            entry[fkey] = _resolve_field(
                cur, teacher_id, fkey, raw_val, last_5_years)
            # Сирий raw для діалогу (без фільтра) — щоб знати тип
            entry[f"_raw_{fkey}"] = raw_val

        result.append(entry)

    cur.close(); conn.close()
    return result


def save_disciplines(teacher_id: str, disciplines: list):
    """
    Зберігає дисципліни.
    Авто-поля:
      ""        → видалити запис (порожньо)
      "__DB__"  → зберегти як є
      JSON ids  → зберегти як є
      текст     → зберегти як є (зворотна сумісність / ручне введення)
    """
    conn = get_connection()
    cur  = conn.cursor()

    cur.execute(
        "SELECT id FROM license_disciplines WHERE teacher_id = %s", (teacher_id,))
    existing_ids = {r[0] for r in cur.fetchall()}
    incoming_ids = {d["id"] for d in disciplines if d.get("id")}

    to_delete = existing_ids - incoming_ids
    if to_delete:
        cur.execute(
            "DELETE FROM license_disciplines WHERE id = ANY(%s)",
            (list(to_delete),))

    for order_i, disc in enumerate(disciplines):
        disc_id     = disc.get("id")
        course_name = disc.get("course_name", "").strip()
        specialty   = disc.get("specialty",   "").strip() or None
        syllabus    = disc.get("syllabus_url","").strip() or None
        program     = disc.get("program_url", "").strip() or None

        if disc_id:
            cur.execute("""
                UPDATE license_disciplines
                SET course_name=%s, specialty=%s,
                    syllabus_url=%s, program_url=%s, sort_order=%s
                WHERE id=%s
            """, (course_name, specialty, syllabus, program, order_i, disc_id))
        else:
            cur.execute("""
                INSERT INTO license_disciplines
                    (teacher_id, course_name, specialty,
                     syllabus_url, program_url, sort_order)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (teacher_id, course_name, specialty, syllabus, program, order_i))
            disc_id = cur.fetchone()[0]
            disc["id"] = disc_id

        for fkey in AUTO_FIELD_KEYS:
            fval = disc.get(fkey, "")
            if fval:
                cur.execute("""
                    INSERT INTO license_auto_fields
                        (discipline_id, field_key, field_value)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (discipline_id, field_key)
                    DO UPDATE SET field_value = EXCLUDED.field_value
                """, (disc_id, fkey, fval))
            else:
                cur.execute("""
                    DELETE FROM license_auto_fields
                    WHERE discipline_id=%s AND field_key=%s
                """, (disc_id, fkey))

    conn.commit()
    cur.close(); conn.close()


# ── Дані для головної таблиці ─────────────────────────────────────────────────

def get_teachers_for_license_table(last_5_years: bool = False) -> list:
    conn = get_connection()
    cur  = conn.cursor()

    year_from = date.today().year - 4 if last_5_years else None

    cur.execute("""
        SELECT t.id::text,
               t.last_name || ' ' || t.first_name || ' ' ||
               COALESCE(t.middle_name, '') AS full_name
        FROM teachers t
        ORDER BY t.last_name, t.first_name
    """)
    teachers = cur.fetchall()

    cur.execute(f"""
        SELECT pa.teacher_id::text, p.type, p.title, p.year
        FROM publications p
        JOIN publication_authors pa ON pa.publication_id = p.id
        {("WHERE p.year >= %s OR p.year IS NULL" if year_from else "WHERE TRUE")}
        ORDER BY p.year DESC NULLS LAST, p.title
    """, ([year_from] if year_from else []))
    pub_rows = cur.fetchall()

    cur.execute(f"""
        SELECT teacher_id::text, title, provider, start_date, hours, ects
        FROM trainings
        {("WHERE EXTRACT(YEAR FROM start_date) >= %s OR start_date IS NULL" if year_from else "")}
        ORDER BY start_date DESC NULLS LAST
    """, ([year_from] if year_from else []))
    training_rows = cur.fetchall()

    cur.close(); conn.close()

    pub_map: dict[str, dict] = {}
    for tid, pub_type, title, year in pub_rows:
        pub_map.setdefault(tid, {}).setdefault(pub_type, [])
        label = f"{title} ({year})" if year else title
        pub_map[tid][pub_type].append(label)

    train_map: dict[str, list] = {}
    for tid, title, provider, start, hours, ects in training_rows:
        parts = [title]
        if provider: parts.append(provider)
        if start:    parts.append(str(start)[:7])
        if hours:    parts.append(f"{hours} год.")
        if ects:     parts.append(f"{ects} ЄКТС")
        train_map.setdefault(tid, []).append(", ".join(parts))

    result = []
    for tid, full_name in teachers:
        pubs = pub_map.get(tid, {})
        result.append({
            "teacher_id":  tid,
            "full_name":   full_name.strip(),
            "articles":    "; ".join(pubs.get("article", [])),
            "conferences": "; ".join(pubs.get("conference_paper", [])),
            "textbooks":   "; ".join(pubs.get("textbook", [])),
            "methodical":  "; ".join(
                pubs.get("monograph", []) +
                pubs.get("other",     []) +
                pubs.get("patent",    [])
            ),
            "trainings":   "; ".join(train_map.get(tid, [])),
        })
    return result


# ── Для діалогу вибору ────────────────────────────────────────────────────────

def get_publications_by_teacher(teacher_id: str,
                                 last_5_years: bool = False) -> dict:
    conn = get_connection()
    cur  = conn.cursor()
    year_cond = (
        f"AND (p.year >= {YEAR_FROM()} OR p.year IS NULL)" if last_5_years else "")
    cur.execute(f"""
        SELECT p.id::text, p.type, p.title, p.year
        FROM publications p
        JOIN publication_authors pa ON pa.publication_id = p.id
        WHERE pa.teacher_id = %s {year_cond}
        ORDER BY p.year DESC NULLS LAST, p.title
    """, (teacher_id,))
    result: dict[str, list] = {
        "articles": [], "conferences": [], "textbooks": [], "methodical": []}
    for pub_id, pub_type, title, year in cur.fetchall():
        key   = PUB_TYPE_MAP.get(pub_type, "methodical")
        label = f"{title} ({year})" if year else title
        result[key].append({"id": pub_id, "label": label})
    cur.close(); conn.close()
    return result


def get_trainings_by_teacher(teacher_id: str,
                              last_5_years: bool = False) -> list:
    conn = get_connection()
    cur  = conn.cursor()
    year_cond = (
        f"AND (EXTRACT(YEAR FROM start_date) >= {YEAR_FROM()} OR start_date IS NULL)"
        if last_5_years else ""
    )
    cur.execute(f"""
        SELECT id::text, title, provider, start_date, hours, ects
        FROM trainings
        WHERE teacher_id = %s {year_cond}
        ORDER BY start_date DESC NULLS LAST
    """, (teacher_id,))
    result = []
    for tid, title, provider, start, hours, ects in cur.fetchall():
        parts = [title]
        if provider: parts.append(provider)
        if start:    parts.append(str(start)[:7])
        if hours:    parts.append(f"{hours} год.")
        if ects:     parts.append(f"{ects} ЄКТС")
        result.append({"id": tid, "label": ", ".join(parts)})
    cur.close(); conn.close()
    return result
