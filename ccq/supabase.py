"""Supabase interaction helpers."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Iterable, List, Mapping, Optional

import requests

from ccq.config import get_supabase_credentials

LOGGER = logging.getLogger(__name__)


class SupabaseClient:
    def __init__(self) -> None:
        creds = get_supabase_credentials()
        self.base_url = f"{creds['url']}/rest/v1"
        self.headers = {
            "apikey": creds["key"],
            "Authorization": f"Bearer {creds['key']}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates",
        }

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{self.base_url}/{path.lstrip('/')}"
        response = requests.request(method, url, headers=self.headers, timeout=30, **kwargs)
        if not response.ok:
            LOGGER.error("Supabase request failed: %s %s - %s", method, url, response.text)
            response.raise_for_status()
        return response

    def fetch_cards(self) -> List[Mapping[str, object]]:
        response = self._request("GET", "cards", params={"select": "*"})
        return response.json()

    def upsert(self, table: str, rows: Iterable[Mapping[str, object]]) -> None:
        payload = json.dumps(list(rows))
        self._request("POST", table, data=payload)

    def update(self, table: str, values: Mapping[str, object], *, filters: Optional[Mapping[str, str]] = None) -> None:
        params = filters or {}
        payload = json.dumps(values)
        self._request("PATCH", table, params=params, data=payload)

    def insert_run(self, table: str, run_data: Mapping[str, object]) -> None:
        payload = json.dumps([run_data])
        self._request("POST", table, data=payload)


class SupabaseRepository:
    def __init__(self) -> None:
        self.client = SupabaseClient()

    def fetch_card_index(self) -> Mapping[str, Mapping[str, object]]:
        cards = self.client.fetch_cards()
        index = {}
        for card in cards:
            key = self._build_key(card)
            index[key] = card
        return index

    @staticmethod
    def _build_key(card: Mapping[str, object]) -> str:
        issuer = str(card.get("issuer", "")).strip().lower()
        name = str(card.get("card_name", "")).strip().lower()
        country = str(card.get("country", "")).strip().lower()
        return "::".join(filter(None, [issuer, name, country]))

    def upsert_cards(self, rows: Iterable[Mapping[str, object]]) -> None:
        self.client.upsert("cards_staging", rows)

    def promote_cards(self, cards: Iterable[Mapping[str, object]]) -> None:
        for card in cards:
            filters = {
                "issuer": f"eq.{card['issuer']}",
                "card_name": f"eq.{card['card_name']}",
                "country": f"eq.{card['country']}",
            }
            payload = {"approved": True}
            self.client.update("cards_staging", payload, filters=filters)
            self.client.upsert("cards", [{**card, "approved": True}])

    def record_run(self, report_path: str, counts: Mapping[str, int]) -> None:
        payload = {
            "run_id": datetime.utcnow().isoformat(),
            "report_path": report_path,
            **counts,
        }
        self.client.insert_run("runs", payload)
