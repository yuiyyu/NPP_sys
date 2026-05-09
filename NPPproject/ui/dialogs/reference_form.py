from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout,
    QLineEdit, QDialogButtonBox, QLabel, QFrame, QMessageBox
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont

from services.reference_service import (
    add_department, update_department,
    add_degree, update_degree,
    add_title, update_title,
)


def _make_name_label(text: str) -> QLabel:
    font = QFont()
    font.setBold(True)
    font.setPointSize(11)
    lbl = QLabel(text)
    lbl.setFont(font)
    lbl.setAlignment(Qt.AlignCenter)
    lbl.setStyleSheet(
        "color: #222; padding: 8px 12px; "
        "background: #f0f0f0; border-radius: 6px;"
    )
    return lbl


def _make_sep() -> QFrame:
    sep = QFrame()
    sep.setFrameShape(QFrame.HLine)
    sep.setFrameShadow(QFrame.Sunken)
    return sep


# ── Форма кафедри ─────────────────────────────────────────────────────────────

class DepartmentForm(QDialog):
    saved = Signal()

    def __init__(self, parent=None, dep_id=None, name="", code=""):
        super().__init__(parent)
        self._dep_id = dep_id
        self.setWindowTitle("Редагування кафедри" if dep_id else "Додати кафедру")
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, False)
        self.setMinimumWidth(420)

        header = _make_name_label("Кафедра" if not dep_id else name)

        self.name_edit = QLineEdit(name)
        self.name_edit.setPlaceholderText("Повна назва кафедри")

        self.code_edit = QLineEdit(code)
        self.code_edit.setPlaceholderText("Наприклад: ІТ, КН, МФ")

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.setVerticalSpacing(10)
        form.addRow("Назва *:", self.name_edit)
        form.addRow("Код:",     self.code_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("Зберегти")
        buttons.button(QDialogButtonBox.Cancel).setText("Скасувати")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.addWidget(header)
        layout.addWidget(_make_sep())
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def _save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Помилка", "Назва є обов'язковою!")
            return
        code = self.code_edit.text().strip()
        if self._dep_id:
            update_department(self._dep_id, name, code)
        else:
            add_department(name, code)
        self.saved.emit()
        self.accept()


# ── Форма наукового ступеня ───────────────────────────────────────────────────

class DegreeForm(QDialog):
    saved = Signal()

    def __init__(self, parent=None, deg_id=None, name="", short_name=""):
        super().__init__(parent)
        self._deg_id = deg_id
        self.setWindowTitle("Редагування ступеня" if deg_id else "Додати науковий ступінь")
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, False)
        self.setMinimumWidth(420)

        header = _make_name_label("Науковий ступінь" if not deg_id else name)

        self.name_edit = QLineEdit(name)
        self.name_edit.setPlaceholderText("Наприклад: доктор технічних наук")

        self.short_edit = QLineEdit(short_name)
        self.short_edit.setPlaceholderText("Наприклад: д.т.н.")

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.setVerticalSpacing(10)
        form.addRow("Повна назва *:", self.name_edit)
        form.addRow("Скорочення:",    self.short_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("Зберегти")
        buttons.button(QDialogButtonBox.Cancel).setText("Скасувати")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.addWidget(header)
        layout.addWidget(_make_sep())
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def _save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Помилка", "Назва є обов'язковою!")
            return
        short = self.short_edit.text().strip()
        if self._deg_id:
            update_degree(self._deg_id, name, short)
        else:
            add_degree(name, short)
        self.saved.emit()
        self.accept()


# ── Форма вченого звання ──────────────────────────────────────────────────────

class TitleForm(QDialog):
    saved = Signal()

    def __init__(self, parent=None, title_id=None, name=""):
        super().__init__(parent)
        self._title_id = title_id
        self.setWindowTitle("Редагування звання" if title_id else "Додати вчене звання")
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, False)
        self.setMinimumWidth(420)

        header = _make_name_label("Вчене звання" if not title_id else name)

        self.name_edit = QLineEdit(name)
        self.name_edit.setPlaceholderText("Наприклад: професор, доцент")

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.setVerticalSpacing(10)
        form.addRow("Назва *:", self.name_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("Зберегти")
        buttons.button(QDialogButtonBox.Cancel).setText("Скасувати")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.addWidget(header)
        layout.addWidget(_make_sep())
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def _save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Помилка", "Назва є обов'язковою!")
            return
        if self._title_id:
            update_title(self._title_id, name)
        else:
            add_title(name)
        self.saved.emit()
        self.accept()