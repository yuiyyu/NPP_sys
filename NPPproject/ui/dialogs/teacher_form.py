import re
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QTextEdit,
    QDialogButtonBox, QTabWidget, QWidget,
    QMessageBox, QLabel, QDateEdit, QFrame
)
from PySide6.QtCore import Signal, QDate, Qt
from PySide6.QtGui import QFont
from services.teacher_service import (
    add_teacher, update_teacher, get_teacher_by_id,
    get_academic_degrees, get_academic_titles, get_departments,
)
from ui.styles import BTN_SAVE_STYLE, BTN_CANCEL_STYLE


STATUS_OPTIONS = [
    ("active",   "Активний"),
    ("on_leave", "У відпустці"),
    ("retired",  "Звільнений"),
]

RE_EMAIL  = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
RE_ORCID  = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")
RE_URL    = re.compile(r"^https?://")


def _str(val) -> str:
    return str(val) if val is not None else ""


def _date_edit(nullable: bool = True) -> QDateEdit:
    w = QDateEdit()
    w.setCalendarPopup(True)
    w.setDisplayFormat("dd.MM.yyyy")
    w.setMinimumWidth(130)
    if nullable:
        w.setSpecialValueText("—")
        w.setMinimumDate(QDate(1900, 1, 1))
        w.setDate(QDate(1900, 1, 1))
    return w


