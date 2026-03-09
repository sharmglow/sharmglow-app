"""ui/tab_marketplace_catalog.py — обзор каталога маркетплейсов"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QTabWidget, QLineEdit, QCheckBox, QFormLayout
)
from PyQt6.QtCore import Qt
from ui.styles import *


class MarketplaceCatalogTab(QWidget):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.main_win = parent
        self.ctx = getattr(parent, "ctx", None)
        self.catalog_service = getattr(self.ctx, "marketplace_catalog_service", None) if self.ctx else None
        self.marketplace_service = getattr(self.ctx, "marketplace_service", None) if self.ctx else None
        self.preview_rows = []
        self.current_account_id = None
        self._build()

    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        tb = QFrame()
        tb.setFixedHeight(56)
        tb.setStyleSheet(f"background:white;border-bottom:1px solid {BORDER};")
        hl = QHBoxLayout(tb)
        hl.setContentsMargins(16, 0, 16, 0)
        hl.setSpacing(10)

        title = QLabel("Каталог маркетплейсов")
        title.setObjectName("title")
        hl.addWidget(title)

        self.market_filter = QComboBox()
        self.market_filter.setFixedWidth(220)
        self.market_filter.addItem("Все маркетплейсы", "")
        for code, name in self._available_marketplaces():
            self.market_filter.addItem(name, code)
        self.market_filter.currentIndexChanged.connect(self.refresh)
        hl.addWidget(self.market_filter)

        btn_refresh = QPushButton("Обновить")
        btn_refresh.clicked.connect(self.refresh)
        hl.addWidget(btn_refresh)

        self.btn_pick = QPushButton("Использовать выбранный аккаунт")
        self.btn_pick.clicked.connect(self.use_selected_account)
        hl.addWidget(self.btn_pick)

        self.btn_wb_load = QPushButton("Загрузить WB каталог")
        self.btn_wb_load.clicked.connect(self.load_wb_catalog)
        hl.addWidget(self.btn_wb_load)

        btn_info = QPushButton("Что дальше")
        btn_info.clicked.connect(self.show_info)
        hl.addWidget(btn_info)

        hl.addStretch()

        self.summary_lbl = QLabel("")
        self.summary_lbl.setStyleSheet(f"font-size:11px;color:{MUTED};")
        hl.addWidget(self.summary_lbl)

        v.addWidget(tb)

        body = QHBoxLayout()
        body.setContentsMargins(12, 12, 12, 12)
        body.setSpacing(12)
        v.addLayout(body)

        left = QFrame()
        left.setStyleSheet("background:white;border:1px solid #e8e1d4;border-radius:10px;")
        lv = QVBoxLayout(left)
        lv.setContentsMargins(12, 12, 12, 12)
        lv.setSpacing(10)

        lbl_acc = QLabel("WB аккаунт для каталога")
        lbl_acc.setStyleSheet("font-weight:600;font-size:14px;")
        lv.addWidget(lbl_acc)

        form = QFrame()
        form.setStyleSheet("background:#fffaf2;border:1px solid #efe4cf;border-radius:8px;")
        fl = QFormLayout(form)
        fl.setContentsMargins(10, 10, 10, 10)
        fl.setSpacing(8)

        self.ed_market = QComboBox()
        for code, name in self._available_marketplaces():
            self.ed_market.addItem(name, code)
        idx = self.ed_market.findData("wb")
        if idx >= 0:
            self.ed_market.setCurrentIndex(idx)
        fl.addRow("Маркетплейс", self.ed_market)

        self.ed_account_name = QLineEdit()
        self.ed_account_name.setPlaceholderText("Основной кабинет WB")
        fl.addRow("Аккаунт", self.ed_account_name)

        self.ed_api_key = QLineEdit()
        self.ed_api_key.setPlaceholderText("WB API token")
        fl.addRow("API ключ", self.ed_api_key)

        self.ed_client_id = QLineEdit()
        self.ed_client_id.setPlaceholderText("Необязательно для WB")
        fl.addRow("Client ID", self.ed_client_id)

        self.chk_active = QCheckBox("Активный аккаунт")
        self.chk_active.setChecked(True)
        fl.addRow("", self.chk_active)

        lv.addWidget(form)

        btns = QHBoxLayout()
        self.btn_save_acc = QPushButton("Сохранить аккаунт")
        self.btn_save_acc.clicked.connect(self.save_account)
        btns.addWidget(self.btn_save_acc)

        self.btn_delete_acc = QPushButton("Удалить")
        self.btn_delete_acc.clicked.connect(self.delete_account)
        btns.addWidget(self.btn_delete_acc)

        self.btn_clear = QPushButton("Новый")
        self.btn_clear.clicked.connect(self._clear_account_form)
        btns.addWidget(self.btn_clear)

        btns.addStretch()
        lv.addLayout(btns)

        self.acc_table = QTableWidget(0, 5)
        self.acc_table.setHorizontalHeaderLabels(["MP", "Аккаунт", "Client ID", "Активен", "Обновлен"])
        self.acc_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.acc_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.acc_table.verticalHeader().setVisible(False)
        self.acc_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.acc_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.acc_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.acc_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        # Без автозагрузки формы по одному клику. Выбор делается отдельной кнопкой.
        self.acc_table.itemDoubleClicked.connect(lambda *_: self.use_selected_account())
        lv.addWidget(self.acc_table)

        self.acc_hint = QLabel("Сохрани аккаунт. Затем выдели строку и нажми 'Использовать выбранный аккаунт'.")
        self.acc_hint.setStyleSheet(f"font-size:11px;color:{MUTED};")
        lv.addWidget(self.acc_hint)

        body.addWidget(left, 4)

        right = QFrame()
        right.setStyleSheet("background:white;border:1px solid #e8e1d4;border-radius:10px;")
        rv = QVBoxLayout(right)
        rv.setContentsMargins(12, 12, 12, 12)
        rv.setSpacing(10)

        self.tabs = QTabWidget()
        rv.addWidget(self.tabs)

        links_page = QWidget()
        links_layout = QVBoxLayout(links_page)
        links_layout.setContentsMargins(0, 0, 0, 0)
        links_layout.setSpacing(10)

        lbl_links = QLabel("Связанные товары")
        lbl_links.setStyleSheet("font-weight:600;font-size:14px;")
        links_layout.addWidget(lbl_links)

        self.links_table = QTableWidget(0, 7)
        self.links_table.setHorizontalHeaderLabels([
            "MP", "Аккаунт", "Артикул", "Товар", "Offer / SKU", "Vendor Code", "Штрихкоды"
        ])
        self.links_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.links_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.links_table.verticalHeader().setVisible(False)
        self.links_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.links_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        links_layout.addWidget(self.links_table)

        self.links_hint = QLabel("Здесь появятся связи товаров Смарт Склад с карточками маркетплейсов.")
        self.links_hint.setStyleSheet(f"font-size:11px;color:{MUTED};")
        links_layout.addWidget(self.links_hint)

        self.tabs.addTab(links_page, "Связанные")

        preview_page = QWidget()
        preview_layout = QVBoxLayout(preview_page)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(10)

        lbl_preview = QLabel("Предпросмотр WB каталога")
        lbl_preview.setStyleSheet("font-weight:600;font-size:14px;")
        preview_layout.addWidget(lbl_preview)

        self.preview_table = QTableWidget(0, 7)
        self.preview_table.setHorizontalHeaderLabels([
            "nmID", "Vendor Code", "Название", "Категория", "Бренд", "Штрихкоды", "Статус"
        ])
        self.preview_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.preview_table.verticalHeader().setVisible(False)
        self.preview_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.preview_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        preview_layout.addWidget(self.preview_table)

        self.preview_hint = QLabel("Здесь появится список карточек WB из выбранного аккаунта.")
        self.preview_hint.setStyleSheet(f"font-size:11px;color:{MUTED};")
        preview_layout.addWidget(self.preview_hint)

        self.tabs.addTab(preview_page, "WB импорт")

        body.addWidget(right, 6)
        self.refresh()

    def _available_marketplaces(self):
        pairs = []
        if self.marketplace_service:
            try:
                for adapter in self.marketplace_service.list_adapters():
                    pairs.append((getattr(adapter, "code", ""), getattr(adapter, "display_name", getattr(adapter, "code", ""))))
            except Exception:
                pass
        if not pairs:
            pairs = [
                ("wb", "Wildberries"),
                ("ozon", "Ozon"),
                ("ym", "Яндекс Маркет"),
                ("aliexpress", "AliExpress"),
            ]
        return pairs

    def _selected_marketplace(self):
        return self.market_filter.currentData() or None

    def _selected_account_id(self):
        selected = self.acc_table.selectionModel().selectedRows()
        if not selected:
            return None
        row = selected[0].row()
        item = self.acc_table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def refresh(self):
        market = self._selected_marketplace()
        self._refresh_accounts(market)
        self._refresh_links(market, selected_account_id=self.current_account_id)
        if not self.preview_rows:
            self._refresh_preview([])

    def _refresh_accounts(self, marketplace_code=None):
        rows = self.catalog_service.get_accounts(marketplace_code=marketplace_code) if self.catalog_service else []
        self.acc_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            vals = [
                row.get("marketplace_code", ""),
                row.get("account_name", ""),
                row.get("client_id", ""),
                "Да" if row.get("is_active") else "Нет",
                row.get("updated_at", ""),
            ]
            for j, val in enumerate(vals):
                item = QTableWidgetItem(str(val or ""))
                self.acc_table.setItem(i, j, item)
            self.acc_table.item(i, 0).setData(Qt.ItemDataRole.UserRole, row.get("id"))
        self.summary_lbl.setText(f"Аккаунтов: {len(rows)}")

    def _refresh_links(self, marketplace_code=None, selected_account_id=None):
        rows = self.catalog_service.get_links(marketplace_code=marketplace_code) if self.catalog_service else []
        if selected_account_id:
            rows = [r for r in rows if r.get("account_id") == selected_account_id]
        self.links_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            product_id = row.get("product_id")
            barcodes = []
            if product_id and self.catalog_service:
                try:
                    barcodes = [b.get("barcode", "") for b in self.catalog_service.get_product_barcodes(product_id)]
                except Exception:
                    barcodes = []
            offer = row.get("external_offer_id") or row.get("external_sku") or row.get("external_product_id") or ""
            vals = [
                row.get("marketplace_code", ""),
                row.get("account_name", ""),
                row.get("art", ""),
                row.get("product_name", ""),
                offer,
                row.get("vendor_code", ""),
                ", ".join([b for b in barcodes if b]),
            ]
            for j, val in enumerate(vals):
                self.links_table.setItem(i, j, QTableWidgetItem(str(val or "")))
        self.links_hint.setText(f"Связей: {len(rows)}")

    def _refresh_preview(self, rows):
        self.preview_rows = list(rows or [])
        self.preview_table.setRowCount(len(self.preview_rows))
        existing_links = set()
        try:
            for link in self.catalog_service.get_links(marketplace_code="wb"):
                existing_links.add((str(link.get("external_product_id") or ""), str(link.get("vendor_code") or "")))
        except Exception:
            existing_links = set()
        for i, row in enumerate(self.preview_rows):
            status = "новый"
            key = (str(row.get("external_id") or ""), str(row.get("vendor_code") or ""))
            if key in existing_links:
                status = "уже связан"
            vals = [
                row.get("external_id", ""),
                row.get("vendor_code", ""),
                row.get("name", ""),
                row.get("category", ""),
                row.get("brand", ""),
                ", ".join(row.get("barcodes") or []),
                status,
            ]
            for j, val in enumerate(vals):
                self.preview_table.setItem(i, j, QTableWidgetItem(str(val or "")))
        self.preview_hint.setText(f"Карточек WB загружено: {len(self.preview_rows)}")

    def use_selected_account(self):
        account_id = self._selected_account_id()
        if not account_id:
            QMessageBox.information(self, "Аккаунт", "Сначала выдели строку аккаунта в таблице.")
            return
        self.current_account_id = account_id
        account = self.catalog_service.get_account(account_id) if self.catalog_service else None
        if account:
            self._fill_account_form(account)
            self.acc_hint.setText(f"Выбран аккаунт: {account.get('account_name', '')} ({account.get('marketplace_code', '')})")
        self._refresh_links(self._selected_marketplace(), self.current_account_id)

    def _fill_account_form(self, account):
        idx = self.ed_market.findData(account.get("marketplace_code", "wb"))
        if idx >= 0:
            self.ed_market.setCurrentIndex(idx)
        self.ed_account_name.setText(account.get("account_name", ""))
        self.ed_api_key.setText(account.get("api_key", ""))
        self.ed_client_id.setText(account.get("client_id", ""))
        self.chk_active.setChecked(bool(account.get("is_active")))

    def _clear_account_form(self):
        self.current_account_id = None
        idx = self.ed_market.findData("wb")
        if idx >= 0:
            self.ed_market.setCurrentIndex(idx)
        self.ed_account_name.clear()
        self.ed_api_key.clear()
        self.ed_client_id.clear()
        self.chk_active.setChecked(True)
        self.acc_table.clearSelection()
        self._refresh_links(self._selected_marketplace(), None)

    def save_account(self):
        if not self.catalog_service:
            QMessageBox.warning(self, "Аккаунт", "Сервис каталога не подключен.")
            return
        marketplace_code = self.ed_market.currentData() or ""
        account_name = self.ed_account_name.text().strip()
        api_key = self.ed_api_key.text().strip()
        client_id = self.ed_client_id.text().strip()
        if not account_name:
            QMessageBox.warning(self, "Аккаунт", "Укажи название аккаунта.")
            return
        if marketplace_code == "wb" and not api_key:
            QMessageBox.warning(self, "Аккаунт", "Для Wildberries нужен API ключ.")
            return
        try:
            saved_id = self.catalog_service.save_account(
                account_id=self.current_account_id,
                marketplace_code=marketplace_code,
                account_name=account_name,
                api_key=api_key,
                client_id=client_id,
                extra={},
                is_active=self.chk_active.isChecked(),
            )
            self.current_account_id = saved_id
            self.refresh()
            QMessageBox.information(self, "Аккаунт", "Аккаунт сохранен.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка сохранения", str(e))

    def delete_account(self):
        if not self.current_account_id:
            QMessageBox.warning(self, "Аккаунт", "Сначала выбери аккаунт через кнопку 'Использовать выбранный аккаунт'.")
            return
        if QMessageBox.question(self, "Удаление", "Удалить выбранный аккаунт?") != QMessageBox.StandardButton.Yes:
            return
        try:
            self.catalog_service.delete_account(self.current_account_id)
            self._clear_account_form()
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка удаления", str(e))

    def load_wb_catalog(self):
        account_id = self.current_account_id or self._selected_account_id()
        if not account_id:
            QMessageBox.warning(self, "WB каталог", "Сначала выбери аккаунт кнопкой 'Использовать выбранный аккаунт'.")
            return
        account = self.catalog_service.get_account(account_id) if self.catalog_service else None
        if not account:
            QMessageBox.warning(self, "WB каталог", "Аккаунт не найден.")
            return
        if (account.get("marketplace_code") or "") != "wb":
            QMessageBox.warning(self, "WB каталог", "Для этой кнопки нужен именно аккаунт Wildberries.")
            return
        try:
            rows = self.catalog_service.fetch_products_preview("wb", account_id)
            self._refresh_preview(rows)
            self.tabs.setCurrentIndex(1)
            QMessageBox.information(self, "WB каталог", f"Загружено карточек: {len(rows)}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка загрузки WB", str(e))

    def show_info(self):
        QMessageBox.information(
            self,
            "Каталог маркетплейсов",
            "На этом шаге выбор аккаунта сделан через отдельную кнопку, без автодействий по одному клику в таблице.\n\n"
            "Порядок работы:\n"
            "1. Сохрани аккаунт WB\n"
            "2. Выдели строку аккаунта\n"
            "3. Нажми 'Использовать выбранный аккаунт'\n"
            "4. Нажми 'Загрузить WB каталог'"
        )
