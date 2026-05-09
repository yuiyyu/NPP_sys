import uuid
from database import get_connection


def get_all_teachers():
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT 
            t.id,
            t.last_name,
            t.first_name,
            COALESCE(t.middle_name, ''),
            COALESCE(t.date_of_birth::text, ''),
            COALESCE(ad.name, '—'),
            COALESCE(at.name, '—'),
            COALESCE(d.name, '—'),
            COALESCE(t.orcid, ''),
            COALESCE(t.google_scholar_url, ''),
            COALESCE(t.email, ''),
            COALESCE(t.phone, ''),
            COALESCE(t.employment_start_date::text, ''),
            COALESCE(t.employment_end_date::text, ''),
            COALESCE(t.status, ''),
            COALESCE(t.notes, '')
        FROM teachers t
        LEFT JOIN academic_degrees ad ON t.academic_degree_id = ad.id
        LEFT JOIN academic_titles at ON t.academic_title_id = at.id
        LEFT JOIN departments d ON t.department_id = d.id
        ORDER BY t.last_name, t.first_name;
    """

    cur.execute(query)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def get_teacher_by_id(teacher_id):
    """Повертає повний запис викладача для форми редагування."""
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT 
            id,
            first_name,
            last_name,
            middle_name,
            date_of_birth,
            academic_degree_id,
            academic_title_id,
            department_id,
            orcid,
            google_scholar_url,
            email,
            phone,
            employment_start_date,
            employment_end_date,
            status,
            notes
        FROM teachers
        WHERE id = %s
    """
    cur.execute(query, (teacher_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def add_teacher(data: dict):
    conn = get_connection()
    cur = conn.cursor()
    teacher_id = str(uuid.uuid4())

    query = """
        INSERT INTO teachers (
            id,
            first_name, last_name, middle_name,
            date_of_birth,
            academic_degree_id, academic_title_id, department_id,
            orcid, google_scholar_url,
            email, phone,
            employment_start_date, employment_end_date,
            status, notes
        )
        VALUES (
            %s,
            %s, %s, %s,
            %s,
            %s, %s, %s,
            %s, %s,
            %s, %s,
            %s, %s,
            %s, %s
        )
    """

    cur.execute(query, (
        teacher_id,
        data["first_name"], data["last_name"], data["middle_name"] or None,
        data["date_of_birth"] or None,
        data["degree_id"] or None, data["title_id"] or None, data["department_id"] or None,
        data["orcid"] or None, data["google_scholar_url"] or None,
        data["email"] or None, data["phone"] or None,
        data["employment_start_date"] or None, data["employment_end_date"] or None,
        data["status"], data["notes"] or None,
    ))

    conn.commit()
    cur.close()
    conn.close()


def update_teacher(teacher_id: str, data: dict):
    conn = get_connection()
    cur = conn.cursor()

    query = """
        UPDATE teachers SET
            first_name            = %s,
            last_name             = %s,
            middle_name           = %s,
            date_of_birth         = %s,
            academic_degree_id    = %s,
            academic_title_id     = %s,
            department_id         = %s,
            orcid                 = %s,
            google_scholar_url    = %s,
            email                 = %s,
            phone                 = %s,
            employment_start_date = %s,
            employment_end_date   = %s,
            status                = %s,
            notes                 = %s
        WHERE id = %s
    """

    cur.execute(query, (
        data["first_name"], data["last_name"], data["middle_name"] or None,
        data["date_of_birth"] or None,
        data["degree_id"] or None, data["title_id"] or None, data["department_id"] or None,
        data["orcid"] or None, data["google_scholar_url"] or None,
        data["email"] or None, data["phone"] or None,
        data["employment_start_date"] or None, data["employment_end_date"] or None,
        data["status"], data["notes"] or None,
        teacher_id,
    ))

    conn.commit()
    cur.close()
    conn.close()


def delete_teacher(teacher_id: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM teachers WHERE id = %s", (teacher_id,))
    conn.commit()
    cur.close()
    conn.close()


# ── Довідники ──────────────────────────────────────────────────────────────────

def get_academic_degrees():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM academic_degrees ORDER BY id")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def get_academic_titles():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM academic_titles ORDER BY id")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def get_departments():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM departments ORDER BY name")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows