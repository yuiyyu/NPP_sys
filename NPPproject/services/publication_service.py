import uuid
from database import get_connection


def get_all_publications():
    """
    Повертає активні публікації (archived_at IS NULL) через v_active_publications.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, title, type, year, journal_or_publisher, doi, url, authors
        FROM v_active_publications
        ORDER BY year DESC, title;
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def get_publication_by_id(pub_id: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, title, type, year, journal_or_publisher, doi, url
        FROM publications
        WHERE id = %s
    """, (pub_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def get_publication_author_ids(pub_id: str) -> list:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT teacher_id
        FROM publication_authors
        WHERE publication_id = %s
        ORDER BY author_order
    """, (pub_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [str(r[0]) for r in rows]


def add_publication(data: dict, author_ids: list):
    conn = get_connection()
    cur = conn.cursor()
    pub_id = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO publications (id, title, type, year, journal_or_publisher, doi, url)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        pub_id,
        data["title"],
        data["type"] or None,
        data["year"] or None,
        data["journal_or_publisher"] or None,
        data["doi"] or None,
        data["url"] or None,
    ))
    _save_authors(cur, pub_id, author_ids)
    conn.commit()
    cur.close()
    conn.close()


def update_publication(pub_id: str, data: dict, author_ids: list):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE publications SET
            title                = %s,
            type                 = %s,
            year                 = %s,
            journal_or_publisher = %s,
            doi                  = %s,
            url                  = %s
        WHERE id = %s
    """, (
        data["title"],
        data["type"] or None,
        data["year"] or None,
        data["journal_or_publisher"] or None,
        data["doi"] or None,
        data["url"] or None,
        pub_id,
    ))
    cur.execute("DELETE FROM publication_authors WHERE publication_id = %s", (pub_id,))
    _save_authors(cur, pub_id, author_ids)
    conn.commit()
    cur.close()
    conn.close()


def delete_publication(pub_id: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM publication_authors WHERE publication_id = %s", (pub_id,))
    cur.execute("DELETE FROM publications WHERE id = %s", (pub_id,))
    conn.commit()
    cur.close()
    conn.close()


def _save_authors(cur, pub_id: str, author_ids: list):
    for order, teacher_id in enumerate(author_ids, start=1):
        cur.execute("""
            INSERT INTO publication_authors (publication_id, teacher_id, author_order)
            VALUES (%s, %s, %s)
        """, (pub_id, teacher_id, order))


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


PUBLICATION_TYPES = [
    "article",
    "monograph",
    "conference_paper",
    "textbook",
    "patent",
    "other",
]

PUBLICATION_TYPE_LABELS = {
    "article":          "Стаття",
    "monograph":        "Монографія",
    "conference_paper": "Тези / матеріали конференції",
    "textbook":         "Підручник / навчальний посібник",
    "patent":           "Патент",
    "other":            "Інше",
}