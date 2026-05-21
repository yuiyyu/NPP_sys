import sys
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from ui.views.security_view import (
    check_password, save_password, is_password_set
)


class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Вхід до системи")
        self.setFixedSize(340, 260)
        self.setWindowFlag(Qt.WindowCloseButtonHint, True)
        self.setStyleSheet("""
            QDialog {
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
                background-color: #3498db;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 6px 20px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #1f618d;
            }
            QLabel {
                background: transparent;
                color: #2c3e50;
            }
        """)

        self._is_first = not is_password_set()

        layout = QVBoxLayout()
        layout.setContentsMargins(30, 24, 30, 24)
        layout.setSpacing(12)
        self.setLayout(layout)

        # Заголовок
        title = QLabel(
            "Створення пароля" if self._is_first else "Вхід до системи"
        )
        f = QFont()
        f.setBold(True)
        f.setPointSize(13)
        title.setFont(f)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Підказка
        if self._is_first:
            hint_text = "Перший запуск. Створіть пароль (3–16 символів)."
        else:
            hint_text = "Введіть пароль для входу до системи."
        hint = QLabel(hint_text)
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        layout.addWidget(hint)

        # Поле пароля
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.Password)
        self.pass_input.setPlaceholderText("Пароль")
        self.pass_input.setMaxLength(16)
        self.pass_input.setFixedHeight(34)
        layout.addWidget(self.pass_input)

        # Підтвердження — тільки при першому запуску
        self.confirm_input = None
        if self._is_first:
            self.confirm_input = QLineEdit()
            self.confirm_input.setEchoMode(QLineEdit.Password)
            self.confirm_input.setPlaceholderText("Підтвердіть пароль")
            self.confirm_input.setMaxLength(16)
            self.confirm_input.setFixedHeight(34)
            layout.addWidget(self.confirm_input)

        # Кнопка
        btn = QPushButton(
            "Створити пароль" if self._is_first else "Увійти"
        )
        btn.setFixedHeight(36)
        btn.clicked.connect(self._submit)
        self.pass_input.returnPressed.connect(self._submit)
        if self.confirm_input:
            self.confirm_input.returnPressed.connect(self._submit)
        layout.addWidget(btn)

    def _submit(self):
        password = self.pass_input.text()

        if len(password) < 3:
            QMessageBox.warning(
                self, "Помилка",
                "Пароль має бути не менше 3 символів."
            )
            return

        if self._is_first:
            confirm = self.confirm_input.text()
            if password != confirm:
                QMessageBox.warning(
                    self, "Помилка",
                    "Паролі не співпадають."
                )
                return
            save_password(password)
            QMessageBox.information(
                self, "Успішно",
                "Пароль створено. Ласкаво просимо!"
            )
            self.accept()
        else:
            if check_password(password):
                self.accept()
            else:
                QMessageBox.warning(
                    self, "Помилка",
                    "Невірний пароль. Спробуйте ще раз."
                )
                self.pass_input.clear()
                self.pass_input.setFocus()

    def closeEvent(self, event):
        sys.exit(0)