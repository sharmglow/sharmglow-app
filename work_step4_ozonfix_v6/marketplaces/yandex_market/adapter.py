from __future__ import annotations

from marketplaces.base import MarketplaceAdapter


class YandexMarketAdapter(MarketplaceAdapter):
    code = "yandex_market"
    display_name = "Яндекс Маркет"

    def validate_credentials(self, credentials=None):
        return True, "Каркас адаптера Яндекс Маркета подключен"

    def fetch_products(self, credentials=None):
        return []
