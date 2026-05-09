"""
Автоматичний пошук публікацій і тренінгів за назвою дисципліни.

Покращення:
  1. Морфологія через pymorphy3 (якщо встановлено) — зводить слова до нормальної форми
  2. Словник синонімів для ІТ/технічних термінів
  3. Бонус за рік публікації — новіші мають вищий score
"""
import re
from datetime import date

# ── Спроба підключити pymorphy3 ───────────────────────────────────────────────
try:
    import pymorphy3
    _morph = pymorphy3.MorphAnalyzer(lang="uk")
    MORPH_AVAILABLE = True
except ImportError:
    _morph = None
    MORPH_AVAILABLE = False

CURRENT_YEAR = date.today().year

# ── Стоп-слова ────────────────────────────────────────────────────────────────
STOP_WORDS = {
    # Прийменники, сполучники, частки
    "та", "і", "й", "або", "з", "із", "зі", "до", "для", "на", "по",
    "в", "у", "про", "як", "що", "це", "є", "не", "за", "при", "від",
    "під", "над", "між", "через", "після", "перед", "без", "крім",
    # Загальні академічні слова що не несуть змісту
    "теорія", "теорії", "практика", "практики", "основи", "вступ",
    "курс", "дисципліна", "навчання", "методи", "методологія",
    "аналіз", "системи", "система", "частина", "розділ", "модуль",
    "загальний", "спеціальний", "сучасний", "прикладний",
    # Англійські
    "the", "and", "or", "of", "in", "to", "for", "with", "a", "an",
    "introduction", "theory", "practice", "methods", "systems", "analysis",
    "based", "using", "applied",
}

MIN_WORD_LEN = 4

# ── Словник синонімів та розширень ────────────────────────────────────────────
# Формат: "слово_з_назви_дисципліни" → [додаткові слова для пошуку]
SYNONYMS: dict[str, list[str]] = {
    # Програмування
    "програмування":  ["програмний", "програма", "код", "coding", "programming"],
    "програм":        ["програмний", "програма", "код"],
    "алгоритм":       ["алгоритмічний", "algorithm"],
    "структур":       ["структурний", "структура"],

    # Бази даних
    "база":           ["бази", "бд", "database", "sql", "реляційн"],
    "баз":            ["бд", "database", "sql"],
    "sql":            ["база", "бд", "запит", "реляційн"],
    "database":       ["база", "бд", "sql"],

    # Мережі
    "мереж":          ["мережевий", "network", "протокол", "tcp"],
    "network":        ["мереж", "протокол", "комунікац"],
    "комунікац":      ["мереж", "протокол", "передача"],

    # ШІ та машинне навчання
    "інтелект":       ["штучний", "інтелектуальн", "нейрон", "навчання"],
    "машинн":         ["навчання", "нейрон", "класифікац", "learning"],
    "нейрон":         ["мереж", "глибок", "навчання", "neural"],
    "навчанн":        ["машинн", "нейрон", "learning", "training"],
    "learning":       ["навчання", "машинн", "нейрон"],
    "neural":         ["нейрон", "мереж", "глибок"],
    "deep":           ["глибок", "нейрон", "навчання"],

    # Безпека
    "безпек":         ["захист", "криптограф", "security", "кібер"],
    "кібер":          ["безпек", "захист", "атак", "вразливіст"],
    "криптограф":     ["шифрування", "безпек", "захист"],
    "security":       ["безпек", "захист", "кібер"],

    # Веб
    "веб":            ["web", "інтернет", "сайт", "браузер", "http"],
    "web":            ["веб", "інтернет", "сайт", "http"],
    "інтернет":       ["веб", "web", "мереж", "http"],

    # Операційні системи
    "операційн":      ["ос", "linux", "windows", "процес", "ядро"],
    "linux":          ["операційн", "unix", "ядро", "процес"],

    # Математика / статистика
    "математик":      ["математичн", "числов", "обчислен"],
    "статистик":      ["статистичн", "ймовірніст", "розподіл"],
    "ймовірніст":     ["статистик", "стохастичн", "випадков"],

    # Комп'ютерна графіка
    "графік":         ["графічн", "зображення", "візуаліз", "rendering"],
    "зображенн":      ["графік", "розпізнавання", "обробк"],

    # Хмарні технології
    "хмарн":          ["cloud", "сервіс", "віртуалізац", "docker"],
    "cloud":          ["хмарн", "сервіс", "aws", "azure"],

    # IoT / вбудовані системи
    "вбудован":       ["мікроконтролер", "embedded", "firmware", "iot"],
    "iot":            ["вбудован", "датчик", "мереж", "пристрій"],

    # Розробка ПЗ
    "розробк":        ["програмування", "тестування", "agile", "проект"],
    "тестуванн":      ["верифікац", "якість", "testing", "автоматизац"],
    "проектуванн":    ["архітектур", "uml", "патерн", "дизайн"],
    "архітектур":     ["проектуванн", "патерн", "дизайн", "microservice"],
}


