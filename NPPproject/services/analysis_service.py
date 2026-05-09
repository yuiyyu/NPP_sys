"""
Сервіс аналізу відповідності НПП вимогам ліцензійних умов.
Види досягнень у професійній діяльності за останні 5 років.
"""
from datetime import date
from database import get_connection

CUTOFF_YEAR = date.today().year - 5
CUTOFF_DATE = date(CUTOFF_YEAR, 1, 1)

# Мінімальна норма підвищення кваліфікації (п.38 ЛУ)
MIN_ECTS = 6.0

# Мінімальна кількість публікацій (п.35, п.36 ЛУ)
MIN_PUBLICATIONS = 5

# Посади які потребують наукового ступеня
POSITIONS_NEED_DEGREE = ["професор", "доцент", "старший викладач"]


def get_teacher_full_info(teacher_id: str) -> dict | None:
    """Повертає повну інформацію про викладача з БД."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            t.id,
            t.first_name,
            t.last_name,
            t.middle_name,
            t.employment_start_date,
            t.status,
            ad.name AS degree,
            at2.name AS title,
            d.name AS department
        FROM teachers t
        LEFT JOIN academic_degrees ad ON ad.id = t.academic_degree_id
        LEFT JOIN academic_titles at2 ON at2.id = t.academic_title_id
        LEFT JOIN departments d ON d.id = t.department_id
        WHERE t.id = %s
    """, (teacher_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return None

    return {
        "id":           str(row[0]),
        "first_name":   row[1],
        "last_name":    row[2],
        "middle_name":  row[3] or "",
        "employment_start_date": row[4],
        "status":       row[5] or "",
        "degree":       row[6] or "",
        "title":        row[7] or "",
        "department":   row[8] or "",
    }


def get_trainings_analysis(teacher_id: str) -> dict:
    """Аналіз підвищення кваліфікації за останні 5 років."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            COUNT(*),
            COALESCE(SUM(hours), 0),
            COALESCE(SUM(ects), 0)
        FROM trainings
        WHERE teacher_id = %s
          AND start_date >= %s
    """, (teacher_id, CUTOFF_DATE))
    row = cur.fetchone()
    cur.close()
    conn.close()

    count      = int(row[0])
    total_hours = float(row[1])
    total_ects  = float(row[2])

    return {
        "count":       count,
        "hours":       total_hours,
        "ects":        total_ects,
        "norm_met":    total_ects >= MIN_ECTS,
        "min_ects":    MIN_ECTS,
    }


def get_publications_analysis(teacher_id: str) -> dict:
    """Аналіз публікацій за останні 5 років (тільки активні - не архівні)."""
    conn = get_connection()
    cur = conn.cursor()

    # Всі публікації за 5 років (не архівні)
    cur.execute("""
        SELECT p.type, COUNT(*)
        FROM publications p
        JOIN publication_authors pa ON pa.publication_id = p.id
        WHERE pa.teacher_id = %s
          AND p.year >= %s
          AND p.archived_at IS NULL
        GROUP BY p.type
    """, (teacher_id, CUTOFF_YEAR))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    by_type = {row[0]: int(row[1]) for row in rows}

    articles     = by_type.get("article", 0)
    monographs   = by_type.get("monograph", 0)
    conferences  = by_type.get("conference_paper", 0)
    textbooks    = by_type.get("textbook", 0)
    patents      = by_type.get("patent", 0)
    other        = by_type.get("other", 0)
    total        = sum(by_type.values())

    # Публікації що зараховуються як досягнення п.35-36 ЛУ:
    # статті у фахових виданнях + статті Scopus/WoS
    scored_pubs = articles + conferences
    # Підручник/монографія - окреме досягнення п.37
    has_textbook_or_monograph = (textbooks + monographs) > 0

    return {
        "total":        total,
        "articles":     articles,
        "monographs":   monographs,
        "conferences":  conferences,
        "textbooks":    textbooks,
        "patents":      patents,
        "other":        other,
        "scored_pubs":  scored_pubs,
        "has_textbook_or_monograph": has_textbook_or_monograph,
        "norm_met":     scored_pubs >= MIN_PUBLICATIONS,
        "min_pubs":     MIN_PUBLICATIONS,
    }


def _calc_npp_experience_years(employment_start_date) -> float:
    """Розраховує стаж НПП роботи в роках."""
    if not employment_start_date:
        return 99.0
    today = date.today()
    delta = today - employment_start_date
    return delta.days / 365.25


