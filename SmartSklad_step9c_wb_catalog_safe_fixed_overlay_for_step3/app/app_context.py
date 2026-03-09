"""app/app_context.py
Единый контейнер зависимостей приложения.

Первая полезная итерация:
- храним db
- подключаем первые сервисы
- UI начинает зависеть от ctx/services, а не только от db
"""

from services.products_service import ProductsService
from services.warehouses_service import WarehousesService
from services.settings_service import SettingsService
from services.marketplace_catalog_service import MarketplaceCatalogService
from marketplaces.registry import MarketplaceRegistry
from marketplaces.service import MarketplaceService


class AppContext:
    def __init__(self, db):
        self.db = db

        self.products_service = ProductsService(db)
        self.warehouses_service = WarehousesService(db)
        self.settings_service = SettingsService(db)

        self.marketplace_registry = MarketplaceRegistry(settings_service=self.settings_service)
        self.marketplace_service = MarketplaceService(self.marketplace_registry)
        self.marketplace_catalog_service = MarketplaceCatalogService(db, marketplace_service=self.marketplace_service)

        # Следующие сервисы подключим поэтапно,
        # чтобы не ломать рабочий проект.
        self.stock_service = None
        self.movements_service = None
        self.labels_service = None
