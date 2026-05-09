from database import get_connection


def get_all_resources():
    """
    Повертає список викладачів із зовнішніми ресурсами.
    [(id, full_name, orcid, google_scholar_url)]
    """
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT
            id::text,
            last_name || ' ' || first_name || ' ' ||
                COALESCE(middle_name, '') AS full_name,
            COALESCE(orcid, '')              AS orcid,
            COALESCE(google_scholar_url, '') AS scholar
        FROM teachers
        ORDER BY last_name, first_name
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def update_resources(teacher_id: str, orcid: str, scholar: str):
    """
    Оновлює ORCID та Google Scholar для викладача в таблиці teachers.
    """
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        UPDATE teachers
        SET orcid              = %s,
            google_scholar_url = %s
        WHERE id = %s
    """, (orcid or None, scholar or None, teacher_id))
    conn.commit()
    cur.close()
    conn.close()