from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MarketplaceCredentials:
    account_name: str = ""
    api_key: str = ""
    client_id: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MarketplaceProduct:
    marketplace_code: str
    external_id: str = ""
    sku: str = ""
    offer_id: str = ""
    vendor_code: str = ""
    name: str = ""
    category: str = ""
    brand: str = ""
    barcodes: List[str] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)


class MarketplaceAdapter(ABC):
    code: str = ""
    display_name: str = ""

    def __init__(self, settings_service=None):
        self.settings_service = settings_service

    @abstractmethod
    def validate_credentials(self, credentials: Optional[MarketplaceCredentials] = None) -> tuple[bool, str]:
        raise NotImplementedError

    @abstractmethod
    def fetch_products(self, credentials: Optional[MarketplaceCredentials] = None) -> List[MarketplaceProduct]:
        raise NotImplementedError

    def fetch_stock(self, credentials: Optional[MarketplaceCredentials] = None):
        return []

    def push_stock(self, items, credentials: Optional[MarketplaceCredentials] = None):
        return {"success": False, "message": "Метод еще не реализован"}

    def fetch_orders(self, credentials: Optional[MarketplaceCredentials] = None):
        return []

    def fetch_sales(self, credentials: Optional[MarketplaceCredentials] = None):
        return []

    def fetch_warehouses(self, credentials: Optional[MarketplaceCredentials] = None):
        return []
