"""ui/tab_marketplace_catalog.py — каталог маркетплейсов"""
import json
import re

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QLineEdit, QFormLayout, QTabWidget, QDialog, QDialogButtonBox,
    QSpinBox, QCompleter
)

from marketplaces.base import MarketplaceCredentials
from ui.styles import *


class MarketplaceCatalogTab(QWidget):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.main_win = parent
        self.ctx = getattr(parent, "ctx", None)
        self.catalog_service = getattr(self.ctx, "marketplace_catalog_service", None) if self.ctx else None
        self.marketplace_service = getattr(self.ctx, "marketplace_service", None) if self.ctx else None
        self.current_account_id = None
        self.current_preview_products = []
        self.current_preview_index = {}
        self.preview_cache = {}
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        top = QFrame()
        top.setFixedHeight(56)
        top.setStyleSheet(f"background:white;border-bottom:1px solid {BORDER};")
        top_l = QHBoxLayout(top)
        top_l.setContentsMargins(16, 0, 16, 0)
        top_l.setSpacing(10)

        title = QLabel("Каталог маркетплейсов")
        title.setObjectName("title")
        top_l.addWidget(title)

        self.market_filter = QComboBox()
        self.market_filter.setFixedWidth(220)
        for code, name in self._available_marketplaces():
            self.market_filter.addItem(name, code)
        self.market_filter.currentIndexChanged.connect(self._on_market_filter_changed)
        top_l.addWidget(self.market_filter)

        btn_refresh = QPushButton("Обновить")
        btn_refresh.clicked.connect(self.refresh)
        top_l.addWidget(btn_refresh)

        btn_info = QPushButton("Что дальше")
        btn_info.clicked.connect(self.show_info)
        top_l.addWidget(btn_info)

        top_l.addStretch()
        self.summary_lbl = QLabel("")
        self.summary_lbl.setStyleSheet(f"font-size:11px;color:{MUTED};")
        top_l.addWidget(self.summary_lbl)
        root.addWidget(top)

        body = QHBoxLayout()
        body.setContentsMargins(12, 12, 12, 12)
        body.setSpacing(12)
        root.addLayout(body)

        # left
        left = QFrame()
        left.setStyleSheet("background:white;border:1px solid #e8e1d4;border-radius:10px;")
        lv = QVBoxLayout(left)
        lv.setContentsMargins(12, 12, 12, 12)
        lv.setSpacing(10)

        self.lbl_acc = QLabel("Маркетплейс: подключение")
        self.lbl_acc.setStyleSheet("font-weight:600;font-size:14px;")
        lv.addWidget(self.lbl_acc)

        form = QFrame()
        form.setStyleSheet("background:#fffaf2;border:1px solid #efe4cf;border-radius:8px;")
        fl = QFormLayout(form)
        fl.setContentsMargins(10, 10, 10, 10)
        fl.setSpacing(8)

        self.ed_account_name = QLineEdit()
        self.ed_api_key = QLineEdit()
        self.ed_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.ed_client_id = QLineEdit()
        fl.addRow("Аккаунт", self.ed_account_name)
        fl.addRow("API ключ", self.ed_api_key)
        fl.addRow("Client ID", self.ed_client_id)
        lv.addWidget(form)

        row1 = QHBoxLayout()
        self.btn_save_acc = QPushButton("Сохранить аккаунт")
        self.btn_save_acc.clicked.connect(self.save_account)
        row1.addWidget(self.btn_save_acc)
        self.btn_use_selected = QPushButton("Использовать выбранный")
        self.btn_use_selected.clicked.connect(self.use_selected_account)
        row1.addWidget(self.btn_use_selected)
        lv.addLayout(row1)

        row2 = QHBoxLayout()
        self.btn_check = QPushButton("Проверить подключение")
        self.btn_check.clicked.connect(self.check_connection)
        row2.addWidget(self.btn_check)
        self.btn_load_catalog = QPushButton("Загрузить каталог")
        self.btn_load_catalog.clicked.connect(self.load_catalog)
        row2.addWidget(self.btn_load_catalog)
        self.btn_import = QPushButton("Импортировать в товары")
        self.btn_import.clicked.connect(self.import_selected_product)
        row2.addWidget(self.btn_import)
        self.btn_delete_acc = QPushButton("Удалить")
        self.btn_delete_acc.clicked.connect(self.delete_account)
        row2.addWidget(self.btn_delete_acc)
        row2.addStretch()
        lv.addLayout(row2)

        self.status_lbl = QLabel("")
        self.status_lbl.setWordWrap(True)
        self.status_lbl.setStyleSheet(f"font-size:11px;color:{MUTED};")
        lv.addWidget(self.status_lbl)

        self.acc_table = QTableWidget(0, 5)
        self.acc_table.setHorizontalHeaderLabels(["MP", "Аккаунт", "Client ID", "Активен", "Обновлен"])
        self.acc_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.acc_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.acc_table.verticalHeader().setVisible(False)
        self.acc_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.acc_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.acc_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.acc_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.acc_table.itemSelectionChanged.connect(self._on_account_selected)
        lv.addWidget(self.acc_table)

        self.acc_hint = QLabel("Один клик по строке только выбирает аккаунт. Никаких переходов в браузер не запускается.")
        self.acc_hint.setStyleSheet(f"font-size:11px;color:{MUTED};")
        lv.addWidget(self.acc_hint)
        body.addWidget(left, 4)

        # right
        right = QFrame()
        right.setStyleSheet("background:white;border:1px solid #e8e1d4;border-radius:10px;")
        rv = QVBoxLayout(right)
        rv.setContentsMargins(12, 12, 12, 12)
        rv.setSpacing(10)

        self.right_tabs = QTabWidget()
        self.right_tabs.setDocumentMode(True)

        links_page = QWidget()
        lp = QVBoxLayout(links_page)
        lp.setContentsMargins(0, 0, 0, 0)
        lp.setSpacing(10)
        lbl_links = QLabel("Связанные товары")
        lbl_links.setStyleSheet("font-weight:600;font-size:14px;")
        lp.addWidget(lbl_links)
        self.links_table = QTableWidget(0, 7)
        self.links_table.setHorizontalHeaderLabels(["MP", "Аккаунт", "Артикул", "Товар", "Offer / SKU", "Vendor Code", "Штрихкоды"])
        self.links_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.links_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.links_table.verticalHeader().setVisible(False)
        self.links_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.links_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        lp.addWidget(self.links_table)
        link_row = QHBoxLayout()
        self.btn_delete_link = QPushButton("Удалить выбранную связь")
        self.btn_delete_link.clicked.connect(self.delete_selected_link)
        link_row.addWidget(self.btn_delete_link)
        link_row.addStretch()
        lp.addLayout(link_row)
        self.links_hint = QLabel("")
        self.links_hint.setStyleSheet(f"font-size:11px;color:{MUTED};")
        lp.addWidget(self.links_hint)

        preview_page = QWidget()
        pp = QVBoxLayout(preview_page)
        pp.setContentsMargins(0, 0, 0, 0)
        pp.setSpacing(10)
        self.preview_label = QLabel("Импорт: предпросмотр")
        self.preview_label.setStyleSheet("font-weight:600;font-size:14px;")
        pp.addWidget(self.preview_label)
        self.preview_table = QTableWidget(0, 7)
        self.preview_table.setHorizontalHeaderLabels(["ID", "Vendor Code", "Товар", "Бренд", "Категория", "Offer / SKU", "Штрихкоды"])
        self.preview_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.preview_table.verticalHeader().setVisible(False)
        self.preview_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.preview_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        pp.addWidget(self.preview_table)
        self.preview_hint = QLabel("")
        self.preview_hint.setStyleSheet(f"font-size:11px;color:{MUTED};")
        pp.addWidget(self.preview_hint)

        self.right_tabs.addTab(links_page, "Связанные")
        self.right_tabs.addTab(preview_page, "Импорт")
        rv.addWidget(self.right_tabs)
        body.addWidget(right, 6)

        self._on_market_filter_changed()

    # ---------- helpers ----------
    def _available_marketplaces(self):
        return [("wb", "Wildberries"), ("ozon", "Ozon")]

    def _selected_marketplace(self):
        return self.market_filter.currentData() or "wb"

    def _row_value(self, row, key, default=""):
        try:
            value = row[key]
        except Exception:
            try:
                value = dict(row).get(key, default)
            except Exception:
                value = default
        return default if value is None else value

    def _credentials_from_form(self):
        return MarketplaceCredentials(
            account_name=self.ed_account_name.text().strip(),
            api_key=self.ed_api_key.text().strip(),
            client_id=self.ed_client_id.text().strip(),
        )

    def _market_label(self):
        return "Ozon" if self._selected_marketplace() == "ozon" else "WB"

    def _preview_headers(self):
        if self._selected_marketplace() == "ozon":
            return ["Product ID", "Offer ID", "Товар", "Бренд", "Категория", "SKU", "Штрихкоды"]
        return ["nmID", "Vendor Code", "Товар", "Бренд", "Категория", "Offer / SKU", "Штрихкоды"]

    def _on_market_filter_changed(self):
        market = self._selected_marketplace()
        label = self._market_label()
        is_ozon = market == "ozon"
        self.lbl_acc.setText(f"{label}: подключение")
        self.ed_account_name.setPlaceholderText("Основной кабинет")
        self.ed_api_key.setPlaceholderText("API key / token")
        self.ed_client_id.setPlaceholderText("Для Ozon обязателен" if is_ozon else "Для WB можно оставить пустым")
        self.btn_save_acc.setText(f"Сохранить {label} аккаунт")
        self.btn_check.setText(f"Проверить подключение {label}")
        self.btn_load_catalog.setText(f"Загрузить каталог {label}")
        self.btn_import.setText(f"Импортировать из {label}")
        self.preview_label.setText(f"{label} импорт: предпросмотр")
        self.preview_table.setHorizontalHeaderLabels(self._preview_headers())
        self.right_tabs.setTabText(1, f"{label} импорт")
        if is_ozon:
            self.status_lbl.setText("Сохрани или выбери Ozon-аккаунт, затем нажми «Проверить подключение Ozon» или «Загрузить каталог Ozon». При импорте: если внутренний SKU уже есть, будет добавлена только Ozon-привязка и штрихкод.")
            self.preview_hint.setText("Каталог Ozon загружается в предпросмотр. Выбери строку и нажми «Импортировать из Ozon».")
        else:
            self.status_lbl.setText("Сохрани или выбери WB-аккаунт, затем нажми «Проверить подключение WB» или «Загрузить каталог WB». Если внутренний SKU уже есть, будет добавлена только WB-привязка и штрихкод.")
            self.preview_hint.setText("Каталог WB загружается в предпросмотр. Выбери строку и нажми «Импортировать из WB».")
        self.current_account_id = None
        self.refresh()

    # ---------- refresh ----------
    def refresh(self):
        market = self._selected_marketplace()
        self._refresh_accounts(market)
        self._refresh_links(market, self.current_account_id)
        self._refresh_preview(self.preview_cache.get(market, []))

    def _refresh_accounts(self, marketplace_code):
        rows = self.catalog_service.get_accounts(marketplace_code=marketplace_code) if self.catalog_service else []
        self.acc_table.setSortingEnabled(False)
        self.acc_table.clearContents()
        self.acc_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            vals = [
                self._row_value(row, "marketplace_code"),
                self._row_value(row, "account_name"),
                self._row_value(row, "client_id"),
                "Да" if self._row_value(row, "is_active", 0) else "Нет",
                self._row_value(row, "updated_at"),
            ]
            for j, val in enumerate(vals):
                item = QTableWidgetItem(str(val or ""))
                if j == 0:
                    item.setForeground(Qt.GlobalColor.darkBlue)
                    item.setData(Qt.ItemDataRole.UserRole, self._row_value(row, "id", None))
                self.acc_table.setItem(i, j, item)
        self.acc_table.setSortingEnabled(True)
        self.summary_lbl.setText(f"Аккаунтов: {len(rows)}")

    def _refresh_links(self, marketplace_code=None, selected_account_id=None):
        rows = self.catalog_service.get_links(marketplace_code=marketplace_code) if self.catalog_service else []
        if selected_account_id:
            rows = [r for r in rows if self._row_value(r, "account_id", None) == selected_account_id]

        # Стабильное отображение: одна строка на внутренний артикул + маркетплейс.
        grouped = {}
        for row in rows:
            art = str(self._row_value(row, "art", "") or "").strip()
            market = str(self._row_value(row, "marketplace_code", "") or "").strip()
            if not art or not market:
                continue
            key = (art, market)
            current = grouped.get(key)
            if current is None:
                grouped[key] = row
                continue
            score_cur = (1 if self._row_value(current, "account_name", "") else 0, int(self._row_value(current, "id", 0) or 0))
            score_new = (1 if self._row_value(row, "account_name", "") else 0, int(self._row_value(row, "id", 0) or 0))
            if score_new > score_cur:
                grouped[key] = row

        rows2 = list(grouped.values())
        rows2.sort(key=lambda r: (self._row_value(r, "marketplace_code", ""), self._row_value(r, "art", "")))

        self.links_table.setSortingEnabled(False)
        self.links_table.clearContents()
        self.links_table.setRowCount(len(rows2))
        for i, row in enumerate(rows2):
            product_id = self._row_value(row, "product_id", None)
            barcodes = []
            if product_id and self.catalog_service:
                try:
                    seen = set()
                    for b in self.catalog_service.get_product_barcodes(product_id):
                        code = str(self._row_value(b, "marketplace_code", "") or "").strip()
                        if code != self._row_value(row, "marketplace_code", ""):
                            continue
                        barcode = str(self._row_value(b, "barcode", "") or "").strip()
                        if barcode and barcode not in seen:
                            seen.add(barcode)
                            barcodes.append(barcode)
                except Exception:
                    barcodes = []
            offer = self._row_value(row, "external_offer_id") or self._row_value(row, "external_sku") or self._row_value(row, "external_product_id") or ""
            vals = [
                self._row_value(row, "marketplace_code"),
                self._row_value(row, "account_name"),
                self._row_value(row, "art"),
                self._row_value(row, "name"),
                offer,
                self._row_value(row, "vendor_code"),
                ", ".join(barcodes),
            ]
            for j, val in enumerate(vals):
                item = QTableWidgetItem(str(val or ""))
                if j == 0:
                    item.setData(Qt.ItemDataRole.UserRole, self._row_value(row, "id", None))
                self.links_table.setItem(i, j, item)
        self.links_table.setSortingEnabled(True)
        self.links_hint.setText(f"Связей: {len(rows2)}")

    def _refresh_preview(self, products):
        self.current_preview_products = list(products or [])
        self.current_preview_index = {}
        self.preview_table.setSortingEnabled(False)
        self.preview_table.clearContents()
        self.preview_table.setRowCount(len(self.current_preview_products))
        for i, product in enumerate(self.current_preview_products):
            row_key = self._preview_row_key(product)
            if row_key:
                self.current_preview_index[row_key] = product
            if self._selected_marketplace() == "ozon":
                vals = [
                    product.external_id,
                    product.offer_id,
                    product.name,
                    product.brand,
                    product.category,
                    product.sku,
                    ", ".join([b for b in product.barcodes if b]),
                ]
            else:
                vals = [
                    product.external_id,
                    product.vendor_code,
                    product.name,
                    product.brand,
                    product.category,
                    product.offer_id or product.sku or product.external_id,
                    ", ".join([b for b in product.barcodes if b]),
                ]
            for j, val in enumerate(vals):
                item = QTableWidgetItem(str(val or ""))
                if j == 0 and row_key:
                    item.setData(Qt.ItemDataRole.UserRole, row_key)
                self.preview_table.setItem(i, j, item)
        self.preview_table.setSortingEnabled(True)
        self.preview_hint.setText(f"Карточек в предпросмотре: {len(self.current_preview_products)}")

    # ---------- accounts ----------
    def _on_account_selected(self):
        items = self.acc_table.selectedItems()
        if not items:
            self.current_account_id = None
            self._refresh_links(self._selected_marketplace(), None)
            self.acc_hint.setText("Выбери аккаунт, чтобы увидеть связанные товары.")
            return
        row_idx = items[0].row()
        self.current_account_id = self.acc_table.item(row_idx, 0).data(Qt.ItemDataRole.UserRole)
        self.ed_account_name.setText(self.acc_table.item(row_idx, 1).text())
        self.ed_client_id.setText(self.acc_table.item(row_idx, 2).text())
        rows = self.catalog_service.get_accounts(marketplace_code=self._selected_marketplace()) if self.catalog_service else []
        for row in rows:
            if self._row_value(row, "id", None) == self.current_account_id:
                self.ed_api_key.setText(self._row_value(row, "api_key"))
                break
        self.acc_hint.setText(f"Выбран аккаунт: {self.ed_account_name.text().strip()}")
        self._refresh_links(self._selected_marketplace(), self.current_account_id)

    def save_account(self):
        if not self.catalog_service:
            QMessageBox.critical(self, "Ошибка", "Сервис каталога недоступен.")
            return
        market = self._selected_marketplace()
        label = self._market_label()
        creds = self._credentials_from_form()
        if not creds.account_name:
            QMessageBox.warning(self, label, "Укажи название аккаунта.")
            return
        if not creds.api_key:
            QMessageBox.warning(self, label, f"Укажи API ключ {label}.")
            return
        if market == "ozon" and not creds.client_id:
            QMessageBox.warning(self, "Ozon", "Для Ozon укажи Client ID.")
            return
        self.current_account_id = self.catalog_service.save_account(
            account_id=self.current_account_id,
            marketplace_code=market,
            account_name=creds.account_name,
            api_key=creds.api_key,
            client_id=creds.client_id,
            extra={},
            is_active=True,
        )
        self.refresh()
        self.status_lbl.setText(f"{label} аккаунт сохранен.")

    def use_selected_account(self):
        if not self.current_account_id:
            QMessageBox.information(self, "Аккаунт", "Сначала выбери строку аккаунта в таблице.")
            return
        self.status_lbl.setText(f"Используется аккаунт: {self.ed_account_name.text().strip() or 'без названия'}")

    def delete_account(self):
        if not self.current_account_id:
            QMessageBox.information(self, "Удаление", "Сначала выбери аккаунт в таблице.")
            return
        if self.catalog_service:
            self.catalog_service.delete_account(self.current_account_id)
        self.current_account_id = None
        self.ed_account_name.clear()
        self.ed_api_key.clear()
        self.ed_client_id.clear()
        self.refresh()
        self.status_lbl.setText(f"{self._market_label()} аккаунт удален.")

    # ---------- actions ----------
    def check_connection(self):
        market = self._selected_marketplace()
        label = self._market_label()
        if not self.marketplace_service:
            QMessageBox.critical(self, label, "Сервис маркетплейсов недоступен.")
            return
        ok, message = self.marketplace_service.validate_credentials(market, self._credentials_from_form())
        self.status_lbl.setText(message)
        if ok:
            QMessageBox.information(self, label, message)
        else:
            QMessageBox.warning(self, label, message)

    def load_catalog(self):
        market = self._selected_marketplace()
        label = self._market_label()
        if not self.marketplace_service:
            QMessageBox.critical(self, label, "Сервис маркетплейсов недоступен.")
            return
        creds = self._credentials_from_form()
        if not creds.api_key:
            QMessageBox.warning(self, label, f"Укажи или выбери {label} аккаунт с API ключом.")
            return
        if market == "ozon" and not creds.client_id:
            QMessageBox.warning(self, "Ozon", "Для Ozon нужен Client ID.")
            return
        try:
            products = self.marketplace_service.fetch_products(market, creds)
        except Exception as e:
            self.status_lbl.setText(str(e))
            QMessageBox.warning(self, label, str(e))
            return
        self.preview_cache[market] = list(products or [])
        self._refresh_preview(self.preview_cache.get(market, []))
        self.right_tabs.setCurrentIndex(1)
        msg = f"Загружено карточек {label}: {len(products)}"
        self.status_lbl.setText(msg)
        QMessageBox.information(self, label, msg)

    def _preview_row_key(self, product):
        return str(product.external_id or product.offer_id or product.sku or product.vendor_code or "").strip()

    def _selected_preview_product(self):
        items = self.preview_table.selectedItems()
        if not items:
            return None
        row_idx = items[0].row()
        key_item = self.preview_table.item(row_idx, 0)
        row_key = key_item.data(Qt.ItemDataRole.UserRole) if key_item else None
        if row_key and row_key in self.current_preview_index:
            return self.current_preview_index[row_key]
        if row_idx < 0 or row_idx >= len(self.current_preview_products):
            return None
        return self.current_preview_products[row_idx]

    def import_selected_product(self):
        market = self._selected_marketplace()
        label = self._market_label()
        product = self._selected_preview_product()
        if not product:
            QMessageBox.information(self, label, f"Сначала выбери строку в таблице {label} импорт.")
            return

        dlg = ImportMarketplaceProductDialog(product, market, self.db, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        data = dlg.get_data()
        art = data["art"].strip()
        if not art:
            QMessageBox.warning(self, label, "Укажи внутренний SKU товара.")
            return

        existing = self.db.get_product(art)
        selected_barcode = data["barcode"].strip()
        market_code = market
        bc_wb = selected_barcode if market_code == "wb" else ""
        bc_ozon = selected_barcode if market_code == "ozon" else ""

        created_new = False
        if existing:
            pid = existing["id"]
            # если товар уже есть, только добавляем привязку/штрихкод
            if not self._product_has_market_barcode(pid, market_code, selected_barcode) and selected_barcode:
                self.db.add_product_barcode(pid, selected_barcode, source=f"{market_code}_smart_import", marketplace_code=market_code, is_primary=1)
        else:
            pid = self.db.add_product(
                art,
                data["name"].strip(),
                data["cat"].strip(),
                data["unit"].strip() or "шт",
                int(data["min_stock"]),
                bc_wb,
                bc_ozon,
                data["supplier"].strip(),
                data["note"].strip(),
            )
            created_new = True
            if selected_barcode and market_code not in ("wb", "ozon"):
                self.db.add_product_barcode(pid, selected_barcode, source=f"{market_code}_smart_import", marketplace_code=market_code, is_primary=1)

        account_id = self.current_account_id
        if not account_id:
            items = self.acc_table.selectedItems()
            if items:
                account_id = self.acc_table.item(items[0].row(), 0).data(Qt.ItemDataRole.UserRole)

        offer = product.offer_id or product.sku or product.external_id or ""
        external_sku = selected_barcode if market_code == "wb" else (product.sku or selected_barcode or "")
        self.db.upsert_marketplace_product_link(
            product_id=pid,
            marketplace_code=market_code,
            account_id=account_id,
            external_product_id=product.external_id or "",
            external_sku=external_sku,
            external_offer_id=offer,
            vendor_code=product.vendor_code or art,
            external_name=product.name or data["name"].strip(),
            raw_payload_json=json.dumps({
                "seed": f"{market_code}_smart_import_v1",
                "selected_barcode": selected_barcode,
                "payload": product.raw_data or {},
            }, ensure_ascii=False),
        )
        if selected_barcode and market_code == "ozon":
            # Ozon barcode хранится как отдельная MP-привязка; при уже существующем товаре добавляется только он.
            self.db.add_product_barcode(pid, selected_barcode, source="ozon_smart_import", marketplace_code="ozon", is_primary=1)

        self._refresh_links(self._selected_marketplace(), self.current_account_id)
        if self.main_win and hasattr(self.main_win, "refresh_all"):
            self.main_win.refresh_all()
        self.right_tabs.setCurrentIndex(0)
        msg = (
            f"Создан новый товар {art} и добавлена привязка {label}."
            if created_new else
            f"Товар {art} уже существовал: добавлена только привязка {label} и штрихкод."
        )
        QMessageBox.information(self, label, msg)

    def _product_has_market_barcode(self, product_id, market_code, barcode):
        if not barcode:
            return False
        for row in self.catalog_service.get_product_barcodes(product_id):
            if str(self._row_value(row, "marketplace_code", "")) == market_code and str(self._row_value(row, "barcode", "")) == barcode:
                return True
        return False

    def delete_selected_link(self):
        items = self.links_table.selectedItems()
        if not items:
            QMessageBox.information(self, "Связи", "Сначала выбери строку в таблице связанных товаров.")
            return
        row_idx = items[0].row()
        item0 = self.links_table.item(row_idx, 0)
        link_id = item0.data(Qt.ItemDataRole.UserRole) if item0 else None
        if not link_id:
            QMessageBox.warning(self, "Связи", "Не удалось определить идентификатор связи.")
            return
        if QMessageBox.question(self, "Удаление связи", "Удалить выбранную связь маркетплейса?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        if self.catalog_service:
            self.catalog_service.delete_link(link_id)
        self._refresh_links(self._selected_marketplace(), self.current_account_id)

    def show_info(self):
        QMessageBox.information(
            self,
            "Каталог маркетплейсов",
            "В этой ветке можно работать с WB и Ozon.\n\n"
            "Порядок:\n"
            "• сохранить аккаунт\n"
            "• выбрать его в таблице\n"
            "• проверить подключение\n"
            "• загрузить каталог\n"
            "• выбрать карточку и импортировать в товары\n\n"
            "Умный импорт: если внутренний SKU уже есть в справочнике, новый товар не создается — добавляется только привязка маркетплейса и штрихкод."
        )


class ImportMarketplaceProductDialog(QDialog):
    def __init__(self, product, market_code, db, parent=None):
        super().__init__(parent)
        self.product = product
        self.market_code = market_code
        self.db = db
        self.setWindowTitle("Импорт товара")
        self.setMinimumWidth(560)
        self._auto_art = True
        self._build()

    def _build(self):
        v = QVBoxLayout(self)
        title = QLabel("Импорт товара в справочник Смарт Склад")
        title.setObjectName("title")
        v.addWidget(title)

        form = QFormLayout()
        self.f_art = QLineEdit(self._suggest_internal_sku())
        self.f_art.setPlaceholderText("К001")
        self._setup_art_completer()

        self.f_name = QLineEdit(self.product.name or "")
        self.f_cat = QLineEdit(self.product.category or "")

        self.f_unit = QComboBox()
        self.f_unit.setEditable(True)
        self.f_unit.addItems(["шт", "кг", "м", "л", "уп"])

        self.f_min = QSpinBox()
        self.f_min.setRange(0, 999999)

        self.f_supplier = QLineEdit(self.product.brand or "")
        self.f_note = QLineEdit(f"Импортировано из {'Ozon' if self.market_code == 'ozon' else 'WB'}. offer/vendor: {self.product.offer_id or self.product.vendor_code or ''}")

        self.f_barcode = QComboBox()
        self.f_barcode.setEditable(True)
        barcodes = self._extract_barcodes()
        if barcodes:
            self.f_barcode.addItems(barcodes)
        else:
            self.f_barcode.addItem("")
        self._setup_barcode_completer()

        self.f_art.textEdited.connect(lambda _t: setattr(self, "_auto_art", False))
        self.f_barcode.currentTextChanged.connect(self._on_barcode_changed)

        form.addRow("Внутренний SKU *", self.f_art)
        form.addRow("Наименование", self.f_name)
        form.addRow("Категория", self.f_cat)
        form.addRow("Единица", self.f_unit)
        form.addRow("Мин. остаток", self.f_min)
        form.addRow("Бренд / поставщик", self.f_supplier)
        form.addRow(f"{'Ozon' if self.market_code == 'ozon' else 'WB'} штрихкод", self.f_barcode)
        if self.market_code == "wb":
            self.lbl_sizes = QLabel(self._market_sizes_text())
            self.lbl_sizes.setWordWrap(True)
            self.lbl_sizes.setStyleSheet(f"font-size:11px;color:{MUTED};")
            form.addRow("Размеры WB", self.lbl_sizes)
        form.addRow("Примечание", self.f_note)
        v.addLayout(form)

        hint = QLabel("Если такой внутренний SKU уже есть, новый товар не создается: будет добавлена только MP-привязка и штрихкод.")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"font-size:11px;color:{MUTED};")
        v.addWidget(hint)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        v.addWidget(buttons)

    def _setup_art_completer(self):
        values = []
        try:
            for row in self.db.get_products():
                art = str((row["art"] if hasattr(row, "keys") and "art" in row.keys() else (row[1] if not hasattr(row, "keys") else row[0]))).strip()
                if art and art not in values:
                    values.append(art)
        except Exception:
            pass
        if not values:
            return
        comp = QCompleter(values, self)
        comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        comp.setFilterMode(Qt.MatchFlag.MatchContains)
        comp.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.f_art.setCompleter(comp)

    def _setup_barcode_completer(self):
        values = []
        current = [self.f_barcode.itemText(i).strip() for i in range(self.f_barcode.count())]
        for bc in current:
            if bc and bc not in values:
                values.append(bc)
        try:
            market = self.market_code
            products = self.db.get_products()
            for row in products:
                pid = row["id"] if hasattr(row, "keys") and "id" in row.keys() else row[0]
                for bc_row in self.db.get_product_barcodes(pid):
                    mp = str(bc_row["marketplace_code"] if hasattr(bc_row, "keys") and "marketplace_code" in bc_row.keys() else '').strip().lower()
                    bc = str(bc_row["barcode"] if hasattr(bc_row, "keys") and "barcode" in bc_row.keys() else '').strip()
                    if market and mp == market and bc and bc not in values:
                        values.append(bc)
        except Exception:
            pass
        if not values:
            return
        line = self.f_barcode.lineEdit()
        if line is None:
            return
        comp = QCompleter(values, self)
        comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        comp.setFilterMode(Qt.MatchFlag.MatchContains)
        comp.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        line.setCompleter(comp)

    def _suggest_internal_sku(self):
        # 1) сначала ищем уже известный внутренний SKU по barcode
        for bc in self._extract_barcodes():
            try:
                row = self.db.get_product_by_barcode(str(bc).strip())
            except Exception:
                row = None
            if row:
                try:
                    return str(row["art"]).strip()
                except Exception:
                    try:
                        return str(row[1]).strip()
                    except Exception:
                        pass

        # 2) затем пробуем найти существующий товар по offer/vendor
        if self.market_code == "ozon":
            raw = str(self.product.offer_id or self.product.vendor_code or "").strip()
        else:
            raw = str(self.product.vendor_code or self.product.offer_id or "").strip()
        if not raw:
            return ""
        raw = raw.replace("—", "-").replace("–", "-")
        import re
        parts = re.split(r"[\s/|]+", raw)
        candidate = parts[0].strip() if parts else raw
        candidate = candidate or raw
        try:
            existing = self.db.get_product(candidate)
        except Exception:
            existing = None
        if existing:
            return candidate
        return candidate

    def _on_barcode_changed(self, text):
        if not getattr(self, "_auto_art", True):
            return
        bc = str(text or "").strip()
        if not bc:
            return
        try:
            row = self.db.get_product_by_barcode(bc)
        except Exception:
            row = None
        if row:
            try:
                art = str(row["art"]).strip()
            except Exception:
                try:
                    art = str(row[1]).strip()
                except Exception:
                    art = ""
            if art:
                self.f_art.setText(art)

    def _extract_barcodes(self):
        result = []
        if self.market_code == "wb":
            raw = getattr(self.product, "raw_data", None) or {}
            for size in raw.get("sizes") or []:
                for sku in size.get("skus") or []:
                    sb = str(sku or "").strip()
                    if sb and sb not in result:
                        result.append(sb)
        for barcode in (self.product.barcodes or []):
            sb = str(barcode or "").strip()
            if sb and sb not in result:
                result.append(sb)
        return result

    def _market_sizes_text(self):
        if self.market_code != "wb":
            return ""
        raw = getattr(self.product, "raw_data", None) or {}
        parts = []
        for size in raw.get("sizes") or []:
            tech = str(size.get("techSize") or "").strip()
            wb = str(size.get("wbSize") or "").strip()
            skus = [str(x).strip() for x in (size.get("skus") or []) if str(x).strip()]
            label = tech or wb or "без размера"
            if tech and wb and wb != tech:
                label = f"{tech} / {wb}"
            if skus:
                label += f": {', '.join(skus)}"
            parts.append(label)
        return "\n".join(parts) if parts else "Размеры/штрихкоды не пришли от WB"

    def get_data(self):
        return {
            "art": self.f_art.text().strip(),
            "name": self.f_name.text().strip(),
            "cat": self.f_cat.text().strip(),
            "unit": self.f_unit.currentText().strip(),
            "min_stock": self.f_min.value(),
            "supplier": self.f_supplier.text().strip(),
            "barcode": self.f_barcode.currentText().strip(),
            "note": self.f_note.text().strip(),
        }
