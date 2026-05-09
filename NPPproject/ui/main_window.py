from PySide6.QtWidgets import (
    QMainWindow, QWidget, QListWidget, QListWidgetItem,
    QStackedWidget, QHBoxLayout, QLabel, QVBoxLayout, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ui.views.teachers_view import TeachersView
from ui.views.publications_view import PublicationsView
from ui.views.trainings_view import TrainingsView
from ui.views.license_view import LicenseView
from ui.views.external_resources_view import ExternalResourcesView
from ui.views.reference_view import ReferenceView
from ui.views.archive_view import ArchiveView
from ui.styles import APP_STYLE, MENU_STYLE, C_WHITE, C_ACCENT, C_BORDER_LT, C_TEXT_MUTED


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Система обліку НПП")
        self.setMinimumSize(1600, 1000)
        self.setStyleSheet(APP_STYLE)

        # ── Бокове меню ───────────────────────────────────────────────────────
        sidebar = QWidget()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet(f"background-color: {C_WHITE};")

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet(f"color: {C_BORDER_LT};")

        self.menu = QListWidget()
        self.menu.setStyleSheet(MENU_STYLE)

        items = [
            "Викладачі",
            "Публікації",
            "Підвищення кваліфікації",
            "Таблиці самооцінювання",
            "Зовнішні ресурси",
            "Довідники",
            "Архів публікацій",
        ]
        for label in items:
            self.menu.addItem(QListWidgetItem(label))

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        sidebar_layout.addWidget(divider)
        sidebar_layout.addWidget(self.menu)
        sidebar_layout.addStretch()

        version_label = QLabel("v1.0")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet(
            f"color: {C_TEXT_MUTED}; font-size: 11px;"
            f"padding: 10px; background: {C_WHITE};"
            f"border-top: 1px solid {C_BORDER_LT};"
        )
        sidebar_layout.addWidget(version_label)
        
        from services.archive_service import run_auto_archive
        run_auto_archive()
        # ── Вертикальна межа між меню і контентом ────────────────────────────
        v_line = QFrame()
        v_line.setFrameShape(QFrame.VLine)
        v_line.setStyleSheet(f"color: {C_BORDER_LT};")

        # ── Стек сторінок ─────────────────────────────────────────────────────
        self.stack = QStackedWidget()

        self.stack.addWidget(TeachersView())          # 0
        self.stack.addWidget(PublicationsView())      # 1
        self.stack.addWidget(TrainingsView())         # 2
        self.stack.addWidget(LicenseView())           # 3
        self.stack.addWidget(ExternalResourcesView()) # 4
        self.stack.addWidget(ReferenceView())         # 5
        self.stack.addWidget(ArchiveView())           # 6

        # ── Збірка ────────────────────────────────────────────────────────────
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(sidebar)
        layout.addWidget(v_line)
        layout.addWidget(self.stack)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.menu.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.menu.setCurrentRow(0)