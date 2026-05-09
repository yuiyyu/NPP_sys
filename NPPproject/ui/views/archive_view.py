import os
from datetime import date
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QHBoxLayout,
    QLineEdit, QHeaderView, QMessageBox,
    QAbstractItemView, QComboBox, QLabel,
    QDialog, QListWidget, QListWidgetItem,
    QDialogButtonBox, QFileDialog
)
from PySide6.QtCore import Qt, QObject, QEvent
from PySide6.QtGui import QFont, QColor

from services.archive_service import (
    get_all_archive_publications,
    delete_archive_publication,
    run_auto_archive,
    get_all_teachers_for_select,
    PUBLICATION_TYPE_LABELS,
)

try:
    from services.export_publications import export_publications
except ImportError:
    from services.export_publications import export_publications


COLUMNS = [
    ("ID",               0,   0),
    ("Назва",            1, 450),
    ("Тип",              2, 180),
    ("Рік",              3,  60),
    ("Журнал / видавець",4, 220),
    ("DOI",              5, 160),
    ("URL",              6, 180),
    ("Архівовано",       7, 130),
    ("Причина",          8, 130),
    ("Автори",           9, 260),
]

CUTOFF_YEAR = date.today().year - 5


class WheelScrollFilter(QObject):
    def __init__(self, table):
        super().__init__(table)
        self.table = table

    def eventFilter(self, obj, event):
        if obj is self.table.viewport() and event.type() == QEvent.Wheel:
            if event.modifiers() & Qt.ShiftModifier:
                delta = event.angleDelta().y()
                bar = self.table.horizontalScrollBar()
                bar.setValue(bar.value() - delta)
                return True
        return super().eventFilter(obj, event)


class TeacherPickerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Оберіть викладача для експорту")
        self.setMinimumWidth(380)
        self.setMinimumHeight(420)

        self._selected_id   = None
        self._selected_name = None

        layout = QVBoxLayout(self)
        lbl = QLabel("Оберіть викладача:")
        lbl.setFont(QFont("Arial", 10))
        layout.addWidget(lbl)

        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍 Пошук...")
        self.search.setFixedHeight(32)
        self.search.textChanged.connect(self._filter)
        layout.addWidget(self.search)

        self.list = QListWidget()
        self.list.doubleClicked.connect(self._accept)
        layout.addWidget(self.list)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("Експортувати")
        btns.button(QDialogButtonBox.Cancel).setText("Скасувати")
        btns.accepted.connect(self._accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self._teachers = get_all_teachers_for_select()
        self._fill_list()

    def _fill_list(self, filter_text: str = ""):
        self.list.clear()
        for t_id, t_name in self._teachers:
            if filter_text and filter_text.lower() not in t_name.lower():
                continue
            item = QListWidgetItem(t_name)
            item.setData(Qt.UserRole, t_id)
            self.list.addItem(item)

    def _filter(self, text: str):
        self._fill_list(filter_text=text)

    def _accept(self):
        item = self.list.currentItem()
        if not item:
            QMessageBox.warning(self, "Увага", "Оберіть викладача зі списку.")
            return
        self._selected_id   = item.data(Qt.UserRole)
        self._selected_name = item.text()
        self.accept()

    def selected(self):
        return self._selected_id, self._selected_name


class ArchiveView(QWidget):
    def __init__(self):
        super().__init__()

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(10)


        # ── Підказка ──────────────────────────────────────────────────────────
        hint = QLabel(
            f"Архів містить публікації старші 5 років (до {CUTOFF_YEAR} р. включно). "
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(
            "color: #5d6d7e; font-size: 11px; font-style: italic; "
            "background: #eaf2fb; padding: 6px 10px; border-radius: 4px;"
        )

        # ── Фільтри ───────────────────────────────────────────────────────────
        filter_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Пошук за назвою або автором...")
        self.search_input.setFixedHeight(32)
        self.search_input.textChanged.connect(self._apply_filters)

        self.year_filter = QComboBox()
        self.year_filter.setFixedWidth(100)
        self.year_filter.setFixedHeight(32)
        self.year_filter.addItem("Всі", None)
        self.year_filter.currentIndexChanged.connect(self._apply_filters)

        self.type_filter = QComboBox()
        self.type_filter.setFixedWidth(300)
        self.type_filter.setFixedHeight(32)
        self.type_filter.addItem("Всі типи", None)
        for key, label in PUBLICATION_TYPE_LABELS.items():
            self.type_filter.addItem(label, key)
        self.type_filter.currentIndexChanged.connect(self._apply_filters)

        filter_layout.addWidget(self.search_input)
        filter_layout.addWidget(QLabel("Рік:"))
        filter_layout.addWidget(self.year_filter)
        filter_layout.addWidget(QLabel("Тип:"))
        filter_layout.addWidget(self.type_filter)

        # ── Кнопки ────────────────────────────────────────────────────────────
        button_layout = QHBoxLayout()

        self.delete_btn  = QPushButton("🗑 Видалити")
        self.refresh_btn = QPushButton("🔄 Оновити")
        self.auto_btn    = QPushButton("⚙️ Авто-архівування")

        self.delete_btn.setFixedHeight(32)
        self.refresh_btn.setFixedHeight(32)
        self.auto_btn.setFixedHeight(32)
        self.auto_btn.setToolTip(
            "Перемістити публікації старші 5 років до архіву автоматично"
        )

        button_layout.addWidget(self.delete_btn)
        button_layout.addWidget(self.refresh_btn)
        button_layout.addWidget(self.auto_btn)
        button_layout.addStretch()

        self.export_all_btn    = QPushButton("📥 Експорт всіх")
        self.export_select_btn = QPushButton("📥 Вибрати експорт")
        self.export_all_btn.setFixedHeight(32)
        self.export_select_btn.setFixedHeight(32)
        button_layout.addWidget(self.export_all_btn)
        button_layout.addWidget(self.export_select_btn)

        # ── Таблиця ───────────────────────────────────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(len(COLUMNS))
        self.table.setHorizontalHeaderLabels([c[0] for c in COLUMNS])
        self.table.setColumnHidden(0, True)

        header = self.table.horizontalHeader()
        for col_index, (_, _, width) in enumerate(COLUMNS):
            if col_index == 0:
                continue
            header.setSectionResizeMode(col_index, QHeaderView.Interactive)
            self.table.setColumnWidth(col_index, width)
        # header.setSectionResizeMode(1, QHeaderView.Stretch)

        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setDefaultSectionSize(28)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setVisible(False)

        self._wheel_filter = WheelScrollFilter(self.table)
        self.table.viewport().installEventFilter(self._wheel_filter)

        # ── Збірка ────────────────────────────────────────────────────────────
        main_layout.addWidget(hint)
        main_layout.addLayout(filter_layout)
        main_layout.addLayout(button_layout)
        main_layout.addWidget(self.table)
        self.setLayout(main_layout)

        # ── Сигнали ───────────────────────────────────────────────────────────
        self.refresh_btn.clicked.connect(self.load_data)
        self.delete_btn.clicked.connect(self.delete_selected)
        self.auto_btn.clicked.connect(self._run_auto_archive)
        self.export_all_btn.clicked.connect(self._export_all)
        self.export_select_btn.clicked.connect(self._export_selected)

        self._data_map = {}
        self.load_data()

    # ── Дані ──────────────────────────────────────────────────────────────────

    def load_data(self):
        data = get_all_archive_publications()
        self._data_map = {i: row for i, row in enumerate(data)}

        current_year = self.year_filter.currentData()
        self.year_filter.blockSignals(True)
        self.year_filter.clear()
        self.year_filter.addItem("Всі", None)
        years = sorted(set(str(r[3]) for r in data if r[3]), reverse=True)
        for y in years:
            self.year_filter.addItem(y, y)
        idx = self.year_filter.findData(current_year)
        self.year_filter.setCurrentIndex(idx if idx >= 0 else 0)
        self.year_filter.blockSignals(False)

        self._fill_table(data)

    def _fill_table(self, data):
        self.table.setRowCount(len(data))
        for row_index, row_data in enumerate(data):
            # row: id, title, type, year, journal, doi, url, archived_at, reason, authors
            values = list(row_data)

            for col_index, value in enumerate(values):
                if col_index == 2 and value:
                    text = PUBLICATION_TYPE_LABELS.get(value, value)
                elif col_index == 7 and value:
                    # archived_at — показуємо тільки дату
                    text = str(value)[:10]
                elif col_index == 8 and value:
                    text = "5 років" if value == "5_year_expiry" else "Вручну"
                else:
                    text = str(value) if value is not None else ""

                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)

                if col_index ==1:
                    item.setToolTip(text)
                if col_index in (3, 7):
                   item.setTextAlignment(Qt.AlignCenter)

                # Підсвічуємо рядки з причиною "5 років" сірим
                if col_index == 8 and value == "5_year_expiry":
                   item.setForeground(QColor("#7f8c8d"))

                self.table.setItem(row_index, col_index, item)

    # ── Фільтри ───────────────────────────────────────────────────────────────

    def _apply_filters(self):
        text     = self.search_input.text().lower()
        year_val = self.year_filter.currentData()
        type_val = self.type_filter.currentData()

        for row_index in range(self.table.rowCount()):
            raw = self._data_map.get(row_index)
            if raw is None:
                self.table.setRowHidden(row_index, True)
                continue

            raw_title   = (raw[1] or "").lower()
            raw_type    = raw[2]
            raw_year    = str(raw[3]) if raw[3] else ""
            raw_authors = (raw[9] or "").lower()

            text_match = not text     or text     in raw_title or text in raw_authors
            year_match = not year_val or raw_year == str(year_val)
            type_match = not type_val or raw_type == type_val

            self.table.setRowHidden(row_index, not (text_match and year_match and type_match))

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def _get_selected_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.text() if item else None

    def delete_selected(self):
        pub_id = self._get_selected_id()
        if not pub_id:
            QMessageBox.information(self, "Увага", "Оберіть запис для видалення.")
            return

        row = self.table.currentRow()
        title_item = self.table.item(row, 1)
        title = title_item.text() if title_item else "запис"

        reply = QMessageBox.question(
            self, "Підтвердження",
            f"Видалити з архіву «{title[:60]}»?\nЦю дію не можна скасувати.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            delete_archive_publication(pub_id)
            self.load_data()

    def _run_auto_archive(self):
        reply = QMessageBox.question(
            self, "Авто-архівування",
            f"Перемістити всі публікації до {CUTOFF_YEAR} року включно до архіву?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        count = run_auto_archive()
        if count > 0:
            QMessageBox.information(
                self, "Готово",
                f"До архіву додано {count} публікацій."
            )
        else:
            QMessageBox.information(
                self, "Готово",
                "Нових публікацій для архівування не знайдено.\n"
                "Всі публікації старші 5 років вже в архіві."
            )
        self.load_data()

    # ── Експорт ───────────────────────────────────────────────────────────────

    def _ask_save_path(self, default_name: str) -> str | None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Зберегти файл експорту",
            default_name, "Excel файл (*.xlsx)",
        )
        return path if path else None

    def _rows_for_export(self, data):
        """Конвертує рядки архіву у формат export_publications (8 колонок)."""
        result = []
        for row in data:
            # archive: id, title, type, year, journal, doi, url, archived_at, reason, authors
            result.append((
                row[0],   # id
                row[1],   # title
                row[2],   # type
                row[3],   # year
                row[4],   # journal
                row[5],   # doi
                row[6],   # url
                row[9],   # authors
            ))
        return result

    def _export_all(self):
        data = list(self._data_map.values())
        if not data:
            QMessageBox.information(self, "Увага", "Немає даних для експорту.")
            return

        path = self._ask_save_path("архів_публікацій_всі.xlsx")
        if not path:
            return

        try:
            export_publications(
                self._rows_for_export(data), path,
                title="Архів публікацій — всі"
            )
            QMessageBox.information(self, "Готово", f"Експорт завершено:\n{path}")
            if os.name == "nt":
                os.startfile(path)
        except Exception as e:
            QMessageBox.critical(self, "Помилка", f"Не вдалося зберегти файл:\n{e}")

    def _export_selected(self):
        dlg = TeacherPickerDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return

        teacher_id, teacher_name = dlg.selected()
        if not teacher_id:
            return

        filtered = [
            row for row in self._data_map.values()
            if teacher_name.split()[0].lower() in (row[9] or "").lower()
        ]

        if not filtered:
            QMessageBox.information(
                self, "Увага",
                f"Архівних публікацій для «{teacher_name}» не знайдено."
            )
            return

        safe_name = teacher_name.replace(" ", "_")
        path = self._ask_save_path(f"архів_{safe_name}.xlsx")
        if not path:
            return

        try:
            export_publications(
                self._rows_for_export(filtered), path,
                title=f"Архів публікацій — {teacher_name}"
            )
            QMessageBox.information(
                self, "Готово",
                f"Експорт завершено ({len(filtered)} записів):\n{path}"
            )
            if os.name == "nt":
                os.startfile(path)
        except Exception as e:
            QMessageBox.critical(self, "Помилка", f"Не вдалося зберегти файл:\n{e}")