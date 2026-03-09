"""ui/main_window.py"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QStatusBar, QFileDialog,
    QMessageBox, QFrame
)
from PyQt6.QtGui import QAction, QKeySequence

from ui.styles import APP_STYLE, INK, GOLD_L
from ui.tab_scanner import ScannerTab
from ui.tab_stock import StockTab
from ui.tab_products import ProductsTab
from ui.tab_history import HistoryTab
from ui.tab_warehouses import WarehousesTab
from ui.tab_labels import LabelsTab
from ui.tab_sync import SyncTab
from ui.tab_marketplace_catalog import MarketplaceCatalogTab


class MainWindow(QMainWindow):
    def __init__(self, db_or_ctx):
        super().__init__()

        # Переходный режим:
        # - можно передать старый db
        # - можно передать новый AppContext
        if hasattr(db_or_ctx, "db"):
            self.ctx = db_or_ctx
            self.db = db_or_ctx.db
        else:
            self.ctx = None
            self.db = db_or_ctx

        self.setWindowTitle("Смарт Склад — SmartSklad")
        self.resize(1280, 800)
        self.setStyleSheet(APP_STYLE)

        self._build_menu()
        self._build_ui()
        self._build_status()

    def _build_menu(self):
        mb = self.menuBar()
        mb.setStyleSheet(f"background:{INK};color:#ccc;")

        # Файл
        fm = mb.addMenu("Файл")

        a_import = QAction("📂 Импорт из xlsx…", self)
        a_import.setShortcut(QKeySequence("Ctrl+O"))
        a_import.triggered.connect(self.do_import)
        fm.addAction(a_import)

        a_export = QAction("💾 Экспорт в xlsx…", self)
        a_export.setShortcut(QKeySequence("Ctrl+S"))
        a_export.triggered.connect(self.do_export)
        fm.addAction(a_export)

        fm.addSeparator()

        a_quit = QAction("Выйти", self)
        a_quit.setShortcut(QKeySequence("Ctrl+Q"))
        a_quit.triggered.connect(self.close)
        fm.addAction(a_quit)

        # Помощь
        hm = mb.addMenu("Помощь")

        a_about = QAction("О программе", self)
        a_about.triggered.connect(self.show_about)
        hm.addAction(a_about)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setFixedHeight(50)
        header.setStyleSheet(f"background:{INK};border-bottom:2px solid {GOLD_L};")

        hl = QHBoxLayout(header)
        hl.setContentsMargins(20, 0, 20, 0)

        brand = QLabel("SmartSklad")
        brand.setStyleSheet(
            f"font-family:'Georgia',serif;font-size:20px;font-weight:700;"
            f"color:{GOLD_L};letter-spacing:0.04em;"
        )

        sub = QLabel("Смарт Склад")
        sub.setStyleSheet(
            "font-size:11px;color:#888;letter-spacing:0.12em;"
            "text-transform:uppercase;margin-left:10px;"
        )

        hl.addWidget(brand)
        hl.addWidget(sub)
        hl.addStretch()

        db_label = QLabel(f"📁 {self.db.path.name}")
        db_label.setStyleSheet("font-size:11px;color:#666;font-family:monospace;")
        hl.addWidget(db_label)

        layout.addWidget(header)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        layout.addWidget(self.tabs)

        # Пока вкладки продолжают работать через self.db.
        # Это безопасный переходный этап.
        self.tab_scanner = ScannerTab(self.db, self)
        self.tab_stock = StockTab(self.db, self)
        self.tab_products = ProductsTab(self.db, self)
        self.tab_history = HistoryTab(self.db, self)
        self.tab_warehouses = WarehousesTab(self.db, self)
        self.tab_labels = LabelsTab(self.db, self)
        self.tab_sync = SyncTab(self.db, self)
        self.tab_market_catalog = MarketplaceCatalogTab(self.db, self)

        self.tabs.addTab(self.tab_scanner, "🔍  Сканер")
        self.tabs.addTab(self.tab_stock, "📊  Остатки")
        self.tabs.addTab(self.tab_products, "📦  Товары")
        self.tabs.addTab(self.tab_market_catalog, "🧩  Каталог MP")
        self.tabs.addTab(self.tab_history, "📋  История")
        self.tabs.addTab(self.tab_warehouses, "🏭  Склады")
        self.tabs.addTab(self.tab_labels, "🏷️   Этикетки")
        self.tabs.addTab(self.tab_sync, "🔄  Маркетплейсы")

        self.tabs.currentChanged.connect(self.on_tab_changed)

    def _build_status(self):
        sb = QStatusBar()
        sb.setStyleSheet(f"background:{INK};color:#666;font-size:11px;")
        self.setStatusBar(sb)

        self.status_msg = QLabel("")
        self.status_msg.setStyleSheet("color:#aaa;")
        sb.addPermanentWidget(self.status_msg)

        self._refresh_status()

    def _refresh_status(self):
        prods = len(self.db.get_products())
        whs = len(self.db.get_warehouses())
        self.status_msg.setText(f"Товаров: {prods}   Складов: {whs}")

    def on_tab_changed(self, idx):
        tab = self.tabs.widget(idx)
        if hasattr(tab, "refresh"):
            tab.refresh()

    def refresh_all(self):
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if hasattr(tab, "refresh"):
                tab.refresh()
        self._refresh_status()

    def set_status(self, msg, ms=3000):
        self.statusBar().showMessage(msg, ms)

    def do_import(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Импорт из xlsx", "", "Excel (*.xlsx)"
        )
        if not path:
            return

        try:
            r = self.db.import_xlsx(path)
            self.refresh_all()
            QMessageBox.information(
                self,
                "Импорт завершён",
                f"Импортировано:\n"
                f"  Товаров:       {r['products']}\n"
                f"  Складов:       {r['warehouses']}\n"
                f"  Поступлений:   {r['arrivals']}\n"
                f"  Перемещений:   {r['moves']}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Ошибка импорта", str(e))

    def do_export(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт в xlsx", "smartsklad_export.xlsx", "Excel (*.xlsx)"
        )
        if not path:
            return

        try:
            self.db.export_xlsx(path)
            self.set_status(f"✓ Экспортировано: {path}")
            QMessageBox.information(self, "Готово", f"Файл сохранён:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка экспорта", str(e))

    def show_about(self):
        QMessageBox.about(
            self,
            "Смарт Склад",
            "<b>Смарт Склад / SmartSklad</b><br><br>"
            "Учёт товаров на складе с поддержкой<br>"
            "маркетплейсов WB и OZON.<br><br>"
            "База данных: SQLite<br>"
            "Этикетки: ReportLab PDF"
        )
