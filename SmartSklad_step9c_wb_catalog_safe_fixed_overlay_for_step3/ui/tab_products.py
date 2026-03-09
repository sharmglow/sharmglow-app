"""ui/tab_products.py — Справочник товаров"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QLineEdit, QPushButton, QHeaderView, QFrame, QDialog,
    QFormLayout, QSpinBox, QComboBox, QMessageBox, QDialogButtonBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont
from ui.styles import *


class ProductsTab(QWidget):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.main_win = parent
        self.ctx = getattr(parent, "ctx", None)
        self.products_service = getattr(self.ctx, "products_service", None) if self.ctx else None
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
        hl.setSpacing(10)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск по артикулу, названию, категории…")
        self.search.setFixedWidth(280)
        self.search.textChanged.connect(lambda: QTimer.singleShot(300, self.refresh))
        hl.addWidget(self.search)
        hl.addStretch()

        self.count_lbl = QLabel("")
        self.count_lbl.setStyleSheet(f"font-size:11px;color:{MUTED};")
        hl.addWidget(self.count_lbl)

        btn_add = QPushButton("+ Добавить товар")
        btn_add.setObjectName("primary")
        btn_add.clicked.connect(self.add_product)
        hl.addWidget(btn_add)
        v.addWidget(tb)

        cols = ["Артикул", "Наименование", "Категория", "Ед.", "Мин.остаток",
                "Штрихкод WB", "Штрихкод OZON", "Поставщик", "Остаток", "Действия"]
        self.table = QTableWidget(0, len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(44)
        self.table.verticalHeader().setMinimumSectionSize(44)
        self.table.setSortingEnabled(True)
        v.addWidget(self.table)
        self.refresh()

    def _get_products(self, search=""):
        if self.products_service:
            return self.products_service.get_all(search)
        return self.db.get_products(search)

    def _get_stock(self, art):
        if self.products_service:
            return self.products_service.get_stock(art)
        return self.db.get_stock(art)

    def _get_product_by_id(self, pid):
        if self.products_service:
            return self.products_service.get_by_id(pid)
        return self.db.conn.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()

    def refresh(self):
        q = self.search.text()
        rows = self._get_products(q)
        self.count_lbl.setText(f"{len(rows)} товаров")
        self.table.setRowCount(len(rows))

        for i, p in enumerate(rows):
            stock = self._get_stock(p["art"])
            vals = [p["art"], p["name"], p["cat"], p["unit"], p["min_stock"],
                    p["bc_wb"], p["bc_ozon"], p["supplier"], stock, ""]
            for j, val in enumerate(vals[:-1]):
                item = QTableWidgetItem(str(val) if val is not None else "")
                if j == 5:
                    item.setForeground(QColor(WB))
                if j == 6:
                    item.setForeground(QColor(OZ))
                if j == 8:
                    f = QFont()
                    f.setBold(True)
                    f.setFamily("Courier New")
                    item.setFont(f)
                    color = DANGER if stock <= 0 else (WARN if p["min_stock"] > 0 and stock <= p["min_stock"] else OK)
                    item.setForeground(QColor(color))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(i, j, item)

            act_w = QWidget()
            act_w.setFixedHeight(44)
            hl = QHBoxLayout(act_w)
            hl.setContentsMargins(4, 4, 4, 4)
            hl.setSpacing(4)

            btn_edit = QPushButton("✏️ Изм.")
            btn_edit.setFixedSize(72, 32)
            btn_edit.setStyleSheet("font-size:11px;padding:0;")
            btn_edit.clicked.connect(lambda _, pid=p["id"]: self.edit_product(pid))

            btn_del = QPushButton("🗑 Удал.")
            btn_del.setObjectName("danger")
            btn_del.setFixedSize(72, 32)
            btn_del.setStyleSheet(f"font-size:11px;padding:0;color:{DANGER};border:1px solid {DANGER};background:white;border-radius:5px;")
            btn_del.clicked.connect(lambda _, pid=p["id"], art=p["art"]: self.delete_product(pid, art))

            hl.addWidget(btn_edit)
            hl.addWidget(btn_del)
            hl.addStretch()
            self.table.setCellWidget(i, 9, act_w)

        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(1, 240)
        self.table.setColumnWidth(9, 160)

    def add_product(self):
        dlg = ProductDialog(self.db, parent=self, products_service=self.products_service)
        if dlg.exec():
            self.refresh()
            self.main_win.refresh_all()

    def edit_product(self, pid):
        p = self._get_product_by_id(pid)
        if not p:
            return
        dlg = ProductDialog(self.db, product=dict(p), parent=self, products_service=self.products_service)
        if dlg.exec():
            self.refresh()
            self.main_win.refresh_all()

    def delete_product(self, pid, art):
        r = QMessageBox.question(
            self,
            "Удалить товар",
            f"Удалить товар «{art}»?\n\nВся история прихода и перемещений сохранится.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if r == QMessageBox.StandardButton.Yes:
            if self.products_service:
                self.products_service.delete(pid)
            else:
                self.db.delete_product(pid)
            self.refresh()
            self.main_win.refresh_all()


class ProductDialog(QDialog):
    def __init__(self, db, product=None, parent=None, products_service=None):
        super().__init__(parent)
        self.db = db
        self.products_service = products_service
        self.product = product
        self.setWindowTitle("Изменить товар" if product else "Новый товар")
        self.setMinimumWidth(460)
        self._build()
        if product:
            self._fill(product)

    def _build(self):
        v = QVBoxLayout(self)
        v.setSpacing(12)

        title = QLabel("Изменить товар" if self.product else "Добавить товар")
        title.setObjectName("title")
        v.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.f_art = QLineEdit()
        self.f_art.setPlaceholderText("К001, АРТ-001…")
        self.f_name = QLineEdit()
        cats = self.products_service.get_categories() if self.products_service else self.db.get_categories()
        self.f_cat = QComboBox()
        self.f_cat.setEditable(True)
        self.f_cat.addItems(cats)
        self.f_unit = QComboBox()
        self.f_unit.setEditable(True)
        self.f_unit.addItems(["шт", "кг", "м", "л", "уп", "пара", "рулон"])
        self.f_min = QSpinBox()
        self.f_min.setRange(0, 999999)
        self.f_bc_wb = QLineEdit()
        self.f_bc_wb.setPlaceholderText("Штрихкод из ЛК Wildberries")
        self.f_bc_wb.setStyleSheet(f"border-color:{WB};")
        self.f_bc_ozon = QLineEdit()
        self.f_bc_ozon.setPlaceholderText("Штрихкод из ЛК OZON")
        self.f_bc_ozon.setStyleSheet(f"border-color:{OZ};")
        self.f_supplier = QLineEdit()
        self.f_note = QLineEdit()

        form.addRow("Артикул *", self.f_art)
        form.addRow("Наименование *", self.f_name)
        form.addRow("Категория", self.f_cat)
        form.addRow("Единица изм.", self.f_unit)
        form.addRow("Мин. остаток", self.f_min)

        bc_title = QLabel("Штрихкоды маркетплейсов")
        bc_title.setStyleSheet(f"font-weight:600;font-size:11px;color:{MUTED};margin-top:6px;")
        form.addRow("", bc_title)
        wb_lbl = QLabel("Штрихкод WB")
        wb_lbl.setStyleSheet(f"color:{WB};font-weight:600;")
        form.addRow(wb_lbl, self.f_bc_wb)
        oz_lbl = QLabel("Штрихкод OZON")
        oz_lbl.setStyleSheet(f"color:{OZ};font-weight:600;")
        form.addRow(oz_lbl, self.f_bc_ozon)
        form.addRow("Поставщик", self.f_supplier)
        form.addRow("Примечание", self.f_note)
        v.addLayout(form)

        hint = QLabel("💡 Штрихкод WB — в ЛК Wildberries: Товары → Баркод\nШтрихкод OZON — в ЛК OZON: Товары → FBO/FBS")
        hint.setStyleSheet(f"font-size:11px;color:{MUTED};background:{PAPER};padding:8px;border-radius:5px;")
        v.addWidget(hint)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        btns.button(QDialogButtonBox.StandardButton.Ok).setObjectName("primary")
        btns.button(QDialogButtonBox.StandardButton.Ok).setText("Сохранить")
        v.addWidget(btns)

    def _fill(self, p):
        self.f_art.setText(p.get("art", ""))
        self.f_name.setText(p.get("name", ""))
        self.f_cat.setCurrentText(p.get("cat", ""))
        self.f_unit.setCurrentText(p.get("unit", "шт"))
        self.f_min.setValue(p.get("min_stock", 0))
        self.f_bc_wb.setText(str(p.get("bc_wb", "") or ""))
        self.f_bc_ozon.setText(str(p.get("bc_ozon", "") or ""))
        self.f_supplier.setText(p.get("supplier", ""))
        self.f_note.setText(p.get("note", ""))
        if self.product:
            self.f_art.setEnabled(False)

    def _save(self):
        art = self.f_art.text().strip()
        name = self.f_name.text().strip()
        if not art or not name:
            QMessageBox.warning(self, "Ошибка", "Артикул и Наименование обязательны")
            return
        args = (
            art,
            name,
            self.f_cat.currentText().strip(),
            self.f_unit.currentText().strip() or "шт",
            self.f_min.value(),
            self.f_bc_wb.text().strip(),
            self.f_bc_ozon.text().strip(),
            self.f_supplier.text().strip(),
            self.f_note.text().strip(),
        )
        try:
            if self.product:
                if self.products_service:
                    self.products_service.update(self.product["id"], *args)
                else:
                    self.db.update_product(self.product["id"], *args)
            else:
                if self.products_service:
                    self.products_service.create(*args)
                else:
                    self.db.add_product(*args)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
