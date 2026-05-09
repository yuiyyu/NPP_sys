from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QSpinBox,
    QDialogButtonBox, QTabWidget, QWidget,
    QListWidget, QListWidgetItem, QLabel,
    QMessageBox, QPushButton
)
from PySide6.QtCore import Signal, Qt

from services.publication_service import (
    add_publication, update_publication,
    get_publication_by_id, get_publication_author_ids,
    get_all_teachers_for_select,
    PUBLICATION_TYPES, PUBLICATION_TYPE_LABELS,
)


class PublicationForm(QDialog):
    """
    Форма додавання / редагування публікації.
    Вкладки: Основне | Автори
    """

    saved = Signal()

    def __init__(self, parent=None, pub_id: str = None):
        super().__init__(parent)

        self.pub_id = pub_id
        self.setWindowTitle("Редагувати публікацію" if pub_id else "Додати публікацію")
        self.setMinimumWidth(560)
        self.setMinimumHeight(500)

        tabs = QTabWidget()
        tabs.addTab(self._build_tab_main(),    "📄 Основне")
        tabs.addTab(self._build_tab_authors(), "👥 Автори")

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("Зберегти")
        buttons.button(QDialogButtonBox.Cancel).setText("Скасувати")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(tabs)
        layout.addWidget(buttons)
        self.setLayout(layout)

        self._load_teachers()

        if pub_id:
            self._fill_fields(pub_id)

    # ── Вкладка 1: Основне ────────────────────────────────────────────────────

    def _build_tab_main(self) -> QWidget:
        tab = QWidget()

        self.title = QLineEdit()
        self.title.setPlaceholderText("Обов'язково")

        self.type_combo = QComboBox()
        for key in PUBLICATION_TYPES:
            self.type_combo.addItem(PUBLICATION_TYPE_LABELS[key], key)

        self.year_spin = QSpinBox()
        self.year_spin.setRange(1900, 2100)
        self.year_spin.setValue(2024)
        self.year_spin.setSpecialValueText("—")
        self.year_spin.setMinimum(0)      # 0 = «не вказано»

        self.journal = QLineEdit()
        self.journal.setPlaceholderText("Назва журналу, видавництва або конференції")

        self.doi = QLineEdit()
        self.doi.setPlaceholderText("10.XXXX/XXXXX")

        self.url = QLineEdit()
        self.url.setPlaceholderText("https://...")

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.addRow("Назва *",             self.title)
        form.addRow("Тип",                 self.type_combo)
        form.addRow("Рік",                 self.year_spin)
        form.addRow("Журнал / видавець",   self.journal)
        form.addRow("DOI",                 self.doi)
        form.addRow("URL",                 self.url)

        tab.setLayout(form)
        return tab

    # ── Вкладка 2: Автори ─────────────────────────────────────────────────────

    def _build_tab_authors(self) -> QWidget:
        tab = QWidget()

        # Ліва частина — всі викладачі
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Всі викладачі:"))

        self.search_teachers = QLineEdit()
        self.search_teachers.setPlaceholderText("🔍 Пошук...")
        self.search_teachers.textChanged.connect(self._filter_teachers)
        left_layout.addWidget(self.search_teachers)

        self.all_teachers_list = QListWidget()
        self.all_teachers_list.setSelectionMode(QListWidget.SingleSelection)
        left_layout.addWidget(self.all_teachers_list)

        # Кнопки переміщення
        mid_layout = QVBoxLayout()
        mid_layout.addStretch()
        self.add_author_btn = QPushButton("→")
        self.add_author_btn.setFixedWidth(36)
        self.add_author_btn.setToolTip("Додати автора")
        self.remove_author_btn = QPushButton("←")
        self.remove_author_btn.setFixedWidth(36)
        self.remove_author_btn.setToolTip("Прибрати автора")
        mid_layout.addWidget(self.add_author_btn)
        mid_layout.addWidget(self.remove_author_btn)
        mid_layout.addStretch()

        # Права частина — вибрані автори
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("Автори публікації (порядок важливий):"))

        self.selected_authors_list = QListWidget()
        self.selected_authors_list.setSelectionMode(QListWidget.SingleSelection)
        right_layout.addWidget(self.selected_authors_list)

        # Кнопки порядку
        order_layout = QHBoxLayout()
        self.move_up_btn   = QPushButton("▲ Вище")
        self.move_down_btn = QPushButton("▼ Нижче")
        order_layout.addWidget(self.move_up_btn)
        order_layout.addWidget(self.move_down_btn)
        right_layout.addLayout(order_layout)

        # Збірка
        h_layout = QHBoxLayout()
        h_layout.addLayout(left_layout)
        h_layout.addLayout(mid_layout)
        h_layout.addLayout(right_layout)
        tab.setLayout(h_layout)

        # Сигнали
        self.add_author_btn.clicked.connect(self._add_author)
        self.remove_author_btn.clicked.connect(self._remove_author)
        self.move_up_btn.clicked.connect(self._move_up)
        self.move_down_btn.clicked.connect(self._move_down)
        self.all_teachers_list.doubleClicked.connect(self._add_author)
        self.selected_authors_list.doubleClicked.connect(self._remove_author)

        return tab

    # ── Завантаження викладачів у список ──────────────────────────────────────

    def _load_teachers(self):
        self._teachers = get_all_teachers_for_select()   # [(id, name), ...]
        self._refresh_all_list()

    def _refresh_all_list(self, filter_text: str = ""):
        """Перемальовує лівий список, виключаючи вже вибраних авторів."""
        selected_ids = self._get_selected_ids()
        self.all_teachers_list.clear()

        for t_id, t_name in self._teachers:
            if t_id in selected_ids:
                continue
            if filter_text and filter_text.lower() not in t_name.lower():
                continue
            item = QListWidgetItem(t_name)
            item.setData(Qt.UserRole, t_id)
            self.all_teachers_list.addItem(item)

    def _filter_teachers(self, text: str):
        self._refresh_all_list(filter_text=text)

    def _get_selected_ids(self) -> set:
        ids = set()
        for i in range(self.selected_authors_list.count()):
            ids.add(self.selected_authors_list.item(i).data(Qt.UserRole))
        return ids

    # ── Переміщення авторів ───────────────────────────────────────────────────

    def _add_author(self):
        item = self.all_teachers_list.currentItem()
        if not item:
            return
        new_item = QListWidgetItem(item.text())
        new_item.setData(Qt.UserRole, item.data(Qt.UserRole))
        self.selected_authors_list.addItem(new_item)
        self._refresh_all_list(self.search_teachers.text())

    def _remove_author(self):
        row = self.selected_authors_list.currentRow()
        if row < 0:
            return
        self.selected_authors_list.takeItem(row)
        self._refresh_all_list(self.search_teachers.text())

    def _move_up(self):
        row = self.selected_authors_list.currentRow()
        if row <= 0:
            return
        item = self.selected_authors_list.takeItem(row)
        self.selected_authors_list.insertItem(row - 1, item)
        self.selected_authors_list.setCurrentRow(row - 1)

    def _move_down(self):
        row = self.selected_authors_list.currentRow()
        if row < 0 or row >= self.selected_authors_list.count() - 1:
            return
        item = self.selected_authors_list.takeItem(row)
        self.selected_authors_list.insertItem(row + 1, item)
        self.selected_authors_list.setCurrentRow(row + 1)

    # ── Заповнення при редагуванні ────────────────────────────────────────────

    def _fill_fields(self, pub_id: str):
        row = get_publication_by_id(pub_id)
        if not row:
            return

        _, title, pub_type, year, journal, doi, url = row

        self.title.setText(title or "")
        self.journal.setText(journal or "")
        self.doi.setText(doi or "")
        self.url.setText(url or "")
        self.year_spin.setValue(year if year else 0)

        idx = self.type_combo.findData(pub_type)
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)

        # Автори
        author_ids = get_publication_author_ids(pub_id)
        teacher_map = {t_id: t_name for t_id, t_name in self._teachers}

        for t_id in author_ids:
            if t_id in teacher_map:
                item = QListWidgetItem(teacher_map[t_id])
                item.setData(Qt.UserRole, t_id)
                self.selected_authors_list.addItem(item)

        self._refresh_all_list()

    # ── Збереження ────────────────────────────────────────────────────────────

    def _save(self):
        title = self.title.text().strip()
        if not title:
            QMessageBox.warning(self, "Помилка", "Назва публікації є обов'язковою!")
            return
        
        if self.selected_authors_list.count() == 0:
            QMessageBox.warning(self, "Помилка", "Додайте хоча б одного автора публікації!")
            return

        year_val = self.year_spin.value()

        data = {
            "title":               title,
            "type":                self.type_combo.currentData(),
            "year":                year_val if year_val > 0 else None,
            "journal_or_publisher": self.journal.text().strip(),
            "doi":                 self.doi.text().strip(),
            "url":                 self.url.text().strip(),
        }

        author_ids = [
            self.selected_authors_list.item(i).data(Qt.UserRole)
            for i in range(self.selected_authors_list.count())
        ]

        if self.pub_id:
            update_publication(self.pub_id, data, author_ids)
        else:
            add_publication(data, author_ids)

        self.saved.emit()
        self.accept()