def build_analysis(teacher_id: str) -> dict:
    """
    Збирає повний аналіз НПП.
    Повертає dict з усіма даними для відображення у діалозі.
    """
    teacher    = get_teacher_full_info(teacher_id)
    if not teacher:
        return {}

    trainings  = get_trainings_analysis(teacher_id)
    pubs       = get_publications_analysis(teacher_id)
    exp_years  = _calc_npp_experience_years(teacher["employment_start_date"])

    # ── Підрахунок досягнень (п.35-38 ЛУ) ────────────────────────────────────
    # Вимога не застосовується до НПП зі стажем < 3 років (п.38 ЛУ)
    exempt_from_requirements = exp_years < 3.0

    achievements = []

    # Досягнення 1: публікації (мін. 5 статей у фахових/Scopus/WoS виданнях)
    achievements.append({
        "title":   "Наукові публікації у фахових/наукометричних виданнях (мін. 5)",
        "met":     pubs["norm_met"],
        "detail":  f"наявно {pubs['scored_pubs']} з {pubs['min_pubs']} необхідних",
    })

    # Досягнення 2: підручник, посібник або монографія
    achievements.append({
        "title":   "Підручник, навчальний посібник або монографія",
        "met":     pubs["has_textbook_or_monograph"],
        "detail":  f"наявно: {'так' if pubs['has_textbook_or_monograph'] else 'немає'}",
    })

    # Досягнення 3: підвищення кваліфікації (мін. 6 ЄКТС за 5 років)
    achievements.append({
        "title":   f"Підвищення кваліфікації (мін. {MIN_ECTS:.0f} кредитів ЄКТС)",
        "met":     trainings["norm_met"],
        "detail":  f"наявно {trainings['ects']:.2f} ЄКТС з {MIN_ECTS:.0f} необхідних",
    })

    # Досягнення 4: патенти (1 патент на винахід або 5 деклараційних)
    achievements.append({
        "title":   "Патент на винахід (або 5 деклараційних патентів)",
        "met":     pubs["patents"] >= 1,
        "detail":  f"наявно патентів: {pubs['patents']}",
    })

    met_count   = sum(1 for a in achievements if a["met"])
    total_need  = 4
    all_met     = met_count >= total_need

    # ── Заключення ────────────────────────────────────────────────────────────
    conclusions = _build_conclusions(
        teacher, trainings, pubs, achievements,
        met_count, all_met, exempt_from_requirements, exp_years
    )

    return {
        "teacher":                  teacher,
        "trainings":                trainings,
        "publications":             pubs,
        "achievements":             achievements,
        "met_count":                met_count,
        "total_need":               total_need,
        "all_met":                  all_met,
        "exempt_from_requirements": exempt_from_requirements,
        "exp_years":                exp_years,
        "conclusions":              conclusions,
        "cutoff_year":              CUTOFF_YEAR,
        "analysis_year":            date.today().year,
    }


def _build_conclusions(teacher, trainings, pubs, achievements,
                       met_count, all_met, exempt, exp_years) -> list[str]:
    """Формує список висновків у вигляді рядків тексту."""
    lines = []

    if exempt:
        lines.append(
            f"Стаж науково-педагогічної роботи складає менше 3 років "
            f"({exp_years:.1f} р.). Згідно з п.38 Ліцензійних умов (КМУ № 1187), "
            f"вимога щодо чотирьох видів досягнень до цього працівника не застосовується."
        )
        return lines

    # Підвищення кваліфікації
    if trainings["norm_met"]:
        lines.append(
            f"Норму підвищення кваліфікації виконано: "
            f"{trainings['ects']:.2f} ЄКТС за {CUTOFF_YEAR}-{date.today().year} рр. "
            f"(вимога - не менше {MIN_ECTS:.0f} ЄКТС за 5 років)."
        )
    else:
        deficit = MIN_ECTS - trainings["ects"]
        lines.append(
            f"Норму підвищення кваліфікації НЕ виконано: "
            f"наявно {trainings['ects']:.2f} ЄКТС, "
            f"не вистачає {deficit:.2f} ЄКТС до мінімальних {MIN_ECTS:.0f} ЄКТС за 5 років."
        )

    # Публікації
    if pubs["norm_met"]:
        lines.append(
            f"Вимогу щодо публікацій виконано: "
            f"{pubs['scored_pubs']} публікацій у фахових та наукометричних виданнях."
        )
    else:
        deficit = pubs["min_pubs"] - pubs["scored_pubs"]
        lines.append(
            f"Вимогу щодо публікацій НЕ виконано: "
            f"наявно {pubs['scored_pubs']} з необхідних {pubs['min_pubs']} публікацій "
            f"у фахових або наукометричних виданнях. "
            f"Рекомендується додати не менше {deficit} публікацій."
        )

    # Підручник/монографія
    if not pubs["has_textbook_or_monograph"]:
        lines.append(
            "Відсутній підручник, навчальний посібник або монографія "
            "за останні 5 років. Рекомендується підготувати навчально-методичне "
            "або наукове видання."
        )

    # Патенти
    if pubs["patents"] == 0:
        lines.append(
            "Патентів на винаходи або корисні моделі не зафіксовано. "
            "Якщо наявні - внесіть їх до системи для повноти аналізу."
        )

    # Загальне заключення
    lines.append(
        f"Загальна оцінка: виконано {met_count} з {4} необхідних видів досягнень "
        f"відповідно до п.35-38 Ліцензійних умов (КМУ № 1187 від 30.12.2015)."
    )

    if all_met:
        lines.append(
            "Висновок: науково-педагогічний працівник відповідає вимогам "
            "Ліцензійних умов провадження освітньої діяльності."
        )
    else:
        shortage = 4 - met_count
        lines.append(
            f"Висновок: науково-педагогічний працівник НЕ відповідає повною мірою "
            f"вимогам Ліцензійних умов - не вистачає {shortage} "
            f"{'виду' if shortage == 1 else 'видів'} досягнень з чотирьох необхідних."
        )

    return lines