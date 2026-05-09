"""
Сервіс для роботи з архівом публікацій.
Підстава: Постанова КМУ № 1187 від 30.12.2015 —
  НПП підтверджують досягнення за останні 5 років.

Архів — це ті самі записи в таблиці publications,
де archived_at IS NOT NULL. Таблиця publication_authors
використовується без змін.
"""
from database import get_connection

PUBLICATION_TYPE_LABELS = {
    "article":          "Стаття",
    "monograph":        "Монографія",
    "conference_paper": "Тези / матеріали конференції",
    "textbook":         "Підручник / навчальний посібник",
    "patent":           "Патент",
    "other":            "Інше",
}


def get_all_archive_publications():
    """Повертає всі записи з архіву через v_archive_publications."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, title, type, year, journal_or_publisher,
               doi, url, archived_at, archive_reason, authors
        FROM v_archive_publications
        ORDER BY year DESC, title;
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def delete_archive_publication(pub_id: str):
    """
    Видаляє публікацію повністю з БД (разом з авторами каскадно).
    publication_authors видаляться якщо є ON DELETE CASCADE,
    інакше видаляємо явно.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM publication_authors WHERE publication_id = %s", (pub_id,)
    )
    cur.execute("DELETE FROM publications WHERE id = %s", (pub_id,))
    conn.commit()
    cur.close()
    conn.close()


def run_auto_archive() -> int:
    """
    Позначає публікації старші 5 років як архівні (archived_at = NOW()).
    Повертає кількість оновлених записів.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT archive_old_publications()")
    count = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return count


def get_all_teachers_for_select():
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