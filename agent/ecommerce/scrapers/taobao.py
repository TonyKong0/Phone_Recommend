from __future__ import annotations

from .base import BaseMarketplaceScraper, extract_json_object


class TaobaoScraper(BaseMarketplaceScraper):
    platform = "淘宝"
    base_url = "https://s.taobao.com"
    search_url_template = "https://s.taobao.com/search?q={query}"

    def parse_html(self, html: str, query: str, limit: int):
        data = extract_json_object(html, "g_page_config")
        auctions = (
            data.get("mods", {})
            .get("itemlist", {})
            .get("data", {})
            .get("auctions", [])
        )
        offers = []
        for idx, item in enumerate(auctions, start=1):
            title = item.get("raw_title") or item.get("title") or ""
            href = item.get("detail_url") or item.get("auctionURL") or ""
            offer = self._offer(
                title=title,
                price=item.get("view_price") or item.get("price"),
                url=href,
                image_url=item.get("pic_url") or item.get("picUrl") or "",
                shop_name=item.get("nick") or item.get("shopName") or "",
                sales_text=item.get("view_sales") or item.get("sale") or "",
                rating_text=item.get("comment_count") or "",
                source_item_id=str(item.get("nid") or item.get("item_id") or ""),
                raw_rank=idx,
            )
            if offer.title:
                offers.append(offer)
        if offers:
            return offers
        return self._parse_fallback_dom(html)

    def _parse_fallback_dom(self, html: str):
        soup = self.soup(html)
        offers = []
        for idx, item in enumerate(soup.select("[data-nid], .item, .Card--doubleCardWrapper--"), start=1):
            link_el = item.select_one("a[href]")
            title_el = item.select_one("[title]") or link_el
            if not link_el or not title_el:
                continue
            price_el = item.select_one(".price, [class*=price], [class*=Price]")
            shop_el = item.select_one(".shop, [class*=shop], [class*=Shop]")
            offer = self._offer(
                title=title_el.get("title") or title_el.get_text(" ", strip=True),
                price=price_el.get_text(" ", strip=True) if price_el else "",
                url=link_el.get("href", ""),
                shop_name=shop_el.get_text(" ", strip=True) if shop_el else "",
                source_item_id=item.get("data-nid", ""),
                raw_rank=idx,
            )
            if offer.title:
                offers.append(offer)
        return offers

