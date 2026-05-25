from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .models import ProductOffer


BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CACHE_PATH = BASE_DIR / "data" / "ecommerce_cache.json"


def normalize_cache_part(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


class EcommerceCache:
    def __init__(self, path: Path = DEFAULT_CACHE_PATH, ttl_minutes: int = 30):
        self.path = path
        self.ttl = timedelta(minutes=ttl_minutes)

    def make_key(self, platform: str, query: str, max_results: int) -> str:
        return "|".join([
            normalize_cache_part(platform),
            normalize_cache_part(query),
            str(max_results),
        ])

    def get(self, platform: str, query: str, max_results: int) -> list[ProductOffer] | None:
        data = self._read()
        item = data.get(self.make_key(platform, query, max_results))
        if not item:
            return None
        fetched_at = self._parse_time(item.get("fetched_at", ""))
        if fetched_at is None or datetime.now(timezone.utc) - fetched_at > self.ttl:
            return None
        offers = [ProductOffer.from_dict(raw) for raw in item.get("offers", [])]
        return offers

    def set(self, platform: str, query: str, max_results: int, offers: list[ProductOffer]) -> None:
        data = self._read()
        key = self.make_key(platform, query, max_results)
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        data[key] = {
            "fetched_at": now,
            "offers": [offer.to_dict() for offer in offers],
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _read(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _parse_time(value: str) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

