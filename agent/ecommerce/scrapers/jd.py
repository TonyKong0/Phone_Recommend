from __future__ import annotations

from .base import BaseMarketplaceScraper, clean_text


class JdScraper(BaseMarketplaceScraper):
    platform = "京东"
    base_url = "https://search.jd.com"
    search_url_template = "https://search.jd.com/Search?keyword={query}&enc=utf-8"

    def parse_html(self, html: str, query: str, limit: int):
        soup = self.soup(html)
        offers = []
        for idx, item in enumerate(soup.select("li.gl-item"), start=1):
            title_el = item.select_one(".p-name em") or item.select_one(".p-name a")
            link_el = item.select_one(".p-name a") or item.select_one(".p-img a")
            price_el = item.select_one(".p-price i") or item.select_one("[data-price]")
            img_el = item.select_one(".p-img img")
            if not title_el or not link_el:
                continue
            title = clean_text(title_el.get_text(" ", strip=True))
            href = link_el.get("href", "")
            price = (
                price_el.get("data-price")
                if price_el and price_el.has_attr("data-price")
                else price_el.get_text(strip=True) if price_el else ""
            )
            shop_el = item.select_one(".p-shop a") or item.select_one(".p-shop span")
            commit_el = item.select_one(".p-commit a") or item.select_one(".p-commit strong")
            image_url = ""
            if img_el:
                image_url = img_el.get("data-lazy-img") or img_el.get("src") or ""
            offer = self._offer(
                title=title,
                price=price,
                url=href,
                image_url=image_url,
                shop_name=shop_el.get_text(" ", strip=True) if shop_el else "",
                rating_text=commit_el.get_text(" ", strip=True) if commit_el else "",
                source_item_id=item.get("data-sku", ""),
                raw_rank=idx,
            )
            if offer.title:
                offers.append(offer)
        return offers

