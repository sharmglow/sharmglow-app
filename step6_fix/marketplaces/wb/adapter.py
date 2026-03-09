from __future__ import annotations

import json
from typing import List
from urllib import error, request

from marketplaces.base import MarketplaceAdapter, MarketplaceCredentials, MarketplaceProduct


class WBAdapter(MarketplaceAdapter):
    code = "wb"
    display_name = "Wildberries"
    CARDS_LIST_URL = "https://content-api.wildberries.ru/content/v2/get/cards/list"

    def validate_credentials(self, credentials=None):
        credentials = credentials or MarketplaceCredentials()
        api_key = (credentials.api_key or "").strip()
        if not api_key:
            return False, "Для WB нужен API ключ"

        payload = {
            "settings": {
                "sort": {"ascending": True},
                "cursor": {"limit": 1},
                "filter": {"withPhoto": -1},
            }
        }
        try:
            data = self._post_json(self.CARDS_LIST_URL, payload, api_key)
            cards = data.get("cards") or []
            return True, f"Подключение к WB успешно. API отвечает, карточек в ответе: {len(cards)}"
        except Exception as e:
            return False, str(e)

    def fetch_products(self, credentials: MarketplaceCredentials | None = None) -> List[MarketplaceProduct]:
        credentials = credentials or MarketplaceCredentials()
        ok, message = self.validate_credentials(credentials)
        if not ok:
            raise ValueError(message)

        cards = []
        cursor = {"limit": 100}
        seen = 0

        for _ in range(10):  # до 1000 карточек за один запуск
            payload = {
                "settings": {
                    "sort": {"ascending": True},
                    "cursor": cursor,
                    "filter": {"withPhoto": -1},
                }
            }
            data = self._post_json(self.CARDS_LIST_URL, payload, credentials.api_key)
            chunk = data.get("cards") or []
            if not chunk:
                break

            for card in chunk:
                cards.append(self._map_card(card))

            seen += len(chunk)
            if seen >= 1000:
                break

            cursor_info = data.get("cursor") or {}
            updated_at = cursor_info.get("updatedAt")
            nm_id = cursor_info.get("nmID")
            total = cursor_info.get("total", 0)
            if not updated_at or not nm_id or len(chunk) < payload["settings"]["cursor"]["limit"]:
                break
            cursor = {
                "limit": 100,
                "updatedAt": updated_at,
                "nmID": nm_id,
            }
            if total and seen >= total:
                break

        return cards

    def _post_json(self, url: str, payload: dict, api_key: str) -> dict:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Authorization": api_key,
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
            raise RuntimeError(f"WB API HTTP {e.code}: {detail[:500]}")
        except error.URLError as e:
            raise RuntimeError(f"WB API недоступен: {e.reason}")

    def _map_card(self, card: dict) -> MarketplaceProduct:
        barcodes = []
        sizes = card.get("sizes") or []
        for size in sizes:
            skus = size.get("skus") or []
            for sku in skus:
                sku = str(sku or "").strip()
                if sku and sku not in barcodes:
                    barcodes.append(sku)

        return MarketplaceProduct(
            marketplace_code=self.code,
            external_id=str(card.get("nmID") or ""),
            sku=str(card.get("nmID") or ""),
            offer_id=str(card.get("nmID") or ""),
            vendor_code=str(card.get("vendorCode") or ""),
            name=str(card.get("title") or ""),
            category=str(card.get("subjectName") or ""),
            brand=str(card.get("brand") or ""),
            barcodes=barcodes,
            raw_data=card,
        )
