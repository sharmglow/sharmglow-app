"""ui/tab_sync.py — Маркетплейсы: остатки, импорт товаров, продажи, аналитика"""
import json, threading
from datetime import date, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QGroupBox, QMessageBox, QSplitter, QTextEdit,
    QCheckBox, QScrollArea, QTabWidget, QSpinBox, QComboBox,
    QDateEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QDate
from PyQt6.QtGui import QColor, QFont
from ui.styles import *


class SyncSignals(QObject):
    log        = pyqtSignal(str, str)
    done       = pyqtSignal(str)
    progress   = pyqtSignal(str)
    table_data = pyqtSignal(str, list)   # (table_id, rows)
    msg_box    = pyqtSignal(str, str)    # (title, text)


class SyncTab(QWidget):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.main_win = parent
        self.sig = SyncSignals()
        self.sig.log.connect(self._append_log)
        self.sig.done.connect(self._on_done)
        self.sig.progress.connect(lambda m: self.main_win.set_status(m))
        self.sig.table_data.connect(self._fill_table)
        self.sig.msg_box.connect(lambda t, m: QMessageBox.information(self, t, m))
        self._build()
        self._load_settings()

    # ══════════════════════════════════════════════════════
    #  BUILD UI
    # ══════════════════════════════════════════════════════
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── LEFT: settings panel ───────────────────────────
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setMaximumWidth(360)
        left_scroll.setStyleSheet(f"background:white;border:none;border-right:1px solid {BORDER};")
        lw = QWidget(); lw.setStyleSheet("background:white;")
        lv = QVBoxLayout(lw); lv.setContentsMargins(16,16,16,16); lv.setSpacing(14)

        # WB
        wb_box = QGroupBox("Wildberries API")
        wb_box.setStyleSheet(f"QGroupBox{{font-weight:700;color:#6a1b9a;border:1px solid rgba(106,27,154,.3);border-radius:6px;margin-top:8px;padding-top:8px;}}")
        wbv = QVBoxLayout(wb_box)
        wbv.addWidget(QLabel("API Token:"))
        self.wb_token = QLineEdit(); self.wb_token.setPlaceholderText("eyJhbGciOi...")
        self.wb_token.setEchoMode(QLineEdit.EchoMode.Password)
        wbv.addWidget(self.wb_token)
        cb_wb = QCheckBox("Показать"); cb_wb.stateChanged.connect(
            lambda s: self.wb_token.setEchoMode(QLineEdit.EchoMode.Normal if s else QLineEdit.EchoMode.Password))
        wbv.addWidget(cb_wb)
        wbv.addWidget(QLabel("ID склада FBS:"))
        self.wb_wh_id = QLineEdit(); self.wb_wh_id.setPlaceholderText("12345")
        wbv.addWidget(self.wb_wh_id)
        note = QLabel("Токен: ЛК WB → Настройки → Доступ к API\nID: ЛК WB → Склады → FBS")
        note.setStyleSheet(f"font-size:11px;color:{MUTED};"); note.setWordWrap(True)
        wbv.addWidget(note)
        lv.addWidget(wb_box)

        # OZON
        oz_box = QGroupBox("OZON API")
        oz_box.setStyleSheet(f"QGroupBox{{font-weight:700;color:#1565c0;border:1px solid rgba(21,101,192,.3);border-radius:6px;margin-top:8px;padding-top:8px;}}")
        ozv = QVBoxLayout(oz_box)
        ozv.addWidget(QLabel("Client-ID:"))
        self.oz_client = QLineEdit(); self.oz_client.setPlaceholderText("123456")
        ozv.addWidget(self.oz_client)
        ozv.addWidget(QLabel("API-Key:"))
        self.oz_key = QLineEdit(); self.oz_key.setPlaceholderText("xxxxxxxx-xxxx-...")
        self.oz_key.setEchoMode(QLineEdit.EchoMode.Password)
        ozv.addWidget(self.oz_key)
        cb_oz = QCheckBox("Показать"); cb_oz.stateChanged.connect(
            lambda s: self.oz_key.setEchoMode(QLineEdit.EchoMode.Normal if s else QLineEdit.EchoMode.Password))
        ozv.addWidget(cb_oz)
        note2 = QLabel("ЛК OZON → Настройки → API ключи")
        note2.setStyleSheet(f"font-size:11px;color:{MUTED};")
        ozv.addWidget(note2)
        lv.addWidget(oz_box)

        btn_save = QPushButton("💾 Сохранить настройки")
        btn_save.setObjectName("primary"); btn_save.setFixedHeight(34)
        btn_save.clicked.connect(self._save_settings)
        lv.addWidget(btn_save)

        # Warehouse import
        wh_box = QGroupBox("Склады маркетплейсов")
        wh_box.setStyleSheet(f"QGroupBox{{font-weight:600;color:#555;border:1px solid {BORDER};border-radius:6px;margin-top:4px;padding-top:8px;}}")
        whv = QVBoxLayout(wh_box)
        wh_note = QLabel("Загрузить склады WB и OZON и сразу добавить в базу:")
        wh_note.setStyleSheet(f"font-size:11px;color:{MUTED};"); wh_note.setWordWrap(True)
        whv.addWidget(wh_note)
        wh_btns = QHBoxLayout()
        self.btn_wh_wb   = QPushButton("📦 Склады WB")
        self.btn_wh_ozon = QPushButton("📦 Склады OZON")
        self.btn_wh_all  = QPushButton("📦 WB + OZON")
        self.btn_wh_wb.setFixedHeight(30)
        self.btn_wh_ozon.setFixedHeight(30)
        self.btn_wh_all.setFixedHeight(30)
        self.btn_wh_wb.setStyleSheet("background:#f3e5f5;color:#6a1b9a;border:1px solid #6a1b9a;border-radius:4px;font-weight:600;")
        self.btn_wh_ozon.setStyleSheet("background:#e3f2fd;color:#1565c0;border:1px solid #1565c0;border-radius:4px;font-weight:600;")
        self.btn_wh_all.setStyleSheet(f"background:{GOLD_L};color:{INK};border:none;border-radius:4px;font-weight:700;")
        self.btn_wh_wb.clicked.connect(lambda: self._run(self._import_warehouses_wb))
        self.btn_wh_ozon.clicked.connect(lambda: self._run(self._import_warehouses_ozon))
        self.btn_wh_all.clicked.connect(lambda: self._run(self._import_warehouses_all))
        wh_btns.addWidget(self.btn_wh_wb)
        wh_btns.addWidget(self.btn_wh_ozon)
        wh_btns.addWidget(self.btn_wh_all)
        whv.addLayout(wh_btns)
        lv.addWidget(wh_box)

        # Log
        log_lbl = QLabel("Лог:"); log_lbl.setStyleSheet(f"color:{MUTED};font-size:11px;margin-top:8px;")
        lv.addWidget(log_lbl)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMinimumHeight(200)
        self.log_view.setStyleSheet(f"""
            QTextEdit{{background:{INK};color:#aaa;font-family:'Courier New',monospace;
            font-size:11px;border:none;border-radius:4px;padding:6px;}}
        """)
        lv.addWidget(self.log_view, 1)
        lv.addStretch()

        left_scroll.setWidget(lw)
        splitter.addWidget(left_scroll)

        # ── RIGHT: inner tabs ──────────────────────────────
        right = QWidget()
        rv = QVBoxLayout(right); rv.setContentsMargins(0,0,0,0); rv.setSpacing(0)

        inner_tabs = QTabWidget()
        inner_tabs.setDocumentMode(True)

        # Tab 1: Остатки (своя база vs МП)
        inner_tabs.addTab(self._build_stocks_tab(), "📊 Остатки")
        # Tab 2: Склады МП — остатки по складам и SKU
        inner_tabs.addTab(self._build_wh_stocks_tab(), "🏭 Склады МП")
        # Tab 3: Импорт товаров
        inner_tabs.addTab(self._build_import_tab(), "📥 Импорт товаров")
        # Tab 4: Продажи / Аналитика
        inner_tabs.addTab(self._build_analytics_tab(), "📈 Продажи & Аналитика")

        rv.addWidget(inner_tabs)
        splitter.addWidget(right)
        splitter.setSizes([355, 950])
        root.addWidget(splitter)

    # ── Tab: Склады МП ─────────────────────────────────────
    def _build_wh_stocks_tab(self):
        w = QWidget()
        v = QVBoxLayout(w); v.setContentsMargins(0,0,0,0); v.setSpacing(0)

        tb = QFrame(); tb.setFixedHeight(46)
        tb.setStyleSheet(f"background:white;border-bottom:1px solid {BORDER};")
        hl = QHBoxLayout(tb); hl.setContentsMargins(12,0,12,0); hl.setSpacing(8)

        self.btn_whs_wb   = self._mp_btn("↓ Остатки по складам WB",   "wb")
        self.btn_whs_ozon = self._mp_btn("↓ Остатки по складам OZON", "ozon")
        self.btn_whs_all  = QPushButton("↓ WB + OZON")
        self.btn_whs_all.setFixedHeight(30); self.btn_whs_all.setObjectName("primary")

        # Фильтр по SKU
        self.whs_filter = QLineEdit(); self.whs_filter.setPlaceholderText("Фильтр по артикулу/SKU…")
        self.whs_filter.setFixedWidth(180); self.whs_filter.setFixedHeight(30)
        self.whs_filter.textChanged.connect(self._filter_wh_stocks)

        self.btn_whs_wb.clicked.connect(lambda: self._run(self._pull_wh_stocks_wb))
        self.btn_whs_ozon.clicked.connect(lambda: self._run(self._pull_wh_stocks_ozon))
        self.btn_whs_all.clicked.connect(lambda: self._run(self._pull_wh_stocks_all))

        for w2 in [self.btn_whs_wb, self.btn_whs_ozon, self.btn_whs_all]:
            hl.addWidget(w2)
        hl.addStretch()
        hl.addWidget(QLabel("🔍")); hl.addWidget(self.whs_filter)
        v.addWidget(tb)

        info = QLabel(
            "  Остатки по каждому складу маркетплейса с разбивкой по SKU. "
            "WB: FBO (склады WB) + FBS (ваши склады). OZON: FBO + FBS."
        )
        info.setStyleSheet(f"font-size:12px;color:{MUTED};padding:6px 12px;background:#fffef8;border-bottom:1px solid {BORDER};")
        info.setWordWrap(True)
        v.addWidget(info)

        self.wh_stocks_table = QTableWidget(0, 6)
        self.wh_stocks_table.setHorizontalHeaderLabels([
            "Маркетплейс", "Склад", "SKU / Артикул", "Наименование", "Кол-во", "Тип"
        ])
        self.wh_stocks_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.wh_stocks_table.verticalHeader().setVisible(False)
        self.wh_stocks_table.verticalHeader().setDefaultSectionSize(34)
        self.wh_stocks_table.setAlternatingRowColors(True)
        self.wh_stocks_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.wh_stocks_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.wh_stocks_table.setSortingEnabled(True)
        v.addWidget(self.wh_stocks_table)

        # Итоговая строка
        self.whs_summary = QLabel("")
        self.whs_summary.setStyleSheet(f"font-size:12px;color:{MUTED};padding:6px 12px;border-top:1px solid {BORDER};background:white;")
        v.addWidget(self.whs_summary)

        self._wh_stocks_all_rows = []   # кэш для фильтра
        return w

    # ── Tab: Остатки ───────────────────────────────────────
    def _build_stocks_tab(self):
        w = QWidget()
        v = QVBoxLayout(w); v.setContentsMargins(0,0,0,0); v.setSpacing(0)

        tb = QFrame(); tb.setFixedHeight(46)
        tb.setStyleSheet(f"background:white;border-bottom:1px solid {BORDER};")
        hl = QHBoxLayout(tb); hl.setContentsMargins(12,0,12,0); hl.setSpacing(8)

        self.btn_pull_wb   = self._mp_btn("↓ Остатки WB",   "wb")
        self.btn_pull_ozon = self._mp_btn("↓ Остатки OZON", "ozon")
        self.btn_push_wb   = self._mp_btn("↑ Обновить FBS WB",   "wb_push")
        self.btn_push_ozon = self._mp_btn("↑ Обновить FBS OZON", "ozon_push")
        self.btn_sync_all  = QPushButton("↕ Всё сразу"); self.btn_sync_all.setFixedHeight(30)
        self.btn_sync_all.setObjectName("primary")

        self.btn_pull_wb.clicked.connect(lambda: self._run(self._pull_wb))
        self.btn_pull_ozon.clicked.connect(lambda: self._run(self._pull_ozon))
        self.btn_push_wb.clicked.connect(lambda: self._confirm_push("WB"))
        self.btn_push_ozon.clicked.connect(lambda: self._confirm_push("OZON"))
        self.btn_sync_all.clicked.connect(lambda: self._run(self._sync_all))

        for btn in [self.btn_pull_wb, self.btn_pull_ozon, self.btn_push_wb,
                    self.btn_push_ozon, self.btn_sync_all]:
            hl.addWidget(btn)
        hl.addStretch()
        v.addWidget(tb)

        self.stocks_table = self._make_table(
            ["Артикул","Наименование","В базе","На WB","На OZON","Расхождение"],
            stretch_col=1
        )
        v.addWidget(self.stocks_table)
        return w

    # ── Tab: Импорт товаров ────────────────────────────────
    def _build_import_tab(self):
        w = QWidget()
        v = QVBoxLayout(w); v.setContentsMargins(0,0,0,0); v.setSpacing(0)

        tb = QFrame(); tb.setFixedHeight(46)
        tb.setStyleSheet(f"background:white;border-bottom:1px solid {BORDER};")
        hl = QHBoxLayout(tb); hl.setContentsMargins(12,0,12,0); hl.setSpacing(8)

        self.btn_imp_wb   = self._mp_btn("↓ Товары с WB",   "wb")
        self.btn_imp_ozon = self._mp_btn("↓ Товары с OZON", "ozon")
        self.btn_imp_all  = QPushButton("↓ WB + OZON"); self.btn_imp_all.setFixedHeight(30)
        self.btn_imp_all.setObjectName("primary")

        self.cb_skip_existing = QCheckBox("Не обновлять существующие")
        self.cb_skip_existing.setChecked(True)

        self.btn_imp_wb.clicked.connect(lambda: self._run(self._import_wb))
        self.btn_imp_ozon.clicked.connect(lambda: self._run(self._import_ozon))
        self.btn_imp_all.clicked.connect(lambda: self._run(self._import_all))

        for w2 in [self.btn_imp_wb, self.btn_imp_ozon, self.btn_imp_all, self.cb_skip_existing]:
            hl.addWidget(w2)
        hl.addStretch()
        v.addWidget(tb)

        info = QLabel(
            "  Импортирует товары из WB/OZON в базу: артикул, название, штрихкоды WB и OZON. "
            "Уже существующие товары обновит штрихкодами если они пустые."
        )
        info.setStyleSheet(f"font-size:12px;color:{MUTED};padding:8px 12px;background:#fffef8;border-bottom:1px solid {BORDER};")
        info.setWordWrap(True)
        v.addWidget(info)

        self.import_table = self._make_table(
            ["Артикул","Наименование","Штрихкод WB","Штрихкод OZON","Категория","Статус"],
            stretch_col=1
        )
        v.addWidget(self.import_table)
        return v.parentWidget() if False else w

    # ── Tab: Продажи & Аналитика ───────────────────────────
    def _build_analytics_tab(self):
        w = QWidget()
        v = QVBoxLayout(w); v.setContentsMargins(0,0,0,0); v.setSpacing(0)

        tb = QFrame(); tb.setFixedHeight(46)
        tb.setStyleSheet(f"background:white;border-bottom:1px solid {BORDER};")
        hl = QHBoxLayout(tb); hl.setContentsMargins(12,0,12,0); hl.setSpacing(8)

        hl.addWidget(QLabel("Период:"))
        self.date_from = QDateEdit(QDate.currentDate().addDays(-30))
        self.date_from.setCalendarPopup(True); self.date_from.setFixedWidth(110)
        self.date_to   = QDateEdit(QDate.currentDate())
        self.date_to.setCalendarPopup(True); self.date_to.setFixedWidth(110)
        hl.addWidget(self.date_from)
        hl.addWidget(QLabel("—"))
        hl.addWidget(self.date_to)

        self.btn_sales_wb   = self._mp_btn("↓ Продажи WB",   "wb")
        self.btn_sales_ozon = self._mp_btn("↓ Продажи OZON", "ozon")
        self.btn_sales_all  = QPushButton("↓ WB + OZON"); self.btn_sales_all.setFixedHeight(30)
        self.btn_sales_all.setObjectName("primary")
        self.btn_writeoff   = QPushButton("✂ Списать продажи со склада")
        self.btn_writeoff.setFixedHeight(30)
        self.btn_writeoff.setStyleSheet(f"background:#fff3e0;color:#e65100;border:1px solid #e65100;border-radius:4px;font-weight:600;padding:0 10px;")

        self.btn_sales_wb.clicked.connect(lambda: self._run(self._pull_sales_wb))
        self.btn_sales_ozon.clicked.connect(lambda: self._run(self._pull_sales_ozon))
        self.btn_sales_all.clicked.connect(lambda: self._run(self._pull_sales_all))
        self.btn_writeoff.clicked.connect(self._confirm_writeoff)

        for w2 in [self.btn_sales_wb, self.btn_sales_ozon, self.btn_sales_all, self.btn_writeoff]:
            hl.addWidget(w2)
        hl.addStretch()
        v.addWidget(tb)

        self.analytics_table = self._make_table(
            ["Артикул","Наименование","Продано WB","Продано OZON","Итого продано","Остаток","Хватит дней"],
            stretch_col=1
        )
        v.addWidget(self.analytics_table)

        # Храним загруженные продажи для списания
        self._last_sales = {}
        return w

    # ── HELPERS ────────────────────────────────────────────
    def _mp_btn(self, text, kind):
        btn = QPushButton(text); btn.setFixedHeight(30)
        if kind == "wb":
            btn.setStyleSheet("background:#f3e5f5;color:#6a1b9a;border:1px solid #6a1b9a;border-radius:4px;font-weight:600;padding:0 10px;")
        elif kind == "ozon":
            btn.setStyleSheet("background:#e3f2fd;color:#1565c0;border:1px solid #1565c0;border-radius:4px;font-weight:600;padding:0 10px;")
        elif kind == "wb_push":
            btn.setStyleSheet("background:#ede7f6;color:#4527a0;border:1px solid #4527a0;border-radius:4px;font-weight:600;padding:0 10px;")
        elif kind == "ozon_push":
            btn.setStyleSheet("background:#e1f5fe;color:#01579b;border:1px solid #01579b;border-radius:4px;font-weight:600;padding:0 10px;")
        return btn

    def _make_table(self, headers, stretch_col=1):
        t = QTableWidget(0, len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.horizontalHeader().setSectionResizeMode(stretch_col, QHeaderView.ResizeMode.Stretch)
        t.verticalHeader().setVisible(False)
        t.verticalHeader().setDefaultSectionSize(36)
        t.setAlternatingRowColors(True)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        return t

    def _all_action_buttons(self):
        return [
            self.btn_pull_wb, self.btn_pull_ozon, self.btn_push_wb,
            self.btn_push_ozon, self.btn_sync_all,
            self.btn_imp_wb, self.btn_imp_ozon, self.btn_imp_all,
            self.btn_sales_wb, self.btn_sales_ozon, self.btn_sales_all,
            self.btn_writeoff,
            self.btn_wh_wb, self.btn_wh_ozon, self.btn_wh_all,
            self.btn_whs_wb, self.btn_whs_ozon, self.btn_whs_all,
        ]

    # ══════════════════════════════════════════════════════
    #  SETTINGS
    # ══════════════════════════════════════════════════════
    def _save_settings(self):
        s = {"wb_token": self.wb_token.text().strip(),
             "wb_wh_id": self.wb_wh_id.text().strip(),
             "oz_client": self.oz_client.text().strip(),
             "oz_key":    self.oz_key.text().strip()}
        self.db.set_setting("mp_sync", json.dumps(s))
        self.main_win.set_status("✓ Настройки API сохранены")
        self._log("Настройки сохранены", "ok")

    def _load_settings(self):
        raw = self.db.get_setting("mp_sync")
        if not raw: return
        try:
            s = json.loads(raw)
            self.wb_token.setText(s.get("wb_token",""))
            self.wb_wh_id.setText(s.get("wb_wh_id",""))
            self.oz_client.setText(s.get("oz_client",""))
            self.oz_key.setText(s.get("oz_key",""))
        except Exception: pass

    def _wb_token_val(self):
        t = self.wb_token.text().strip()
        if not t: self._log("Не задан токен WB", "error")
        return t

    def _oz_creds(self):
        c, k = self.oz_client.text().strip(), self.oz_key.text().strip()
        if not c or not k: self._log("Не заданы ключи OZON", "error")
        return (c, k) if c and k else (None, None)

    # ══════════════════════════════════════════════════════
    #  LOG / ASYNC
    # ══════════════════════════════════════════════════════
    def _log(self, msg, level="info"):
        self.sig.log.emit(msg, level)

    def _append_log(self, msg, level):
        from datetime import datetime
        colors = {"info":"#aaa","ok":"#81c784","warn":"#ffb74d","error":"#e57373"}
        icons  = {"info":"·","ok":"✓","warn":"⚠","error":"✕"}
        t = datetime.now().strftime("%H:%M:%S")
        self.log_view.append(
            f'<span style="color:#555;">[{t}]</span> '
            f'<span style="color:{colors.get(level,"#aaa")};">{icons.get(level,"·")} {msg}</span>')
        sb = self.log_view.verticalScrollBar(); sb.setValue(sb.maximum())

    def _on_done(self, msg):
        for btn in self._all_action_buttons(): btn.setEnabled(True)
        self.main_win.set_status(msg)

    def _run(self, fn):
        for btn in self._all_action_buttons(): btn.setEnabled(False)
        self.log_view.clear()
        threading.Thread(target=self._safe_run, args=(fn,), daemon=True).start()

    def _safe_run(self, fn):
        try: fn()
        except Exception as e:
            self.sig.log.emit(f"Ошибка: {e}", "error")
            self.sig.done.emit(f"❌ {e}")

    def _fill_table(self, table_id, rows):
        tables = {
            "stocks":    (self.stocks_table,    ["art","name","local","wb","ozon","diff"]),
            "import":    (self.import_table,    ["art","name","bc_wb","bc_ozon","cat","status"]),
            "analytics": (self.analytics_table, ["art","name","sold_wb","sold_ozon","sold_total","stock","days"]),
        }
        if table_id not in tables: return
        tbl, _ = tables[table_id]
        tbl.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, val in enumerate(row):
                item = QTableWidgetItem(str(val) if val is not None else "—")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter if j != 1 else Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                # Color hints
                if table_id == "stocks" and j == 5 and str(val) != "—":
                    item.setForeground(QColor(DANGER)); item.setBackground(QColor("#fff3f3"))
                if table_id == "stocks" and j == 3 and val not in (None,"—"):
                    item.setForeground(QColor("#6a1b9a"))
                if table_id == "stocks" and j == 4 and val not in (None,"—"):
                    item.setForeground(QColor("#1565c0"))
                if table_id == "import" and j == 5:
                    if str(val) == "Добавлен":    item.setForeground(QColor(OK))
                    elif str(val) == "Обновлён":  item.setForeground(QColor("#f9a825"))
                    elif str(val) == "Пропущен":  item.setForeground(QColor(MUTED))
                if table_id == "analytics" and j == 6:
                    try:
                        d = int(val)
                        if d <= 7:   item.setForeground(QColor(DANGER))
                        elif d <= 14: item.setForeground(QColor("#f9a825"))
                        else:         item.setForeground(QColor(OK))
                    except: pass
                tbl.setItem(i, j, item)
        tbl.resizeColumnsToContents(); tbl.setColumnWidth(1, 260)

    # ══════════════════════════════════════════════════════
    #  HTTP HELPERS
    # ══════════════════════════════════════════════════════
    def _wb_get(self, path, token, params=""):
        import urllib.request, urllib.error
        url = f"https://statistics-api.wildberries.ru{path}{params}"
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            raise Exception(f"WB {e.code}: {e.read().decode()[:200]}")

    def _wb_post(self, path, token, body, base="https://marketplace-api.wildberries.ru"):
        import urllib.request, urllib.error
        data = json.dumps(body).encode()
        req  = urllib.request.Request(f"{base}{path}", data=data,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            method="PUT" if "stocks" in path else "POST")
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read().decode()) if r.length else {}
        except urllib.error.HTTPError as e:
            raise Exception(f"WB {e.code}: {e.read().decode()[:200]}")

    def _wb_content(self, path, token, body):
        """WB Content API (товары)"""
        import urllib.request, urllib.error
        data = json.dumps(body).encode()
        req  = urllib.request.Request(
            f"https://content-api.wildberries.ru{path}", data=data,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            method="POST")
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            raise Exception(f"WB Content {e.code}: {e.read().decode()[:200]}")

    def _oz_post(self, path, client_id, api_key, body):
        import urllib.request, urllib.error
        data = json.dumps(body).encode()
        req  = urllib.request.Request(
            f"https://api-seller.ozon.ru{path}", data=data,
            headers={"Client-Id": client_id, "Api-Key": api_key,
                     "Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            raise Exception(f"OZON {e.code}: {e.read().decode()[:200]}")

    # ══════════════════════════════════════════════════════
    #  STOCKS
    # ══════════════════════════════════════════════════════
    def _pull_wb(self):
        token = self._wb_token_val()
        if not token: return
        self._log("WB: загрузка остатков…", "info")
        date_from = (date.today() - timedelta(days=1)).isoformat()
        resp = self._wb_get("/api/v1/supplier/stocks", token, f"?dateFrom={date_from}")
        wb = {}
        for item in (resp or []):
            bc = str(item.get("barcode",""))
            if bc: wb[bc] = wb.get(bc,0) + item.get("quantity",0)
        self._log(f"WB: {len(wb)} позиций", "ok")
        self._render_stocks(wb, {})
        self.sig.done.emit(f"✓ WB остатки: {len(wb)} позиций")

    def _pull_ozon(self):
        c, k = self._oz_creds()
        if not c: return
        self._log("OZON: загрузка остатков…", "info")
        oz = self._fetch_oz_stocks(c, k)
        self._render_stocks({}, oz)
        self.sig.done.emit(f"✓ OZON остатки: {len(oz)} позиций")

    def _sync_all(self):
        self._log("=== Полная синхронизация ===", "info")
        token = self._wb_token_val() or ""
        c, k  = self._oz_creds() or ("","")
        wb, oz = {}, {}
        if token:
            try:
                date_from = (date.today()-timedelta(days=1)).isoformat()
                resp = self._wb_get("/api/v1/supplier/stocks", token, f"?dateFrom={date_from}")
                for item in (resp or []):
                    bc = str(item.get("barcode",""))
                    if bc: wb[bc] = wb.get(bc,0)+item.get("quantity",0)
                self._log(f"WB: {len(wb)} позиций", "ok")
            except Exception as e: self._log(f"WB: {e}", "error")
        if c and k:
            try:
                oz = self._fetch_oz_stocks(c, k)
                self._log(f"OZON: {len(oz)} позиций", "ok")
            except Exception as e: self._log(f"OZON: {e}", "error")
        self._render_stocks(wb, oz)
        self.sig.done.emit(f"✓ WB:{len(wb)} / OZON:{len(oz)}")

    def _render_stocks(self, wb, oz):
        rows = []
        for p in self.db.get_products(""):
            local  = self.db.get_stock(p["art"])
            bc_wb  = str(p["bc_wb"]  or "")
            bc_oz  = str(p["bc_ozon"] or "")
            wb_q   = wb.get(bc_wb,  None) if bc_wb  else None
            oz_q   = oz.get(bc_oz,  None) if bc_oz  else None
            parts  = []
            if wb_q  is not None and wb_q  != local: parts.append(f"WB:{wb_q}≠{local}")
            if oz_q  is not None and oz_q  != local: parts.append(f"OZ:{oz_q}≠{local}")
            rows.append([p["art"], p["name"] or p["art"], local, wb_q, oz_q,
                         ", ".join(parts) if parts else "—"])
        self.sig.table_data.emit("stocks", rows)

    def _fetch_oz_stocks(self, c, k):
        resp = self._oz_post("/v2/product/list", c, k, {"filter":{},"limit":1000,"last_id":""})
        items = resp.get("result",{}).get("items",[])
        if not items: return {}
        offer_ids = [i["offer_id"] for i in items[:500]]
        info = self._oz_post("/v3/product/info/stocks", c, k,
            {"filter":{"offer_id":offer_ids,"visibility":"ALL"},"limit":500,"last_id":""})
        oz = {}
        for item in info.get("result",{}).get("items",[]):
            total = sum(s.get("present",0) for s in item.get("stocks",[]))
            for bc in item.get("barcodes",[]): oz[str(bc)] = total
            if item.get("offer_id"): oz[item["offer_id"]] = total
        return oz

    def _confirm_push(self, mp):
        r = QMessageBox.question(self, f"Обновить {mp}",
            f"Отправить текущие остатки из базы на {mp}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            self._run(self._push_wb if mp=="WB" else self._push_ozon)

    def _push_wb(self):
        token = self._wb_token_val()
        if not token: return
        wh_id = self.wb_wh_id.text().strip()
        if not wh_id:
            self._log("Укажите ID склада FBS", "error")
            self.sig.done.emit("❌ WB: нет ID склада"); return
        stocks = [{"sku": str(p["bc_wb"]), "amount": max(0,self.db.get_stock(p["art"]))}
                  for p in self.db.get_products("") if p["bc_wb"]]
        if not stocks:
            self.sig.done.emit("⚠ WB: нет товаров с штрихкодом"); return
        self._log(f"WB: отправка {len(stocks)} позиций…", "info")
        self._wb_post(f"/api/v3/warehouses/{wh_id}/stocks", token, {"stocks": stocks})
        self.sig.done.emit(f"✓ WB FBS обновлён: {len(stocks)} позиций")

    def _push_ozon(self):
        c, k = self._oz_creds()
        if not c: return
        wh_resp = self._oz_post("/v1/warehouse/list", c, k, {})
        whs = wh_resp.get("result",[])
        if not whs:
            self._log("OZON: нет складов", "error")
            self.sig.done.emit("❌ OZON: нет складов"); return
        wh_id = whs[0]["warehouse_id"]
        stocks = [{"offer_id": str(p["bc_ozon"]), "stock": max(0,self.db.get_stock(p["art"])),
                   "warehouse_id": wh_id}
                  for p in self.db.get_products("") if p["bc_ozon"]]
        if not stocks:
            self.sig.done.emit("⚠ OZON: нет товаров с штрихкодом"); return
        # ✅ ИСПРАВЛЕНО: актуальный endpoint /v3/products/stocks (v1 устарел → 404)
        ok = 0
        for i in range(0, len(stocks), 100):
            self._oz_post("/v3/products/stocks", c, k, {"stocks": stocks[i:i+100]})
            ok += min(100, len(stocks)-i)
            self._log(f"OZON: отправлено {ok}/{len(stocks)}", "info")
        self.sig.done.emit(f"✓ OZON FBS обновлён: {ok} позиций")

    # ══════════════════════════════════════════════════════
    #  IMPORT PRODUCTS
    # ══════════════════════════════════════════════════════
    def _import_wb(self):
        token = self._wb_token_val()
        if not token: return
        self._log("WB: получение списка товаров…", "info")
        # WB Content API — список НМ
        resp = self._wb_content("/content/v2/get/cards/list", token,
            {"settings": {"cursor": {"limit": 1000}, "filter": {"withPhoto": -1}}})
        cards = resp.get("cards", [])
        self._log(f"WB: получено {len(cards)} карточек", "ok")
        rows, imported = [], 0
        skip = self.cb_skip_existing.isChecked()
        for card in cards:
            art  = card.get("vendorCode","")
            name = card.get("title","") or card.get("subjectName","")
            bcs  = [str(s.get("skus",[""])[0]) for s in card.get("sizes",[]) if s.get("skus")]
            bc   = bcs[0] if bcs else ""
            cat  = card.get("subjectName","")
            exists = self.db.conn.execute(
                "SELECT bc_wb FROM products WHERE art=?", (art,)).fetchone()
            if exists:
                if skip and exists["bc_wb"]:
                    status = "Пропущен"
                else:
                    self.db.conn.execute(
                        "UPDATE products SET name=CASE WHEN name='' THEN ? ELSE name END, bc_wb=? WHERE art=?",
                        (name, bc, art))
                    self.db.conn.commit()
                    status = "Обновлён"
            else:
                try:
                    self.db.conn.execute(
                        "INSERT INTO products(art,name,cat,bc_wb) VALUES(?,?,?,?)",
                        (art, name, cat, bc))
                    self.db.conn.commit()
                    imported += 1; status = "Добавлен"
                except Exception as e:
                    status = f"Ошибка: {e}"
            rows.append([art, name, bc, "", cat, status])
        self.sig.table_data.emit("import", rows)
        self.sig.done.emit(f"✓ WB импорт: добавлено {imported}, всего {len(cards)}")

    def _import_ozon(self):
        c, k = self._oz_creds()
        if not c: return
        self._log("OZON: получение списка товаров…", "info")
        resp = self._oz_post("/v2/product/list", c, k,
            {"filter":{},"limit":1000,"last_id":""})
        items = resp.get("result",{}).get("items",[])
        if not items:
            self._log("OZON: список пуст", "warn")
            self.sig.done.emit("⚠ OZON: нет товаров"); return

        # Детали товаров пачками по 100
        rows, imported = [], 0
        skip = self.cb_skip_existing.isChecked()
        for i in range(0, len(items), 100):
            batch_ids = [it["product_id"] for it in items[i:i+100]]
            info = self._oz_post("/v2/product/info/list", c, k,
                {"product_id": batch_ids})
            for prod in info.get("result",{}).get("items",[]):
                art   = prod.get("offer_id","")
                name  = prod.get("name","")
                bcs   = prod.get("barcodes",[])
                bc    = str(bcs[0]) if bcs else ""
                cat   = prod.get("category_id","")
                exists = self.db.conn.execute(
                    "SELECT bc_ozon FROM products WHERE art=?", (art,)).fetchone()
                if exists:
                    if skip and exists["bc_ozon"]:
                        status = "Пропущен"
                    else:
                        self.db.conn.execute(
                            "UPDATE products SET name=CASE WHEN name='' THEN ? ELSE name END, bc_ozon=? WHERE art=?",
                            (name, bc, art))
                        self.db.conn.commit(); status = "Обновлён"
                else:
                    try:
                        self.db.conn.execute(
                            "INSERT INTO products(art,name,cat,bc_ozon) VALUES(?,?,?,?)",
                            (art, name, str(cat), bc))
                        self.db.conn.commit(); imported += 1; status = "Добавлен"
                    except Exception as e: status = f"Ошибка: {e}"
                rows.append([art, name, "", bc, str(cat), status])
            self._log(f"OZON: обработано {min(i+100,len(items))}/{len(items)}", "info")
        self.sig.table_data.emit("import", rows)
        self.sig.done.emit(f"✓ OZON импорт: добавлено {imported}, всего {len(items)}")

    def _import_all(self):
        self._log("=== Импорт WB + OZON ===", "info")
        token = self._wb_token_val() or ""
        c, k  = self._oz_creds() or ("","")
        if token:
            try: self._import_wb()
            except Exception as e: self._log(f"WB: {e}", "error")
        if c and k:
            try: self._import_ozon()
            except Exception as e: self._log(f"OZON: {e}", "error")

    # ══════════════════════════════════════════════════════
    #  SALES & ANALYTICS
    # ══════════════════════════════════════════════════════
    def _get_period(self):
        df = self.date_from.date().toString("yyyy-MM-dd")
        dt = self.date_to.date().toString("yyyy-MM-dd")
        return df, dt

    def _pull_sales_wb(self):
        token = self._wb_token_val()
        if not token: return
        df, dt = self._get_period()
        self._log(f"WB: продажи с {df} по {dt}…", "info")
        resp = self._wb_get("/api/v1/supplier/orders", token,
            f"?dateFrom={df}&flag=1")
        orders = resp or []
        # Суммируем по штрихкоду
        sales = {}
        for o in orders:
            bc  = str(o.get("barcode",""))
            qty = 1  # каждая запись = 1 заказ
            if o.get("isCancel"): continue
            if bc: sales[bc] = sales.get(bc,0) + qty
        self._log(f"WB: {len(orders)} заказов → {sum(sales.values())} шт.", "ok")
        self._last_sales["wb"] = sales
        self._render_analytics()
        self.sig.done.emit(f"✓ WB продажи: {sum(sales.values())} шт.")

    def _pull_sales_ozon(self):
        c, k = self._oz_creds()
        if not c: return
        df, dt = self._get_period()
        self._log(f"OZON: продажи с {df} по {dt}…", "info")
        resp = self._oz_post("/v3/posting/fbs/list", c, k, {
            "dir": "asc", "filter": {
                "since": f"{df}T00:00:00.000Z",
                "to":    f"{dt}T23:59:59.000Z",
                "status": "delivered"
            }, "limit": 1000, "offset": 0,
            "with": {"analytics_data": False}
        })
        postings = resp.get("result",{}).get("postings",[])
        sales = {}
        for p in postings:
            for prod in p.get("products",[]):
                offer_id = prod.get("offer_id","")
                qty = prod.get("quantity",1)
                if offer_id: sales[offer_id] = sales.get(offer_id,0) + qty
        self._log(f"OZON: {len(postings)} отправлений → {sum(sales.values())} шт.", "ok")
        self._last_sales["ozon"] = sales
        self._render_analytics()
        self.sig.done.emit(f"✓ OZON продажи: {sum(sales.values())} шт.")

    def _pull_sales_all(self):
        self._log("=== Загрузка продаж WB + OZON ===", "info")
        token = self._wb_token_val() or ""
        c, k  = self._oz_creds() or ("","")
        if token:
            try: self._pull_sales_wb()
            except Exception as e: self._log(f"WB: {e}", "error")
        if c and k:
            try: self._pull_sales_ozon()
            except Exception as e: self._log(f"OZON: {e}", "error")

    def _render_analytics(self):
        wb_s  = self._last_sales.get("wb",{})
        oz_s  = self._last_sales.get("ozon",{})
        df = self.date_from.date(); dt = self.date_to.date()
        days = max(1, df.daysTo(dt))
        rows = []
        for p in self.db.get_products(""):
            bc_wb  = str(p["bc_wb"]  or "")
            bc_oz  = str(p["bc_ozon"] or "") or p["art"]
            sold_wb  = wb_s.get(bc_wb,  0)
            sold_oz  = oz_s.get(bc_oz,  0)
            total    = sold_wb + sold_oz
            stock    = self.db.get_stock(p["art"])
            # Дней хватит
            daily = total / days if total > 0 else 0
            days_left = int(stock / daily) if daily > 0 else 999
            rows.append([p["art"], p["name"] or p["art"],
                         sold_wb, sold_oz, total, stock,
                         days_left if days_left < 999 else "∞"])
        # Сортируем по продажам убыванием
        rows.sort(key=lambda r: r[4], reverse=True)
        self.sig.table_data.emit("analytics", rows)

    def _confirm_writeoff(self):
        wb_s  = self._last_sales.get("wb",{})
        oz_s  = self._last_sales.get("ozon",{})
        if not wb_s and not oz_s:
            QMessageBox.warning(self, "Нет данных",
                "Сначала загрузите продажи кнопками ↓ Продажи WB / ↓ Продажи OZON")
            return
        total_items = sum(wb_s.values()) + sum(oz_s.values())
        r = QMessageBox.question(self, "Списать продажи",
            f"Создать перемещения в историю на основе загруженных продаж?\n\n"
            f"WB: {sum(wb_s.values())} шт.  /  OZON: {sum(oz_s.values())} шт.\n"
            f"Итого: {total_items} шт.\n\n"
            f"Это уменьшит остатки в базе.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            self._run(self._do_writeoff)

    def _do_writeoff(self):
        wb_s = self._last_sales.get("wb",{})
        oz_s = self._last_sales.get("ozon",{})
        df, dt = self._get_period()
        created = 0
        products = self.db.get_products("")

        for p in products:
            art   = p["art"]
            bc_wb = str(p["bc_wb"] or "")
            bc_oz = str(p["bc_ozon"] or "") or art

            sold_wb = wb_s.get(bc_wb, 0)
            sold_oz = oz_s.get(bc_oz, 0)

            if sold_wb > 0:
                self.db.conn.execute(
                    "INSERT INTO moves(dt,art,from_wh,to_wh,qty,barcode,mp_type,note) VALUES(?,?,?,?,?,?,?,?)",
                    (dt, art, "ТВ-2", "WB-1", sold_wb, bc_wb, "WB", f"Продажи WB {df}–{dt}"))
                created += 1

            if sold_oz > 0:
                self.db.conn.execute(
                    "INSERT INTO moves(dt,art,from_wh,to_wh,qty,barcode,mp_type,note) VALUES(?,?,?,?,?,?,?,?)",
                    (dt, art, "ТВ-2", "OZ-1", sold_oz, bc_oz, "OZON", f"Продажи OZON {df}–{dt}"))
                created += 1

        self.db.conn.commit()
        self._last_sales.clear()
        self._log(f"Создано {created} перемещений", "ok")
        self.sig.done.emit(f"✓ Списано: {created} строк в истории")
        self.sig.msg_box.emit("Готово",
            f"Создано {created} записей в истории перемещений.\n"
            f"Остатки обновлены во вкладке Остатки.")

    # ══════════════════════════════════════════════════════
    #  WAREHOUSE STOCKS (остатки по складам МП)
    # ══════════════════════════════════════════════════════
    def _pull_wh_stocks_wb(self):
        token = self._wb_token_val()
        if not token: return
        self._log("WB: остатки по складам FBO…", "info")

        # FBO — остатки на складах WB
        from datetime import date, timedelta
        date_from = (date.today() - timedelta(days=1)).isoformat()
        rows = []

        try:
            fbo = self._wb_get("/api/v1/supplier/stocks", token, f"?dateFrom={date_from}")
            # Группируем по складу + баркод
            wh_sku = {}
            for item in (fbo or []):
                wh   = item.get("warehouseName","") or item.get("subject","Склад WB")
                bc   = str(item.get("barcode",""))
                art  = item.get("supplierArticle","") or bc
                name = item.get("subject","") or item.get("category","")
                qty  = item.get("quantity", 0)
                key  = (wh, bc or art)
                if key in wh_sku:
                    wh_sku[key]["qty"] += qty
                else:
                    wh_sku[key] = {"wh": wh, "sku": bc or art, "name": name,
                                   "art": art, "qty": qty, "type": "FBO"}
            rows += list(wh_sku.values())
            self._log(f"WB FBO: {len(wh_sku)} позиций на {len(set(v['wh'] for v in wh_sku.values()))} складах", "ok")
        except Exception as e:
            self._log(f"WB FBO: {e}", "error")

        # FBS — остатки на складах продавца
        try:
            wh_id = self.wb_wh_id.text().strip()
            if wh_id:
                fbs_resp = self._wb_post(
                    f"/api/v3/warehouses/{wh_id}/remains", token, {},
                    base="https://marketplace-api.wildberries.ru"
                )
                for item in (fbs_resp or []):
                    sku = str(item.get("sku",""))
                    qty = item.get("amount", 0)
                    # Ищем название по штрихкоду в базе
                    prod = self.db.conn.execute(
                        "SELECT name, art FROM products WHERE bc_wb=?", (sku,)).fetchone()
                    name = prod["name"] if prod else ""
                    art  = prod["art"]  if prod else sku
                    rows.append({"wh": f"FBS (ID {wh_id})", "sku": sku,
                                 "name": name, "art": art, "qty": qty, "type": "FBS"})
                self._log(f"WB FBS: {len(fbs_resp or [])} SKU", "ok")
        except Exception as e:
            self._log(f"WB FBS: {e}", "warn")

        self._show_wh_stocks(rows, "WB")
        self.sig.done.emit(f"✓ WB: {len(rows)} строк по складам")

    def _pull_wh_stocks_ozon(self):
        c, k = self._oz_creds()
        if not c: return
        self._log("OZON: остатки по складам…", "info")
        rows = []

        # Получаем список складов
        try:
            wh_resp = self._oz_post("/v1/warehouse/list", c, k, {})
            warehouses = wh_resp.get("result", [])
        except Exception as e:
            self._log(f"OZON список складов: {e}", "error")
            self.sig.done.emit("❌ OZON: ошибка"); return

        self._log(f"OZON: найдено складов: {len(warehouses)}", "info")

        # Получаем товары
        try:
            prod_resp = self._oz_post("/v2/product/list", c, k,
                {"filter": {}, "limit": 1000, "last_id": ""})
            items = prod_resp.get("result", {}).get("items", [])
        except Exception as e:
            self._log(f"OZON список товаров: {e}", "error")
            self.sig.done.emit("❌ OZON: ошибка товаров"); return

        if not items:
            self._log("OZON: нет товаров", "warn")
            self.sig.done.emit("⚠ OZON: нет товаров"); return

        # Остатки FBO + FBS по каждому складу
        offer_ids = [i["offer_id"] for i in items[:500]]
        try:
            stocks_resp = self._oz_post("/v3/product/info/stocks", c, k, {
                "filter": {"offer_id": offer_ids, "visibility": "ALL"},
                "limit": 500, "last_id": ""
            })
            stock_items = stocks_resp.get("result", {}).get("items", [])
        except Exception as e:
            self._log(f"OZON остатки: {e}", "error")
            self.sig.done.emit("❌ OZON: ошибка остатков"); return

        # wh_id → name map
        wh_names = {str(wh["warehouse_id"]): wh.get("name","") for wh in warehouses}

        for item in stock_items:
            offer_id = item.get("offer_id","")
            # Ищем в базе
            prod = self.db.conn.execute(
                "SELECT name FROM products WHERE art=? OR bc_ozon=?",
                (offer_id, offer_id)).fetchone()
            name = prod["name"] if prod else ""

            for s in item.get("stocks", []):
                wh_id  = str(s.get("warehouse_id",""))
                wh_name = wh_names.get(wh_id, f"Склад {wh_id}")
                qty_fbo = s.get("present", 0)
                qty_res = s.get("reserved", 0)
                s_type  = s.get("type", "fbo").upper()

                if qty_fbo > 0:
                    rows.append({"wh": wh_name, "sku": offer_id, "name": name,
                                 "art": offer_id, "qty": qty_fbo, "type": s_type})
                if qty_res > 0:
                    rows.append({"wh": wh_name, "sku": offer_id, "name": f"[резерв] {name}",
                                 "art": offer_id, "qty": qty_res, "type": f"{s_type} резерв"})

        self._log(f"OZON: {len(rows)} строк по {len(warehouses)} складам", "ok")
        self._show_wh_stocks(rows, "OZON")
        self.sig.done.emit(f"✓ OZON: {len(rows)} строк по складам")

    def _pull_wh_stocks_all(self):
        self._log("=== Остатки по складам WB + OZON ===", "info")
        token = self._wb_token_val() or ""
        c, k  = self._oz_creds() or ("","")
        all_rows = []
        if token:
            try:
                self._pull_wh_stocks_wb()
            except Exception as e: self._log(f"WB: {e}", "error")
        if c and k:
            try:
                self._pull_wh_stocks_ozon()
            except Exception as e: self._log(f"OZON: {e}", "error")

    def _show_wh_stocks(self, rows, mp_label):
        """Заполняет таблицу остатков по складам"""
        tbl_rows = []
        for r in rows:
            tbl_rows.append([
                mp_label,
                r.get("wh",""),
                r.get("sku","") or r.get("art",""),
                r.get("name",""),
                r.get("qty", 0),
                r.get("type",""),
            ])
        # Сортируем по складу, потом по SKU
        tbl_rows.sort(key=lambda x: (x[1], x[2]))
        self._wh_stocks_all_rows = tbl_rows

        # Применяем текущий фильтр
        q = self.whs_filter.text().strip().lower()
        filtered = [r for r in tbl_rows
                    if not q or q in r[2].lower() or q in r[3].lower()] if q else tbl_rows
        self._fill_wh_stocks_table(filtered)

        total_qty = sum(r[4] for r in tbl_rows)
        wh_count  = len(set(r[1] for r in tbl_rows))
        self.sig.progress.emit(
            f"✓ {mp_label}: {len(tbl_rows)} строк на {wh_count} складах, итого {total_qty} шт.")

    def _fill_wh_stocks_table(self, rows):
        t = self.wh_stocks_table
        t.setSortingEnabled(False)
        t.setRowCount(len(rows))
        for i, (mp, wh, sku, name, qty, s_type) in enumerate(rows):
            mp_item = QTableWidgetItem(mp)
            mp_item.setForeground(QColor("#6a1b9a" if mp=="WB" else "#1565c0"))
            mp_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            t.setItem(i, 0, mp_item)

            t.setItem(i, 1, QTableWidgetItem(wh))

            sku_item = QTableWidgetItem(sku)
            sku_item.setFont(QFont("Courier New", 9))
            sku_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            t.setItem(i, 2, sku_item)

            t.setItem(i, 3, QTableWidgetItem(name))

            qty_item = QTableWidgetItem(str(qty))
            qty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if qty == 0:
                qty_item.setForeground(QColor(DANGER))
            elif qty <= 5:
                qty_item.setForeground(QColor("#f9a825"))
            else:
                qty_item.setForeground(QColor(OK))
            t.setItem(i, 4, qty_item)

            type_item = QTableWidgetItem(s_type)
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            type_item.setForeground(QColor(MUTED))
            t.setItem(i, 5, type_item)

        t.setSortingEnabled(True)
        t.resizeColumnsToContents()
        t.setColumnWidth(3, 260)

        total = sum(r[4] for r in rows)
        self.whs_summary.setText(
            f"Показано: {len(rows)} строк  |  Итого на складах: {total} шт.")

    def _filter_wh_stocks(self, text):
        if not self._wh_stocks_all_rows: return
        q = text.strip().lower()
        filtered = [r for r in self._wh_stocks_all_rows
                    if not q or q in r[2].lower() or q in r[3].lower()]
        self._fill_wh_stocks_table(filtered)

    # ══════════════════════════════════════════════════════
    #  IMPORT WAREHOUSES
    # ══════════════════════════════════════════════════════
    def _import_warehouses_wb(self):
        token = self._wb_token_val()
        if not token: return
        self._log("WB: загрузка списка складов…", "info")

        # WB API — склады продавца (FBS)
        import urllib.request, urllib.error
        req = urllib.request.Request(
            "https://marketplace-api.wildberries.ru/api/v3/warehouses",
            headers={"Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                warehouses = json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            self._log(f"WB: {e.code} {e.read().decode()[:150]}", "error")
            self.sig.done.emit("❌ WB: ошибка API складов"); return

        added, updated, skipped = 0, 0, 0
        for wh in warehouses:
            wh_id   = str(wh.get("id",""))
            name    = wh.get("name","") or f"WB Склад {wh_id}"
            code    = f"WB-{wh_id}"
            wh_type = "Маркетплейс WB"
            note    = f"ID: {wh_id} | WB FBS"

            exists = self.db.conn.execute(
                "SELECT id FROM warehouses WHERE code=?", (code,)).fetchone()
            if exists:
                self.db.conn.execute(
                    "UPDATE warehouses SET name=?, type=?, note=? WHERE code=?",
                    (name, wh_type, note, code))
                updated += 1
            else:
                self.db.conn.execute(
                    "INSERT INTO warehouses(code,name,type,note) VALUES(?,?,?,?)",
                    (code, name, wh_type, note))
                added += 1
            self._log(f"WB склад: {name} (код {code})", "info")

        self.db.conn.commit()
        msg = f"WB: добавлено {added}, обновлено {updated} складов"
        self._log(msg, "ok")
        self.sig.done.emit(f"✓ {msg}")
        self.sig.msg_box.emit("Склады WB загружены",
            f"Добавлено: {added}\nОбновлено: {updated}\n\n"
            f"Склады доступны во вкладке 🏭 Склады")

    def _import_warehouses_ozon(self):
        c, k = self._oz_creds()
        if not c: return
        self._log("OZON: загрузка списка складов…", "info")

        try:
            resp = self._oz_post("/v1/warehouse/list", c, k, {})
        except Exception as e:
            self._log(f"OZON: {e}", "error")
            self.sig.done.emit("❌ OZON: ошибка API складов"); return

        warehouses = resp.get("result", [])
        if not warehouses:
            self._log("OZON: нет складов в ответе", "warn")
            self.sig.done.emit("⚠ OZON: нет складов"); return

        added, updated = 0, 0
        for wh in warehouses:
            wh_id   = str(wh.get("warehouse_id",""))
            name    = wh.get("name","") or f"OZON Склад {wh_id}"
            is_rfbs = wh.get("is_rfbs", False)
            wh_type = "Маркетплейс OZON"
            note    = f"ID: {wh_id} | {'rFBS' if is_rfbs else 'FBS'}"
            code    = f"OZ-{wh_id}"

            exists = self.db.conn.execute(
                "SELECT id FROM warehouses WHERE code=?", (code,)).fetchone()
            if exists:
                self.db.conn.execute(
                    "UPDATE warehouses SET name=?, type=?, note=? WHERE code=?",
                    (name, wh_type, note, code))
                updated += 1
            else:
                self.db.conn.execute(
                    "INSERT INTO warehouses(code,name,type,note) VALUES(?,?,?,?)",
                    (code, name, wh_type, note))
                added += 1
            self._log(f"OZON склад: {name} (код {code})", "info")

        self.db.conn.commit()
        msg = f"OZON: добавлено {added}, обновлено {updated} складов"
        self._log(msg, "ok")
        self.sig.done.emit(f"✓ {msg}")
        self.sig.msg_box.emit("Склады OZON загружены",
            f"Добавлено: {added}\nОбновлено: {updated}\n\n"
            f"Склады доступны во вкладке 🏭 Склады")

    def _import_warehouses_all(self):
        self._log("=== Импорт складов WB + OZON ===", "info")
        token = self._wb_token_val() or ""
        c, k  = self._oz_creds() or ("","")
        wb_ok, oz_ok = False, False
        if token:
            try: self._import_warehouses_wb(); wb_ok = True
            except Exception as e: self._log(f"WB склады: {e}", "error")
        if c and k:
            try: self._import_warehouses_ozon(); oz_ok = True
            except Exception as e: self._log(f"OZON склады: {e}", "error")
        parts = []
        if wb_ok:   parts.append("WB ✓")
        if oz_ok:   parts.append("OZON ✓")
        if not parts: parts.append("ошибка")
        self.sig.done.emit("✓ Склады: " + " / ".join(parts))
