"""
Діалог вибору публікацій і тренінгів з БД для конкретної дисципліни.
Підтримує два режими:
  - Звичайний (manual=True): всі записи, без передпозначення
  - Авто (auto_match_result): записи відсортовані за score, знайдені позначені
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QWidget, QLabel, QListWidget, QListWidgetItem,
    QDialogButtonBox, QPushButton, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

PUB_GROUPS = [
    ("articles",    "📄 Фахові статті"),
    ("conferences", "🎤 Тези конференцій"),
    ("textbooks",   "📚 Підручники / посібники"),
    ("methodical",  "📋 Методичні матеріали"),
    ("trainings",   "🎓 Підвищення кваліфікації"),
]

# Кольори для підсвічування за score
# (фон, колір тексту)
SCORE_COLORS = {
    0: None,
    1: (QColor("#fff3cd"), QColor("#000000")),   # 1 збіг  — жовтий
    2: (QColor("#d4edda"), QColor("#000000")),   # 2 збіги — зелений
    3: (QColor("#a8d5a2"), QColor("#000000")),   # 3+ збіги — насичений зелений
}


def _score_color(score: int):
    if score >= 3:
        return SCORE_COLORS[3]
    return SCORE_COLORS.get(score)


class LicenseSelectDialog(QDialog):
    """
    selected емітує {field_key: "текст; текст; ..."} для всіх полів.
    """
    selected = Signal(dict)

    def __init__(self, parent=None,
                 publications: dict = None,
                 trainings: list = None,
                 current_vals: dict = None,
                 disc_name: str = "",
                 auto_match_result: dict = None):
        """
        auto_match_result — якщо передано, працює в режимі авто-пошуку:
            {"articles":[{"id","label","score"},...], ..., "keywords":[...]}
            Записи з score>0 позначені галочкою і підсвічені кольором.
        """
        super().__init__(parent)
        self._pubs      = publications or {}
        self._trains    = trainings    or []
        self._cur_vals  = current_vals or {}
        self._auto      = auto_match_result  # None = звичайний режим
        self._checks    = {}   # {field_key: [QListWidgetItem]}

        is_auto = auto_match_result is not None
        prefix  = "🤖 Авто-пошук" if is_auto else "📋 Вибір даних з БД"
        self.setWindowTitle(f"{prefix} — {disc_name or 'дисципліна'}")
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, False)
        self.setMinimumWidth(740)
        self.setMinimumHeight(560)

        self._build_ui(is_auto)

    def _build_ui(self, is_auto: bool):
        lay = QVBoxLayout(self)
        lay.setSpacing(8)

        # Підказка
        if is_auto and self._auto:
            kws   = self._auto.get("keywords", [])
            terms = self._auto.get("search_terms", [])
            morph = self._auto.get("morph_used", False)
            kw_str   = ", ".join(f"«{k}»" for k in kws)   if kws   else "—"
            ext_str  = ", ".join(f"«{t}»" for t in terms[:12]) if terms else "—"
            morph_str = "✅ з морфологією (pymorphy3)" if morph else "⚠️ без морфології (встановіть pymorphy3)"
            hint_text = (
                f"Ключові слова: {kw_str}\n"
                f"Розширений пошук ({morph_str}): {ext_str}\n"
                "Знайдені збіги позначені ★ і галочкою. Перевірте результат."
            )
            hint_color = "#1a5276"
        else:
            hint_text  = ("Оберіть публікації та підвищення кваліфікації "
                          "що відповідають цій дисципліні.")
            hint_color = "#444"

        hint = QLabel(hint_text)
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color:#000000; font-size:11px; "
                           f"background:#dbeeff; padding:6px; border-radius:4px; border:1px solid #b0d0ee;")
        lay.addWidget(hint)

        # Легенда кольорів для авто-режиму
        if is_auto:
            leg = QHBoxLayout()
            for color, label in [
                ("#fff3cd", "1 збіг"),
                ("#d4edda", "2 збіги"),
                ("#a8d5a2", "3+ збіги"),
            ]:
                dot = QLabel(f"  {label}")
                dot.setStyleSheet(
                    f"background:{color}; border:1px solid #aaa; color:#000000; "
                    f"padding:2px 8px; font-size:10px; border-radius:3px;"
                )
                leg.addWidget(dot)
            leg.addStretch()
            lay.addLayout(leg)

        tabs = QTabWidget()

        for field_key, tab_label in PUB_GROUPS:
            if field_key == "trainings":
                raw_items = self._trains
            else:
                raw_items = self._pubs.get(field_key, [])

            # В авто-режимі беремо scored список
            if is_auto and self._auto:
                scored_items = {
                    item["id"]: item.get("score", 0)
                    for item in self._auto.get(field_key, [])
                }
            else:
                scored_items = {}

            tab   = self._build_tab(field_key, raw_items, scored_items, is_auto)
            found = len(scored_items) if is_auto else len(raw_items)
            badge = f"  ✓{len(scored_items)}" if is_auto and scored_items else ""
            tabs.addTab(tab, f"{tab_label}  ({len(raw_items)}){badge}")

        lay.addWidget(tabs, stretch=1)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("✅ Підставити обране")
        btns.button(QDialogButtonBox.Cancel).setText("Скасувати")
        btns.accepted.connect(self._apply)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def _build_tab(self, field_key: str, items: list,
                   scored_ids: dict, is_auto: bool) -> QWidget:
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(4, 6, 4, 4)
        lay.setSpacing(4)

        if not items:
            empty = QLabel("Записів не знайдено.")
            empty.setStyleSheet("color:#888; font-style:italic;")
            lay.addWidget(empty)
            lay.addStretch()
            self._checks[field_key] = []
            return tab

        # Кнопки виділення
        sel_row = QHBoxLayout()
        btn_all  = QPushButton("☑ Всі")
        btn_none = QPushButton("☐ Жодного")
        btn_all.setFixedWidth(72)
        btn_none.setFixedWidth(86)
        btn_all.setStyleSheet("font-size:11px;")
        btn_none.setStyleSheet("font-size:11px;")
        sel_row.addWidget(btn_all)
        sel_row.addWidget(btn_none)

        if is_auto and scored_ids:
            btn_auto = QPushButton("🤖 Тільки знайдені")
            btn_auto.setStyleSheet("font-size:11px;")
            sel_row.addWidget(btn_auto)
        else:
            btn_auto = None

        sel_row.addStretch()
        lay.addLayout(sel_row)

        lw = QListWidget()
        lw.setSelectionMode(QListWidget.NoSelection)
        lw.setSpacing(1)

        cur_text    = self._cur_vals.get(field_key, "")
        item_widgets = []

        # Сортуємо: спочатку знайдені (за score), потім решта
        if is_auto and scored_ids:
            found     = [it for it in items if it["id"] in scored_ids]
            not_found = [it for it in items if it["id"] not in scored_ids]
            found.sort(key=lambda x: scored_ids.get(x["id"], 0), reverse=True)

            # Роздільник якщо є обидві групи
            sorted_items = found
            has_sep      = bool(found and not_found)
            rest_items   = not_found
        else:
            sorted_items = items
            has_sep      = False
            rest_items   = []

        def _add_item(entry, check_default):
            score = scored_ids.get(entry["id"], 0)
            label = entry["label"]

            # Додаємо індикатор score
            if is_auto and score > 0:
                stars = "★" * min(int(score), 3)
                display = f"{stars}  {label}"
            else:
                display = label

            li = QListWidgetItem(display)
            li.setFlags(li.flags() | Qt.ItemIsUserCheckable)

            # Галочка:
            # - авто-режим: тільки якщо цей запис є серед знайдених (score > 0)
            # - звичайний: якщо вже є у поточному значенні поля
            already    = label in cur_text
            is_found   = entry["id"] in scored_ids  # знайдено авто-пошуком
            should_check = (is_auto and is_found) or (not is_auto and already)
            li.setCheckState(Qt.Checked if should_check else Qt.Unchecked)
            li.setData(Qt.UserRole,     label)        # label без зірок
            li.setData(Qt.UserRole + 1, entry["id"])  # id для збереження

            # Підсвічування — явно задаємо і фон і колір тексту
            colors = _score_color(score)
            if colors:
                bg, fg = colors
                li.setBackground(bg)
                li.setForeground(fg)

            lw.addItem(li)
            item_widgets.append(li)
            return li

        for entry in sorted_items:
            _add_item(entry, check_default=is_auto)

        if has_sep:
            sep_item = QListWidgetItem("─── Не знайдено за ключовими словами ───")
            sep_item.setFlags(Qt.NoItemFlags)
            sep_item.setForeground(QColor("#555555"))
            sep_item.setBackground(QColor("#f0f0f0"))
            f = QFont(); f.setItalic(True); f.setPointSize(9)
            sep_item.setFont(f)
            lw.addItem(sep_item)
            for entry in rest_items:
                _add_item(entry, check_default=False)

        btn_all.clicked.connect(
            lambda: [it.setCheckState(Qt.Checked) for it in item_widgets])
        btn_none.clicked.connect(
            lambda: [it.setCheckState(Qt.Unchecked) for it in item_widgets])
        if btn_auto:
            auto_ids = set(scored_ids.keys())
            btn_auto.clicked.connect(
                lambda: [
                    it.setCheckState(
                        Qt.Checked if any(
                            it.data(Qt.UserRole) == e["label"]
                            for e in items if e["id"] in auto_ids
                        ) else Qt.Unchecked
                    )
                    for it in item_widgets
                ]
            )

        lay.addWidget(lw, stretch=1)
        self._checks[field_key] = item_widgets
        return tab

    def _apply(self):
        result = {}
        for field_key, _ in PUB_GROUPS:
            checked_items = [
                it for it in self._checks.get(field_key, [])
                if it.checkState() == Qt.Checked
            ]
            if checked_items:
                ids    = [it.data(Qt.UserRole + 1) for it in checked_items]
                labels = "; ".join(it.data(Qt.UserRole) for it in checked_items)
                result[field_key] = {"selected_ids": ids, "labels": labels}
            else:
                result[field_key] = ""
        self.selected.emit(result)
        self.accept()