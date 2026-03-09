from __future__ import annotations

from typing import Dict, List, Optional, Type

from marketplaces.base import MarketplaceAdapter
from marketplaces.wb.adapter import WBAdapter
from marketplaces.ozon.adapter import OzonAdapter
from marketplaces.yandex_market.adapter import YandexMarketAdapter
from marketplaces.aliexpress.adapter import AliExpressAdapter


class MarketplaceRegistry:
    def __init__(self, settings_service=None):
        self.settings_service = settings_service
        self._classes: Dict[str, Type[MarketplaceAdapter]] = {
            "wb": WBAdapter,
            "ozon": OzonAdapter,
            "yandex_market": YandexMarketAdapter,
            "aliexpress": AliExpressAdapter,
        }

    def get_codes(self) -> List[str]:
        return list(self._classes.keys())

    def get_adapter(self, code: str) -> Optional[MarketplaceAdapter]:
        cls = self._classes.get(code)
        if not cls:
            return None
        return cls(settings_service=self.settings_service)

    def get_adapter_or_raise(self, code: str) -> MarketplaceAdapter:
        adapter = self.get_adapter(code)
        if not adapter:
            raise ValueError(f"Маркетплейс не зарегистрирован: {code}")
        return adapter

    def get_items_for_ui(self):
        items = []
        for code in self.get_codes():
            adapter = self.get_adapter(code)
            items.append({
                "code": adapter.code,
                "display_name": adapter.display_name,
            })
        return items
