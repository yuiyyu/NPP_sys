from database import get_connection


# ── Кафедри ───────────────────────────────────────────────────────────────────

def get_all_departments():
    """[(id, name, code)]"""
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("SELECT id, name, COALESCE(code, '') FROM departments ORDER BY name")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def add_department(name: str, code: str):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute(
        "INSERT INTO departments (name, code) VALUES (%s, %s)",
        (name, code or None)
    )
    conn.commit()
    cur.close()
    conn.close()


def update_department(dep_id: int, name: str, code: str):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute(
        "UPDATE departments SET name = %s, code = %s WHERE id = %s",
        (name, code or None, dep_id)
    )
    conn.commit()
    cur.close()
    conn.close()


def delete_department(dep_id: int):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("DELETE FROM departments WHERE id = %s", (dep_id,))
    conn.commit()
    cur.close()
    conn.close()


# ── Наукові ступені ───────────────────────────────────────────────────────────

def get_all_degrees():
    """[(id, name, short_name)]"""
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("SELECT id, name, COALESCE(short_name, '') FROM academic_degrees ORDER BY name")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def add_degree(name: str, short_name: str):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute(
        "INSERT INTO academic_degrees (name, short_name) VALUES (%s, %s)",
        (name, short_name or None)
    )
    conn.commit()
    cur.close()
    conn.close()


def update_degree(deg_id: int, name: str, short_name: str):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute(
        "UPDATE academic_degrees SET name = %s, short_name = %s WHERE id = %s",
        (name, short_name or None, deg_id)
    )
    conn.commit()
    cur.close()
    conn.close()


def delete_degree(deg_id: int):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("DELETE FROM academic_degrees WHERE id = %s", (deg_id,))
    conn.commit()
    cur.close()
    conn.close()


# ── Вчені звання ──────────────────────────────────────────────────────────────

def get_all_titles():
    """[(id, name)]"""
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("SELECT id, name FROM academic_titles ORDER BY name")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def add_title(name: str):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("INSERT INTO academic_titles (name) VALUES (%s)", (name,))
    conn.commit()
    cur.close()
    conn.close()


def update_title(title_id: int, name: str):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("UPDATE academic_titles SET name = %s WHERE id = %s", (name, title_id))
    conn.commit()
    cur.close()
    conn.close()


def delete_title(title_id: int):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("DELETE FROM academic_titles WHERE id = %s", (title_id,))
    conn.commit()
    cur.close()
    conn.close()