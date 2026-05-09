# ui/styles.py

# ── Кольори ───────────────────────────────────────────────────────────────────
C_BG          = "#f4f6f8"   # фон сторінок
C_WHITE       = "#ffffff"
C_SIDEBAR     = "#ffffff"   # бокове меню — біле
C_SIDEBAR_BRD = "#dde1e5"   # права межа меню
C_ACCENT      = "#3498db"   # синій акцент
C_ACCENT_HOV  = "#2980b9"
C_ACCENT_DRK  = "#1f618d"
C_ACCENT_BG   = "#eaf2fb"   # світло-синій фон активного пункту
C_BORDER      = "#c8d0d8"
C_BORDER_LT   = "#dde1e5"
C_HEADER_BG   = "#eaecee"
C_TEXT        = "#2c3e50"
C_TEXT_MUTED  = "#7f8c8d"
C_ALT_ROW     = "#f8f9fa"
C_SEL_ROW     = "#d6eaf8"
C_RED         = "#e74c3c"
C_RED_HOV     = "#c0392b"
C_RED_BG      = "#fdf2f2"
C_RED_PRESS   = "#fadbd8"


# ── Меню (sidebar) — світле ───────────────────────────────────────────────────
MENU_STYLE = f"""
    QListWidget {{
        background-color: {C_WHITE};
        color: {C_TEXT};
        border: none;
        border-right: 1px solid {C_BORDER_LT};
        font-size: 13px;
        padding-top: 4px;
        outline: none;
    }}
    QListWidget::item {{
        padding: 11px 16px;
        border-left: 3px solid transparent;
        color: {C_TEXT_MUTED};
        border-radius: 0px;
    }}
    QListWidget::item:hover {{
        background-color: {C_ACCENT_BG};
        color: {C_ACCENT};
        border-left: 3px solid #a9d4f0;
    }}
    QListWidget::item:selected {{
        background-color: {C_ACCENT_BG};
        border-left: 3px solid {C_ACCENT};
        color: {C_ACCENT};
        font-weight: bold;
    }}
"""

