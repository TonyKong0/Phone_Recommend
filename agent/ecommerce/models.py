from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(slots=True)
class ProductOffer:
    platform: str
    title: str = ""
    price_cny: float | None = None
    shop_name: str = ""
    product_url: str = ""
    image_url: str = ""
    sales_text: str = ""
    rating_text: str = ""
    source_item_id: str = ""
    raw_rank: int = 0
    fetched_at: str = field(default_factory=utc_now_iso)
    status: str = "ok"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProductOffer":
        fields = cls.__dataclass_fields__
        return cls(**{k: v for k, v in data.items() if k in fields})

    @property
    def ok(self) -> bool:
        return self.status == "ok" and bool(self.title)

