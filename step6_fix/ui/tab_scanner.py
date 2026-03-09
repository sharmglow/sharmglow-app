"""ui/tab_scanner.py — Сканер: приход, перемещение, поиск"""
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QSpinBox, QFrame, QListWidget,
    QListWidgetItem, QButtonGroup, QRadioButton, QGroupBox,
    QSizePolicy, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from ui.styles import *


class ScannerTab(QWidget):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.main_win = parent
        self.cur_product = None
        self.mode = "receive"   # receive | move | search
        self._build()

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── LEFT PANEL ──────────────────────────────────────
        left = QFrame()
        left.setFixedWidth(380)
        left.setStyleSheet(f"background:white;border-right:1px solid {BORDER};")
        lv = QVBoxLayout(left)
        lv.setContentsMargins(20, 20, 20, 16)
        lv.setSpacing(14)

        # Mode buttons
        mode_lbl = QLabel("РЕЖИМ")
        mode_lbl.setObjectName("section")
        lv.addWidget(mode_lbl)

        mode_row = QHBoxLayout()
        self.btn_receive = QPushButton("➕ Приход")
        self.btn_move    = QPushButton("🔄 Перемещение")
        self.btn_search  = QPushButton("🔎 Поиск")
        for btn in [self.btn_receive, self.btn_move, self.btn_search]:
            btn.setCheckable(True)
            btn.setMinimumHeight(34)
            mode_row.addWidget(btn)
        self.btn_receive.setChecked(True)
        self.btn_receive.clicked.connect(lambda: self.set_mode("receive"))
        self.btn_move.clicked.connect(lambda: self.set_mode("move"))
        self.btn_search.clicked.connect(lambda: self.set_mode("search"))
        lv.addLayout(mode_row)

        # Scanner input
        scan_lbl = QLabel("СКАНЕР / АРТИКУЛ")
        scan_lbl.setObjectName("section")
        lv.addWidget(scan_lbl)

        self.scan_input = QLineEdit()
        self.scan_input.setPlaceholderText("Штрихкод WB, OZON или артикул…")
        self.scan_input.setStyleSheet(f"""
            QLineEdit {{
                font-family: 'Courier New', monospace;
                font-size: 14px;
                padding: 10px 12px;
                border: 2px solid {BORDER};
                border-radius: 6px;
                background: {CREAM};
            }}
            QLineEdit:focus {{ border-color: {GOLD}; background: white; }}
        """)
        self.scan_input.returnPressed.connect(self._do_scan)
        self.scan_input.textChanged.connect(self._on_text_changed)
        lv.addWidget(self.scan_input)

        self._scan_timer = QTimer()
        self._scan_timer.setSingleShot(True)
        self._scan_timer.timeout.connect(self._do_scan)

        # Product card
        self.card = ProductCard(self.db)
        self.card.setVisible(False)
        lv.addWidget(self.card)

        # Action button
        self.act_btn = QPushButton("➕ Оприходовать")
        self.act_btn.setObjectName("primary")
        self.act_btn.setMinimumHeight(40)
        self.act_btn.setVisible(False)
        self.act_btn.clicked.connect(self._do_action)
        lv.addWidget(self.act_btn)

        lv.addStretch()
        layout.addWidget(left)

        # ── RIGHT PANEL: ops log ────────────────────────────
        right = QFrame()
        right.setStyleSheet(f"background:{PAPER};")
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(0)

        hdr = QFrame()
        hdr.setFixedHeight(44)
        hdr.setStyleSheet(f"background:white;border-bottom:1px solid {BORDER};")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(16, 0, 16, 0)
        ops_lbl = QLabel("ОПЕРАЦИИ СЕССИИ")
        ops_lbl.setObjectName("section")
        hl.addWidget(ops_lbl)
        self.ops_count = QLabel("")
        self.ops_count.setStyleSheet(f"font-size:11px;color:{MUTED};font-family:monospace;")
        hl.addStretch()
        hl.addWidget(self.ops_count)
        rv.addWidget(hdr)

        self.ops_list = QListWidget()
        self.ops_list.setAlternatingRowColors(True)
        self.ops_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.ops_list.setStyleSheet(f"""
            QListWidget {{ background:{PAPER}; border:none; }}
            QListWidget::item {{ padding:8px 12px; border-bottom:1px solid {BORDER}; background:white; }}
            QListWidget::item:alternate {{ background:{CREAM}; }}
            QListWidget::item:hover {{ background:{CREAM}; }}
        """)
        rv.addWidget(self.ops_list)
        layout.addWidget(right)

        self.set_mode("receive")

    # ── MODE ──────────────────────────────────────────────
    def set_mode(self, mode):
        self.mode = mode
        for btn, m in [(self.btn_receive,"receive"),(self.btn_move,"move"),(self.btn_search,"search")]:
            btn.setChecked(m == mode)
            btn.setStyleSheet(
                f"background:{INK};color:{GOLD_L};border:none;font-weight:700;" if m == mode
                else f"background:{PAPER};color:{INK};border:1px solid {BORDER};")
        self.card.set_mode(mode)
        self._update_act_btn()
        if self.cur_product:
            self.card.set_product(self.cur_product, self.mode)
        self.scan_input.setFocus()

    def _update_act_btn(self):
        labels = {"receive": "➕ Оприходовать", "move": "🔄 Переместить", "search": ""}
        lbl = labels.get(self.mode, "")
        self.act_btn.setText(lbl)
        self.act_btn.setVisible(bool(lbl) and self.cur_product is not None)

    # ── SCAN ──────────────────────────────────────────────
    def _on_text_changed(self, text):
        if len(text) >= 4:
            self._scan_timer.start(600)

    def _do_scan(self):
        q = self.scan_input.text().strip()
        if not q: return
        p = self.db.get_product_by_barcode(q) or self.db.get_product(q)
        if p:
            self._flash(True)
            self.cur_product = dict(p)
            self.card.set_product(self.cur_product, self.mode, scanned=q)
            self.card.setVisible(True)
            self._update_act_btn()
        else:
            self._flash(False)
            self.main_win.set_status(f"Не найден: {q}", 2500)

    def _flash(self, ok):
        color = OK_BG if ok else DANGER_BG
        self.scan_input.setStyleSheet(
            f"QLineEdit{{font-family:'Courier New',monospace;font-size:14px;"
            f"padding:10px 12px;border:2px solid {OK if ok else DANGER};"
            f"border-radius:6px;background:{color};}}")
        QTimer.singleShot(700, self._reset_scan_style)

    def _reset_scan_style(self):
        self.scan_input.setStyleSheet(f"""
            QLineEdit {{
                font-family:'Courier New',monospace;font-size:14px;
                padding:10px 12px;border:2px solid {BORDER};
                border-radius:6px;background:{CREAM};
            }}
            QLineEdit:focus {{ border-color:{GOLD};background:white; }}
        """)

    # ── ACTION ────────────────────────────────────────────
    def _do_action(self):
        if not self.cur_product: return
        if self.mode == "receive":
            self._do_receive()
        elif self.mode == "move":
            self._do_move()

    def _do_receive(self):
        qty = self.card.get_qty()
        wh  = self.card.get_wh()
        if qty <= 0: return
        self.db.add_arrival(self.cur_product["art"], wh, qty)
        self._push_op("in", self.cur_product, qty, wh)
        self.main_win.set_status(f"✓ Приход: {self.cur_product['art']} +{qty}")
        self._reset_after_op()

    def _do_move(self):
        qty     = self.card.get_qty()
        from_wh = self.card.get_from_wh()
        to_wh   = self.card.get_to_wh()
        if qty <= 0 or from_wh == to_wh: return
        mp_type = self.db.mp_type_for_wh(to_wh)
        barcode = (self.cur_product.get("bc_wb","") if mp_type == "WB"
                   else self.cur_product.get("bc_ozon","") if mp_type == "OZON"
                   else "")
        self.db.add_move(self.cur_product["art"], from_wh, to_wh, qty,
                         barcode=barcode, mp_type=mp_type)
        self._push_op("out", self.cur_product, qty, f"{from_wh} → {to_wh}")
        self.main_win.set_status(f"✓ Перемещено: {self.cur_product['art']} {qty}")
        self._reset_after_op()

    def _reset_after_op(self):
        self.scan_input.clear()
        self.scan_input.setFocus()
        # Refresh stock in card
        if self.cur_product:
            p = self.db.get_product(self.cur_product["art"])
            if p:
                self.cur_product = dict(p)
                self.card.set_product(self.cur_product, self.mode)
        self.main_win.tab_stock.refresh()

    def _push_op(self, kind, product, qty, detail):
        from datetime import datetime
        t = datetime.now().strftime("%H:%M")
        ico = "↑" if kind == "in" else "→"
        txt = f"{ico}  {product['art']}   {product['name']}   ×{qty}   {detail}   {t}"
        item = QListWidgetItem(txt)
        if kind == "in":
            item.setForeground(QColor(OK))
        else:
            # Определяем цвет по маркетплейсу
            if "Wildberries" in detail or "WB" in detail.upper():
                item.setForeground(QColor("#6a1b9a"))  # WB лиловый
            elif "OZON" in detail.upper() or "Озон" in detail:
                item.setForeground(QColor("#1565c0"))  # OZON синий
            else:
                item.setForeground(QColor(WARN))
        self.ops_list.insertItem(0, item)
        self.ops_count.setText(f"{self.ops_list.count()} оп.")

    def refresh(self):
        self.card.refresh_warehouses()
        self.scan_input.setFocus()


