from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout,
    QLineEdit, QDialogButtonBox, QLabel, QFrame
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont

from services.external_resource_service import update_resources


class ExternalResourceForm(QDialog):
    """
    Форма редагування зовнішніх ресурсів викладача:
    ORCID та Google Scholar URL.
    """

    saved = Signal()

    def __init__(self, parent=None, teacher_id: str = None,
                 teacher_name: str = "", orcid: str = "", scholar: str = ""):
        super().__init__(parent)

        self._teacher_id = teacher_id

        self.setWindowTitle("Редагування зовнішніх ресурсів")
        self.setMinimumWidth(540)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, False)

        # ── ПІБ викладача ─────────────────────────────────────────────────────
        name_font = QFont()
        name_font.setBold(True)
        name_font.setPointSize(11)

        name_label = QLabel(teacher_name)
        name_label.setFont(name_font)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setStyleSheet(
            "color: #222; padding: 8px 12px; "
            "background: #f0f0f0; border-radius: 6px;"
        )

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)

        # ── Поля ──────────────────────────────────────────────────────────────
        self.orcid_edit = QLineEdit(orcid)
        self.orcid_edit.setPlaceholderText("0000-0002-1234-5678")

        self.scholar_edit = QLineEdit(scholar)
        self.scholar_edit.setPlaceholderText("https://scholar.google.com/citations?user=...")

        # ── Layout ────────────────────────────────────────────────────────────
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.setVerticalSpacing(12)
        form.addRow("ORCID:",          self.orcid_edit)
        form.addRow("Google Scholar:", self.scholar_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("Зберегти")
        buttons.button(QDialogButtonBox.Cancel).setText("Скасувати")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.addWidget(name_label)
        layout.addWidget(sep)
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

    # ── Збереження ────────────────────────────────────────────────────────────

    def _save(self):
        orcid   = self.orcid_edit.text().strip()
        scholar = self.scholar_edit.text().strip()
        update_resources(self._teacher_id, orcid, scholar)
        self.saved.emit()
        self.accept()