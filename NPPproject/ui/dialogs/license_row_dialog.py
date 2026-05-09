from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QTextEdit, QDialogButtonBox,
    QLabel, QWidget, QFrame,
    QPushButton, QScrollArea, QListWidget,
    QListWidgetItem, QMessageBox, QSplitter, QMenu, QSizePolicy
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont
from services.license_service import (get_publications_by_teacher,
    get_trainings_by_teacher, encode_ids, decode_ids, is_json_ids)
from ui.dialogs.license_select_dialog import LicenseSelectDialog
try:
    from services.license_auto_match import auto_match
except ImportError:
    try:
        from services.license_auto_match import auto_match
    except ImportError:
        from services.license_auto_match import auto_match


DISC_FIELDS = [
    ("course_name",  "Назва ОК *:",                  "Назва дисципліни / освітнього компонента"),
    ("specialty",    "Спеціальність:",               "Наприклад: 121, 122, 123"),
    ("syllabus_url", "Силабус (посилання):",          "https://drive.google.com/..."),
    ("program_url",  "Робоча програма (посилання):", "https://drive.google.com/..."),
]

AUTO_FIELDS = [
    ("articles",    "Фахові публікації за ОК"),
    ("conferences", "Тези / матеріали конференцій"),
    ("textbooks",   "Підручники / навчально-методичні посібники"),
    ("methodical",  "Методичні матеріали, розробки тощо"),
    ("trainings",   "Підвищення кваліфікації, стажування"),
]

ALL_KEYS    = [f[0] for f in DISC_FIELDS] + [f[0] for f in AUTO_FIELDS]
DB_SENTINEL = "__DB__"

STYLE_EMPTY = "background:#fffbe6; border:1px solid #ccc; color:#000000;"
STYLE_DB    = "background:#f0f0f0; border:1px solid #ccc; color:#000000;"
STYLE_LOCAL = "background:#ffffff; border:1px solid #999; color:#000000;"


