from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QDoubleSpinBox,
    QDialogButtonBox, QWidget, QMessageBox,
    QDateEdit, QLabel, QHBoxLayout
)
from PySide6.QtCore import Signal, QDate
from PySide6.QtWidgets import QAbstractSpinBox
from services.training_service import (
    add_training, update_training, get_training_by_id,
    get_all_teachers_for_select,
    TRAINING_TYPES, TRAINING_TYPE_LABELS,
)


def _date_edit() -> QDateEdit:
    w = QDateEdit()
    w.setCalendarPopup(True)
    w.setDisplayFormat("dd.MM.yyyy")
    w.setSpecialValueText("—")
    w.setMinimumDate(QDate(1900, 1, 1))
    w.setDate(QDate(1900, 1, 1))
    return w


class TrainingForm(QDialog):
    """
    Форма додавання / редагування запису підвищення кваліфікації.
    """

    saved = Signal()

    def __init__(self, parent=None, training_id: str = None):
        super().__init__(parent)

        self.training_id = training_id
        self.setWindowTitle(
            "Редагувати підвищення кваліфікації"
            if training_id else
            "Додати підвищення кваліфікації"
        )
        self.setMinimumWidth(480)

        # ── Поля ──────────────────────────────────────────────────────────────

        # Викладач
        self.teacher_combo = QComboBox()
        self.teacher_combo.setMinimumWidth(300)

        # Назва заходу
        self.title = QLineEdit()
        self.title.setPlaceholderText("Обов'язково")

        # Тип
        self.type_combo = QComboBox()
        for key in TRAINING_TYPES:
            self.type_combo.addItem(TRAINING_TYPE_LABELS[key], key)

        # Організатор / провайдер
        self.provider = QLineEdit()
        self.provider.setPlaceholderText("Установа, організація")

        # Дати
        self.start_date = _date_edit()
        self.end_date   = _date_edit()

        # Години та кредити ЄКТС
        self.hours = QDoubleSpinBox()
        self.hours.setRange(0, 9999)
        self.hours.setDecimals(1)
        self.hours.setSingleStep(1)
        self.hours.setSpecialValueText("—")
        self.hours.setValue(0)

        self.ects = QDoubleSpinBox()
        self.ects.setRange(0, 999)
        self.ects.setDecimals(2)
        self.ects.setSingleStep(0.5)
        self.ects.setSpecialValueText("—")
        self.ects.setValue(0)

        self.hours.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.ects.setButtonSymbols(QAbstractSpinBox.NoButtons)
        # Підказка: автоматичний розрахунок годин → ЄКТС
        hint = QLabel("1 кредит ЄКТС = 30 годин")
        hint.setStyleSheet("color: gray; font-size: 11px;")

        # Авторозрахунок ЄКТС при зміні годин
        self.hours.valueChanged.connect(self._auto_ects)

        # ── Layout ────────────────────────────────────────────────────────────
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.addRow("Викладач *",    self.teacher_combo)
        form.addRow("Назва заходу *", self.title)
        form.addRow("Тип заходу",    self.type_combo)
        form.addRow("Провайдер",     self.provider)
        form.addRow("Дата початку",  self.start_date)
        form.addRow("Дата закінчення", self.end_date)

        hours_widget = QWidget()
        hours_row = QHBoxLayout(hours_widget)
        hours_row.setContentsMargins(0, 0, 0, 0)
        hours_row.addWidget(self.hours)
        hours_row.addWidget(QLabel("год."))
        hours_row.addStretch()
        form.addRow("Кількість годин", hours_widget)

        ects_widget = QWidget()
        ects_row = QHBoxLayout(ects_widget)
        ects_row.setContentsMargins(0, 0, 0, 0)
        ects_row.addWidget(self.ects)
        ects_row.addWidget(QLabel("кредитів"))
        ects_row.addStretch()
        form.addRow("Кредити ЄКТС", ects_widget)
        form.addRow("", hint)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("Зберегти")
        buttons.button(QDialogButtonBox.Cancel).setText("Скасувати")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

        # ── Завантаження викладачів ────────────────────────────────────────────
        self._load_teachers()

        # ── Режим редагування ─────────────────────────────────────────────────
        if training_id:
            self._fill_fields(training_id)

    # ── Довідники ─────────────────────────────────────────────────────────────

    def _load_teachers(self):
        self._teachers = get_all_teachers_for_select()
        self.teacher_combo.clear()
        for t_id, t_name in self._teachers:
            self.teacher_combo.addItem(t_name, t_id)

    # ── Авторозрахунок ЄКТС ───────────────────────────────────────────────────

    def _auto_ects(self, hours_val: float):
        """Якщо години змінились — автоматично перераховує кредити ЄКТС."""
        if hours_val > 0:
            self.ects.blockSignals(True)
            self.ects.setValue(round(hours_val / 30, 2))
            self.ects.blockSignals(False)

    # ── Допоміжні ─────────────────────────────────────────────────────────────

    def _set_combo_by_data(self, combo: QComboBox, value):
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                return

    def _set_date(self, widget: QDateEdit, value):
        if value:
            if isinstance(value, str):
                d = QDate.fromString(value, "yyyy-MM-dd")
            else:
                d = QDate(value.year, value.month, value.day)
            if d.isValid():
                widget.setDate(d)
                return
        widget.setDate(QDate(1900, 1, 1))

    def _read_date(self, widget: QDateEdit):
        d = widget.date()
        return None if d == QDate(1900, 1, 1) else d.toString("yyyy-MM-dd")

    def _read_double(self, spin: QDoubleSpinBox):
        return None if spin.value() == 0 else spin.value()

    # ── Заповнення при редагуванні ────────────────────────────────────────────

    def _fill_fields(self, training_id: str):
        row = get_training_by_id(training_id)
        if not row:
            return

        # (id, teacher_id, title, type, provider, start_date, end_date, hours, ects)
        _, teacher_id, title, t_type, provider, start, end, hours, ects = row

        self._set_combo_by_data(self.teacher_combo, str(teacher_id))
        self.title.setText(title or "")
        self._set_combo_by_data(self.type_combo, t_type)
        self.provider.setText(provider or "")
        self._set_date(self.start_date, start)
        self._set_date(self.end_date, end)

        # Спочатку вимикаємо авторозрахунок, щоб не перезаписати ЄКТС
        self.hours.blockSignals(True)
        self.hours.setValue(float(hours) if hours else 0)
        self.hours.blockSignals(False)

        self.ects.setValue(float(ects) if ects else 0)

    # ── Збереження ────────────────────────────────────────────────────────────

    def _save(self):
        title = self.title.text().strip()
        teacher_id = self.teacher_combo.currentData()

        if not title:
            QMessageBox.warning(self, "Помилка", "Назва заходу є обов'язковою!")
            return
        if not teacher_id:
            QMessageBox.warning(self, "Помилка", "Оберіть викладача!")
            return

        data = {
            "teacher_id": teacher_id,
            "title":      title,
            "type":       self.type_combo.currentData(),
            "provider":   self.provider.text().strip(),
            "start_date": self._read_date(self.start_date),
            "end_date":   self._read_date(self.end_date),
            "hours":      self._read_double(self.hours),
            "ects":       self._read_double(self.ects),
        }

        if self.training_id:
            update_training(self.training_id, data)
        else:
            add_training(data)

        self.saved.emit()
        self.accept()
