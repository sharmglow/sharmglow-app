from __future__ import annotations

from marketplaces.base import MarketplaceAdapter, MarketplaceProduct


class OzonAdapter(MarketplaceAdapter):
    code = "ozon"
    display_name = "Ozon"

    def validate_credentials(self, credentials=None):
        return True, "Каркас адаптера Ozon подключен"

    def fetch_products(self, credentials=None):
        # Следующим шагом подключим реальный Ozon API.
        return []
