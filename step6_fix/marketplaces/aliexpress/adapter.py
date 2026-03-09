from marketplaces.base import MarketplaceAdapter, MarketplaceCredentials, MarketplaceProduct
from typing import List

class AliExpressAdapter(MarketplaceAdapter):
    code = "aliexpress"
    display_name = "AliExpress"

    def validate_credentials(self, credentials=None):
        return False, "AliExpress: интеграция в разработке"

    def fetch_products(self, credentials=None) -> List[MarketplaceProduct]:
        return []
