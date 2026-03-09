"""services/marketplace_catalog_service.py"""

import json

from marketplaces.base import MarketplaceCredentials


class MarketplaceCatalogService:
    def __init__(self, db, marketplace_service=None):
        self.db = db
        self.marketplace_service = marketplace_service

    def get_accounts(self, marketplace_code=None, only_active=False):
        rows = self.db.get_marketplace_accounts(
            marketplace_code=marketplace_code,
            only_active=only_active,
        )
        return [dict(r) for r in rows]

    def get_account(self, account_id):
        if not account_id:
            return None
        rows = self.db.get_marketplace_accounts()
        for row in rows:
            if row.get("id") == account_id:
                return row
        return None

    def save_account(self, account_id, marketplace_code, account_name, api_key="", client_id="", extra=None, is_active=True):
        return self.db.save_marketplace_account(
            account_id=account_id,
            marketplace_code=marketplace_code,
            account_name=account_name,
            api_key=api_key,
            client_id=client_id,
            extra_json=json.dumps(extra or {}, ensure_ascii=False),
            is_active=is_active,
        )

    def delete_account(self, account_id):
        self.db.delete_marketplace_account(account_id)

    def get_product_barcodes(self, product_id):
        return [dict(r) for r in self.db.get_product_barcodes(product_id)]

    def add_product_barcode(self, product_id, barcode, source="", marketplace_code="", is_primary=False):
        self.db.add_product_barcode(
            product_id=product_id,
            barcode=barcode,
            source=source,
            marketplace_code=marketplace_code,
            is_primary=is_primary,
        )

    def get_links(self, product_id=None, marketplace_code=None):
        rows = self.db.get_marketplace_product_links(
            product_id=product_id,
            marketplace_code=marketplace_code,
        )
        return [dict(r) for r in rows]

    def link_product(self, product_id, marketplace_code, account_id=None,
                     external_product_id="", external_sku="", external_offer_id="",
                     vendor_code="", external_name="", raw_payload=None):
        return self.db.upsert_marketplace_product_link(
            product_id=product_id,
            marketplace_code=marketplace_code,
            account_id=account_id,
            external_product_id=external_product_id,
            external_sku=external_sku,
            external_offer_id=external_offer_id,
            vendor_code=vendor_code,
            external_name=external_name,
            raw_payload_json=json.dumps(raw_payload or {}, ensure_ascii=False),
        )

    def build_credentials(self, account_row):
        extra = {}
        raw_extra = account_row.get("extra_json") if account_row else "{}"
        try:
            extra = json.loads(raw_extra or "{}")
        except Exception:
            extra = {}
        return MarketplaceCredentials(
            account_name=account_row.get("account_name", "") if account_row else "",
            api_key=account_row.get("api_key", "") if account_row else "",
            client_id=account_row.get("client_id", "") if account_row else "",
            extra=extra,
        )

    def fetch_products_preview(self, marketplace_code, account_id):
        if not self.marketplace_service:
            raise RuntimeError("MarketplaceService не подключен")
        account = self.get_account(account_id)
        if not account:
            raise ValueError("Аккаунт маркетплейса не найден")
        credentials = self.build_credentials(account)
        products = self.marketplace_service.fetch_products(marketplace_code, credentials)
        rows = []
        for item in products:
            rows.append({
                "marketplace_code": item.marketplace_code,
                "external_id": item.external_id,
                "sku": item.sku,
                "offer_id": item.offer_id,
                "vendor_code": item.vendor_code,
                "name": item.name,
                "category": item.category,
                "brand": item.brand,
                "barcodes": list(item.barcodes or []),
                "raw_data": dict(item.raw_data or {}),
            })
        return rows