class LicenseRowDialog(QDialog):
    saved = Signal(list)

    def __init__(self, parent=None, row_data: dict = None,
                 disciplines: list = None, last_5_years: bool = False):
        super().__init__(parent)
        self._row_data   = row_data or {}
        self._discs      = [dict(d) for d in (disciplines or [])]
        self._cur        = -1
        self._loading    = False
        self._dirty      = False
        self._last_5y    = last_5_years
        self._teacher_id = (row_data or {}).get("teacher_id", "")
        self._db_pubs    = None
        self._db_trains  = None

        self.setWindowTitle(f"Редагування — {self._row_data.get('full_name', '')}")
        self.setMinimumWidth(1100)
        self.setMinimumHeight(780)
        self.resize(1200, 820)

        self._build_ui()

        if self._discs:
            self.disc_list.setCurrentRow(0)

    # ─────────────────────────────────────────────────────────────────────────
    # UI
    # ─────────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(0)

        # ── Заголовок ─────────────────────────────────────────────────────────
        header = QWidget()
        hl = QHBoxLayout(header)
        hl.setContentsMargins(0, 0, 0, 6)

        title_lbl = QLabel(f"Редагування — {self._row_data.get('full_name', '')}")
        tf = QFont(); tf.setBold(True); tf.setPointSize(11)
        title_lbl.setFont(tf)
        hl.addWidget(title_lbl)
        hl.addStretch()

        self._btn_save   = QPushButton("💾 Зберегти")
        self._btn_cancel = QPushButton("Скасувати")
        self._btn_save.setMinimumWidth(120)
        self._btn_save.setMinimumHeight(30)
        sf = QFont(); sf.setBold(True); sf.setPointSize(10)
        self._btn_save.setFont(sf)
        self._btn_save.clicked.connect(self._save)
        self._btn_cancel.clicked.connect(self._on_cancel)
        hl.addWidget(self._btn_save)
        hl.addWidget(self._btn_cancel)

        root.addWidget(header)

        # ── Панель дій ────────────────────────────────────────────────────────
        action_bar = QWidget()
        al = QHBoxLayout(action_bar)
        al.setContentsMargins(0, 0, 0, 6)
        al.setSpacing(6)

        self.btn_add       = QPushButton("➕ Додати")
        self.btn_del       = QPushButton("🗑 Видалити")
        self.btn_fill_all  = QPushButton("Заповнити з БД")
        self.btn_auto      = QPushButton("Автоматичне заповнення з БД по дисципліні")
        self.btn_clear_all = QPushButton("✕ Очистити поля")

        self.btn_add.setToolTip("Додати нову дисципліну")
        self.btn_del.setToolTip("Видалити обрану дисципліну")
        self.btn_fill_all.setToolTip("Відкрити список публікацій для ручного вибору")
        self.btn_auto.setToolTip("Авто-пошук публікацій за назвою дисципліни")
        self.btn_clear_all.setToolTip("Очистити авто-поля обраної дисципліни")

        self.btn_add.clicked.connect(self._add)
        self.btn_del.clicked.connect(self._delete)
        self.btn_fill_all.clicked.connect(self._fill_all_from_db)
        self.btn_auto.clicked.connect(self._auto_search)
        self.btn_clear_all.clicked.connect(self._clear_all_from_db)

        for b in [self.btn_add, self.btn_del, self.btn_fill_all,
                  self.btn_auto, self.btn_clear_all]:
            al.addWidget(b)
        al.addStretch()

        root.addWidget(action_bar)

        # ── Сплітер ───────────────────────────────────────────────────────────
        splitter = QSplitter(Qt.Horizontal)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 6, 0)
        ll.setSpacing(4)

        bf = QFont(); bf.setBold(True)
        lbl_disc = QLabel("Дисципліни:")
        lbl_disc.setFont(bf)
        ll.addWidget(lbl_disc)

        self.disc_list = QListWidget()
        self.disc_list.setMinimumWidth(200)
        self.disc_list.currentRowChanged.connect(self._on_select)
        ll.addWidget(self.disc_list, stretch=1)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)

        self._lbl_empty = QLabel("← Оберіть або додайте дисципліну")
        self._lbl_empty.setAlignment(Qt.AlignCenter)
        self._lbl_empty.setStyleSheet(
            "color:#aaa; font-style:italic; font-size:14px;")
        rl.addWidget(self._lbl_empty)

        self._scroll = self._build_form()
        self._scroll.setVisible(False)
        rl.addWidget(self._scroll, stretch=1)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([240, 860])
        splitter.setStretchFactor(1, 1)

        root.addWidget(splitter, stretch=1)
        self._refresh_list()

    def _build_form(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        w   = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(10)

        bf = QFont(); bf.setBold(True)

        sec1 = QLabel("Основні поля дисципліни")
        sec1.setFont(bf)
        lay.addWidget(sec1)

        self._lines = {}
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.setVerticalSpacing(8)
        for key, label, ph in DISC_FIELDS:
            le = QLineEdit()
            le.setPlaceholderText(ph)
            if key == "specialty":
                le.setFixedWidth(180)
            le.textChanged.connect(self._mark_dirty)
            form.addRow(label, le)
            self._lines[key] = le
        lay.addLayout(form)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        lay.addWidget(sep)

        sec2 = QLabel("Публікації та кваліфікація")
        sec2.setFont(bf)
        lay.addWidget(sec2)

        self._texts    = {}
        self._use_db   = {}

        for key, label_text in AUTO_FIELDS:
            hdr = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setFont(bf)

            btn_clr = QPushButton("Очистити поле")
            btn_clr.setToolTip("Зробити це поле порожнім")
            btn_clr.setStyleSheet(
                "QPushButton{font-size:10px; padding:2px 6px;}"
            )
            btn_clr.clicked.connect(lambda chk=False, k=key: self._clear_field(k))

            hdr.addWidget(lbl)
            hdr.addStretch()
            hdr.addWidget(btn_clr)

            te = QTextEdit()
            te.setFixedHeight(80)
            te.setStyleSheet(STYLE_EMPTY)
            te.document().contentsChanged.connect(
                lambda k=key: self._on_text_changed(k)
            )

            lay.addLayout(hdr)
            lay.addWidget(te)
            self._texts[key]  = te
            self._use_db[key] = False

            fs = QFrame()
            fs.setFrameShape(QFrame.HLine)
            fs.setFrameShadow(QFrame.Sunken)
            lay.addWidget(fs)

        lay.addStretch()
        scroll.setWidget(w)
        return scroll

    # ─────────────────────────────────────────────────────────────────────────
    # Відстеження змін
    # ─────────────────────────────────────────────────────────────────────────

    def _mark_dirty(self):
        if not self._loading:
            self._dirty = True

    # ─────────────────────────────────────────────────────────────────────────
    # Сигнали полів форми
    # ─────────────────────────────────────────────────────────────────────────

    def _on_text_changed(self, key: str):
        if self._loading:
            return
        te = self._texts[key]
        self._use_db[key] = False
        self._dirty = True
        if 0 <= self._cur < len(self._discs):
            existing_raw = self._discs[self._cur].get(f"_raw_{key}", "")
            if is_json_ids(existing_raw):
                disc = dict(self._discs[self._cur])
                new_text = te.toPlainText().strip()
                disc[f"_raw_{key}"] = new_text
                disc[key]           = new_text
                self._discs[self._cur] = disc
        te.setStyleSheet(STYLE_LOCAL if te.toPlainText().strip() else STYLE_EMPTY)

    def _clear_field(self, key: str):
        self._loading = True
        self._texts[key].setPlainText("")
        self._texts[key].setStyleSheet(STYLE_EMPTY)
        self._use_db[key] = False
        self._loading = False
        self._dirty = True
        if 0 <= self._cur < len(self._discs):
            disc = dict(self._discs[self._cur])
            disc[key]           = ""
            disc[f"_raw_{key}"] = ""
            self._discs[self._cur] = disc

    # ─────────────────────────────────────────────────────────────────────────
    # Список дисциплін
    # ─────────────────────────────────────────────────────────────────────────

    def _refresh_list(self):
        self.disc_list.blockSignals(True)
        self.disc_list.clear()
        for d in self._discs:
            name = (d.get("course_name") or "").strip() or "— без назви —"
            spec = (d.get("specialty")   or "").strip()
            self.disc_list.addItem(name + (f"  [{spec}]" if spec else ""))
        self.disc_list.blockSignals(False)

    def _on_select(self, idx: int):
        self._flush()
        self._cur = idx
        if 0 <= idx < len(self._discs):
            self._load(self._discs[idx])
            self._lbl_empty.setVisible(False)
            self._scroll.setVisible(True)
        else:
            self._scroll.setVisible(False)
            self._lbl_empty.setVisible(True)

    def _load(self, disc: dict):
        self._loading = True

        for key, _, _ in DISC_FIELDS:
            self._lines[key].setText(disc.get(key, "") or "")

        for key, _ in AUTO_FIELDS:
            te      = self._texts[key]
            raw_val = disc.get(f"_raw_{key}", disc.get(key, "")) or ""
            display = (disc.get(key) or "").strip()

            if raw_val == DB_SENTINEL:
                te.setPlainText(display)
                te.setStyleSheet(STYLE_DB)
                self._use_db[key] = True
            elif is_json_ids(raw_val):
                te.setPlainText(display)
                te.setStyleSheet(STYLE_LOCAL)
                self._use_db[key] = False
            elif raw_val:
                te.setPlainText(raw_val)
                te.setStyleSheet(STYLE_LOCAL)
                self._use_db[key] = False
            else:
                te.setPlainText("")
                te.setStyleSheet(STYLE_EMPTY)
                self._use_db[key] = False

        self._loading = False

    def _flush(self):
        if not (0 <= self._cur < len(self._discs)):
            return

        disc = dict(self._discs[self._cur])

        for key, _, _ in DISC_FIELDS:
            disc[key] = self._lines[key].text().strip()

        for key, _ in AUTO_FIELDS:
            if self._use_db[key]:
                disc[key]           = DB_SENTINEL
                disc[f"_raw_{key}"] = DB_SENTINEL
            else:
                form_text    = self._texts[key].toPlainText().strip()
                existing_raw = disc.get(f"_raw_{key}", "")
                display_text = (disc.get(key) or "").strip()

                if is_json_ids(existing_raw):
                    if form_text != display_text:
                        disc[key]           = form_text
                        disc[f"_raw_{key}"] = form_text
                else:
                    disc[key]           = form_text
                    disc[f"_raw_{key}"] = form_text

        self._discs[self._cur] = disc

    # ─────────────────────────────────────────────────────────────────────────
    # CRUD дисциплін
    # ─────────────────────────────────────────────────────────────────────────

    def _add(self):
        self._flush()
        new_disc = {k: "" for k in ALL_KEYS}
        for k, _ in AUTO_FIELDS:
            new_disc[f"_raw_{k}"] = ""
        self._discs.append(new_disc)
        new_idx = len(self._discs) - 1
        self._refresh_list()
        self._cur = new_idx
        self.disc_list.blockSignals(True)
        self.disc_list.setCurrentRow(new_idx)
        self.disc_list.blockSignals(False)
        self._load(new_disc)
        self._lbl_empty.setVisible(False)
        self._scroll.setVisible(True)
        self._dirty = True

    def _delete(self):
        idx = self.disc_list.currentRow()
        if idx < 0 or idx >= len(self._discs):
            QMessageBox.information(self, "Увага", "Оберіть дисципліну.")
            return
        self._flush()
        name = (self._discs[idx].get("course_name") or "цю дисципліну")[:60]
        if QMessageBox.question(
            self, "Підтвердження", f"Видалити «{name}»?",
            QMessageBox.Yes | QMessageBox.No
        ) != QMessageBox.Yes:
            return
        self._discs.pop(idx)
        self._cur = -1
        self._dirty = True
        self._refresh_list()
        if self._discs:
            self.disc_list.setCurrentRow(min(idx, len(self._discs) - 1))
        else:
            self._scroll.setVisible(False)
            self._lbl_empty.setVisible(True)

    # ─────────────────────────────────────────────────────────────────────────
    # Заповнення з БД
    # ─────────────────────────────────────────────────────────────────────────

    def _get_db_data(self):
        if self._db_pubs is None:
            self._db_pubs   = get_publications_by_teacher(
                self._teacher_id, self._last_5y)
            self._db_trains = get_trainings_by_teacher(
                self._teacher_id, self._last_5y)

    def _pick_target_disc(self, btn: QPushButton) -> int | None:
        if not self._discs:
            QMessageBox.information(self, "Увага", "Спочатку додайте дисципліну.")
            return None

        if len(self._discs) == 1:
            return 0

        menu = QMenu(self)
        actions = []
        for i, d in enumerate(self._discs):
            name  = (d.get("course_name") or "").strip() or "— без назви —"
            spec  = (d.get("specialty")   or "").strip()
            label = f"{i + 1}. {name}" + (f"  [{spec}]" if spec else "")
            act   = menu.addAction(label)
            if i == self._cur:
                act.setCheckable(True)
                act.setChecked(True)
            actions.append((act, i))

        chosen = menu.exec(btn.mapToGlobal(btn.rect().bottomLeft()))
        if chosen is None:
            return None
        for act, idx in actions:
            if chosen == act:
                return idx
        return None

    def _fill_all_from_db(self):
        target = self._pick_target_disc(self.btn_fill_all)
        if target is None:
            return
        self._open_select_dialog(target)

    def _open_select_dialog(self, disc_idx: int):
        self._flush()
        self._get_db_data()

        disc      = self._discs[disc_idx]
        disc_name = (disc.get("course_name") or "").strip() or "— без назви —"

        cur_vals = {}
        for key, _ in AUTO_FIELDS:
            val = disc.get(key, "")
            cur_vals[key] = val if (val and val != DB_SENTINEL) else ""

        dlg = LicenseSelectDialog(
            parent=self,
            publications=self._db_pubs,
            trainings=self._db_trains,
            current_vals=cur_vals,
            disc_name=disc_name,
        )
        dlg.selected.connect(
            lambda res, di=disc_idx: self._apply_selection(di, res))
        dlg.exec()

    def _auto_search(self):
        target = self._pick_target_disc(self.btn_auto)
        if target is None:
            return
        self._open_auto_dialog(target)

    def _open_auto_dialog(self, disc_idx: int):
        self._flush()
        self._get_db_data()

        disc      = self._discs[disc_idx]
        disc_name = (disc.get("course_name") or "").strip()

        if not disc_name:
            QMessageBox.warning(
                self, "Увага",
                "Введіть назву дисципліни перед авто-пошуком.\n"
                "Назва потрібна для визначення ключових слів."
            )
            return

        match_result = auto_match(disc_name, self._db_pubs, self._db_trains)

        total_found = sum(
            len(match_result.get(k, []))
            for k in ["articles", "conferences", "textbooks", "methodical", "trainings"]
        )

        if total_found == 0:
            if QMessageBox.question(
                self, "Нічого не знайдено",
                f"За ключовими словами з «{disc_name}» нічого не знайдено.\n\n"
                "Відкрити список вручну для самостійного вибору?",
                QMessageBox.Yes | QMessageBox.No
            ) == QMessageBox.Yes:
                self._open_select_dialog(disc_idx)
            return

        cur_vals = {}
        for key, _ in AUTO_FIELDS:
            val = disc.get(key, "")
            cur_vals[key] = val if (val and val != DB_SENTINEL) else ""

        dlg = LicenseSelectDialog(
            parent=self,
            publications=self._db_pubs,
            trainings=self._db_trains,
            current_vals=cur_vals,
            disc_name=disc_name,
            auto_match_result=match_result,
        )
        dlg.selected.connect(
            lambda res, di=disc_idx: self._apply_selection(di, res))
        dlg.exec()

    def _apply_selection(self, disc_idx: int, result: dict):
        disc = dict(self._discs[disc_idx])
        for key, val in result.items():
            if isinstance(val, dict):
                ids    = val.get("selected_ids", [])
                labels = val.get("labels", "")
                disc[f"_raw_{key}"] = encode_ids(ids) if ids else ""
                disc[key]           = labels
            else:
                disc[f"_raw_{key}"] = ""
                disc[key]           = ""
        self._discs[disc_idx] = disc
        self._dirty = True
        if disc_idx == self._cur:
            self._load(disc)

    def _clear_all_from_db(self):
        if not self._discs:
            QMessageBox.information(self, "Увага", "Спочатку додайте дисципліну.")
            return

        if len(self._discs) == 1:
            self._clear_disc_fields(0)
            return

        menu = QMenu(self)
        act_all = menu.addAction("Всі дисципліни")
        menu.addSeparator()
        actions = []
        for i, d in enumerate(self._discs):
            name  = (d.get("course_name") or "").strip() or "— без назви —"
            spec  = (d.get("specialty")   or "").strip()
            label = f"{i + 1}. {name}" + (f"  [{spec}]" if spec else "")
            actions.append((menu.addAction(label), i))

        chosen = menu.exec(
            self.btn_clear_all.mapToGlobal(self.btn_clear_all.rect().bottomLeft()))

        if chosen is None:
            return
        if chosen == act_all:
            for i in range(len(self._discs)):
                self._clear_disc_fields(i)
        else:
            for act, idx in actions:
                if chosen == act:
                    self._clear_disc_fields(idx)
                    break

    def _clear_disc_fields(self, disc_idx: int):
        if disc_idx != self._cur:
            self._flush()

        disc = dict(self._discs[disc_idx])
        for key, _ in AUTO_FIELDS:
            disc[key]           = ""
            disc[f"_raw_{key}"] = ""
        self._discs[disc_idx] = disc
        self._dirty = True

        if disc_idx == self._cur:
            self._loading = True
            for key, _ in AUTO_FIELDS:
                self._texts[key].setPlainText("")
                self._texts[key].setStyleSheet(STYLE_EMPTY)
                self._use_db[key] = False
            self._loading = False

    # ─────────────────────────────────────────────────────────────────────────
    # Закриття з підтвердженням
    # ─────────────────────────────────────────────────────────────────────────

    def _on_cancel(self):
        self.close()

    def closeEvent(self, event):
        if self._dirty:
            reply = QMessageBox.question(
                self, "Незбережені зміни",
                "Є незбережені зміни. Вийти без збереження?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                event.ignore()
                return
        event.accept()

    # ─────────────────────────────────────────────────────────────────────────
    # Збереження
    # ─────────────────────────────────────────────────────────────────────────

    def _save(self):
        self._flush()
        self._dirty = False
        discs_to_save = []
        for disc in self._discs:
            d = dict(disc)
            for key, _ in AUTO_FIELDS:
                raw = d.get(f"_raw_{key}", d.get(key, ""))
                d[key] = raw
            discs_to_save.append(d)
        self.saved.emit(discs_to_save)
        self.accept()