"""ui/tab_history.py"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QLineEdit, QPushButton, QHeaderView, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
from ui.styles import *


class HistoryTab(QWidget):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self._flt_type = "all"
        self._flt_mp   = ""
        self._build()

    def _build(self):
        v = QVBoxLayout(self); v.setContentsMargins(0,0,0,0); v.setSpacing(0)

        tb = QFrame(); tb.setFixedHeight(50)
        tb.setStyleSheet(f"background:white;border-bottom:1px solid {BORDER};")
        hl = QHBoxLayout(tb); hl.setContentsMargins(16,0,16,0); hl.setSpacing(8)

        self.search = QLineEdit(); self.search.setPlaceholderText("Поиск…")
        self.search.setFixedWidth(180)
        self.search.textChanged.connect(lambda: QTimer.singleShot(300, self.refresh))
        hl.addWidget(self.search)

        for lbl, t in [("Все","all"),("➕ Приход","arrive"),("🔄 Перемещения","move")]:
            btn = QPushButton(lbl); btn.setCheckable(True); btn.setChecked(t=="all")
            btn.setProperty("ft", t); btn.setFixedHeight(30)
            btn.clicked.connect(lambda _, b=btn, ft=t: self._set_type(ft, b))
            hl.addWidget(btn)

        for lbl, mp in [("WB","WB"),("OZON","OZON")]:
            btn = QPushButton(lbl); btn.setCheckable(True)
            btn.setProperty("mp", mp); btn.setFixedHeight(30)
            btn.setStyleSheet(f"color:{'#7b1fa2' if mp=='WB' else '#0d47a1'};font-weight:700;")
            btn.clicked.connect(lambda _, b=btn, m=mp: self._set_mp(m, b))
            hl.addWidget(btn)

        self.count_lbl = QLabel(""); self.count_lbl.setStyleSheet(f"font-size:11px;color:{MUTED};")
        hl.addStretch(); hl.addWidget(self.count_lbl)

        btn_print = QPushButton("🖨️ Печать документа")
        btn_print.setFixedHeight(30)
        btn_print.clicked.connect(self._print_move_doc)
        hl.addWidget(btn_print)
        v.addWidget(tb)

        # Arrivals table
        self.arr_table = self._make_table(
            ["Дата","Артикул","Наименование","Склад","Кол-во","Поставщик","Примечание",""])
        self.arr_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        # Moves table
        self.mov_table = self._make_table(
            ["Дата","Артикул","Наименование","Откуда","Куда","Кол-во","Ш/К МП","Тип МП","Примечание",""])
        self.mov_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        v.addWidget(self.arr_table)
        v.addWidget(self.mov_table)
        self.refresh()

    def _make_table(self, cols):
        t = QTableWidget(0, len(cols))
        t.setHorizontalHeaderLabels(cols)
        t.setAlternatingRowColors(True)
        t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.verticalHeader().setVisible(False)
        t.verticalHeader().setDefaultSectionSize(44)
        t.verticalHeader().setMinimumSectionSize(44)
        return t

    def _set_type(self, ft, btn):
        self._flt_type = ft
        for b in self.findChildren(QPushButton):
            if b.property("ft"): b.setChecked(b.property("ft") == ft)
        self.refresh()

    def _set_mp(self, mp, btn):
        self._flt_mp = "" if (self._flt_mp == mp) else mp
        btn.setChecked(self._flt_mp == mp)
        self.refresh()

    def refresh(self):
        q = self.search.text()
        show_arr = self._flt_type in ("all","arrive") and not self._flt_mp
        show_mov = self._flt_type in ("all","move")

        self.arr_table.setVisible(show_arr)
        self.mov_table.setVisible(show_mov)

        total = 0

        if show_arr:
            rows = self.db.get_arrivals(q)
            self.arr_table.setRowCount(len(rows))
            for i, r in enumerate(rows):
                vals = [r["dt"], r["art"], r["pname"] or r["art"], r["wh_name"],
                        r["qty"], r["supplier"], r["note"], ""]
                for j, v in enumerate(vals[:-1]):
                    item = QTableWidgetItem(str(v) if v else "")
                    if j == 4:
                        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                        item.setForeground(QColor(OK))
                    self.arr_table.setItem(i, j, item)
                btn_del = QPushButton("🗑 Удалить")
                btn_del.setObjectName("danger")
                btn_del.setFixedSize(90, 32)
                btn_del.setStyleSheet(f"font-size:11px;padding:0;color:{DANGER};border:1px solid {DANGER};background:white;border-radius:5px;")
                btn_del.clicked.connect(lambda _, rid=r["id"]: self._del_arrival(rid))
                w = QWidget()
                w.setFixedHeight(44)
                hl = QHBoxLayout(w); hl.setContentsMargins(4,4,4,4)
                hl.addWidget(btn_del)
                self.arr_table.setCellWidget(i, 7, w)
            self.arr_table.resizeColumnsToContents()
            total += len(rows)

        if show_mov:
            rows = self.db.get_moves(q, self._flt_mp)
            self.mov_table.setRowCount(len(rows))
            for i, r in enumerate(rows):
                vals = [r["dt"], r["art"], r["pname"] or r["art"],
                        r["from_wh"], r["to_wh"], r["qty"],
                        r["barcode"], r["mp_type"], r["note"], ""]
                for j, v in enumerate(vals[:-1]):
                    item = QTableWidgetItem(str(v) if v else "")
                    if j == 5:
                        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                        item.setForeground(QColor(WARN))
                    if j == 6:
                        mp = r["mp_type"]
                        item.setForeground(QColor("#6a1b9a" if mp=="WB" else "#1565c0" if mp=="OZON" else MUTED))
                    if j == 7:
                        mp = r["mp_type"]
                        item.setForeground(QColor("#6a1b9a" if mp=="WB" else "#1565c0" if mp=="OZON" else MUTED))
                    self.mov_table.setItem(i, j, item)
                btn_del = QPushButton("🗑 Удалить")
                btn_del.setObjectName("danger")
                btn_del.setFixedSize(90, 32)
                btn_del.setStyleSheet(f"font-size:11px;padding:0;color:{DANGER};border:1px solid {DANGER};background:white;border-radius:5px;")
                btn_del.clicked.connect(lambda _, rid=r["id"]: self._del_move(rid))
                w = QWidget(); w.setFixedHeight(44)
                hl = QHBoxLayout(w); hl.setContentsMargins(4,4,4,4)
                hl.addWidget(btn_del)
                self.mov_table.setCellWidget(i, 9, w)
            self.mov_table.resizeColumnsToContents()
            total += len(rows)

        self.count_lbl.setText(f"{total} записей")

    def _del_arrival(self, rid):
        r = QMessageBox.question(self, "Удалить", "Удалить запись прихода?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            self.db.delete_arrival(rid)
            self.refresh()

    def _del_move(self, mid):
        r = QMessageBox.question(self, "Удалить", "Удалить запись перемещения?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            self.db.delete_move(mid)
            self.refresh()

    def _print_move_doc(self):
        """Печать документа перемещения — HTML → браузер → Ctrl+P"""
        rows = self.db.get_moves(self._flt_mp, limit=9999) if self._flt_mp else self.db.get_moves(limit=9999)
        if not rows:
            QMessageBox.information(self, "Нет данных", "Нет перемещений для печати")
            return

        from datetime import date
        import tempfile, os, webbrowser

        lines = ""
        for r in rows:
            mp = r["mp_type"] or ""
            color = "#6a1b9a" if mp=="WB" else ("#1565c0" if mp=="OZON" else "#333")
            badge = f'<span style="background:{color};color:white;padding:1px 6px;border-radius:3px;font-size:10px;font-weight:700;">{mp}</span>' if mp else ""
            lines += f"""
            <tr>
                <td>{r["dt"]}</td>
                <td style="font-family:monospace;font-weight:700;">{r["art"]}</td>
                <td>{r["pname"] or r["art"]}</td>
                <td>{r["from_wh"]}</td>
                <td>{r["to_wh"]}</td>
                <td style="text-align:right;font-weight:700;">{r["qty"]}</td>
                <td style="font-family:monospace;font-size:11px;">{r["barcode"] or ""}</td>
                <td>{badge}</td>
            </tr>"""

        total_qty = sum(r["qty"] for r in rows)
        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>Перемещения — SharmGlow</title>
<style>
  body {{ font-family: Arial, sans-serif; font-size: 12px; margin: 20px; color: #1a1208; }}
  h1 {{ font-size: 18px; color: #1a1208; border-bottom: 2px solid #b8860b; padding-bottom: 8px; }}
  .meta {{ color: #888; font-size: 11px; margin-bottom: 16px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ background: #1a1208; color: #d4a017; padding: 7px 10px; text-align: left; font-size: 11px; letter-spacing: .05em; }}
  td {{ padding: 5px 10px; border-bottom: 1px solid #f0ebe0; }}
  tr:nth-child(even) td {{ background: #faf7f0; }}
  .total {{ margin-top: 12px; font-weight: 700; text-align: right; font-size: 13px; }}
  @media print {{ body {{ margin: 5mm; }} }}
</style>
</head><body>
<h1>SharmGlow — Документ перемещений</h1>
<div class="meta">Дата печати: {date.today().strftime("%d.%m.%Y")} &nbsp;|&nbsp; Записей: {len(rows)}</div>
<table>
  <thead><tr>
    <th>Дата</th><th>Артикул</th><th>Наименование</th>
    <th>Откуда</th><th>Куда</th><th>Кол-во</th><th>Штрихкод МП</th><th>МП</th>
  </tr></thead>
  <tbody>{lines}</tbody>
</table>
<div class="total">Итого единиц: {total_qty}</div>
</body></html>"""

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html",
                                          mode="w", encoding="utf-8")
        tmp.write(html); tmp.close()
        import sys
        if sys.platform == "win32":
            os.startfile(tmp.name)
        else:
            webbrowser.open(f"file://{tmp.name}")
        QMessageBox.information(self, "Документ открыт",
            "Документ открыт в браузере.\nДля печати нажмите Ctrl+P в браузере.")