# ── Глобальний стиль застосунку ───────────────────────────────────────────────
APP_STYLE = f"""
    QMainWindow, QDialog {{
        background-color: {C_BG};
    }}
    QWidget {{
        background-color: {C_BG};
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 13px;
        color: {C_TEXT};
    }}
    QPushButton {{
        background-color: {C_WHITE};
        color: {C_TEXT};
        border: 1px solid {C_BORDER};
        border-radius: 4px;
        padding: 5px 14px;
        font-size: 12px;
    }}
    QPushButton:hover {{
        background-color: {C_ACCENT_BG};
        border-color: {C_ACCENT};
        color: {C_ACCENT_HOV};
    }}
    QPushButton:pressed {{
        background-color: {C_SEL_ROW};
        border-color: {C_ACCENT_HOV};
    }}
    QPushButton:disabled {{
        background-color: #f0f0f0;
        color: #aaaaaa;
        border-color: #dddddd;
    }}
    QLineEdit {{
        background-color: {C_WHITE};
        border: 1px solid {C_BORDER};
        border-radius: 4px;
        padding: 5px 8px;
        font-size: 12px;
        color: {C_TEXT};
    }}
    QLineEdit:focus {{
        border-color: {C_ACCENT};
    }}
    QTextEdit {{
        background-color: {C_WHITE};
        border: 1px solid {C_BORDER};
        border-radius: 4px;
        padding: 4px 8px;
        font-size: 12px;
        color: {C_TEXT};
    }}
    QTextEdit:focus {{
        border-color: {C_ACCENT};
    }}
    QTableWidget {{
        background-color: {C_WHITE};
        alternate-background-color: {C_ALT_ROW};
        gridline-color: #e8ecef;
        border: 1px solid {C_BORDER_LT};
        border-radius: 4px;
        font-size: 12px;
        color: {C_TEXT};
    }}
    QTableWidget::item:selected {{
        background-color: {C_SEL_ROW};
        color: #1a252f;
    }}
QHeaderView::section {{
        background-color: {C_HEADER_BG};
        color: {C_TEXT};
        border: none;
        border-right: 1px solid #d5d8dc;
        border-bottom: 1px solid #d5d8dc;
        padding: 6px 8px;
        font-weight: bold;
        font-size: 12px;
    }}
    QHeaderView::section:hover {{
        background-color: {C_ACCENT_BG};
        color: {C_ACCENT};
    }}
    QHeaderView::section:pressed {{
        background-color: {C_SEL_ROW};
        color: {C_ACCENT_DRK};
    }}
    QComboBox {{
        background-color: {C_WHITE};
        border: 1px solid {C_BORDER};
        border-radius: 4px;
        padding: 4px 32px 4px 8px;   /* ← більший відступ праворуч для стрілки */
        font-size: 12px;
        color: {C_TEXT};
    }}
    QComboBox:focus {{
        border-color: {C_ACCENT};
    }}
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 24px;
        border-left: 1px solid {C_BORDER};   /* ← роздільник */
        border-radius: 0 4px 4px 0;
    }}
    QComboBox::down-arrow {{
        image: none;
        width: 0;
        height: 0;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 6px solid {C_TEXT_MUTED};  /* ← трикутник ▼ */
    }}
    QComboBox::down-arrow:on {{
        border-top: none;
        border-bottom: 6px solid {C_ACCENT};   /* ← синій коли відкрито */
    }}
    QComboBox QAbstractItemView {{
        background-color: {C_WHITE};
        border: 1px solid {C_BORDER};
        selection-background-color: {C_SEL_ROW};
        color: {C_TEXT};
    }}
    QScrollBar:vertical {{
        background: {C_BG};
        width: 8px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical {{
        background: {C_BORDER};
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {C_ACCENT};
    }}
    QScrollBar:horizontal {{
        background: {C_BG};
        height: 8px;
        border-radius: 4px;
    }}
    QScrollBar::handle:horizontal {{
        background: {C_BORDER};
        border-radius: 4px;
        min-width: 30px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {C_ACCENT};
    }}
    QScrollBar::add-line, QScrollBar::sub-line {{
        width: 0; height: 0;
    }}
    QTabWidget::pane {{
        border: 1px solid {C_BORDER_LT};
        border-radius: 4px;
        background: {C_WHITE};
    }}
    QTabBar::tab {{
        background: {C_HEADER_BG};
        color: {C_TEXT_MUTED};
        border: 1px solid {C_BORDER_LT};
        border-bottom: none;
        padding: 6px 16px;
        border-radius: 4px 4px 0 0;
        font-size: 12px;
    }}
    QTabBar::tab:selected {{
        background: {C_WHITE};
        color: {C_TEXT};
        font-weight: bold;
        border-bottom: 2px solid {C_ACCENT};
    }}
    QTabBar::tab:hover:!selected {{
        background: {C_ACCENT_BG};
        color: {C_ACCENT_HOV};
    }}
    QCheckBox {{
        color: {C_TEXT};
        font-size: 12px;
    }}
    QCheckBox::indicator {{
        width: 15px;
        height: 15px;
        border: 1px solid {C_BORDER};
        border-radius: 3px;
        background: {C_WHITE};
    }}
    QCheckBox::indicator:checked {{
        background-color: {C_ACCENT};
        border-color: {C_ACCENT_HOV};
    }}
    QSplitter::handle {{
        background-color: {C_BORDER_LT};
        width: 2px;
    }}
    QListWidget {{
        background-color: {C_WHITE};
        border: 1px solid {C_BORDER_LT};
        border-radius: 4px;
    }}
    QListWidget::item {{
        padding: 6px 8px;
        color: {C_TEXT};
    }}
    QListWidget::item:selected {{
        background-color: {C_SEL_ROW};
        color: #1a252f;
    }}
    QListWidget::item:hover {{
        background-color: {C_ACCENT_BG};
    }}
    QLabel {{
        background: transparent;
    }}
    QSpinBox {{
        background-color: {C_WHITE};
        border: 1px solid {C_BORDER};
        border-radius: 4px;
        padding: 4px 8px;
        font-size: 12px;
        color: {C_TEXT};
    }}
    QSpinBox:focus {{
        border-color: {C_ACCENT};
    }}
    QSpinBox::up-button, QSpinBox::down-button {{
        width: 0;
        height: 0;
        border: none;
    }}
    QDoubleSpinBox, QSpinBox {{
        background-color: {C_WHITE};
        border: 1px solid {C_BORDER};
        border-radius: 4px;
        padding: 4px 8px;
        font-size: 12px;
        color: {C_TEXT};
    }}
    QDoubleSpinBox:focus, QSpinBox:focus {{
        border-color: {C_ACCENT};
    }}
    QDateEdit {{
        background-color: {C_WHITE};
        border: 1px solid {C_BORDER};
        border-radius: 4px;
        padding: 4px 32px 4px 8px;   /* ← відступ щоб текст не ховався під кнопкою */
        font-size: 12px;
        color: {C_TEXT};
        min-width: 120px;             /* ← мінімальна ширина */
    }}
    QDateEdit:focus {{
        border-color: {C_ACCENT};
    }}
    QDateEdit::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 24px;
        border-left: 1px solid {C_BORDER};
        border-radius: 0 4px 4px 0;
    }}
    QDateEdit::down-arrow {{
        image: none;
        width: 0;
        height: 0;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 6px solid {C_TEXT_MUTED};
    }}
    QDateEdit::down-arrow:on {{
        border-top: none;
        border-bottom: 6px solid {C_ACCENT};
    }}
"""

