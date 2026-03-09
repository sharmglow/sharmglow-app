"""ui/tab_labels.py — Этикетки: очередь печати + редактор дизайна"""
import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QFrame, QLabel,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem, QSpinBox,
    QComboBox, QScrollArea, QGroupBox, QCheckBox, QColorDialog,
    QDialog, QFormLayout, QDialogButtonBox, QMessageBox, QFileDialog,
    QTabWidget, QSlider, QDoubleSpinBox, QButtonGroup, QRadioButton,
    QToolButton, QSizePolicy, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF, QSizeF, pyqtSignal
from PyQt6.QtGui import (
    QColor, QPainter, QPen, QBrush, QFont, QFontMetrics, QPainterPath,
    QPixmap, QImage
)
from ui.styles import *


MM_TO_PX = 3.7795  # 1mm at 96dpi


class LabelsTab(QWidget):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.main_win = parent
        self.print_queue = []   # [{art, name, mp, bc, qty}]
        self.cur_template = None
        self._build()
        self._load_default_template()

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── LEFT: product list + queue ──────────────────────
        left = QFrame()
        left.setMinimumWidth(320)
        left.setMaximumWidth(400)
        left.setStyleSheet(f"background:white;border-right:1px solid {BORDER};")
        lv = QVBoxLayout(left); lv.setContentsMargins(14,14,14,14); lv.setSpacing(10)

        lv.addWidget(self._section("ПОИСК ТОВАРА"))
        self.search = QLineEdit(); self.search.setPlaceholderText("Артикул или название…")
        self.search.textChanged.connect(lambda: QTimer.singleShot(300, self._refresh_list))
        lv.addWidget(self.search)

        self.prod_list = QListWidget()
        self.prod_list.setMaximumHeight(220)
        self.prod_list.itemClicked.connect(self._on_prod_select)
        self.prod_list.setStyleSheet(f"""
            QListWidget::item{{padding:6px 8px;border-bottom:1px solid {PAPER};}}
            QListWidget::item:selected{{background:#fff8e7;color:{INK};}}
            QListWidget::item:hover{{background:{CREAM};}}
        """)
        lv.addWidget(self.prod_list)

        # Selected product config
        self.cfg_box = QGroupBox("Выбранный товар")
        cfg_v = QVBoxLayout(self.cfg_box)
        self.cfg_name = QLabel("—"); self.cfg_name.setWordWrap(True)
        self.cfg_name.setStyleSheet(f"font-weight:600;font-size:12px;")
        cfg_v.addWidget(self.cfg_name)

        mp_row = QHBoxLayout()
        mp_row.addWidget(QLabel("МП:"))
        self.mp_wb = QPushButton("WB"); self.mp_wb.setCheckable(True)
        self.mp_wb.setFixedSize(70, 32)
        self.mp_ozon = QPushButton("OZON"); self.mp_ozon.setCheckable(True)
        self.mp_ozon.setFixedSize(70, 32)

        def _style_mp(wb_on, ozon_on):
            self.mp_wb.setStyleSheet(
                f"background:#6a1b9a;color:white;border:2px solid #6a1b9a;border-radius:5px;font-weight:700;font-size:12px;"
                if wb_on else
                f"background:white;color:#6a1b9a;border:2px solid #6a1b9a;border-radius:5px;font-weight:700;font-size:12px;"
            )
            self.mp_ozon.setStyleSheet(
                f"background:#1565c0;color:white;border:2px solid #1565c0;border-radius:5px;font-weight:700;font-size:12px;"
                if ozon_on else
                f"background:white;color:#1565c0;border:2px solid #1565c0;border-radius:5px;font-weight:700;font-size:12px;"
            )
        self._style_mp = _style_mp

        def _click_wb():
            self.mp_wb.setChecked(True)
            self.mp_ozon.setChecked(False)
            _style_mp(True, False)
            if self._cur_product:
                self._update_preview_product(self._cur_product)

        def _click_ozon():
            self.mp_ozon.setChecked(True)
            self.mp_wb.setChecked(False)
            _style_mp(False, True)
            if self._cur_product:
                self._update_preview_product(self._cur_product)

        self.mp_wb.clicked.connect(_click_wb)
        self.mp_ozon.clicked.connect(_click_ozon)
        _style_mp(False, False)
        mp_row.addWidget(self.mp_wb); mp_row.addWidget(self.mp_ozon)
        mp_row.addStretch()
        cfg_v.addLayout(mp_row)

        qty_row = QHBoxLayout()
        qty_row.addWidget(QLabel("Кол-во:"))
        minus = QPushButton("−"); minus.setFixedSize(26,26)
        minus.clicked.connect(lambda: self.qty_spin.setValue(max(1,self.qty_spin.value()-1)))
        self.qty_spin = QSpinBox(); self.qty_spin.setRange(1,9999); self.qty_spin.setValue(1)
        self.qty_spin.setFixedWidth(65)
        plus = QPushButton("+"); plus.setFixedSize(26,26)
        plus.clicked.connect(lambda: self.qty_spin.setValue(self.qty_spin.value()+1))
        qty_row.addStretch(); qty_row.addWidget(minus); qty_row.addWidget(self.qty_spin); qty_row.addWidget(plus)
        cfg_v.addLayout(qty_row)

        btn_add_q = QPushButton("🏷️  Добавить в очередь")
        btn_add_q.setObjectName("primary"); btn_add_q.clicked.connect(self._add_to_queue)
        cfg_v.addWidget(btn_add_q)
        lv.addWidget(self.cfg_box)
        self.cfg_box.setVisible(False)

        # Queue
        lv.addWidget(self._section("ОЧЕРЕДЬ ПЕЧАТИ"))
        self.queue_list = QListWidget()
        self.queue_list.setStyleSheet(f"QListWidget::item{{padding:6px 8px;border-bottom:1px solid {PAPER};}}")
        lv.addWidget(self.queue_list, 1)

        q_btns = QHBoxLayout()
        self.queue_total = QLabel("Пусто"); self.queue_total.setStyleSheet(f"font-size:11px;color:{MUTED};")
        btn_clear = QPushButton("Очистить"); btn_clear.setObjectName("danger")
        btn_clear.setFixedHeight(30); btn_clear.clicked.connect(self._clear_queue)
        btn_print = QPushButton("🖨️ Печатать (Ctrl+P)")
        btn_print.setObjectName("primary"); btn_print.setFixedHeight(32)
        btn_print.clicked.connect(self._print_queue)
        q_btns.addWidget(self.queue_total); q_btns.addStretch()
        q_btns.addWidget(btn_clear)
        lv.addLayout(q_btns)
        lv.addWidget(btn_print)

        splitter.addWidget(left)

        # ── RIGHT: designer ─────────────────────────────────
        right = QTabWidget()
        right.setDocumentMode(True)

        # Preview tab
        preview_tab = QWidget()
        pv = QVBoxLayout(preview_tab); pv.setContentsMargins(0,0,0,0)
        ptb = QFrame(); ptb.setFixedHeight(46)
        ptb.setStyleSheet(f"background:white;border-bottom:1px solid {BORDER};")
        ptb_h = QHBoxLayout(ptb); ptb_h.setContentsMargins(14,0,14,0)
        self.tmpl_combo = QComboBox()
        self.tmpl_combo.setMinimumWidth(200)
        self.tmpl_combo.currentIndexChanged.connect(self._on_template_change)
        btn_new_tmpl  = QPushButton("+ Новый"); btn_new_tmpl.setFixedHeight(28)
        btn_new_tmpl.clicked.connect(self._new_template)
        btn_del_tmpl  = QPushButton("Удалить"); btn_del_tmpl.setObjectName("danger"); btn_del_tmpl.setFixedHeight(28)
        btn_del_tmpl.clicked.connect(self._del_template)
        btn_dup_tmpl  = QPushButton("Дублировать"); btn_dup_tmpl.setFixedHeight(28)
        btn_dup_tmpl.clicked.connect(self._dup_template)
        ptb_h.addWidget(QLabel("Шаблон:")); ptb_h.addWidget(self.tmpl_combo)
        ptb_h.addWidget(btn_new_tmpl); ptb_h.addWidget(btn_dup_tmpl); ptb_h.addWidget(btn_del_tmpl)
        ptb_h.addStretch()
        pv.addWidget(ptb)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"background:{PAPER};border:none;")
        scroll_inner = QWidget(); scroll_inner.setStyleSheet(f"background:{PAPER};")
        si_layout = QVBoxLayout(scroll_inner); si_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        si_layout.setContentsMargins(30,30,30,30)
        self.preview = LabelPreview()
        si_layout.addWidget(self.preview)
        scroll.setWidget(scroll_inner)
        pv.addWidget(scroll, 1)

        right.addTab(preview_tab, "👁️ Превью")

        # Designer tab
        designer_tab = QScrollArea()
        designer_tab.setWidgetResizable(True)
        designer_inner = QWidget()
        dv = QVBoxLayout(designer_inner); dv.setContentsMargins(16,16,16,16); dv.setSpacing(12)

        # Canvas size
        size_box = QGroupBox("Размер этикетки")
        sb = QHBoxLayout(size_box)
        sb.addWidget(QLabel("Ширина (мм):"))
        self.d_width  = QDoubleSpinBox(); self.d_width.setRange(20,200); self.d_width.setValue(58); self.d_width.setSuffix(" мм")
        sb.addWidget(self.d_width)
        sb.addWidget(QLabel("Высота (мм):"))
        self.d_height = QDoubleSpinBox(); self.d_height.setRange(10,200); self.d_height.setValue(40); self.d_height.setSuffix(" мм")
        sb.addWidget(self.d_height)
        self.d_border = QCheckBox("Рамка"); self.d_border.setChecked(True)
        sb.addWidget(self.d_border)
        sb.addStretch()
        dv.addWidget(size_box)

        # Background
        bg_box = QGroupBox("Фон")
        bg_h = QHBoxLayout(bg_box)
        bg_h.addWidget(QLabel("Цвет фона:"))
        self.d_bg_btn = QPushButton("  "); self.d_bg_btn.setFixedSize(40,26)
        self.d_bg_btn.setStyleSheet("background:#ffffff;border:1px solid #ccc;border-radius:4px;")
        self.d_bg_btn.clicked.connect(lambda: self._pick_color("bg"))
        bg_h.addWidget(self.d_bg_btn)
        bg_h.addStretch()
        dv.addWidget(bg_box)

        # Blocks
        blocks_box = QGroupBox("Блоки этикетки")
        blocks_v = QVBoxLayout(blocks_box)
        self.block_widgets = []

        BLOCK_DEFS = [
            ("mp_badge",  "Значок WB/OZON"),
            ("name",      "Название товара"),
            ("name2",     "Строка текста 2"),
            ("name3",     "Строка текста 3"),
            ("divider",   "Разделитель"),
            ("art",       "Артикул"),
            ("logo",      "Логотип (текст)"),
            ("barcode",   "Штрихкод"),
            ("bc_number", "Цифры штрихкода"),
            ("price",     "Цена"),
        ]
        for btype, blabel in BLOCK_DEFS:
            bw = BlockEditor(btype, blabel)
            bw.changed.connect(self._on_designer_change)
            blocks_v.addWidget(bw)
            self.block_widgets.append(bw)
        dv.addWidget(blocks_box)

        btn_save_tmpl = QPushButton("💾 Сохранить шаблон")
        btn_save_tmpl.setObjectName("primary"); btn_save_tmpl.setMinimumHeight(36)
        btn_save_tmpl.clicked.connect(self._save_template)
        dv.addWidget(btn_save_tmpl)
        dv.addStretch()

        designer_tab.setWidget(designer_inner)
        right.addTab(designer_tab, "✏️ Редактор дизайна")

        splitter.addWidget(right)
        splitter.setSizes([340, 800])
        layout.addWidget(splitter)

        self._cur_product = None
        self._refresh_list()
        self._refresh_template_combo()

    def _section(self, text):
        l = QLabel(text); l.setObjectName("section"); return l

    # ── PRODUCT LIST ─────────────────────────────────────
    def _refresh_list(self):
        q = self.search.text()
        prods = self.db.get_products(q)
        self.prod_list.clear()
        for p in prods:
            markers = []
            if p["bc_wb"]:   markers.append("WB")
            if p["bc_ozon"]: markers.append("OZ")
            txt = f"{p['art']}   {p['name']}"
            if markers: txt += f"  [{' / '.join(markers)}]"
            item = QListWidgetItem(txt)
            item.setData(Qt.ItemDataRole.UserRole, dict(p))
            self.prod_list.addItem(item)

    def _on_prod_select(self, item):
        p = item.data(Qt.ItemDataRole.UserRole)
        self._cur_product = p
        self.cfg_name.setText(p["name"])
        has_wb   = bool(p["bc_wb"])
        has_ozon = bool(p["bc_ozon"])
        self.mp_wb.setEnabled(has_wb)
        self.mp_ozon.setEnabled(has_ozon)
        # Выбираем WB если есть, иначе OZON
        wb_on   = has_wb
        ozon_on = has_ozon and not has_wb
        self.mp_wb.setChecked(wb_on)
        self.mp_ozon.setChecked(ozon_on)
        self._style_mp(wb_on, ozon_on)
        self.cfg_box.setVisible(True)
        self._update_preview_product(p)

    def _update_preview_product(self, p):
        mp = "WB" if self.mp_wb.isChecked() else ("OZON" if self.mp_ozon.isChecked() else "")
        bc = p["bc_wb"] if mp=="WB" else p["bc_ozon"] if mp=="OZON" else (p["bc_wb"] or p["bc_ozon"])
        self.preview.set_data(p["name"], p["art"], bc, mp)

    # ── QUEUE ────────────────────────────────────────────
    def _add_to_queue(self):
        if not self._cur_product: return
        mp = "WB" if self.mp_wb.isChecked() else ("OZON" if self.mp_ozon.isChecked() else "")
        bc = self._cur_product["bc_wb"] if mp=="WB" else (self._cur_product["bc_ozon"] if mp=="OZON" else "")
        if not bc:
            QMessageBox.warning(self, "Штрихкод", "Штрихкод не задан для этого маркетплейса")
            return
        qty = self.qty_spin.value()
        art = self._cur_product["art"]

        ex = next((x for x in self.print_queue if x["art"]==art and x["mp"]==mp), None)
        if ex: ex["qty"] += qty
        else: self.print_queue.append({"art":art,"name":self._cur_product["name"],"mp":mp,"bc":bc,"qty":qty})

        self._refresh_queue_list()
        self.main_win.set_status(f"✓ В очередь: {art} {mp} ×{qty}")

    def _refresh_queue_list(self):
        self.queue_list.clear()
        total = sum(x["qty"] for x in self.print_queue)
        for i, item in enumerate(self.print_queue):
            color = WB if item["mp"]=="WB" else OZ
            txt = f"[{item['mp']}]  {item['art']}  —  {item['name']}  ×{item['qty']}"
            li = QListWidgetItem(txt)
            li.setForeground(QColor(color))
            self.queue_list.addItem(li)
        self.queue_total.setText(f"{len(self.print_queue)} поз. · {total} эт." if self.print_queue else "Пусто")

    def _clear_queue(self):
        if not self.print_queue: return
        if QMessageBox.question(self, "Очистить", "Очистить всю очередь?",
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self.print_queue.clear(); self._refresh_queue_list()

    def _print_queue(self):
        if not self.print_queue:
            QMessageBox.information(self, "Очередь пуста", "Добавьте товары в очередь"); return
        try:
            tmpl = self._get_current_config()
            html = self._render_html(self.print_queue, tmpl)
            import tempfile, os, subprocess, sys
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html",
                                              mode="w", encoding="utf-8")
            tmp.write(html); tmp.close()
            # Windows: открываем через os.startfile (браузер по умолчанию)
            if sys.platform == "win32":
                os.startfile(tmp.name)
            else:
                import webbrowser
                webbrowser.open(f"file:///{tmp.name}")
            self.main_win.set_status("✓ Открыто в браузере — нажмите Ctrl+P для печати")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _render_html(self, queue, tmpl):
        """Генерирует HTML с этикетками для печати через браузер"""
        import base64, io
        w_mm = tmpl.get("width_mm", 58)
        h_mm = tmpl.get("height_mm", 40)
        bg   = tmpl.get("bg_color", "#ffffff")
        border = "1px solid #ccc" if tmpl.get("border", True) else "none"
        blocks = tmpl.get("blocks", [])

        def block_css(b):
            """Конвертирует блок в CSS+HTML"""
            if not b.get("visible", True): return ""
            btype = b["type"]
            x_pct = b.get("x", 0.05) * 100
            y_pct = b.get("y", 0.05) * 100
            color = b.get("color", "#000000")
            fs    = b.get("font_size", 9)
            bold  = "700" if b.get("bold") else "400"
            italic = "italic" if b.get("italic") else "normal"
            align = b.get("align", "left")
            font_map = {
                "serif":    "Georgia, serif",
                "mono":     "'Courier New', monospace",
                "sans":     "Arial, sans-serif",
                "vladimir": "'Vladimir Script', 'Brush Script MT', cursive",
            }
            font_family = font_map.get(b.get("font","sans"), "Arial, sans-serif")
            base_style = (f"position:absolute;left:{x_pct:.1f}%;top:{y_pct:.1f}%;"
                          f"color:{color};font-size:{fs}pt;font-weight:{bold};"
                          f"font-style:{italic};font-family:{font_family};"
                          f"text-align:{align};")
            return base_style

        labels_html = []
        for item in queue:
            for _ in range(item["qty"]):
                inner = ""
                for b in blocks:
                    if not b.get("visible", True): continue
                    btype = b["type"]
                    style = block_css(b)

                    if btype == "divider":
                        x_pct = b.get("x", 0.05) * 100
                        y_pct = b.get("y", 0.35) * 100
                        c = b.get("color","#cccccc")
                        inner += f'<div style="position:absolute;left:3%;top:{y_pct:.1f}%;width:94%;height:1px;background:{c};"></div>'

                    elif btype == "mp_badge":
                        mp = item.get("mp","")
                        if not mp: continue
                        bg_c = "#6a1b9a" if mp=="WB" else "#1565c0"
                        x_pct = b.get("x", 0.72) * 100
                        y_pct = b.get("y", 0.04) * 100
                        fs = b.get("font_size", 7)
                        inner += (f'<div style="position:absolute;left:{x_pct:.1f}%;top:{y_pct:.1f}%;'
                                  f'background:{bg_c};color:white;padding:1px 5px;border-radius:3px;'
                                  f'font-size:{fs}pt;font-weight:700;font-family:Arial;">{mp}</div>')

                    elif btype == "barcode":
                        bc = item.get("bc","")
                        if not bc: continue
                        try:
                            import barcode as bc_lib
                            from barcode.writer import ImageWriter
                            buf = io.BytesIO()
                            bc_obj = bc_lib.Code128(str(bc), writer=ImageWriter())
                            bc_obj.write(buf, options={
                                "module_width": 0.5, "module_height": 10.0,
                                "quiet_zone": 2.0, "write_text": False, "dpi": 300
                            })
                            b64 = base64.b64encode(buf.getvalue()).decode()
                            x_pct = b.get("x", 0.05) * 100
                            y_pct = b.get("y", 0.58) * 100
                            h_pct = b.get("height_ratio", 0.30) * 100
                            inner += (f'<img src="data:image/png;base64,{b64}" '
                                      f'style="position:absolute;left:{x_pct:.1f}%;top:{y_pct:.1f}%;'
                                      f'width:90%;height:{h_pct:.1f}%;" />')
                        except Exception:
                            pass

                    else:
                        text_map = {
                            "name":      item.get("name",""),
                            "art":       item.get("art",""),
                            "logo":      b.get("text","SharmGlow"),
                            "name2":     b.get("text",""),
                            "name3":     b.get("text",""),
                            "bc_number": item.get("bc",""),
                            "price":     "999 ₽",
                        }
                        text = text_map.get(btype, "")
                        if not text: continue
                        width_pct = (1.0 - b.get("x", 0.05)) * 90
                        inner += f'<div style="{style}width:{width_pct:.1f}%;overflow:hidden;white-space:nowrap;">{text}</div>'

                labels_html.append(
                    f'<div style="width:{w_mm}mm;height:{h_mm}mm;background:{bg};'
                    f'border:{border};position:relative;display:inline-block;'
                    f'overflow:hidden;margin:0;page-break-after:always;">'
                    f'{inner}</div>')

        all_labels = "\n".join(labels_html)
        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Этикетки — SharmGlow</title>
