from __future__ import annotations

import json
import re

from .base import BaseMarketplaceScraper


class PddScraper(BaseMarketplaceScraper):
    platform = "拼多多"
    base_url = "https://mobile.yangkeduo.com"
    search_url_template = "https://mobile.yangkeduo.com/search_result.html?search_key={query}"

    def parse_html(self, html: str, query: str, limit: int):
        offers = self._parse_embedded_goods(html)
        if offers:
            return offers
        return self._parse_dom(html)

    def _parse_embedded_goods(self, html: str):
        offers = []
        candidates = []
        for match in re.finditer(r'"goods_list"\s*:\s*(\[[\s\S]*?\])\s*[,}]', html):
            try:
                candidates.extend(json.loads(match.group(1)))
            except json.JSONDecodeError:
                continue
        for match in re.finditer(r'"items"\s*:\s*(\[[\s\S]*?\])\s*[,}]', html):
            try:
                candidates.extend(json.loads(match.group(1)))
            except json.JSONDecodeError:
                continue
        for idx, item in enumerate(candidates, start=1):
            price = (
                item.get("price")
                or item.get("min_group_price")
                or item.get("normal_price")
                or item.get("sales_tip")
            )
            if isinstance(price, int) and price > 10000:
                price = price / 100
            goods_id = str(item.get("goods_id") or item.get("goodsID") or "")
            offer = self._offer(
                title=item.get("goods_name") or item.get("goodsName") or item.get("title") or "",
                price=price,
                url=f"https://mobile.yangkeduo.com/goods.html?goods_id={goods_id}" if goods_id else "",
                image_url=item.get("thumb_url") or item.get("hd_thumb_url") or item.get("image_url") or "",
                shop_name=item.get("mall_name") or "",
                sales_text=item.get("sales_tip") or item.get("salesTip") or "",
                source_item_id=goods_id,
                raw_rank=idx,
            )
            if offer.title:
                offers.append(offer)
        return offers

    def _parse_dom(self, html: str):
        soup = self.soup(html)
        offers = []
        for idx, item in enumerate(soup.select("a[href*='goods_id'], [data-goods-id]"), start=1):
            title_el = item.select_one("[class*=title], [class*=name], [class*=Name]") or item
            price_el = item.select_one("[class*=price], [class*=Price]")
            href = item.get("href") or ""
            goods_id = item.get("data-goods-id") or ""
            if not goods_id:
                match = re.search(r"goods_id=(\d+)", href)
                goods_id = match.group(1) if match else ""
            offer = self._offer(
                title=title_el.get_text(" ", strip=True),
                price=price_el.get_text(" ", strip=True) if price_el else "",
                url=href,
                source_item_id=goods_id,
                raw_rank=idx,
            )
            if offer.title:
                offers.append(offer)
        return offers