# ── Морфологія ────────────────────────────────────────────────────────────────

def _normalize(word: str) -> str:
    """Зводить слово до нормальної форми (лема)."""
    if MORPH_AVAILABLE and _morph:
        parsed = _morph.parse(word)
        if parsed:
            return parsed[0].normal_form
    # Fallback: простий стемінг (обрізаємо до 70%, мін 4)
    if len(word) > 5:
        return word[:max(4, int(len(word) * 0.70))]
    return word


def _get_search_terms(keywords: list) -> set:
    """
    Розширює список ключових слів синонімами.
    Повертає множину нормалізованих термінів для пошуку.
    """
    terms = set()
    for kw in keywords:
        norm = _normalize(kw)
        terms.add(norm)
        terms.add(kw)  # оригінал теж
        # Додаємо синоніми
        for key, syns in SYNONYMS.items():
            if key in kw or kw in key or key in norm or norm in key:
                for s in syns:
                    terms.add(s)
                    terms.add(_normalize(s))
    return terms


def extract_keywords(text: str) -> list:
    """Витягує значущі ключові слова з тексту."""
    if not text:
        return []
    words = re.findall(r"[а-яіїєґa-z]{%d,}" % MIN_WORD_LEN, text.lower())
    keywords = [w for w in words if w not in STOP_WORDS]
    seen, unique = set(), []
    for w in keywords:
        if w not in seen:
            seen.add(w)
            unique.append(w)
    return unique


# ── Підрахунок score ──────────────────────────────────────────────────────────

def _year_bonus(label: str) -> float:
    """
    Повертає бонус за рік публікації:
      - поточний рік:       +1.5
      - 1-2 роки тому:      +1.0
      - 3-4 роки тому:      +0.5
      - 5+ років тому:       0
      - рік не знайдено:     0
    """
    m = re.search(r"\((\d{4})\)", label)
    if not m:
        return 0.0
    year = int(m.group(1))
    diff = CURRENT_YEAR - year
    if diff <= 0:   return 1.5
    if diff <= 2:   return 1.0
    if diff <= 4:   return 0.5
    return 0.0


def score_item(search_terms: set, label: str) -> float:
    """
    Рахує score для одного запису:
      - +1.0 за кожен знайдений термін у назві
      - +бонус за рік
    Повертає float.
    """
    if not search_terms or not label:
        return 0.0

    label_lower = label.lower()
    # Нормалізуємо слова з label для порівняння
    label_words = re.findall(r"[а-яіїєґa-z]{3,}", label_lower)
    label_norms = {_normalize(w) for w in label_words} | set(label_words)

    keyword_score = 0.0
    for term in search_terms:
        # Шукаємо або як підрядок або як нормалізовану форму
        if term in label_lower or term in label_norms:
            keyword_score += 1.0

    if keyword_score == 0:
        return 0.0

    return keyword_score + _year_bonus(label)


# ── Головна функція ───────────────────────────────────────────────────────────

def auto_match(disc_name: str, publications: dict, trainings: list,
               threshold: float = 1.0) -> dict:
    """
    Автоматично відбирає публікації і тренінги що підходять до дисципліни.

    Параметри:
        disc_name    — назва дисципліни / ОК
        publications — {"articles": [{"id","label"},...], ...}
        trainings    — [{"id","label"}, ...]
        threshold    — мінімальний score (за замовчуванням 1.0)

    Повертає:
        {
          "articles":    [{"id","label","score"}, ...],  # відсортовано за score DESC
          "conferences": [...],
          "textbooks":   [...],
          "methodical":  [...],
          "trainings":   [...],
          "keywords":    ["слово1", ...],
          "search_terms": ["термін1", ...],   # розширений список для відображення
          "morph_used":  True/False,
        }
    """
    keywords     = extract_keywords(disc_name)
    search_terms = _get_search_terms(keywords)

    result = {
        "keywords":     keywords,
        "search_terms": sorted(search_terms),
        "morph_used":   MORPH_AVAILABLE,
        "articles":     [],
        "conferences":  [],
        "textbooks":    [],
        "methodical":   [],
        "trainings":    [],
    }

    if not search_terms:
        return result

    for field_key in ["articles", "conferences", "textbooks", "methodical"]:
        for item in publications.get(field_key, []):
            sc = score_item(search_terms, item["label"])
            if sc >= threshold:
                result[field_key].append({**item, "score": sc})
        result[field_key].sort(key=lambda x: x["score"], reverse=True)

    for item in trainings:
        sc = score_item(search_terms, item["label"])
        if sc >= threshold:
            result["trainings"].append({**item, "score": sc})
    result["trainings"].sort(key=lambda x: x["score"], reverse=True)

    return result