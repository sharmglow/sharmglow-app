from __future__ import annotations

from marketplaces.base import MarketplaceCredentials
from marketplaces.registry import MarketplaceRegistry


class MarketplaceService:
    def __init__(self, registry: MarketplaceRegistry):
        self.registry = registry

    def get_marketplaces(self):
        return self.registry.get_items_for_ui()

    def list_adapters(self):
        adapters = []
        for code in self.registry.get_codes():
            adapter = self.registry.get_adapter(code)
            if adapter:
                adapters.append(adapter)
        return adapters

    def validate_credentials(self, marketplace_code: str, credentials: MarketplaceCredentials | None = None):
        adapter = self.registry.get_adapter_or_raise(marketplace_code)
        return adapter.validate_credentials(credentials)

    def fetch_products(self, marketplace_code: str, credentials: MarketplaceCredentials | None = None):
        adapter = self.registry.get_adapter_or_raise(marketplace_code)
        return adapter.fetch_products(credentials)
