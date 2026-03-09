from __future__ import annotations

from marketplaces.base import MarketplaceAdapter


class AliExpressAdapter(MarketplaceAdapter):
    code = "aliexpress"
    display_name = "AliExpress"

    def validate_credentials(self, credentials=None):
        return True, "Каркас адаптера AliExpress подключен"

    def fetch_products(self, credentials=None):
        return []
