"""services/marketplace_catalog_service.py"""

import json


class MarketplaceCatalogService:
    def __init__(self, db):
        self.db = db

    def get_accounts(self, marketplace_code=None, only_active=False):
        return self.db.get_marketplace_accounts(
            marketplace_code=marketplace_code,
            only_active=only_active,
        )

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
        return self.db.get_product_barcodes(product_id)

    def add_product_barcode(self, product_id, barcode, source="", marketplace_code="", is_primary=False):
        self.db.add_product_barcode(
            product_id=product_id,
            barcode=barcode,
            source=source,
            marketplace_code=marketplace_code,
            is_primary=is_primary,
        )

    def get_links(self, product_id=None, marketplace_code=None):
        return self.db.get_marketplace_product_links(
            product_id=product_id,
            marketplace_code=marketplace_code,
        )

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

    def delete_link(self, link_id):
        self.db.delete_marketplace_product_link(link_id)
