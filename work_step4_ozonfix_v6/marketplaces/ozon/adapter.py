from __future__ import annotations

import json
from typing import List
from urllib import error, request

from marketplaces.base import MarketplaceAdapter, MarketplaceCredentials, MarketplaceProduct


class OzonAdapter(MarketplaceAdapter):
    code = "ozon"
    display_name = "Ozon"
    PRODUCT_LIST_URL = "https://api-seller.ozon.ru/v2/product/list"
    PRODUCT_INFO_LIST_URL = "https://api-seller.ozon.ru/v2/product/info/list"

    def validate_credentials(self, credentials: MarketplaceCredentials | None = None):
        credentials = credentials or MarketplaceCredentials()
        api_key = (credentials.api_key or "").strip()
        client_id = str(credentials.client_id or "").strip()
        if not client_id:
            return False, "Для Ozon нужен Client ID"
        if not api_key:
            return False, "Для Ozon нужен API key"

        payload = {
            "filter": {"visibility": "ALL"},
            "last_id": "",
            "limit": 1,
        }
        try:
            data = self._post_json(self.PRODUCT_LIST_URL, payload, client_id, api_key)
            result = data.get("result") or {}
            items = result.get("items") or []
            return True, f"Подключение к Ozon успешно. API отвечает, товаров в ответе: {len(items)}"
        except Exception as e:
            return False, str(e)

    def fetch_products(self, credentials: MarketplaceCredentials | None = None) -> List[MarketplaceProduct]:
        credentials = credentials or MarketplaceCredentials()
        ok, message = self.validate_credentials(credentials)
        if not ok:
            raise ValueError(message)

        all_items = []
        last_id = ""
        for _ in range(10):
            payload = {
                "filter": {},
                "last_id": last_id,
                "limit": 100,
            }
            data = self._post_json(self.PRODUCT_LIST_URL, payload, credentials.client_id, credentials.api_key)
            result = data.get("result") or {}
            items = result.get("items") or []
            if not items:
                break
            all_items.extend(items)
            next_last_id = result.get("last_id") or ""
            if not next_last_id or next_last_id == last_id or len(items) < 100:
                break
            last_id = next_last_id

        info_map = self._fetch_info_map(credentials.client_id, credentials.api_key, all_items)
        products: List[MarketplaceProduct] = []
        for item in all_items:
            info = self._find_info_for_item(item, info_map)
            products.append(self._map_item(item, info))
        return products

    def _fetch_info_map(self, client_id: str, api_key: str, items: list[dict]) -> dict[str, dict]:
        """Получаем детали товаров батчами по product_id.

        Для Ozon в реальном кабинете пользователя стабильно сработал сценарий:
        - список товаров через /v2/product/list
        - детали через /v2/product/info/list c телом {"product_id": [...]}
        """
        result_map: dict[str, dict] = {}

        product_ids = []
        for item in items:
            product_id = item.get("product_id") or item.get("id")
            if product_id is None:
                continue
            try:
                pid = int(product_id)
            except Exception:
                continue
            if pid not in product_ids:
                product_ids.append(pid)

        for start in range(0, len(product_ids), 100):
            chunk = product_ids[start:start + 100]
            if not chunk:
                continue
            try:
                data = self._post_json(
                    self.PRODUCT_INFO_LIST_URL,
                    {"product_id": chunk},
                    client_id,
                    api_key,
                )
                for info in self._extract_info_items(data):
                    for key in self._possible_info_keys(info):
                        if key and key not in result_map:
                            result_map[key] = info
            except Exception:
                pass

        return result_map

    def _extract_info_items(self, data: dict):
        result = data.get("result") or []
        if isinstance(result, dict):
            return result.get("items") or []
        if isinstance(result, list):
            return result
        return []

    def _possible_info_keys(self, info: dict) -> list[str]:
        keys = []
        for raw in (
            info.get("offer_id"), info.get("offerId"),
            info.get("id"), info.get("product_id"),
            info.get("sku"),
        ):
            sval = str(raw or "").strip()
            if sval and sval not in keys:
                keys.append(sval)
        return keys


    def _find_info_for_item(self, item: dict, info_map: dict[str, dict]) -> dict:
        for raw in (item.get("offer_id"), item.get("product_id"), item.get("id"), item.get("sku")):
            sval = str(raw or "").strip()
            if sval and sval in info_map:
                return info_map[sval]
        return {}

    def _item_key(self, item: dict) -> str:
        for raw in (item.get("offer_id"), item.get("product_id"), item.get("id"), item.get("sku")):
            sval = str(raw or "").strip()
            if sval:
                return sval
        return ""

    def _extract_barcodes(self, item: dict, info: dict) -> list[str]:
        barcodes = []
        candidates = [
            info.get("barcodes"), item.get("barcodes"),
            info.get("barcode"), item.get("barcode"),
            info.get("sources"), item.get("sources"),
        ]
        for source in candidates:
            if isinstance(source, list):
                for val in source:
                    if isinstance(val, dict):
                        for k in ("barcode", "value", "sku"):
                            sv = str(val.get(k) or "").strip()
                            if sv and sv not in barcodes:
                                barcodes.append(sv)
                    else:
                        sv = str(val or "").strip()
                        if sv and sv not in barcodes:
                            barcodes.append(sv)
            elif isinstance(source, str):
                sv = source.strip()
                if sv and sv not in barcodes:
                    barcodes.append(sv)
        return barcodes

    def _pick(self, *values) -> str:
        for value in values:
            if value is None:
                continue
            if isinstance(value, str):
                sval = value.strip()
                if sval:
                    return sval
            elif value not in (None, "", [], {}):
                return str(value)
        return ""

    def _map_item(self, item: dict, info: dict) -> MarketplaceProduct:
        product_id = self._pick(item.get("product_id"), item.get("id"), info.get("id"), info.get("product_id"))
        offer_id = self._pick(item.get("offer_id"), info.get("offer_id"), info.get("offerId"))
        sku = self._pick(item.get("sku"), info.get("sku"))
        if not sku:
            sources = info.get("sources") or item.get("sources") or []
            if isinstance(sources, list) and sources:
                first = sources[0]
                if isinstance(first, dict):
                    sku = self._pick(first.get("sku"), first.get("value"), first.get("barcode"))
                else:
                    sku = self._pick(first)

        name = self._pick(
            info.get("name"), info.get("title"),
            item.get("name"), item.get("title"),
            offer_id, sku, product_id,
        )
        category = self._pick(
            info.get("category_name"), info.get("description_category_name"),
            item.get("category_name"), item.get("type_name"),
        )
        brand = self._pick(info.get("brand"), item.get("brand"))
        barcodes = self._extract_barcodes(item, info)

        vendor_code = offer_id or sku or product_id

        raw_data = {"list_item": item, "info": info}
        return MarketplaceProduct(
            marketplace_code=self.code,
            external_id=product_id,
            sku=sku,
            offer_id=offer_id,
            vendor_code=vendor_code,
            name=name,
            category=category,
            brand=brand,
            barcodes=barcodes,
            raw_data=raw_data,
        )

    def _post_json(self, url: str, payload: dict, client_id: str, api_key: str) -> dict:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Client-Id": str(client_id),
                "Api-Key": str(api_key),
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with request.urlopen(req, timeout=45) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Ozon API HTTP {e.code}: {detail[:500]}")
        except error.URLError as e:
            raise RuntimeError(f"Ozon API недоступен: {e.reason}")
