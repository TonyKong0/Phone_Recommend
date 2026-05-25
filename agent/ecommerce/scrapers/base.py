from __future__ import annotations

import json
import random
import re
import time
from abc import ABC, abstractmethod
from urllib.parse import urljoin

import requests

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover - exercised in environments without scraper deps
    BeautifulSoup = None

from ..models import ProductOffer


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def parse_price_cny(value: str | int | float | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return round(float(value), 2) if value >= 0 else None
    text = str(value)
    text = text.replace(",", "").replace("￥", "¥")
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    if not match:
        return None
    price = float(match.group(1))
    if price <= 0:
        return None
    return round(price, 2)


def absolute_url(base_url: str, value: str | None) -> str:
    if not value:
        return ""
    value = value.strip()
    if value.startswith("//"):
        return "https:" + value
    return urljoin(base_url, value)


def extract_json_object(text: str, marker: str) -> dict:
    start = text.find(marker)
    if start < 0:
        return {}
    brace_start = text.find("{", start)
    if brace_start < 0:
        return {}
    depth = 0
    in_string = False
    escaped = False
    for idx in range(brace_start, len(text)):
        ch = text[idx]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                raw = text[brace_start:idx + 1]
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    return {}
    return {}


class BaseMarketplaceScraper(ABC):
    platform = ""
    search_url_template = ""
    base_url = ""

    def __init__(self, delay: float = 0.8, timeout: int = 12):
        self.delay = delay
        self.timeout = timeout
        self.session = requests.Session()

    def search(self, query: str, limit: int = 5) -> list[ProductOffer]:
        query = clean_text(query)
        if not query:
            return [self._error_offer("empty_query")]
        try:
            html = self._fetch_requests(query)
            offers = self.parse_html(html, query, limit)
            if offers:
                return self._rank_and_trim(offers, query, limit)
        except Exception:
            pass
        try:
            html = self._fetch_playwright(query)
            offers = self.parse_html(html, query, limit)
            if offers:
                return self._rank_and_trim(offers, query, limit)
            return [self._error_offer("no_public_results")]
        except Exception as exc:
            return [self._error_offer(f"blocked_or_failed: {exc.__class__.__name__}")]

    def _fetch_requests(self, query: str) -> str:
        time.sleep(self.delay)
        response = self.session.get(
            self.build_search_url(query),
            headers=self.headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        response.encoding = response.apparent_encoding or "utf-8"
        return response.text

    def _fetch_playwright(self, query: str) -> str:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1366, "height": 900},
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
            )
            context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            page = context.new_page()
            page.goto(self.build_search_url(query), wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2500)
            html = page.content()
            browser.close()
            return html

    def headers(self) -> dict[str, str]:
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
        }

    def soup(self, html: str) -> BeautifulSoup:
        if BeautifulSoup is None:
            raise RuntimeError("beautifulsoup4 is required for ecommerce scraping")
        return BeautifulSoup(html, "lxml")

    def build_search_url(self, query: str) -> str:
        from urllib.parse import quote

        return self.search_url_template.format(query=quote(query))

    @abstractmethod
    def parse_html(self, html: str, query: str, limit: int) -> list[ProductOffer]:
        raise NotImplementedError

    def _offer(
        self,
        *,
        title: str,
        price: str | int | float | None,
        url: str,
        image_url: str = "",
        shop_name: str = "",
        sales_text: str = "",
        rating_text: str = "",
        source_item_id: str = "",
        raw_rank: int = 0,
    ) -> ProductOffer:
        return ProductOffer(
            platform=self.platform,
            title=clean_text(title),
            price_cny=parse_price_cny(price),
            shop_name=clean_text(shop_name),
            product_url=absolute_url(self.base_url, url),
            image_url=absolute_url(self.base_url, image_url),
            sales_text=clean_text(sales_text),
            rating_text=clean_text(rating_text),
            source_item_id=clean_text(source_item_id),
            raw_rank=raw_rank,
        )

    def _error_offer(self, status: str) -> ProductOffer:
        return ProductOffer(platform=self.platform, status=status)

    def _rank_and_trim(
        self,
        offers: list[ProductOffer],
        query: str,
        limit: int,
    ) -> list[ProductOffer]:
        tokens = [t.lower() for t in re.findall(r"[\w\u4e00-\u9fff]+", query) if len(t) >= 2]

        def score(offer: ProductOffer) -> tuple[int, int]:
            title = offer.title.lower()
            matched = sum(1 for token in tokens if token in title)
            return (-matched, offer.raw_rank)

        deduped: list[ProductOffer] = []
        seen: set[str] = set()
        for offer in sorted([o for o in offers if o.ok], key=score):
            key = offer.source_item_id or offer.product_url or offer.title
            if key in seen:
                continue
            seen.add(key)
            deduped.append(offer)
            if len(deduped) >= limit:
                break
        return deduped
