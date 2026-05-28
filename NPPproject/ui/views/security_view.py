import hashlib
import winreg
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFormLayout, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

REG_PATH = r"Software\KafedraSystem"
REG_KEY  = "cfg"


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def get_saved_hash() -> str:
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, REG_PATH
        )
        value, _ = winreg.QueryValueEx(key, REG_KEY)
        winreg.CloseKey(key)
        return value
    except FileNotFoundError:
        return ""
    except OSError:
        return ""


def is_password_set() -> bool:
    return bool(get_saved_hash())


def check_password(password: str) -> bool:
    return _hash(password) == get_saved_hash()


def save_password(password: str):
    key = winreg.CreateKey(
        winreg.HKEY_CURRENT_USER, REG_PATH
    )
    winreg.SetValueEx(key, REG_KEY, 0, winreg.REG_SZ, _hash(password))
    winreg.CloseKey(key)


class SecurityView(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()
        layout.setContentsMargins(60, 40, 60, 40)
        layout.setSpacing(16)
        self.setLayout(layout)

        self.setStyleSheet("""
            QWidget {
                background-color: #f4f6f8;
            }
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #c8d0d8;
                border-radius: 4px;
                padding: 5px 8px;
                font-size: 12px;
                color: #2c3e50;
            }
            QLineEdit:focus {
                border-color: #3498db;
            }
            QPushButton {
                background-color: #ffffff;
                color: #2c3e50;
                border: 1px solid #c8d0d8;
                border-radius: 4px;
                padding: 5px 14px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #eaf2fb;
                border-color: #3498db;
                color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #d6eaf8;
            }
            QLabel {
                background: transparent;
                color: #2c3e50;
            }
        """)

        # ── Заголовок ─────────────────────────────────────────────
        title = QLabel("Безпека")
        f = QFont()
        f.setBold(True)
        f.setPointSize(14)
        title.setFont(f)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #1F3864; background: transparent;")
        layout.addWidget(title)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.HLine)
        sep1.setStyleSheet("color: #dde1e5;")
        layout.addWidget(sep1)

        # ── Форма зміни пароля ────────────────────────────────────
        form_label = QLabel("Змінити пароль")
        fl = QFont()
        fl.setBold(True)
        fl.setPointSize(11)
        form_label.setFont(fl)
        form_label.setStyleSheet(
            "color: #2c3e50; background: transparent;"
        )
        layout.addWidget(form_label)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("color: #dde1e5;")
        layout.addWidget(sep2)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)

        self.old_pass = QLineEdit()
        self.old_pass.setEchoMode(QLineEdit.Password)
        self.old_pass.setPlaceholderText("Введіть поточний пароль")
        self.old_pass.setMaxLength(16)
        self.old_pass.setFixedHeight(32)

        self.new_pass = QLineEdit()
        self.new_pass.setEchoMode(QLineEdit.Password)
        self.new_pass.setPlaceholderText("Від 3 до 16 символів")
        self.new_pass.setMaxLength(16)
        self.new_pass.setFixedHeight(32)

        self.confirm_pass = QLineEdit()
        self.confirm_pass.setEchoMode(QLineEdit.Password)
        self.confirm_pass.setPlaceholderText("Повторіть новий пароль")
        self.confirm_pass.setMaxLength(16)
        self.confirm_pass.setFixedHeight(32)

        form.addRow("Поточний пароль:", self.old_pass)
        form.addRow("Новий пароль:",    self.new_pass)
        form.addRow("Підтвердження:",   self.confirm_pass)
        layout.addLayout(form)

        layout.addSpacing(8)

        btn = QPushButton("Змінити пароль")
        btn.setFixedHeight(36)
        btn.setFixedWidth(180)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #1f618d;
            }
        """)
        btn.clicked.connect(self._change_password)

        btn_layout = QVBoxLayout()
        btn_layout.setAlignment(Qt.AlignCenter)
        btn_layout.addWidget(btn)
        layout.addLayout(btn_layout)

        layout.addStretch()

    def _change_password(self):
        old     = self.old_pass.text()
        new     = self.new_pass.text()
        confirm = self.confirm_pass.text()

        if not old:
            QMessageBox.warning(
                self, "Помилка", "Введіть поточний пароль."
            )
            return

        if not check_password(old):
            QMessageBox.warning(
                self, "Помилка", "Поточний пароль невірний."
            )
            self.old_pass.clear()
            self.old_pass.setFocus()
            return

        if len(new) < 3:
            QMessageBox.warning(
                self, "Помилка",
                "Новий пароль має бути не менше 3 символів."
            )
            return

        if new != confirm:
            QMessageBox.warning(
                self, "Помилка", "Паролі не співпадають."
            )
            self.confirm_pass.clear()
            self.confirm_pass.setFocus()
            return

        save_password(new)
        self.old_pass.clear()
        self.new_pass.clear()
        self.confirm_pass.clear()
        QMessageBox.information(
            self, "Успішно", "Пароль успішно змінено!"
        )