# ── Кнопки ────────────────────────────────────────────────────────────────────
BTN_DELETE_STYLE = f"""
    QPushButton {{
        background-color: {C_WHITE};
        color: {C_RED};
        border: 1px solid {C_RED};
        border-radius: 4px;
        padding: 5px 14px;
        font-size: 12px;
    }}
    QPushButton:hover {{
        background-color: {C_RED_BG};
        border-color: {C_RED_HOV};
        color: {C_RED_HOV};
    }}
    QPushButton:pressed {{
        background-color: {C_RED_PRESS};
    }}
"""

BTN_SAVE_STYLE = f"""
    QPushButton {{
        background-color: {C_ACCENT};
        color: #ffffff;
        border: none;
        border-radius: 4px;
        padding: 6px 20px;
        font-size: 12px;
        font-weight: bold;
    }}
    QPushButton:hover {{
        background-color: {C_ACCENT_HOV};
    }}
    QPushButton:pressed {{
        background-color: {C_ACCENT_DRK};
    }}
"""

BTN_CANCEL_STYLE = f"""
    QPushButton {{
        background-color: {C_WHITE};
        color: {C_TEXT_MUTED};
        border: 1px solid {C_BORDER};
        border-radius: 4px;
        padding: 6px 20px;
        font-size: 12px;
    }}
    QPushButton:hover {{
        background-color: {C_BG};
        color: {C_TEXT};
    }}
"""

BTN_ACCENT_STYLE = f"""
    QPushButton {{
        background-color: {C_ACCENT};
        color: #ffffff;
        border: none;
        border-radius: 4px;
        padding: 5px 14px;
        font-size: 12px;
    }}
    QPushButton:hover {{
        background-color: {C_ACCENT_HOV};
    }}
    QPushButton:pressed {{
        background-color: {C_ACCENT_DRK};
    }}
    QPushButton:disabled {{
        background-color: #a9cce3;
        color: #ffffff;
    }}
"""