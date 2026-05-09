from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QHBoxLayout,
    QLineEdit, QHeaderView, QMessageBox, QAbstractItemView,
    QLabel
)
from PySide6.QtCore import Qt, QObject, QEvent
from PySide6.QtGui import QWheelEvent, QFont, QColor
from services.teacher_service import get_all_teachers, delete_teacher
from ui.dialogs.teacher_form import TeacherForm
from ui.styles import BTN_DELETE_STYLE


COLUMNS = [
    ("ID",             0,   0),
    ("Прізвище",       1, 140),
    ("Ім'я",           2, 110),
    ("По батькові",    3, 130),
    ("Дата нар.",      4,  90),
    ("Ступінь",        5, 160),
    ("Звання",         6, 160),
    ("Кафедра",        7, 220),
    ("ORCID",          8, 160),
    ("Google Scholar", 9, 180),
    ("Email",         10, 180),
    ("Телефон",       11, 120),
    ("Прийнятий",     12, 100),
    ("Звільнений",    13, 100),
    ("Статус",        14,  90),
    ("Примітки",      15, 200),
]

# Маппінг статусів — ключ БД → українська назва + колір
STATUS_MAP = {
    "active":   ("Активний",     "#1a7a1a", "#eafaea"),
    "on_leave": ("У відпустці",  "#7a5a00", "#fffbe6"),
    "retired":  ("Звільнений",   "#7a1a1a", "#fdf2f2"),
}


class WheelScrollFilter(QObject):
    def __init__(self, table: QTableWidget):
        super().__init__(table)
        self.table = table

    def eventFilter(self, obj, event):
        if obj is self.table.viewport() and event.type() == QEvent.Wheel:
            wheel: QWheelEvent = event
            if wheel.modifiers() & Qt.ShiftModifier:
                delta = wheel.angleDelta().y()
                h_bar = self.table.horizontalScrollBar()
                h_bar.setValue(h_bar.value() - delta)
                return True
        return super().eventFilter(obj, event)


class TeachersView(QWidget):
    def __init__(self):
        super().__init__()

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(10)

        # ── Пошук + кнопки ────────────────────────────────────────────────────
        top_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Пошук за прізвищем або ім'ям...")
        self.search_input.setFixedHeight(28)
        self.search_input.textChanged.connect(self._filter_table)

        self.add_btn     = QPushButton("➕ Додати")
        self.edit_btn    = QPushButton("✏️ Редагувати")
        self.delete_btn  = QPushButton("🗑 Видалити")
        self.refresh_btn = QPushButton("🔄 Оновити")

        for btn in [self.add_btn, self.edit_btn, self.refresh_btn]:
            btn.setFixedHeight(28)
        self.delete_btn.setFixedHeight(28)

        top_layout.addWidget(self.search_input)
        top_layout.addWidget(self.add_btn)
        top_layout.addWidget(self.edit_btn)
        top_layout.addWidget(self.delete_btn)
        top_layout.addWidget(self.refresh_btn)
        top_layout.addStretch()

        # ── Таблиця ───────────────────────────────────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(len(COLUMNS))
        self.table.setHorizontalHeaderLabels([c[0] for c in COLUMNS])
        self.table.setColumnHidden(0, True)

        header = self.table.horizontalHeader()
        for col_index, (_, _, min_width) in enumerate(COLUMNS):
            if col_index == 0:
                continue
            header.setSectionResizeMode(col_index, QHeaderView.Interactive)
            self.table.setColumnWidth(col_index, min_width)

        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setDefaultSectionSize(30)
        self.table.verticalHeader().setVisible(False)

        self._wheel_filter = WheelScrollFilter(self.table)
        self.table.viewport().installEventFilter(self._wheel_filter)

        # ── Збірка ────────────────────────────────────────────────────────────
        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.table)
        self.setLayout(main_layout)

        # ── Сигнали ───────────────────────────────────────────────────────────
        self.refresh_btn.clicked.connect(self.load_data)
        self.add_btn.clicked.connect(self.open_add_form)
        self.edit_btn.clicked.connect(self.open_edit_form)
        self.delete_btn.clicked.connect(self.delete_selected)
        self.table.doubleClicked.connect(self.open_edit_form)

        self.load_data()

    def load_data(self):
        data = get_all_teachers()
        self.table.setRowCount(len(data))
        for row_index, row_data in enumerate(data):
            for col_index, value in enumerate(row_data):
                # Колонка статусу — локалізуємо і фарбуємо
                if col_index == 14:
                    key = value or "active"
                    label, fg, bg = STATUS_MAP.get(
                        key, (key, "#2c3e50", "#ffffff"))
                    item = QTableWidgetItem(label)
                    item.setForeground(QColor(fg))
                    item.setBackground(QColor(bg))
                    item.setTextAlignment(Qt.AlignCenter)
                else:
                    text = str(value) if value is not None else ""
                    item = QTableWidgetItem(text)
                    if col_index in (4, 12, 13):
                        item.setTextAlignment(Qt.AlignCenter)

                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row_index, col_index, item)

    def _filter_table(self, text):
        text = text.lower()
        for row in range(self.table.rowCount()):
            last  = self.table.item(row, 1)
            first = self.table.item(row, 2)
            combined = (
                (last.text()  if last  else "") + " " +
                (first.text() if first else "")
            ).lower()
            self.table.setRowHidden(row, text not in combined)

    def _get_selected_id(self):
        selected = self.table.currentRow()
        if selected < 0:
            return None
        item = self.table.item(selected, 0)
        return item.text() if item else None

    def open_add_form(self):
        form = TeacherForm(self)
        form.saved.connect(self.load_data)
        form.exec()

    def open_edit_form(self):
        teacher_id = self._get_selected_id()
        if not teacher_id:
            QMessageBox.information(self, "Увага", "Оберіть викладача для редагування.")
            return
        form = TeacherForm(self, teacher_id=teacher_id)
        form.saved.connect(self.load_data)
        form.exec()

    def delete_selected(self):
        teacher_id = self._get_selected_id()
        if not teacher_id:
            QMessageBox.information(self, "Увага", "Оберіть викладача для видалення.")
            return
        row   = self.table.currentRow()
        last  = self.table.item(row, 1)
        first = self.table.item(row, 2)
        name  = f"{last.text() if last else ''} {first.text() if first else ''}".strip()
        reply = QMessageBox.question(
            self, "Підтвердження", f"Видалити {name}?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            delete_teacher(teacher_id)
            self.load_data()