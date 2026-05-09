"""
Діалог аналізу відповідності НПП ліцензійним умовам.
"""
from datetime import date
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QPushButton,
    QTextEdit, QFrame, QScrollArea, QWidget,
    QMessageBox, QLineEdit, QListWidget, QListWidgetItem,
    QDialogButtonBox, QSplitter
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from services.analysis_service import build_analysis
from services.training_service import get_all_teachers_for_select


class TeacherSearchDialog(QDialog):
    """Діалог вибору викладача для аналізу."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Вибір викладача для аналізу")
        self.setMinimumWidth(400)
        self.setMinimumHeight(440)

        self._selected_id   = None
        self._selected_name = None

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        lbl = QLabel("Оберіть викладача:")
        bf = QFont()
        bf.setBold(True)
        lbl.setFont(bf)
        layout.addWidget(lbl)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Пошук за прізвищем...")
        self.search.setFixedHeight(32)
        self.search.textChanged.connect(self._filter)
        layout.addWidget(self.search)

        self.list = QListWidget()
        self.list.doubleClicked.connect(self._accept)
        layout.addWidget(self.list)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("Аналізувати")
        btns.button(QDialogButtonBox.Cancel).setText("Скасувати")
        btns.accepted.connect(self._accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self._teachers = get_all_teachers_for_select()
        self._fill_list()

    def _fill_list(self, filter_text: str = ""):
        self.list.clear()
        for t_id, t_name in self._teachers:
            if filter_text and filter_text.lower() not in t_name.lower():
                continue
            item = QListWidgetItem(t_name)
            item.setData(Qt.UserRole, t_id)
            self.list.addItem(item)

    def _filter(self, text: str):
        self._fill_list(filter_text=text)

    def _accept(self):
        item = self.list.currentItem()
        if not item:
            QMessageBox.warning(self, "Увага", "Оберіть викладача зі списку.")
            return
        self._selected_id   = item.data(Qt.UserRole)
        self._selected_name = item.text()
        self.accept()

    def selected(self):
        return self._selected_id, self._selected_name


class AnalysisDialog(QDialog):
    """Діалог з результатами аналізу НПП."""

    def __init__(self, parent=None, teacher_id: str = None):
        super().__init__(parent)
        self.setWindowTitle("Аналіз відповідності НПП - ліцензійні умови")
        self.setMinimumWidth(700)
        self.setMinimumHeight(620)

        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(20, 20, 20, 20)
        self._content_layout.setSpacing(12)

        scroll.setWidget(self._content)
        layout.addWidget(scroll)

        # Кнопка закрити
        close_btn = QPushButton("Закрити")
        close_btn.setFixedHeight(32)
        close_btn.clicked.connect(self.accept)
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(20, 8, 20, 12)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        if teacher_id:
            self._run_analysis(teacher_id)

    def _separator(self):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #c8d0d8;")
        return line

    def _section_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        f = QFont()
        f.setBold(True)
        f.setPointSize(10)
        lbl.setFont(f)
        lbl.setStyleSheet("color: #2c3e50; padding-top: 6px;")
        return lbl

    def _info_label(self, text: str, color: str = "#2c3e50") -> QLabel:
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color: {color}; font-size: 12px;")
        return lbl

    def _run_analysis(self, teacher_id: str):
        data = build_analysis(teacher_id)
        if not data:
            self._content_layout.addWidget(
                self._info_label("Дані про викладача не знайдено.")
            )
            return

        teacher = data["teacher"]
        tr      = data["trainings"]
        pubs    = data["publications"]

        # ── Заголовок ─────────────────────────────────────────────────────────
        full_name = (
            f"{teacher['last_name']} {teacher['first_name']} {teacher['middle_name']}"
        ).strip()

        name_lbl = QLabel(full_name)
        nf = QFont()
        nf.setBold(True)
        nf.setPointSize(13)
        name_lbl.setFont(nf)
        name_lbl.setStyleSheet("color: #1a252f;")
        self._content_layout.addWidget(name_lbl)

        meta_parts = []
        if teacher["degree"]:
            meta_parts.append(teacher["degree"])
        if teacher["title"]:
            meta_parts.append(teacher["title"])
        if teacher["department"]:
            meta_parts.append(teacher["department"])

        if meta_parts:
            self._content_layout.addWidget(
                self._info_label(" | ".join(meta_parts), color="#5d6d7e")
            )

        self._content_layout.addWidget(
            self._info_label(
                f"Аналіз за {data['cutoff_year']}–{data['analysis_year']} рр.",
                color="#7f8c8d"
            )
        )

        self._content_layout.addWidget(self._separator())

        # ── Підвищення кваліфікації ────────────────────────────────────────────
        self._content_layout.addWidget(
            self._section_label("ПІДВИЩЕННЯ КВАЛІФІКАЦІЇ (останні 5 років)")
        )
        self._content_layout.addWidget(
            self._info_label(
                f"Записів: {tr['count']}   |   "
                f"Годин: {tr['hours']:.1f}   |   "
                f"Кредитів ЄКТС: {tr['ects']:.2f}"
            )
        )
        norm_text = (
            f"Норма ({tr['min_ects']:.0f} ЄКТС): "
            + ("виконана" if tr["norm_met"] else "НЕ виконана")
        )
        norm_color = "#1a7a1a" if tr["norm_met"] else "#c0392b"
        self._content_layout.addWidget(self._info_label(norm_text, color=norm_color))

        self._content_layout.addWidget(self._separator())

        # ── Публікації ────────────────────────────────────────────────────────
        self._content_layout.addWidget(
            self._section_label("ПУБЛІКАЦІЇ (останні 5 років, активні)")
        )
        self._content_layout.addWidget(
            self._info_label(
                f"Всього: {pubs['total']}   |   "
                f"Статті: {pubs['articles']}   |   "
                f"Тези: {pubs['conferences']}   |   "
                f"Монографії: {pubs['monographs']}   |   "
                f"Підручники/посібники: {pubs['textbooks']}   |   "
                f"Патенти: {pubs['patents']}"
            )
        )
        pub_norm_text = (
            f"Вимога (мін. {pubs['min_pubs']} статей/тез у фахових виданнях): "
            + ("виконана" if pubs["norm_met"] else "НЕ виконана")
            + f"  ({pubs['scored_pubs']} з {pubs['min_pubs']})"
        )
        pub_color = "#1a7a1a" if pubs["norm_met"] else "#c0392b"
        self._content_layout.addWidget(self._info_label(pub_norm_text, color=pub_color))

        self._content_layout.addWidget(self._separator())

        # ── Досягнення ────────────────────────────────────────────────
        self._content_layout.addWidget(
            self._section_label(
                f"ДОСЯГНЕННЯ У ПРОФЕСІЙНІЙ ДІЯЛЬНОСТІ"
            )
        )

        if data["exempt_from_requirements"]:
            self._content_layout.addWidget(
                self._info_label(
                    f"Стаж НПП роботи: {data['exp_years']:.1f} р. - вимога щодо "
                    f"4 досягнень не застосовується (стаж менше 3 років).",
                    color="#7f8c8d"
                )
            )
        else:
            for i, ach in enumerate(data["achievements"], start=1):
                status = "Виконано" if ach["met"] else "Не виконано"
                color  = "#1a7a1a" if ach["met"] else "#c0392b"
                text   = f"[{i}] {ach['title']}: {status} - {ach['detail']}"
                self._content_layout.addWidget(self._info_label(text, color=color))

            total_lbl = QLabel(
                f"\nВсього досягнень: {data['met_count']} з {data['total_need']} необхідних"
            )
            tf = QFont()
            tf.setBold(True)
            total_lbl.setFont(tf)
            color = "#1a7a1a" if data["all_met"] else "#c0392b"
            total_lbl.setStyleSheet(f"color: {color}; font-size: 12px;")
            self._content_layout.addWidget(total_lbl)

        self._content_layout.addWidget(self._separator())

        # ── Заключення ────────────────────────────────────────────────────────
        self._content_layout.addWidget(self._section_label("ЗАКЛЮЧЕННЯ"))

        conclusion_box = QTextEdit()
        conclusion_box.setReadOnly(True)
        conclusion_box.setFrameShape(QFrame.NoFrame)
        conclusion_box.setStyleSheet(
            "background: #f4f6f8; border-radius: 4px; "
            "padding: 10px; font-size: 12px; color: #2c3e50;"
        )
        conclusion_box.setMinimumHeight(140)
        conclusion_box.setMaximumHeight(240)

        text = "\n\n".join(data["conclusions"])
        conclusion_box.setPlainText(text)
        self._content_layout.addWidget(conclusion_box)

        # Посилання на НПА
        npa_lbl = QLabel(
        )
        npa_lbl.setWordWrap(True)
        npa_lbl.setStyleSheet("color: #aab7b8; font-size: 10px; padding-top: 8px;")
        self._content_layout.addWidget(npa_lbl)

        self._content_layout.addStretch()