<style>
  @page {{ size: {w_mm}mm {h_mm}mm; margin: 0; }}
  body {{ margin: 0; padding: 0; background: #eee; }}
  @media print {{
    body {{ background: white; }}
    div {{ page-break-after: always; }}
  }}
</style>
</head><body>{all_labels}</body></html>"""

    # ── TEMPLATES ────────────────────────────────────────
    def _load_default_template(self):
        t = self.db.get_default_template()
        if t:
            self._apply_template(dict(t))
        self._refresh_template_combo()

    def _refresh_template_combo(self):
        self.tmpl_combo.blockSignals(True)
        self.tmpl_combo.clear()
        for t in self.db.get_templates():
            self.tmpl_combo.addItem(t["name"], t["id"])
        self.tmpl_combo.blockSignals(False)
        if self.cur_template:
            for i in range(self.tmpl_combo.count()):
                if self.tmpl_combo.itemData(i) == self.cur_template.get("id"):
                    self.tmpl_combo.setCurrentIndex(i); break

    def _on_template_change(self, idx):
        tid = self.tmpl_combo.itemData(idx)
        if not tid: return
        row = self.db.conn.execute("SELECT * FROM label_templates WHERE id=?", (tid,)).fetchone()
        if row: self._apply_template(dict(row))

    def _apply_template(self, t):
        self.cur_template = t
        cfg = json.loads(t["config"])
        self.d_width.setValue(cfg.get("width_mm", 58))
        self.d_height.setValue(cfg.get("height_mm", 40))
        self.d_border.setChecked(cfg.get("border", True))
        bg = cfg.get("bg_color","#ffffff")
        self.d_bg_btn.setStyleSheet(f"background:{bg};border:1px solid #ccc;border-radius:4px;")
        self.d_bg_btn.setProperty("color", bg)

        blocks_by_type = {b["type"]: b for b in cfg.get("blocks", [])}
        for bw in self.block_widgets:
            bw.load(blocks_by_type.get(bw.btype, {}))

        self.preview.set_template(cfg)

    def _get_current_config(self):
        cfg = {
            "width_mm":  self.d_width.value(),
            "height_mm": self.d_height.value(),
            "border":    self.d_border.isChecked(),
            "bg_color":  self.d_bg_btn.property("color") or "#ffffff",
            "blocks":    [bw.get_config() for bw in self.block_widgets]
        }
        return cfg

    def _on_designer_change(self):
        cfg = self._get_current_config()
        self.preview.set_template(cfg)

    def _save_template(self):
        cfg = self._get_current_config()
        tid = self.cur_template.get("id") if self.cur_template else None
        name = self.tmpl_combo.currentText() or "Шаблон"
        new_tid = self.db.save_template(tid, name, json.dumps(cfg, ensure_ascii=False))
        # Обновляем cur_template из БД
        row = self.db.conn.execute(
            "SELECT * FROM label_templates WHERE id=?", (new_tid,)
        ).fetchone()
        if row:
            self.cur_template = dict(row)
        self._refresh_template_combo()
        self.main_win.set_status("✓ Шаблон сохранён: " + name)

    def _new_template(self):
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Новый шаблон", "Название:")
        if not ok or not name: return
        default_cfg = self._get_current_config()
        tid = self.db.save_template(None, name, json.dumps(default_cfg))
        row = self.db.conn.execute("SELECT * FROM label_templates WHERE id=?", (tid,)).fetchone()
        self._apply_template(dict(row))
        self._refresh_template_combo()

    def _dup_template(self):
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Дублировать", "Название копии:")
        if not ok or not name: return
        cfg = self._get_current_config()
        tid = self.db.save_template(None, name, json.dumps(cfg))
        row = self.db.conn.execute("SELECT * FROM label_templates WHERE id=?", (tid,)).fetchone()
        self._apply_template(dict(row))
        self._refresh_template_combo()

    def _del_template(self):
        tid = self.tmpl_combo.currentData()
        if not tid: return
        if self.db.conn.execute("SELECT COUNT(*) FROM label_templates").fetchone()[0] <= 1:
            QMessageBox.warning(self, "Нельзя", "Нельзя удалить последний шаблон"); return
        if QMessageBox.question(self, "Удалить шаблон",
            f"Удалить шаблон «{self.tmpl_combo.currentText()}»?",
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self.db.delete_template(tid)
            self._refresh_template_combo()
            self._load_default_template()

    def _pick_color(self, target):
        cur = self.d_bg_btn.property("color") or "#ffffff"
        color = QColorDialog.getColor(QColor(cur), self, "Цвет фона")
        if color.isValid():
            hex_c = color.name()
            self.d_bg_btn.setStyleSheet(f"background:{hex_c};border:1px solid #ccc;border-radius:4px;")
            self.d_bg_btn.setProperty("color", hex_c)
            self._on_designer_change()

    def refresh(self):
        self._refresh_list()
        self._refresh_template_combo()


# ── BLOCK EDITOR ─────────────────────────────────────────
class BlockEditor(QFrame):
    changed = pyqtSignal()
    LABELS = {
        "mp_badge":  "🏷 Значок WB/OZON",
        "name":      "📝 Название товара",
        "name2":     "📝 Строка текста 2",
        "name3":     "📝 Строка текста 3",
        "divider":   "➖ Разделитель",
        "art":       "🔑 Артикул",
        "logo":      "✨ Логотип (текст)",
        "barcode":   "▊ Штрихкод",
        "bc_number": "# Цифры штрихкода",
        "price":     "💰 Цена",
    }

    def __init__(self, btype, label):
        super().__init__()
        self.btype = btype
        self.setStyleSheet(f"border:1px solid {BORDER};border-radius:6px;margin:2px;")
        v = QVBoxLayout(self); v.setContentsMargins(8,6,8,6); v.setSpacing(6)

        # Header row
        hr = QHBoxLayout()
        self.check = QCheckBox(self.LABELS.get(btype, label))
        self.check.setChecked(True)
        self.check.stateChanged.connect(self._toggle_body)
        self.check.stateChanged.connect(lambda: self.changed.emit())
        hr.addWidget(self.check, 1)
        v.addLayout(hr)

        # Body (collapsible)
        self.body = QWidget()
        bv = QHBoxLayout(self.body); bv.setContentsMargins(4,0,4,0); bv.setSpacing(8)

        def spin(min_v, max_v, val, suffix="", decimals=0):
            if decimals:
                s = QDoubleSpinBox(); s.setDecimals(decimals)
            else:
                s = QSpinBox()
            s.setRange(min_v, max_v); s.setValue(val)
            if suffix: s.setSuffix(suffix)
            s.setFixedWidth(72); s.valueChanged.connect(lambda: self.changed.emit())
            return s

        bv.addWidget(QLabel("X:")); self.f_x = spin(0,100,5,"%",1); bv.addWidget(self.f_x)
        bv.addWidget(QLabel("Y:")); self.f_y = spin(0,100,5,"%",1); bv.addWidget(self.f_y)

        self.f_fs = None
        self.f_bold = None
        self.f_italic = None
        self.f_color_btn = None
        self.f_align = None
        self.f_font = None

        if btype not in ("divider", "barcode"):
            bv.addWidget(QLabel("Размер:"))
            self.f_fs = spin(4,36,9," pt")
            bv.addWidget(self.f_fs)
            self.f_bold = QCheckBox("Жирный"); self.f_bold.stateChanged.connect(lambda: self.changed.emit())
            self.f_italic = QCheckBox("Курсив"); self.f_italic.stateChanged.connect(lambda: self.changed.emit())
            bv.addWidget(self.f_bold); bv.addWidget(self.f_italic)

        if btype in ("name","name2","name3","art","logo","bc_number","price"):
            self.f_align = QComboBox(); self.f_align.addItems(["left","center","right"])
            self.f_align.setFixedWidth(76)
            self.f_align.currentIndexChanged.connect(lambda: self.changed.emit())
            bv.addWidget(QLabel("Выровн.:")); bv.addWidget(self.f_align)

        if btype in ("art","logo","name2","name3"):
            self.f_font = QComboBox()
            self.f_font.addItems(["sans","serif","mono","vladimir"])
            self.f_font.setFixedWidth(90)
            self.f_font.currentIndexChanged.connect(lambda: self.changed.emit())
            bv.addWidget(QLabel("Шрифт:")); bv.addWidget(self.f_font)

        if btype in ("logo","name2","name3"):
            default_text = "SharmGlow" if btype == "logo" else ""
            bv.addWidget(QLabel("Текст:"))
            self.f_logo_text = QLineEdit(default_text); self.f_logo_text.setFixedWidth(120)
            self.f_logo_text.setPlaceholderText("Введите текст…")
            self.f_logo_text.textChanged.connect(lambda: self.changed.emit())
            bv.addWidget(self.f_logo_text)
        else:
            self.f_logo_text = None

        if btype == "barcode":
            bv.addWidget(QLabel("Высота%:"))
            self.f_bc_h = spin(10,80,30,"%")
            bv.addWidget(self.f_bc_h)
        else:
            self.f_bc_h = None

        # Color picker
        self.f_color_btn = QPushButton("  ")
        self.f_color_btn.setFixedSize(28,22)
        self.f_color_btn.setStyleSheet("background:#000000;border:1px solid #ccc;border-radius:3px;")
        self.f_color_btn.setProperty("color","#000000")
        self.f_color_btn.clicked.connect(self._pick_color)
        bv.addWidget(QLabel("Цвет:")); bv.addWidget(self.f_color_btn)

        bv.addStretch()
        v.addWidget(self.body)

    def _toggle_body(self, state):
        self.body.setVisible(bool(state))

    def _pick_color(self):
        cur = self.f_color_btn.property("color") or "#000000"
        c = QColorDialog.getColor(QColor(cur), self, "Цвет текста")
        if c.isValid():
            self.f_color_btn.setStyleSheet(f"background:{c.name()};border:1px solid #ccc;border-radius:3px;")
            self.f_color_btn.setProperty("color", c.name())
            self.changed.emit()

    def load(self, cfg):
        self.check.setChecked(cfg.get("visible", True))
        self.body.setVisible(cfg.get("visible", True))
        if self.f_x: self.f_x.setValue(cfg.get("x", 0.05) * 100)
        if self.f_y: self.f_y.setValue(cfg.get("y", 0.05) * 100)
        if self.f_fs:    self.f_fs.setValue(cfg.get("font_size", 9))
        if self.f_bold:  self.f_bold.setChecked(cfg.get("bold", False))
        if self.f_italic:self.f_italic.setChecked(cfg.get("italic", False))
        if self.f_align: self.f_align.setCurrentText(cfg.get("align","left"))
        if self.f_font:  self.f_font.setCurrentText(cfg.get("font","sans"))
        if self.f_bc_h:  self.f_bc_h.setValue(int(cfg.get("height_ratio",0.3)*100))
        if self.f_logo_text and "text" in cfg: self.f_logo_text.setText(cfg["text"])
        color = cfg.get("color","#000000")
        if self.f_color_btn:
            self.f_color_btn.setStyleSheet(f"background:{color};border:1px solid #ccc;border-radius:3px;")
            self.f_color_btn.setProperty("color", color)

    def get_config(self):
        cfg = {
            "type":    self.btype,
            "visible": self.check.isChecked(),
            "x":       (self.f_x.value() if self.f_x else 5) / 100,
            "y":       (self.f_y.value() if self.f_y else 5) / 100,
            "color":   self.f_color_btn.property("color") or "#000000",
        }
        if self.f_fs:     cfg["font_size"]    = self.f_fs.value()
        if self.f_bold:   cfg["bold"]         = self.f_bold.isChecked()
        if self.f_italic: cfg["italic"]       = self.f_italic.isChecked()
        if self.f_align:  cfg["align"]        = self.f_align.currentText()
        if self.f_font:   cfg["font"]         = self.f_font.currentText()
        if self.f_bc_h:   cfg["height_ratio"] = self.f_bc_h.value() / 100
        if self.f_logo_text: cfg["text"]      = self.f_logo_text.text()
        return cfg


# ── LABEL PREVIEW WIDGET ──────────────────────────────────
class LabelPreview(QWidget):
    SCALE = 4.5  # preview scale factor

    def __init__(self):
        super().__init__()
        self._tmpl = {}
        self._name = "Кольцо вольфрам 6мм р.16"
        self._art  = "К001"
        self._bc   = "2049405646001"
        self._mp   = "WB"
        self._update_size()

    def _update_size(self):
        w = self._tmpl.get("width_mm",  58)
        h = self._tmpl.get("height_mm", 40)
        self.setFixedSize(int(w * MM_TO_PX * self.SCALE),
                          int(h * MM_TO_PX * self.SCALE))

    def set_template(self, cfg):
        self._tmpl = cfg
        self._update_size()
        self.update()

    def set_data(self, name, art, bc, mp):
        self._name = name; self._art = art; self._bc = bc or ""; self._mp = mp
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        W = self.width(); H = self.height()
        cfg = self._tmpl

        # Background
        bg = QColor(cfg.get("bg_color","#ffffff"))
        p.fillRect(0, 0, W, H, QBrush(bg))

        # Border
        if cfg.get("border", True):
            p.setPen(QPen(QColor("#c0c0c0"), 1))
            p.drawRect(0, 0, W-1, H-1)

        # Draw blocks
        for block in cfg.get("blocks", []):
            if not block.get("visible", True): continue
            self._draw_block(p, block, W, H)

        p.end()

    def _draw_block(self, p, block, W, H):
        btype   = block["type"]
        x_rel   = block.get("x", 0.05)
        y_rel   = block.get("y", 0.05)
        x = int(x_rel * W)
        y = int(y_rel * H)
        color   = QColor(block.get("color","#000000"))
        fs      = block.get("font_size", 9)
        bold    = block.get("bold", False)
        italic  = block.get("italic", False)
        align   = block.get("align","left")
        font_family = {
            "serif":    "Georgia,serif",
            "mono":     "Courier New",
            "sans":     "Arial",
            "vladimir": "Vladimir Script,Brush Script MT,cursive"
        }.get(block.get("font","sans"),"Arial")

        if btype == "divider":
            p.setPen(QPen(QColor(block.get("color","#cccccc")), 1))
            p.drawLine(int(0.03*W), y, int(0.97*W), y)

        elif btype == "barcode":
            bc = self._bc
            if bc:
                try:
                    import io
                    from barcode import Code128
                    from barcode.writer import SVGWriter, ImageWriter
                    # Use ImageWriter to get pixel data
                    buf = io.BytesIO()
                    bc_obj = Code128(bc, writer=ImageWriter())
                    bc_obj.write(buf, options={
                        "module_width": 0.5, "module_height": 8.0,
                        "quiet_zone": 2.0, "write_text": False,
                        "dpi": 200
                    })
                    buf.seek(0)
                    img = QImage.fromData(buf.read())
                    if not img.isNull():
                        bh = int(block.get("height_ratio", 0.30) * H)
                        bw = int(0.90 * W)
                        bx = int(0.05 * W)
                        scaled = img.scaled(bw, bh,
                            Qt.AspectRatioMode.IgnoreAspectRatio,
                            Qt.TransformationMode.SmoothTransformation)
                        p.drawImage(bx, y, scaled)
                except Exception:
                    # Fallback: draw placeholder bars
                    p.setPen(QPen(QColor("#333"), 1))
                    bh = int(block.get("height_ratio", 0.30) * H)
                    bx = int(0.05*W); bw = int(0.90*W)
                    bar_w = max(1, bw // 60)
                    for i in range(0, bw, bar_w*2):
                        p.fillRect(bx+i, y, bar_w, bh, QBrush(QColor("#222")))

        elif btype == "mp_badge":
            mp = self._mp
            if mp:
                bg_c = QColor(WB if mp=="WB" else OZ)
                fs_b = max(6, fs)
                font = QFont("Arial", fs_b); font.setBold(True)
                p.setFont(font)
                fm = QFontMetrics(font)
                txt_w = fm.horizontalAdvance(mp) + 8
                txt_h = fm.height() + 4
                bx = int(x_rel * W)
                p.fillRect(bx, int(y_rel*H), txt_w, txt_h, QBrush(bg_c))
                p.setPen(QPen(QColor("#ffffff")))
                p.drawText(bx+4, int(y_rel*H) + txt_h - 4, mp)

        else:
            # Text blocks
            text_map = {
                "name":      self._name,
                "art":       self._art,
                "logo":      block.get("text", "SharmGlow"),
                "name2":     block.get("text", ""),
                "name3":     block.get("text", ""),
                "bc_number": self._bc,
                "price":     "999 ₽",
            }
            text = text_map.get(btype, "")
            if not text: return

            font = QFont(font_family, fs)
            font.setBold(bold); font.setItalic(italic)
            p.setFont(font); p.setPen(QPen(color))
            fm = QFontMetrics(font)

            avail_w = int(0.90*W - x)
            max_lines = block.get("max_lines", 1)

            if btype == "name" and max_lines > 1:
                words = text.split()
                lines, cur = [], ""
                for w in words:
                    test = (cur + " " + w).strip()
                    if fm.horizontalAdvance(test) <= avail_w:
                        cur = test
                    else:
                        if cur: lines.append(cur)
                        cur = w
                if cur: lines.append(cur)
                lines = lines[:max_lines]
                for li, line in enumerate(lines):
                    ty = y + li * (fm.height() + 1)
                    if align == "center":
                        tx = (W - fm.horizontalAdvance(line)) // 2
                    elif align == "right":
                        tx = W - fm.horizontalAdvance(line) - int(0.05*W)
                    else:
                        tx = x
                    p.drawText(tx, ty + fm.ascent(), line)
            else:
                elided = fm.elidedText(text, Qt.TextElideMode.ElideRight, avail_w)
                if align == "center":
                    tx = (W - fm.horizontalAdvance(elided)) // 2
                elif align == "right":
                    tx = W - fm.horizontalAdvance(elided) - int(0.05*W)
                else:
                    tx = x
                p.drawText(tx, y + fm.ascent(), elided)
