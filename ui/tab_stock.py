"""ui/tab_stock.py — Остатки по всем товарам"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QLineEdit, QPushButton, QHeaderView, QFrame, QComboBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont
from ui.styles import *


class StockTab(QWidget):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.main_win = parent
        self._flt = "all"
        self._build()

    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # Toolbar
        tb = QFrame()
        tb.setFixedHeight(50)
        tb.setStyleSheet(f"background:white;border-bottom:1px solid {BORDER};")
        hl = QHBoxLayout(tb)
        hl.setContentsMargins(16, 0, 16, 0)
        hl.setSpacing(10)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск…")
        self.search.setFixedWidth(200)
        self.search.textChanged.connect(lambda: QTimer.singleShot(300, self.refresh))
        hl.addWidget(self.search)

        for lbl, flt in [("Все","all"),("🟢 OK","ok"),("🟡 Мало","warn"),("🔴 Нет","none")]:
            btn = QPushButton(lbl)
            btn.setCheckable(True)
            btn.setChecked(flt == "all")
            btn.setProperty("flt", flt)
            btn.clicked.connect(lambda _, b=btn, f=flt: self._set_flt(f, b))
            btn.setFixedHeight(30)
            hl.addWidget(btn)

        self.count_lbl = QLabel("")
        self.count_lbl.setStyleSheet(f"font-size:11px;color:{MUTED};")
        hl.addStretch()
        hl.addWidget(self.count_lbl)

        btn_exp = QPushButton("💾 Экспорт xlsx")
        btn_exp.clicked.connect(self.main_win.do_export)
        hl.addWidget(btn_exp)
        v.addWidget(tb)

        # Table
        cols = ["Артикул","Наименование","Кат.","Ед.",
                "Приход","→WB","→OZON","→др.","Остаток ТВ-2","Мин.","Статус",
                "Штрихкод WB","Штрихкод OZON"]
        self.table = QTableWidget(0, len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setSortingEnabled(True)
        v.addWidget(self.table)

        self.refresh()

    def _set_flt(self, flt, btn):
        self._flt = flt
        for b in self.findChildren(QPushButton):
            if b.property("flt"):
                b.setChecked(b.property("flt") == flt)
        self.refresh()

    def refresh(self):
        q = self.search.text().lower()
        rows = self.db.get_all_stock()

        if self._flt == "ok":
            rows = [r for r in rows if r["stock"] > 0 and (r["min_stock"] == 0 or r["stock"] > r["min_stock"])]
        elif self._flt == "warn":
            rows = [r for r in rows if r["stock"] > 0 and r["min_stock"] > 0 and r["stock"] <= r["min_stock"]]
        elif self._flt == "none":
            rows = [r for r in rows if r["stock"] <= 0]

        if q:
            rows = [r for r in rows if q in r["art"].lower() or q in r["name"].lower() or q in r["cat"].lower()]

        self.count_lbl.setText(f"{len(rows)} позиций")
        self.table.setRowCount(len(rows))
        self.table.setSortingEnabled(False)

        for i, r in enumerate(rows):
            s = r["stock"]
            if s <= 0: status, sc, bg = "🔴 НЕТ", DANGER, QColor(DANGER_BG)
            elif r["min_stock"] > 0 and s <= r["min_stock"]: status, sc, bg = "🟡 МАЛО", WARN, QColor(WARN_BG)
            else: status, sc, bg = "🟢 OK", OK, QColor(OK_BG)

            vals = [r["art"], r["name"], r["cat"], r["unit"],
                    r["inc"], r["wb"], r["ozon"], r["other"], s,
                    r["min_stock"], status, r["bc_wb"], r["bc_ozon"]]
            for j, v in enumerate(vals):
                item = QTableWidgetItem(str(v) if not isinstance(v, str) else v)
                if j == 8:  # stock col
                    item.setForeground(QColor(sc))
                    f = QFont(); f.setBold(True); f.setFamily("Courier New"); f.setPointSize(11)
                    item.setFont(f)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if j == 10: # status
                    item.setBackground(bg)
                if j in (5,11): item.setForeground(QColor(WB))
                if j in (6,12): item.setForeground(QColor(OZ))
                if j in (4,5,6,7,8,9): item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(i, j, item)

        self.table.setSortingEnabled(True)
        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(1, 260)
