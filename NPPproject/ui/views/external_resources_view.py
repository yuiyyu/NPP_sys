from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QAbstractItemView,
    QLabel, QMessageBox, QLineEdit
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QFont, QColor

from services.external_resource_service import get_all_resources
from ui.dialogs.external_resource_form import ExternalResourceForm


COLUMNS = [
    ("ID",                             "id",      0),
    ("Прізвище, ім'я та по батькові", "name",   280),
    ("ORCID",                          "orcid",  240),
    ("Google Scholar",                 "scholar", 340),
    ("Перейти",                        "actions", 200),
]

# Ті самі кольори що й у license_view.py
C_NAME_BG   = "#ffffff"   # білий — ПІБ
C_HAS_BG    = "#f0f0f0"   # сірий — є посилання
C_NONE_BG   = "#fffbe6"   # жовтий — не заповнено
C_LINK_FG   = "#0055cc"   # синій — текст посилання
C_NONE_FG   = "#999999"   # сірий — немає посилання
C_TEXT      = "#000000"   # чорний — звичайний текст


def make_item(text: str, bg: str, fg: str = "#000000", align=None, underline=False) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setBackground(QColor(bg))
    item.setForeground(QColor(fg))
    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
    item.setTextAlignment(align if align else (Qt.AlignLeft | Qt.AlignVCenter))
    if underline:
        font = item.font()
        font.setUnderline(True)
        item.setFont(font)
    return item


class ExternalResourcesView(QWidget):
    def __init__(self):
        super().__init__()

        self._data = []   # [(id, full_name, orcid, scholar)]

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)
        self.setLayout(main_layout)

        # ── Кнопки + пошук ────────────────────────────────────────────────────
        btn_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Пошук за прізвищем...")
        self.search_input.textChanged.connect(self._apply_filter)

        self.edit_btn    = QPushButton("✏️ Редагувати")
        self.refresh_btn = QPushButton("🔄 Оновити")

        self.edit_btn.clicked.connect(self._open_edit_form)
        self.refresh_btn.clicked.connect(self.load_data)

        btn_layout.addWidget(self.search_input)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addStretch()

        main_layout.addLayout(btn_layout)  

        # ── Таблиця ───────────────────────────────────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(len(COLUMNS))
        self.table.setHorizontalHeaderLabels([c[0] for c in COLUMNS])
        self.table.setColumnHidden(0, True)

        header = self.table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignCenter)
        for col_i, (_, _, width) in enumerate(COLUMNS):
            if col_i == 0:
                continue
            header.setSectionResizeMode(col_i, QHeaderView.Interactive)
            self.table.setColumnWidth(col_i, width)
        header.setSectionResizeMode(1, QHeaderView.Stretch)

        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.setWordWrap(False)
        self.table.setStyleSheet("""
            QTableWidget {
                gridline-color: #e0e0e0;
            }
            QTableWidget::item:selected {
                background: #cfe2ff;
                color: #000000;
            }
            QTableWidget::item:selected:!active {
                background: #ddeeff;
                color: #000000;
            }
        """)

        self.table.doubleClicked.connect(self._on_double_click)

        main_layout.addWidget(self.table, stretch=1)

        # ── Підсумок ──────────────────────────────────────────────────────────
        self.summary_label = QLabel()
        bold = QFont()
        bold.setBold(True)
        self.summary_label.setFont(bold)
        main_layout.addWidget(self.summary_label)

        self.load_data()

    # ── Завантаження ──────────────────────────────────────────────────────────

    def load_data(self):
        self._data = get_all_resources()
        self._fill_table()

    def _fill_table(self):
        self.table.setRowCount(0)
        self.table.setRowCount(len(self._data))

        for row_i, (tid, name, orcid, scholar) in enumerate(self._data):

            # ID прихований
            self.table.setItem(row_i, 0, QTableWidgetItem(tid))

            # ПІБ
            self.table.setItem(row_i, 1, make_item(name, C_NAME_BG))

            # ORCID — синій підкреслений якщо є
            if orcid:
                self.table.setItem(row_i, 2,
                    make_item(orcid, C_HAS_BG, C_LINK_FG, underline=True))
            else:
                self.table.setItem(row_i, 2,
                    make_item("— не вказано —", C_NONE_BG, C_NONE_FG))

            # Google Scholar — синій підкреслений якщо є
            if scholar:
                self.table.setItem(row_i, 3,
                    make_item(scholar, C_HAS_BG, C_LINK_FG, underline=True))
            else:
                self.table.setItem(row_i, 3,
                    make_item("— не вказано —", C_NONE_BG, C_NONE_FG))

            # Колонка "Перейти" — кнопки 50/50 з hover/press анімацією
            actions = QWidget()
            actions.setStyleSheet("background: transparent;")
            act_layout = QHBoxLayout(actions)
            act_layout.setContentsMargins(4, 3, 4, 3)
            act_layout.setSpacing(4)

            STYLE_ACTIVE = """
                QPushButton {
                    font-size: 11px; font-weight: bold;
                    color: #0055cc;
                    background: #eef3fb;
                    border: 1px solid #a8c4e8;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background: #ddeaff;
                    border-color: #0055cc;
                    color: #003399;
                }
                QPushButton:pressed {
                    background: #b8d0f8;
                    border-color: #003399;
                    padding-top: 2px;
                }
            """
            STYLE_DISABLED = """
                QPushButton {
                    font-size: 11px;
                    color: #bbb;
                    background: #f5f5f5;
                    border: 1px solid #e0e0e0;
                    border-radius: 4px;
                }
            """

            btn_orcid = QPushButton("ORCID ↗")
            btn_orcid.setFixedHeight(28)
            if orcid:
                btn_orcid.setStyleSheet(STYLE_ACTIVE)
                url = orcid if orcid.startswith("http") else f"https://orcid.org/{orcid}"
                btn_orcid.clicked.connect(
                    lambda _, u=url: QDesktopServices.openUrl(QUrl(u))
                )
            else:
                btn_orcid.setEnabled(False)
                btn_orcid.setStyleSheet(STYLE_DISABLED)

            btn_scholar = QPushButton("Scholar ↗")
            btn_scholar.setFixedHeight(28)
            if scholar:
                btn_scholar.setStyleSheet(STYLE_ACTIVE)
                btn_scholar.clicked.connect(
                    lambda _, u=scholar: QDesktopServices.openUrl(QUrl(u))
                )
            else:
                btn_scholar.setEnabled(False)
                btn_scholar.setStyleSheet(STYLE_DISABLED)

            # stretch=1 для кожної — рівно 50/50
            act_layout.addWidget(btn_orcid, 1)
            act_layout.addWidget(btn_scholar, 1)
            self.table.setCellWidget(row_i, 4, actions)

        # Підсумок
        total       = len(self._data)
        has_orcid   = sum(1 for _, _, o, _ in self._data if o)
        has_scholar = sum(1 for _, _, _, s in self._data if s)
        self.summary_label.setText(
            f"Всього викладачів: {total}   |   "
            f"ORCID заповнено: {has_orcid} з {total}   |   "
            f"Google Scholar заповнено: {has_scholar} з {total}"
        )

    # ── Фільтр ────────────────────────────────────────────────────────────────

    def _apply_filter(self):
        text = self.search_input.text().lower()
        for row_i in range(self.table.rowCount()):
            name_item = self.table.item(row_i, 1)
            name = name_item.text().lower() if name_item else ""
            self.table.setRowHidden(row_i, bool(text) and text not in name)

    # ── Подвійний клік — відкрити посилання ──────────────────────────────────

    def _on_double_click(self, index):
        row_i = index.row()
        col_i = index.column()
        if row_i < 0 or row_i >= len(self._data):
            return

        tid_item = self.table.item(row_i, 0)
        if not tid_item:
            return

        row = next((r for r in self._data if r[0] == tid_item.text()), None)
        if not row:
            return

        _, _, orcid, scholar = row

        if col_i == 2 and orcid:
            url = orcid if orcid.startswith("http") else f"https://orcid.org/{orcid}"
            QDesktopServices.openUrl(QUrl(url))
        elif col_i == 3 and scholar:
            QDesktopServices.openUrl(QUrl(scholar))

    # ── Редагування ───────────────────────────────────────────────────────────

    def _open_edit_form(self):
        row_i = self.table.currentRow()
        if row_i < 0:
            QMessageBox.information(self, "Увага", "Оберіть викладача для редагування.")
            return

        tid_item = self.table.item(row_i, 0)
        if not tid_item:
            return

        row = next((r for r in self._data if r[0] == tid_item.text()), None)
        if not row:
            return

        tid, name, orcid, scholar = row

        form = ExternalResourceForm(
            parent=self,
            teacher_id=tid,
            teacher_name=name,
            orcid=orcid,
            scholar=scholar,
        )
        form.saved.connect(lambda: self._on_saved(tid))
        form.exec()

    def _on_saved(self, tid: str):
        self.load_data()
        for row_i in range(self.table.rowCount()):
            item = self.table.item(row_i, 0)
            if item and item.text() == tid:
                self.table.setCurrentCell(row_i, 1)
                break