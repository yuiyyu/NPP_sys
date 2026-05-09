from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QHBoxLayout,
    QLineEdit, QHeaderView, QMessageBox,
    QAbstractItemView, QComboBox, QLabel, QFrame,
    QListWidget, QListWidgetItem, QSplitter, QCheckBox
)
from PySide6.QtCore import Qt, QObject, QEvent
from PySide6.QtGui import QFont

from services.training_service import (
    get_trainings_by_teacher, get_trainings_by_teacher_5y, delete_training,
    get_training_summary, get_training_summary_5y,
    get_all_teachers_for_select,
    TRAINING_TYPE_LABELS,
)
from ui.dialogs.training_form import TrainingForm
from ui.dialogs.analysis_dialog import TeacherSearchDialog, AnalysisDialog


COLUMNS = [
    ("ID",             0,   0),
    ("Викладач",       1, 220),
    ("Назва заходу",   2, 280),
    ("Тип",            3, 190),
    ("Провайдер",      4, 200),
    ("Початок",        5,  95),
    ("Кінець",         6,  95),
    ("Годин",          7,  70),
    ("Кредитів ЄКТС",  8, 110),
]


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


class TrainingsView(QWidget):
    def __init__(self):
        super().__init__()

        self._data_map           = {}
        self._current_teacher_id = None

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        # ── Фільтри ───────────────────────────────────────────────────────────
        filter_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Пошук за назвою заходу або провайдером...")
        self.search_input.setFixedHeight(32)
        self.search_input.textChanged.connect(self._apply_filters)

        self.type_filter = QComboBox()
        self.type_filter.setFixedWidth(300)
        self.type_filter.setFixedHeight(32)
        self.type_filter.addItem("Всі типи", None)
        for key, label in TRAINING_TYPE_LABELS.items():
            self.type_filter.addItem(label, key)
        self.type_filter.currentIndexChanged.connect(self._apply_filters)

        self.filter_5y = QCheckBox("📅 Останні 5 років")
        self.filter_5y.setStyleSheet("font-size: 11px; color: #2c3e50;")
        self.filter_5y.stateChanged.connect(self._load_teacher_table)

        filter_layout.addWidget(self.search_input)
        filter_layout.addWidget(QLabel("Тип:"))
        filter_layout.addWidget(self.type_filter)
        filter_layout.addWidget(self.filter_5y)
        main_layout.addLayout(filter_layout)

        # ── Кнопки ────────────────────────────────────────────────────────────
        button_layout = QHBoxLayout()

        self.add_btn      = QPushButton("➕ Додати")
        self.edit_btn     = QPushButton("✏️ Редагувати")
        self.delete_btn   = QPushButton("🗑 Видалити")
        self.refresh_btn  = QPushButton("🔄 Оновити")
        self.analysis_btn = QPushButton("Аналіз НПП")


        for btn in [self.add_btn, self.edit_btn, self.delete_btn,
                    self.refresh_btn]:
            btn.setFixedHeight(32)
            button_layout.addWidget(btn)

        button_layout.addStretch()

        self.analysis_btn.setFixedHeight(32)
        self.analysis_btn.setToolTip(
            "Аналіз відповідності НПП вимогам ліцензійних умов (КМУ № 1187)"
        )
        button_layout.addWidget(self.analysis_btn)

        main_layout.addLayout(button_layout)

        # ── Сплітер ───────────────────────────────────────────────────────────
        splitter = QSplitter(Qt.Horizontal)

        # Ліва панель — список викладачів
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 4, 0)
        left_layout.setSpacing(4)

        list_label = QLabel("Викладачі:")
        bold_font = QFont()
        bold_font.setBold(True)
        list_label.setFont(bold_font)
        left_layout.addWidget(list_label)

        self.teacher_list = QListWidget()
        self.teacher_list.setFixedWidth(220)
        left_layout.addWidget(self.teacher_list)

        # Права панель
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(4, 0, 0, 0)
        right_layout.setSpacing(4)

        self.current_label = QLabel("Оберіть викладача зі списку")
        self.current_label.setStyleSheet("color: #888; font-style: italic;")
        right_layout.addWidget(self.current_label)

        # Таблиця
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
        header.setSectionResizeMode(2, QHeaderView.Stretch)

        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setDefaultSectionSize(28)
        self.table.verticalHeader().setVisible(False)

        self._wheel_filter = WheelScrollFilter(self.table)
        self.table.viewport().installEventFilter(self._wheel_filter)

        right_layout.addWidget(self.table)

        # Підсумок
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)

        self.summary_label = QLabel()
        summary_font = QFont()
        summary_font.setBold(True)
        self.summary_label.setFont(summary_font)

        self.norm_label = QLabel()
        norm_font = QFont()
        norm_font.setBold(True)
        self.norm_label.setFont(norm_font)

        right_layout.addWidget(line)
        right_layout.addWidget(self.summary_label)
        right_layout.addWidget(self.norm_label)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([220, 900])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter, stretch=1)
        self.setLayout(main_layout)

        # ── Сигнали ───────────────────────────────────────────────────────────
        self.refresh_btn.clicked.connect(self.load_data)
        self.add_btn.clicked.connect(self.open_add_form)
        self.edit_btn.clicked.connect(self.open_edit_form)
        self.delete_btn.clicked.connect(self.delete_selected)
        self.table.doubleClicked.connect(self.open_edit_form)
        self.teacher_list.currentRowChanged.connect(self._on_teacher_selected)
        self.analysis_btn.clicked.connect(self._open_analysis)

        self.load_data()

    # ── Завантаження ──────────────────────────────────────────────────────────

    def load_data(self):
        self._fill_teacher_list()
        if self._current_teacher_id:
            for i in range(self.teacher_list.count()):
                if self.teacher_list.item(i).data(Qt.UserRole) == self._current_teacher_id:
                    self.teacher_list.setCurrentRow(i)
                    return
        if self.teacher_list.count() > 0:
            self.teacher_list.setCurrentRow(0)

    def _fill_teacher_list(self):
        self.teacher_list.blockSignals(True)
        self.teacher_list.clear()
        for t_id, t_name in get_all_teachers_for_select():
            _, __, count = get_training_summary(t_id)
            item = QListWidgetItem(f"{t_name}  ({int(count)})")
            item.setData(Qt.UserRole, t_id)
            self.teacher_list.addItem(item)
        self.teacher_list.blockSignals(False)

    # ── Вибір викладача ───────────────────────────────────────────────────────

    def _on_teacher_selected(self, row_i: int):
        item = self.teacher_list.item(row_i)
        if not item:
            return
        self._current_teacher_id = item.data(Qt.UserRole)
        teacher_name = item.text().rsplit("  (", 1)[0]
        self.current_label.setText(teacher_name)
        self.current_label.setStyleSheet("color: #222; font-weight: bold;")
        self._load_teacher_table()

    def _load_teacher_table(self):
        if not self._current_teacher_id:
            return
        if self.filter_5y.isChecked():
            rows = get_trainings_by_teacher_5y(self._current_teacher_id)
        else:
            rows = get_trainings_by_teacher(self._current_teacher_id)
        self._data_map = {i: row for i, row in enumerate(rows)}
        self._fill_table(rows)
        self._update_summary()
        self._apply_filters()

    # ── Таблиця ───────────────────────────────────────────────────────────────

    def _fill_table(self, data):
        self.table.setRowCount(len(data))
        for row_index, row_data in enumerate(data):
            for col_index, value in enumerate(row_data):
                if col_index == 3 and value:
                    text = TRAINING_TYPE_LABELS.get(value, value)
                else:
                    text = str(value) if value is not None else ""
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if col_index == 2:
                    item.setToolTip(text)
                if col_index in (7, 8):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                elif col_index in (5, 6):
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row_index, col_index, item)

    # ── Підсумок ──────────────────────────────────────────────────────────────

    def _update_summary(self):
        if not self._current_teacher_id:
            self.summary_label.setText("")
            self.norm_label.setText("")
            return

        if self.filter_5y.isChecked():
            total_hours, total_ects, count = get_training_summary_5y(self._current_teacher_id)
            self.summary_label.setText(
                f"Записів за 5 років: {int(count)}   |   "
                f"Годин: {float(total_hours):.1f}   |   "
                f"Кредитів ЄКТС: {float(total_ects):.2f}"
            )
            ects_5y = float(total_ects)
            NORM = 6.0
            if ects_5y >= NORM:
                status = f"Норма виконана ({ects_5y:.2f} / {NORM:.0f} ЄКТС за 5 років)"
                color  = "#1a7a1a"
            else:
                remaining = NORM - ects_5y
                status = (
                    f"Норма НЕ виконана  "
                    f"({ects_5y:.2f} / {NORM:.0f} ЄКТС за 5 років, "
                    f"не вистачає {remaining:.2f})"
                )
                color = "#b84a00"
            self.norm_label.setText(status)
            self.norm_label.setStyleSheet(
                f"color: {color}; font-size: 11px; font-weight: bold;"
            )
        else:
            total_hours, total_ects, count = get_training_summary(self._current_teacher_id)
            self.summary_label.setText(
                f"Записів: {int(count)}   |   "
                f"Годин: {float(total_hours):.1f}   |   "
                f"Кредитів ЄКТС: {float(total_ects):.2f}"
            )
            self.norm_label.setText("")

    # ── Фільтри ───────────────────────────────────────────────────────────────

    def _apply_filters(self):
        text     = self.search_input.text().lower()
        type_val = self.type_filter.currentData()
        for row_index in range(self.table.rowCount()):
            raw = self._data_map.get(row_index)
            if raw is None:
                self.table.setRowHidden(row_index, True)
                continue
            raw_title    = (raw[2] or "").lower()
            raw_provider = (raw[4] or "").lower()
            raw_type     = raw[3]
            text_match = not text     or text in raw_title or text in raw_provider
            type_match = not type_val or raw_type == type_val
            self.table.setRowHidden(row_index, not (text_match and type_match))

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def _get_selected_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.text() if item else None

    def open_add_form(self):
        form = TrainingForm(self)
        if self._current_teacher_id:
            form._set_combo_by_data(form.teacher_combo, self._current_teacher_id)
        form.saved.connect(self.load_data)
        form.exec()

    def open_edit_form(self):
        training_id = self._get_selected_id()
        if not training_id:
            QMessageBox.information(self, "Увага", "Оберіть запис для редагування.")
            return
        form = TrainingForm(self, training_id=training_id)
        form.saved.connect(self.load_data)
        form.exec()

    def delete_selected(self):
        training_id = self._get_selected_id()
        if not training_id:
            QMessageBox.information(self, "Увага", "Оберіть запис для видалення.")
            return
        row = self.table.currentRow()
        title_item = self.table.item(row, 2)
        title = title_item.text() if title_item else "запис"
        reply = QMessageBox.question(
            self, "Підтвердження",
            f"Видалити «{title[:60]}»?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            delete_training(training_id)
            self.load_data()

    # ── Аналіз НПП ────────────────────────────────────────────────────────────

    def _open_analysis(self):
        picker = TeacherSearchDialog(self)
        if picker.exec() != TeacherSearchDialog.Accepted:
            return
        teacher_id, _ = picker.selected()
        if not teacher_id:
            return
        dlg = AnalysisDialog(self, teacher_id=teacher_id)
        dlg.exec()