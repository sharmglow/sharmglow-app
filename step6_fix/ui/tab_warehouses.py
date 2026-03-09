"""ui/tab_warehouses.py"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QPushButton, QHeaderView, QFrame, QDialog, QFormLayout,
    QLineEdit, QComboBox, QMessageBox, QDialogButtonBox
)
from PyQt6.QtCore import Qt
from ui.styles import *


class WarehousesTab(QWidget):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.main_win = parent
        self.ctx = getattr(parent, "ctx", None)
        self.warehouses_service = getattr(self.ctx, "warehouses_service", None) if self.ctx else None
        self._build()

    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        tb = QFrame()
        tb.setFixedHeight(50)
        tb.setStyleSheet(f"background:white;border-bottom:1px solid {BORDER};")
        hl = QHBoxLayout(tb)
        hl.setContentsMargins(16, 0, 16, 0)
        lbl = QLabel("Справочник складов")
        lbl.setStyleSheet(f"font-size:13px;font-weight:600;color:{INK};")
        hl.addWidget(lbl)
        hl.addStretch()
        btn_add = QPushButton("+ Добавить склад")
        btn_add.setObjectName("primary")
        btn_add.clicked.connect(self.add_wh)
        hl.addWidget(btn_add)
        v.addWidget(tb)

        hint = QLabel(
            "💡  Если название склада содержит «WB» или «Wildberries» — при перемещении подставится штрихкод WB.  "
            "Если «OZON» или «Озон» — штрихкод OZON."
        )
        hint.setStyleSheet(f"background:{PAPER};padding:10px 16px;font-size:12px;color:{MUTED};border-bottom:1px solid {BORDER};")
        hint.setWordWrap(True)
        v.addWidget(hint)

        cols = ["Код", "Название", "Тип", "Примечание", "Действия"]
        self.table = QTableWidget(0, len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        v.addWidget(self.table)
        self.refresh()

    def _get_warehouses(self):
        if self.warehouses_service:
            return self.warehouses_service.get_all()
        return self.db.get_warehouses()

    def _get_warehouse_by_id(self, wid):
        if self.warehouses_service:
            return self.warehouses_service.get_by_id(wid)
        return self.db.conn.execute("SELECT * FROM warehouses WHERE id=?", (wid,)).fetchone()

    def refresh(self):
        rows = self._get_warehouses()
        self.table.setRowCount(len(rows))
        for i, w in enumerate(rows):
            for j, (val, col) in enumerate([
                (w["code"], None),
                (w["name"], None),
                (w["type"], WB if "WB" in w["type"] else OZ if "OZON" in w["type"] else None),
                (w["note"], MUTED),
            ]):
                item = QTableWidgetItem(str(val) if val else "")
                if col:
                    item.setForeground(__import__('PyQt6.QtGui', fromlist=['QColor']).QColor(col))
                self.table.setItem(i, j, item)

            act = QWidget()
            hl = QHBoxLayout(act)
            hl.setContentsMargins(4, 2, 4, 2)
            hl.setSpacing(4)
            btn_e = QPushButton("Изменить")
            btn_e.setFixedHeight(24)
            btn_e.clicked.connect(lambda _, wid=w["id"]: self.edit_wh(wid))
            btn_d = QPushButton("Удалить")
            btn_d.setObjectName("danger")
            btn_d.setFixedHeight(24)
            btn_d.clicked.connect(lambda _, wid=w["id"], name=w["name"]: self.del_wh(wid, name))
            hl.addWidget(btn_e)
            hl.addWidget(btn_d)
            self.table.setCellWidget(i, 4, act)

        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(1, 280)

    def add_wh(self):
        dlg = WHDialog(self.db, parent=self, warehouses_service=self.warehouses_service)
        if dlg.exec():
            self.refresh()
            self.main_win.tab_scanner.card.refresh_warehouses()
            self.main_win._refresh_status()

    def edit_wh(self, wid):
        w = self._get_warehouse_by_id(wid)
        if not w:
            return
        dlg = WHDialog(self.db, wh=dict(w), parent=self, warehouses_service=self.warehouses_service)
        if dlg.exec():
            self.refresh()
            self.main_win.tab_scanner.card.refresh_warehouses()

    def del_wh(self, wid, name):
        r = QMessageBox.question(
            self,
            "Удалить склад",
            f"Удалить склад «{name}»?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if r == QMessageBox.StandardButton.Yes:
            if self.warehouses_service:
                self.warehouses_service.delete(wid)
            else:
                self.db.delete_warehouse(wid)
            self.refresh()
            self.main_win.tab_scanner.card.refresh_warehouses()


class WHDialog(QDialog):
    def __init__(self, db, wh=None, parent=None, warehouses_service=None):
        super().__init__(parent)
        self.db = db
        self.warehouses_service = warehouses_service
        self.wh = wh
        self.setWindowTitle("Изменить склад" if wh else "Новый склад")
        self.setMinimumWidth(400)
        self._build()
        if wh:
            self._fill(wh)

    def _build(self):
        v = QVBoxLayout(self)
        v.setSpacing(12)
        title = QLabel("Изменить склад" if self.wh else "Добавить склад")
        title.setObjectName("title")
        v.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.f_code = QLineEdit()
        self.f_code.setPlaceholderText("ТВ-2, WB-1, OZ-1…")
        self.f_name = QLineEdit()
        self.f_name.setPlaceholderText("Склад Wildberries Коледино")
        self.f_type = QComboBox()
        self.f_type.addItems(["Центральный", "Маркетплейс WB", "Маркетплейс OZON", "Собственный", "Транзитный"])
        self.f_note = QLineEdit()
        form.addRow("Код *", self.f_code)
        form.addRow("Название *", self.f_name)
        form.addRow("Тип", self.f_type)
        form.addRow("Примечание", self.f_note)
        v.addLayout(form)

        hint = QLabel("⚡ Название должно содержать «WB»/«Wildberries» или «OZON»/«Озон»\nдля автоматической подстановки штрихкода при перемещении.")
        hint.setStyleSheet(f"font-size:11px;color:{MUTED};background:{PAPER};padding:8px;border-radius:5px;")
        hint.setWordWrap(True)
        v.addWidget(hint)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        btns.button(QDialogButtonBox.StandardButton.Ok).setObjectName("primary")
        btns.button(QDialogButtonBox.StandardButton.Ok).setText("Сохранить")
        v.addWidget(btns)

    def _fill(self, w):
        self.f_code.setText(w.get("code", ""))
        self.f_code.setEnabled(False)
        self.f_name.setText(w.get("name", ""))
        self.f_type.setCurrentText(w.get("type", "Собственный"))
        self.f_note.setText(w.get("note", ""))

    def _save(self):
        code = self.f_code.text().strip()
        name = self.f_name.text().strip()
        if not code or not name:
            QMessageBox.warning(self, "Ошибка", "Код и Название обязательны")
            return
        try:
            if self.wh:
                if self.warehouses_service:
                    self.warehouses_service.update(self.wh["id"], code, name, self.f_type.currentText(), self.f_note.text().strip())
                else:
                    self.db.update_warehouse(self.wh["id"], code, name, self.f_type.currentText(), self.f_note.text().strip())
            else:
                if self.warehouses_service:
                    self.warehouses_service.create(code, name, self.f_type.currentText(), self.f_note.text().strip())
                else:
                    self.db.add_warehouse(code, name, self.f_type.currentText(), self.f_note.text().strip())
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Код уже существует или другая ошибка:\n{e}")