class TeacherForm(QDialog):
    saved = Signal()

    def __init__(self, parent=None, teacher_id: str = None):
        super().__init__(parent)

        self.teacher_id = teacher_id
        self.setWindowTitle("Редагувати викладача" if teacher_id else "Додати викладача")
        self.setMinimumWidth(520)
        self.setMinimumHeight(500)

        header = QLabel("Редагування викладача" if teacher_id else "Новий викладач")
        header_font = QFont()
        header_font.setBold(True)
        header_font.setPointSize(12)
        header.setFont(header_font)
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet(
            "color: #2c3e50; padding: 10px; "
            "background: #eaf2fb; border-radius: 4px;"
        )

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #dde1e5;")

        tabs = QTabWidget()
        tabs.addTab(self._build_tab_main(),      "📋 Основне")
        tabs.addTab(self._build_tab_contacts(),  "📞 Контакти & Посилання")
        tabs.addTab(self._build_tab_employment(),"🗓 Зайнятість")

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("Зберегти")
        buttons.button(QDialogButtonBox.Cancel).setText("Скасувати")
        buttons.button(QDialogButtonBox.Save).setStyleSheet(BTN_SAVE_STYLE)
        buttons.button(QDialogButtonBox.Cancel).setStyleSheet(BTN_CANCEL_STYLE)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.addWidget(header)
        layout.addWidget(sep)
        layout.addWidget(tabs)
        layout.addWidget(buttons)
        self.setLayout(layout)

        self._load_references()
        if teacher_id:
            self._fill_fields(teacher_id)

    def _build_tab_main(self) -> QWidget:
        tab = QWidget()
        self.last_name        = QLineEdit()
        self.last_name.setPlaceholderText("Обов'язково")
        self.first_name       = QLineEdit()
        self.first_name.setPlaceholderText("Обов'язково")
        self.middle_name      = QLineEdit()
        self.date_of_birth    = _date_edit()
        self.degree_combo     = QComboBox()
        self.title_combo      = QComboBox()
        self.department_combo = QComboBox()
        self.status_combo     = QComboBox()
        for key, label in STATUS_OPTIONS:
            self.status_combo.addItem(label, key)

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.setVerticalSpacing(10)
        form.setContentsMargins(12, 12, 12, 12)
        form.addRow("Прізвище *",      self.last_name)
        form.addRow("Ім'я *",          self.first_name)
        form.addRow("По батькові",      self.middle_name)
        form.addRow("Дата народження",  self.date_of_birth)
        form.addRow("Науковий ступінь", self.degree_combo)
        form.addRow("Вчене звання",     self.title_combo)
        form.addRow("Кафедра",          self.department_combo)
        form.addRow("Статус",           self.status_combo)
        tab.setLayout(form)
        return tab

    def _build_tab_contacts(self) -> QWidget:
        tab = QWidget()
        self.email = QLineEdit()
        self.email.setPlaceholderText("example@university.edu")
        self.phone = QLineEdit()
        self.phone.setPlaceholderText("+380XXXXXXXXX")
        self.orcid = QLineEdit()
        self.orcid.setPlaceholderText("0000-0000-0000-0000")
        self.google_scholar_url = QLineEdit()
        self.google_scholar_url.setPlaceholderText("https://scholar.google.com/citations?user=...")

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.setVerticalSpacing(10)
        form.setContentsMargins(12, 12, 12, 12)
        form.addRow("Email",          self.email)
        form.addRow("Телефон",        self.phone)
        form.addRow("ORCID",          self.orcid)
        form.addRow("Google Scholar", self.google_scholar_url)
        tab.setLayout(form)
        return tab

    def _build_tab_employment(self) -> QWidget:
        tab = QWidget()
        self.employment_start_date = _date_edit()
        self.employment_end_date   = _date_edit()
        self.notes = QTextEdit()
        self.notes.setPlaceholderText("Довільні примітки…")
        self.notes.setFixedHeight(90)

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.setVerticalSpacing(10)
        form.setContentsMargins(12, 12, 12, 12)
        form.addRow("Дата прийому",    self.employment_start_date)
        form.addRow("Дата звільнення", self.employment_end_date)
        form.addRow("Примітки",        self.notes)
        tab.setLayout(form)
        return tab

    def _load_references(self):
        self.degree_combo.addItem("— не вказано —", None)
        for deg_id, deg_name in get_academic_degrees():
            self.degree_combo.addItem(deg_name, deg_id)

        self.title_combo.addItem("— не вказано —", None)
        for t_id, t_name in get_academic_titles():
            self.title_combo.addItem(t_name, t_id)

        self.department_combo.addItem("— не вказано —", None)
        for d_id, d_name in get_departments():
            self.department_combo.addItem(d_name, d_id)

    def _set_combo(self, combo: QComboBox, value):
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

    def _fill_fields(self, teacher_id: str):
        row = get_teacher_by_id(teacher_id)
        if not row:
            return
        (_, first, last, middle, dob,
         deg_id, title_id, dept_id,
         orcid, scholar, email, phone,
         emp_start, emp_end, status, notes) = row

        self.last_name.setText(_str(last))
        self.first_name.setText(_str(first))
        self.middle_name.setText(_str(middle))
        self._set_date(self.date_of_birth, dob)
        self._set_combo(self.degree_combo, deg_id)
        self._set_combo(self.title_combo, title_id)
        self._set_combo(self.department_combo, dept_id)
        self._set_combo(self.status_combo, status or "active")
        self.email.setText(_str(email))
        self.phone.setText(_str(phone))
        self.orcid.setText(_str(orcid))
        self.google_scholar_url.setText(_str(scholar))
        self._set_date(self.employment_start_date, emp_start)
        self._set_date(self.employment_end_date, emp_end)
        self.notes.setPlainText(_str(notes))

    def _read_date(self, widget: QDateEdit):
        d = widget.date()
        return None if d == QDate(1900, 1, 1) else d.toString("yyyy-MM-dd")

    # ── Валідація ─────────────────────────────────────────────────────────────

    def _validate(self) -> list:
        errors = []
        today = QDate.currentDate()
        empty = QDate(1900, 1, 1)

        # Обов'язкові поля
        if not self.last_name.text().strip():
            errors.append("Прізвище є обов'язковим полем.")
        if not self.first_name.text().strip():
            errors.append("Ім'я є обов'язковим полем.")

        # Дата народження — не в майбутньому
        dob = self.date_of_birth.date()
        if dob != empty and dob > today:
            errors.append("Дата народження не може бути в майбутньому.")

        # Дати прийому/звільнення — логіка порядку
        emp_start = self.employment_start_date.date()
        emp_end   = self.employment_end_date.date()

        if emp_start != empty and emp_start > today:
            errors.append("Дата прийому не може бути в майбутньому.")

        if emp_start != empty and emp_end != empty and emp_end < emp_start:
            errors.append("Дата звільнення не може бути раніше дати прийому.")

        # Email
        email = self.email.text().strip()
        if email and not RE_EMAIL.match(email):
            errors.append(
                "Невірний формат Email.\n"
                "Очікуваний формат: example@university.edu"
            )

        # ORCID
        orcid = self.orcid.text().strip()
        if orcid and not RE_ORCID.match(orcid):
            errors.append(
                "Невірний формат ORCID.\n"
                "Очікуваний формат: 0000-0000-0000-0000"
            )

        # Google Scholar URL
        scholar = self.google_scholar_url.text().strip()
        if scholar and not RE_URL.match(scholar):
            errors.append(
                "Google Scholar URL має починатись з https:// або http://"
            )

        return errors

    # ── Збереження ────────────────────────────────────────────────────────────

    def _save(self):
        errors = self._validate()
        if errors:
            QMessageBox.warning(
                self,
                "Помилка введення даних",
                "\n\n".join(f"• {e}" for e in errors)
            )
            return

        data = {
            "first_name":            self.first_name.text().strip(),
            "last_name":             self.last_name.text().strip(),
            "middle_name":           self.middle_name.text().strip(),
            "date_of_birth":         self._read_date(self.date_of_birth),
            "degree_id":             self.degree_combo.currentData(),
            "title_id":              self.title_combo.currentData(),
            "department_id":         self.department_combo.currentData(),
            "orcid":                 self.orcid.text().strip(),
            "google_scholar_url":    self.google_scholar_url.text().strip(),
            "email":                 self.email.text().strip(),
            "phone":                 self.phone.text().strip(),
            "employment_start_date": self._read_date(self.employment_start_date),
            "employment_end_date":   self._read_date(self.employment_end_date),
            "status":                self.status_combo.currentData(),
            "notes":                 self.notes.toPlainText().strip(),
        }

        if self.teacher_id:
            update_teacher(self.teacher_id, data)
        else:
            add_teacher(data)

        self.saved.emit()
        self.accept()