class ProductCard(QWidget):
    """Shows found product info + qty / wh selectors"""
    def __init__(self, db):
        super().__init__()
        self.db = db
        self._build()

    def _build(self):
        self.setStyleSheet(f"background:{CREAM};border:1px solid {BORDER};border-radius:8px;")
        v = QVBoxLayout(self)
        v.setContentsMargins(12, 10, 12, 10)
        v.setSpacing(8)

        # Name + art
        row1 = QHBoxLayout()
        self.name_lbl = QLabel("—")
        self.name_lbl.setStyleSheet(f"font-weight:600;font-size:13px;color:{INK};")
        self.name_lbl.setWordWrap(True)
        self.art_lbl = QLabel("—")
        self.art_lbl.setStyleSheet(f"font-family:monospace;font-size:11px;color:{GOLD};font-weight:700;")
        row1.addWidget(self.name_lbl, 1)
        row1.addWidget(self.art_lbl)
        v.addLayout(row1)

        # Stock
        stock_row = QHBoxLayout()
        QLabel_s = lambda t, s: (lambda l: (l.setStyleSheet(s), l))( QLabel(t) )[1]
        self.stock_lbl = QLabel("0")
        self.stock_lbl.setStyleSheet(f"font-family:monospace;font-size:20px;font-weight:700;color:{OK};")
        self.unit_lbl  = QLabel("шт")
        self.unit_lbl.setStyleSheet(f"font-size:11px;color:{MUTED};")
        self.status_lbl = QLabel("OK")
        self.status_lbl.setStyleSheet(f"background:{OK_BG};color:{OK};font-size:10px;padding:2px 8px;border-radius:9px;font-family:monospace;")
        stock_row.addWidget(QLabel("Остаток:"))
        stock_row.addWidget(self.stock_lbl)
        stock_row.addWidget(self.unit_lbl)
        stock_row.addWidget(self.status_lbl)
        stock_row.addStretch()
        v.addLayout(stock_row)

        # Barcodes
        bc_row = QHBoxLayout()
        self.wb_bc  = BarcodeChip("WB",   WB,  WB_LT)
        self.oz_bc  = BarcodeChip("OZON", OZ,  OZ_LT)
        bc_row.addWidget(self.wb_bc)
        bc_row.addWidget(self.oz_bc)
        self.bc_row_widget = QWidget()
        self.bc_row_widget.setLayout(bc_row)
        v.addWidget(self.bc_row_widget)

        # WH selectors (move mode)
        self.move_frame = QFrame()
        mv = QVBoxLayout(self.move_frame)
        mv.setContentsMargins(0,0,0,0); mv.setSpacing(6)
        fr_row = QHBoxLayout()
        fr_row.addWidget(QLabel("Откуда:"))
        self.from_combo = QComboBox(); fr_row.addWidget(self.from_combo, 1)
        mv.addLayout(fr_row)
        to_row = QHBoxLayout()
        to_row.addWidget(QLabel("Куда:"))
        self.to_combo = QComboBox()
        self.to_combo.currentTextChanged.connect(self._on_dest_changed)
        to_row.addWidget(self.to_combo, 1)
        mv.addLayout(to_row)
        self.mp_info = QLabel("")
        self.mp_info.setStyleSheet(f"font-size:11px;font-family:monospace;padding:4px 8px;border-radius:5px;")
        mv.addWidget(self.mp_info)
        v.addWidget(self.move_frame)

        # Receive WH selector
        self.recv_frame = QFrame()
        rf = QHBoxLayout(self.recv_frame)
        rf.setContentsMargins(0,0,0,0)
        rf.addWidget(QLabel("Склад прихода:"))
        self.recv_combo = QComboBox(); rf.addWidget(self.recv_combo, 1)
        v.addWidget(self.recv_frame)

        # Qty
        qty_row = QHBoxLayout()
        qty_row.addWidget(QLabel("Количество:"))
        minus = QPushButton("−"); minus.setFixedSize(28,28); minus.clicked.connect(lambda: self._chq(-1))
        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(1, 99999); self.qty_spin.setValue(1)
        self.qty_spin.setFixedWidth(70)
        self.qty_spin.setStyleSheet("font-family:monospace;font-size:14px;font-weight:700;text-align:center;")
        plus = QPushButton("+"); plus.setFixedSize(28,28); plus.clicked.connect(lambda: self._chq(1))
        qty_row.addStretch()
        qty_row.addWidget(minus); qty_row.addWidget(self.qty_spin); qty_row.addWidget(plus)
        v.addLayout(qty_row)

        self.refresh_warehouses()

    def _chq(self, d):
        self.qty_spin.setValue(max(1, self.qty_spin.value() + d))

    def refresh_warehouses(self):
        whs = self.db.get_warehouses()
        wh_names = [w["name"] for w in whs]
        for combo in [self.from_combo, self.to_combo, self.recv_combo]:
            cur = combo.currentText()
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(wh_names)
            if cur in wh_names: combo.setCurrentText(cur)
            combo.blockSignals(False)
        # Default: from=central, to=WB
        central = next((w["name"] for w in whs if w["type"]=="Центральный"), wh_names[0] if wh_names else "")
        wb_wh   = next((w["name"] for w in whs if "WB" in w["name"].upper()), "")
        if central: self.from_combo.setCurrentText(central)
        if central: self.recv_combo.setCurrentText(central)
        if wb_wh:   self.to_combo.setCurrentText(wb_wh)

    def _on_dest_changed(self, name):
        mp = self.db.mp_type_for_wh(name)
        if mp and self._cur_product:
            bc = (self._cur_product.get("bc_wb","") if mp=="WB"
                  else self._cur_product.get("bc_ozon",""))
            color, bg = (WB, WB_LT) if mp=="WB" else (OZ, OZ_LT)
            self.mp_info.setText(f"📦 {mp}: {bc or '⚠️ штрихкод не задан'}")
            self.mp_info.setStyleSheet(f"font-size:11px;font-family:monospace;padding:4px 8px;border-radius:5px;background:{bg};color:{color};")
            self.mp_info.setVisible(True)
        else:
            self.mp_info.setVisible(False)

    def set_product(self, p, mode, scanned=None):
        self._cur_product = p
        self.name_lbl.setText(p["name"])
        self.art_lbl.setText(p["art"])
        detail = self.db.get_stock_detail(p["art"])
        s = detail["stock"]
        self.stock_lbl.setText(str(s))
        self.unit_lbl.setText(p["unit"])
        if s <= 0:
            self.stock_lbl.setStyleSheet(f"font-family:monospace;font-size:20px;font-weight:700;color:{DANGER};")
            self.status_lbl.setText("НЕТ"); self.status_lbl.setStyleSheet(f"background:{DANGER_BG};color:{DANGER};font-size:10px;padding:2px 8px;border-radius:9px;font-family:monospace;")
        elif p["min_stock"] > 0 and s <= p["min_stock"]:
            self.stock_lbl.setStyleSheet(f"font-family:monospace;font-size:20px;font-weight:700;color:{WARN};")
            self.status_lbl.setText("МАЛО"); self.status_lbl.setStyleSheet(f"background:{WARN_BG};color:{WARN};font-size:10px;padding:2px 8px;border-radius:9px;font-family:monospace;")
        else:
            self.stock_lbl.setStyleSheet(f"font-family:monospace;font-size:20px;font-weight:700;color:{OK};")
            self.status_lbl.setText("OK"); self.status_lbl.setStyleSheet(f"background:{OK_BG};color:{OK};font-size:10px;padding:2px 8px;border-radius:9px;font-family:monospace;")

        self.wb_bc.set_code(p.get("bc_wb",""))
        self.oz_bc.set_code(p.get("bc_ozon",""))
        self.set_mode(mode)
        self._on_dest_changed(self.to_combo.currentText())
        self.qty_spin.setValue(1)

    def set_mode(self, mode):
        self.move_frame.setVisible(mode == "move")
        self.recv_frame.setVisible(mode == "receive")

    def get_qty(self):     return self.qty_spin.value()
    def get_wh(self):      return self.recv_combo.currentText()
    def get_from_wh(self): return self.from_combo.currentText()
    def get_to_wh(self):   return self.to_combo.currentText()


class BarcodeChip(QFrame):
    def __init__(self, mp, color, bg):
        super().__init__()
        self.setStyleSheet(f"background:{bg};border:1.5px solid {color};border-radius:7px;padding:5px 8px;")
        v = QVBoxLayout(self)
        v.setContentsMargins(5,4,5,4); v.setSpacing(2)
        lbl = QLabel(mp)
        lbl.setStyleSheet(f"color:{color};font-size:9px;font-weight:700;font-family:monospace;letter-spacing:.1em;border:none;background:transparent;")
        self.code_lbl = QLabel("—")
        self.code_lbl.setStyleSheet(f"font-family:monospace;font-size:10px;color:#333;border:none;background:transparent;word-wrap:break-word;")
        v.addWidget(lbl)
        v.addWidget(self.code_lbl)

    def set_code(self, code):
        self.code_lbl.setText(code if code else "не задан")
        self.code_lbl.setStyleSheet(
            f"font-family:monospace;font-size:10px;color:{'#333' if code else MUTED};border:none;background:transparent;")
