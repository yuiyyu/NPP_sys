import uuid
from database import get_connection


# ── Довідники ─────────────────────────────────────────────────────────────────

TRAINING_TYPES = [
    "course",
    "seminar",
    "internship",
    "conference",
    "webinar",
    "other",
]

TRAINING_TYPE_LABELS = {
    "course":       "Курси підвищення кваліфікації",
    "seminar":      "Семінар / тренінг",
    "internship":   "Стажування",
    "conference":   "Конференція",
    "webinar":      "Вебінар",
    "other":        "Інше",
}


# ── Читання ───────────────────────────────────────────────────────────────────

def get_all_trainings():
    """Повертає всі записи для таблиці (всі викладачі)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            tr.id,
            t.last_name || ' ' || t.first_name || ' ' ||
                COALESCE(t.middle_name, '') AS teacher_name,
            tr.title,
            COALESCE(tr.type, ''),
            COALESCE(tr.provider, ''),
            COALESCE(tr.start_date::text, ''),
            COALESCE(tr.end_date::text, ''),
            COALESCE(tr.hours::text, ''),
            COALESCE(tr.ects::text, '')
        FROM trainings tr
        JOIN teachers t ON t.id = tr.teacher_id
        ORDER BY tr.start_date DESC NULLS LAST, t.last_name
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def get_trainings_by_teacher(teacher_id: str):
    """Повертає записи тільки одного викладача."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            tr.id,
            t.last_name || ' ' || t.first_name || ' ' ||
                COALESCE(t.middle_name, '') AS teacher_name,
            tr.title,
            COALESCE(tr.type, ''),
            COALESCE(tr.provider, ''),
            COALESCE(tr.start_date::text, ''),
            COALESCE(tr.end_date::text, ''),
            COALESCE(tr.hours::text, ''),
            COALESCE(tr.ects::text, '')
        FROM trainings tr
        JOIN teachers t ON t.id = tr.teacher_id
        WHERE tr.teacher_id = %s
        ORDER BY tr.start_date DESC NULLS LAST
    """, (teacher_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def get_training_by_id(training_id: str):
    """Повертає повний запис для форми редагування."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            id, teacher_id, title, type, provider,
            start_date, end_date, hours, ects
        FROM trainings
        WHERE id = %s
    """, (training_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


# ── Запис ─────────────────────────────────────────────────────────────────────

def add_training(data: dict):
    conn = get_connection()
    cur = conn.cursor()
    training_id = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO trainings (
            id, teacher_id, title, type, provider,
            start_date, end_date, hours, ects
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        training_id,
        data["teacher_id"],
        data["title"],
        data["type"]       or None,
        data["provider"]   or None,
        data["start_date"] or None,
        data["end_date"]   or None,
        data["hours"]      or None,
        data["ects"]       or None,
    ))
    conn.commit()
    cur.close()
    conn.close()


def update_training(training_id: str, data: dict):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE trainings SET
            teacher_id = %s, title      = %s, type       = %s,
            provider   = %s, start_date = %s, end_date   = %s,
            hours      = %s, ects       = %s
        WHERE id = %s
    """, (
        data["teacher_id"],
        data["title"],
        data["type"]       or None,
        data["provider"]   or None,
        data["start_date"] or None,
        data["end_date"]   or None,
        data["hours"]      or None,
        data["ects"]       or None,
        training_id,
    ))
    conn.commit()
    cur.close()
    conn.close()


def delete_training(training_id: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM trainings WHERE id = %s", (training_id,))
    conn.commit()
    cur.close()
    conn.close()


# ── Допоміжні ─────────────────────────────────────────────────────────────────

def get_all_teachers_for_select():
    """Повертає [(id, ПІБ)] для комбобокса вибору викладача."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id,
               last_name || ' ' || first_name || ' ' ||
               COALESCE(middle_name, '') AS full_name
        FROM teachers
        ORDER BY last_name, first_name
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [(str(r[0]), r[1].strip()) for r in rows]


def get_training_summary(teacher_id: str = None):
    """
    Підсумок по викладачу (або по всіх якщо teacher_id=None).
    Повертає (total_hours, total_ects, count).
    """
    conn = get_connection()
    cur = conn.cursor()
    if teacher_id:
        cur.execute("""
            SELECT COALESCE(SUM(hours), 0),
                   COALESCE(SUM(ects), 0),
                   COUNT(*)
            FROM trainings
            WHERE teacher_id = %s
        """, (teacher_id,))
    else:
        cur.execute("""
            SELECT COALESCE(SUM(hours), 0),
                   COALESCE(SUM(ects), 0),
                   COUNT(*)
            FROM trainings
        """)
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def get_trainings_last_5_years():
    """Кількість викладачів що підвищили кваліфікацію за останні 5 років."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(DISTINCT teacher_id)
        FROM trainings
        WHERE start_date >= CURRENT_DATE - INTERVAL '5 years'
    """)
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else 0


def get_training_summary_5y(teacher_id: str):
    """
    Підсумок підвищення кваліфікації за останні 5 років.
    Повертає (total_hours, total_ects, count).
    """
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT COALESCE(SUM(hours), 0),
               COALESCE(SUM(ects), 0),
               COUNT(*)
        FROM trainings
        WHERE teacher_id = %s
          AND start_date >= CURRENT_DATE - INTERVAL '5 years'
    """, (teacher_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def get_trainings_by_teacher_5y(teacher_id: str):
    """Повертає записи тільки одного викладача за останні 5 років."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            tr.id,
            t.last_name || ' ' || t.first_name || ' ' ||
                COALESCE(t.middle_name, '') AS teacher_name,
            tr.title,
            COALESCE(tr.type, ''),
            COALESCE(tr.provider, ''),
            COALESCE(tr.start_date::text, ''),
            COALESCE(tr.end_date::text, ''),
            COALESCE(tr.hours::text, ''),
            COALESCE(tr.ects::text, '')
        FROM trainings tr
        JOIN teachers t ON t.id = tr.teacher_id
        WHERE tr.teacher_id = %s    
          AND tr.start_date >= CURRENT_DATE - INTERVAL '5 years'
        ORDER BY tr.start_date DESC NULLS LAST
    """, (teacher_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows