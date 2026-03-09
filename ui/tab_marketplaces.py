
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QFrame,
    QComboBox, QLineEdit, QPushButton, QCheckBox,
    QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView
)
from PyQt6.QtCore import Qt

class MarketplacesTab(QWidget):
    def __init__(self, db, main_win=None):
        super().__init__()
        self.db = db
        self.main_win = main_win
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Маркетплейсы")
        title.setStyleSheet("font-size:18px;font-weight:700;")
        layout.addWidget(title)

        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(10)

        row1 = QHBoxLayout()
        self.cb_market = QComboBox()
        self.cb_market.addItems(["wb", "ozon", "yandex_market", "aliexpress"])
        self.ed_name = QLineEdit()
        self.ed_name.setPlaceholderText("Название аккаунта")
        row1.addWidget(QLabel("Маркетплейс:"))
        row1.addWidget(self.cb_market)
        row1.addWidget(QLabel("Аккаунт:"))
        row1.addWidget(self.ed_name)
        card_layout.addLayout(row1)

        row2 = QHBoxLayout()
        self.ed_api_key = QLineEdit()
        self.ed_api_key.setPlaceholderText("API key / token")
        self.ed_client_id = QLineEdit()
        self.ed_client_id.setPlaceholderText("Client ID / Seller ID")
        row2.addWidget(QLabel("Ключ:"))
        row2.addWidget(self.ed_api_key)
        row2.addWidget(QLabel("Client ID:"))
        row2.addWidget(self.ed_client_id)
        card_layout.addLayout(row2)

        row3 = QHBoxLayout()
        self.chk_active = QCheckBox("Активный аккаунт")
        self.btn_save = QPushButton("Сохранить")
        self.btn_delete = QPushButton("Удалить")
        self.btn_test = QPushButton("Проверить адаптер")
        row3.addWidget(self.chk_active)
        row3.addStretch()
        row3.addWidget(self.btn_test)
        row3.addWidget(self.btn_delete)
        row3.addWidget(self.btn_save)
        card_layout.addLayout(row3)

        layout.addWidget(card)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            "ID", "Маркетплейс", "Аккаунт", "Client ID", "Активен"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.itemSelectionChanged.connect(self._load_selected)
        layout.addWidget(self.table, 1)

        self.btn_save.clicked.connect(self._save_account)
        self.btn_delete.clicked.connect(self._delete_account)
        self.btn_test.clicked.connect(self._test_adapter)

    def refresh(self):
        self._fill_table()

    def _ensure_accounts_table(self):
        with self.db.connect() as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS marketplace_accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    marketplace_code TEXT NOT NULL,
                    account_name TEXT NOT NULL,
                    api_key TEXT DEFAULT '',
                    client_id TEXT DEFAULT '',
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            con.commit()

    def _fill_table(self):
        self._ensure_accounts_table()
        with self.db.connect() as con:
            rows = con.execute(
                "SELECT id, marketplace_code, account_name, client_id, is_active FROM marketplace_accounts ORDER BY id DESC"
            ).fetchall()

        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            values = [row[0], row[1], row[2], row[3], "Да" if row[4] else "Нет"]
            for c, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if c == 0:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(r, c, item)

    def _load_selected(self):
        items = self.table.selectedItems()
        if not items:
            return
        acc_id = int(items[0].text())
        with self.db.connect() as con:
            row = con.execute(
                "SELECT id, marketplace_code, account_name, api_key, client_id, is_active FROM marketplace_accounts WHERE id = ?",
                (acc_id,)
            ).fetchone()
        if not row:
            return
        self.cb_market.setCurrentText(row[1])
        self.ed_name.setText(row[2] or "")
        self.ed_api_key.setText(row[3] or "")
        self.ed_client_id.setText(row[4] or "")
        self.chk_active.setChecked(bool(row[5]))

    def _save_account(self):
        self._ensure_accounts_table()
        market = self.cb_market.currentText().strip()
        name = self.ed_name.text().strip()
        api_key = self.ed_api_key.text().strip()
        client_id = self.ed_client_id.text().strip()
        is_active = 1 if self.chk_active.isChecked() else 0
        if not name:
            QMessageBox.warning(self, "Смарт Склад", "Укажи название аккаунта.")
            return

        selected = self.table.selectedItems()
        with self.db.connect() as con:
            if selected:
                acc_id = int(selected[0].text())
                con.execute(
                    "UPDATE marketplace_accounts SET marketplace_code=?, account_name=?, api_key=?, client_id=?, is_active=? WHERE id=?",
                    (market, name, api_key, client_id, is_active, acc_id)
                )
            else:
                con.execute(
                    "INSERT INTO marketplace_accounts (marketplace_code, account_name, api_key, client_id, is_active) VALUES (?, ?, ?, ?, ?)",
                    (market, name, api_key, client_id, is_active)
                )
            con.commit()
        self.refresh()
        QMessageBox.information(self, "Смарт Склад", "Аккаунт сохранён.")

    def _delete_account(self):
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Смарт Склад", "Выбери аккаунт в таблице.")
            return
        acc_id = int(selected[0].text())
        with self.db.connect() as con:
            con.execute("DELETE FROM marketplace_accounts WHERE id = ?", (acc_id,))
            con.commit()
        self.ed_name.clear()
        self.ed_api_key.clear()
        self.ed_client_id.clear()
        self.chk_active.setChecked(False)
        self.refresh()
        QMessageBox.information(self, "Смарт Склад", "Аккаунт удалён.")

    def _test_adapter(self):
        QMessageBox.information(
            self,
            "Смарт Склад",
            "Архитектура маркетплейсов подключена. Реальные API-вызовы добавим следующим шагом."
        )
