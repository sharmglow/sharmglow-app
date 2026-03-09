from marketplaces.base import MarketplaceAdapter, MarketplaceCredentials, MarketplaceProduct
from typing import List

class YandexMarketAdapter(MarketplaceAdapter):
    code = "yandex_market"
    display_name = "Яндекс Маркет"

    def validate_credentials(self, credentials=None):
        return False, "Яндекс Маркет: интеграция в разработке"

    def fetch_products(self, credentials=None) -> List[MarketplaceProduct]:
        return []
