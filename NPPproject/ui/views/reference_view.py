from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QAbstractItemView,
    QLabel, QMessageBox, QTabWidget, QLineEdit
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from services.reference_service import (
    get_all_departments, delete_department,
    get_all_degrees, delete_degree,
    get_all_titles, delete_title,
)
from ui.dialogs.reference_form import DepartmentForm, DegreeForm, TitleForm


C_BG   = "#f0f0f0"
C_TEXT = "#000000"


def make_item(text: str, align=None) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setBackground(QColor(C_BG))
    item.setForeground(QColor(C_TEXT))
    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
    item.setTextAlignment(align if align else (Qt.AlignLeft | Qt.AlignVCenter))
    return item


# ── Базовий віджет для одного довідника ──────────────────────────────────────

class _ReferenceTab(QWidget):
    """
    Базовий клас для вкладки довідника.
    Підкласи визначають колонки, завантаження, форми і видалення.
    """

    def __init__(self, columns: list):
        super().__init__()

        self._data = []

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        self.setLayout(layout)

        # Кнопки
        btn_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Пошук...")
        self.search_input.textChanged.connect(self._apply_filter)

        self.add_btn    = QPushButton("➕ Додати")
        self.edit_btn   = QPushButton("✏️ Редагувати")
        self.delete_btn = QPushButton("🗑 Видалити")
        self.refresh_btn = QPushButton("🔄 Оновити")

        self.add_btn.clicked.connect(self._open_add)
        self.edit_btn.clicked.connect(self._open_edit)
        self.delete_btn.clicked.connect(self._delete)
        self.refresh_btn.clicked.connect(self.load_data)

        btn_layout.addWidget(self.search_input)
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Таблиця
        self.table = QTableWidget()
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.setColumnHidden(0, True)   # ID завжди прихований

        header = self.table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignCenter)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        for i in range(2, len(columns)):
            header.setSectionResizeMode(i, QHeaderView.Interactive)
            self.table.setColumnWidth(i, 160)

        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(32)
        self.table.setStyleSheet("""
            QTableWidget { gridline-color: #e0e0e0; }
            QTableWidget::item:selected { background: #cfe2ff; color: #000000; }
            QTableWidget::item:selected:!active { background: #ddeeff; color: #000000; }
        """)

        self.table.doubleClicked.connect(self._open_edit)
        layout.addWidget(self.table, stretch=1)

        # Підсумок
        self.summary_label = QLabel()
        bold = QFont()
        bold.setBold(True)
        self.summary_label.setFont(bold)
        layout.addWidget(self.summary_label)

        self.load_data()

    def load_data(self):
        raise NotImplementedError

    def _fill_table(self, rows: list, col_getters: list):
        """
        rows — список кортежів з БД
        col_getters — список функцій (row -> str) для кожної видимої колонки
        """
        self._data = rows
        self.table.setRowCount(len(rows))
        for row_i, row in enumerate(rows):
            self.table.setItem(row_i, 0, QTableWidgetItem(str(row[0])))  # ID
            for col_i, getter in enumerate(col_getters, start=1):
                self.table.setItem(row_i, col_i, make_item(getter(row)))
        self.summary_label.setText(f"Всього записів: {len(rows)}")

    def _apply_filter(self):
        text = self.search_input.text().lower()
        for row_i in range(self.table.rowCount()):
            item = self.table.item(row_i, 1)
            name = item.text().lower() if item else ""
            self.table.setRowHidden(row_i, bool(text) and text not in name)

    def _get_selected_id(self):
        row_i = self.table.currentRow()
        if row_i < 0:
            return None
        item = self.table.item(row_i, 0)
        return int(item.text()) if item else None

    def _get_selected_row(self):
        row_i = self.table.currentRow()
        if row_i < 0 or row_i >= len(self._data):
            return None
        return self._data[row_i]

    def _open_add(self):
        raise NotImplementedError

    def _open_edit(self):
        raise NotImplementedError

    def _delete(self):
        raise NotImplementedError

    def _on_saved(self):
        rec_id = self._get_selected_id()
        self.load_data()
        if rec_id:
            for row_i in range(self.table.rowCount()):
                item = self.table.item(row_i, 0)
                if item and item.text() == str(rec_id):
                    self.table.setCurrentCell(row_i, 1)
                    break


# ── Вкладка кафедр ────────────────────────────────────────────────────────────

class DepartmentsTab(_ReferenceTab):
    def __init__(self):
        super().__init__(["ID", "Назва кафедри", "Код"])

    def load_data(self):
        rows = get_all_departments()
        self._fill_table(rows, [
            lambda r: r[1],   # name
            lambda r: r[2],   # code
        ])

    def _open_add(self):
        form = DepartmentForm(self)
        form.saved.connect(self._on_saved)
        form.exec()

    def _open_edit(self):
        row = self._get_selected_row()
        if not row:
            QMessageBox.information(self, "Увага", "Оберіть запис для редагування.")
            return
        form = DepartmentForm(self, dep_id=row[0], name=row[1], code=row[2])
        form.saved.connect(self._on_saved)
        form.exec()

    def _delete(self):
        row = self._get_selected_row()
        if not row:
            QMessageBox.information(self, "Увага", "Оберіть запис для видалення.")
            return
        reply = QMessageBox.question(
            self, "Підтвердження",
            f"Видалити кафедру «{row[1]}»?\n"
            "Увага: якщо до кафедри прив'язані викладачі — видалення не вдасться.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                delete_department(row[0])
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, "Помилка", f"Не вдалося видалити:\n{e}")


# ── Вкладка наукових ступенів ─────────────────────────────────────────────────

class DegreesTab(_ReferenceTab):
    def __init__(self):
        super().__init__(["ID", "Науковий ступінь", "Скорочення"])

    def load_data(self):
        rows = get_all_degrees()
        self._fill_table(rows, [
            lambda r: r[1],   # name
            lambda r: r[2],   # short_name
        ])

    def _open_add(self):
        form = DegreeForm(self)
        form.saved.connect(self._on_saved)
        form.exec()

    def _open_edit(self):
        row = self._get_selected_row()
        if not row:
            QMessageBox.information(self, "Увага", "Оберіть запис для редагування.")
            return
        form = DegreeForm(self, deg_id=row[0], name=row[1], short_name=row[2])
        form.saved.connect(self._on_saved)
        form.exec()

    def _delete(self):
        row = self._get_selected_row()
        if not row:
            QMessageBox.information(self, "Увага", "Оберіть запис для видалення.")
            return
        reply = QMessageBox.question(
            self, "Підтвердження",
            f"Видалити ступінь «{row[1]}»?\n"
            "Увага: якщо ступінь прив'язаний до викладачів — видалення не вдасться.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                delete_degree(row[0])
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, "Помилка", f"Не вдалося видалити:\n{e}")


# ── Вкладка вчених звань ──────────────────────────────────────────────────────

class TitlesTab(_ReferenceTab):
    def __init__(self):
        super().__init__(["ID", "Вчене звання"])

    def load_data(self):
        rows = get_all_titles()
        self._fill_table(rows, [
            lambda r: r[1],   # name
        ])

    def _open_add(self):
        form = TitleForm(self)
        form.saved.connect(self._on_saved)
        form.exec()

    def _open_edit(self):
        row = self._get_selected_row()
        if not row:
            QMessageBox.information(self, "Увага", "Оберіть запис для редагування.")
            return
        form = TitleForm(self, title_id=row[0], name=row[1])
        form.saved.connect(self._on_saved)
        form.exec()

    def _delete(self):
        row = self._get_selected_row()
        if not row:
            QMessageBox.information(self, "Увага", "Оберіть запис для видалення.")
            return
        reply = QMessageBox.question(
            self, "Підтвердження",
            f"Видалити звання «{row[1]}»?\n"
            "Увага: якщо звання прив'язане до викладачів — видалення не вдасться.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                delete_title(row[0])
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, "Помилка", f"Не вдалося видалити:\n{e}")


# ── Головний віджет вкладки "Інше" ───────────────────────────────────────────

class ReferenceView(QWidget):
    def __init__(self):
        super().__init__()

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)
        self.setLayout(main_layout)

        # Вкладки
        tabs = QTabWidget()
        tabs.addTab(DepartmentsTab(), "🏛 Кафедри")
        tabs.addTab(DegreesTab(),     "🎓 Наукові ступені")
        tabs.addTab(TitlesTab(),      "📜 Вчені звання")

        main_layout.addWidget(tabs, stretch=1)