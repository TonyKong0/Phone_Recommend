from __future__ import annotations

from .cache import EcommerceCache
from .models import ProductOffer
from .scrapers import SCRAPER_CLASSES


PLATFORM_ALIASES = {
    "jd": "jd",
    "jingdong": "jd",
    "京东": "jd",
    "taobao": "taobao",
    "淘宝": "taobao",
    "tb": "taobao",
    "pdd": "pdd",
    "pinduoduo": "pdd",
    "拼多多": "pdd",
}


def parse_platforms(platforms: str) -> list[str]:
    if not platforms:
        return ["jd", "taobao", "pdd"]
    normalized = []
    for raw in platforms.replace("，", ",").split(","):
        key = raw.strip().lower()
        if not key:
            continue
        normalized_key = PLATFORM_ALIASES.get(key) or PLATFORM_ALIASES.get(raw.strip())
        if normalized_key and normalized_key not in normalized:
            normalized.append(normalized_key)
    return normalized or ["jd", "taobao", "pdd"]


def search_live_products(
    query: str,
    platforms: str = "jd,taobao,pdd",
    max_results: int = 5,
    cache: EcommerceCache | None = None,
) -> tuple[list[ProductOffer], list[str]]:
    cache = cache or EcommerceCache()
    max_results = max(1, min(int(max_results), 10))
    offers: list[ProductOffer] = []
    notes: list[str] = []
    for platform_key in parse_platforms(platforms):
        scraper_cls = SCRAPER_CLASSES[platform_key]
        cached = cache.get(platform_key, query, max_results)
        if cached is not None:
            offers.extend(cached)
            notes.append(f"{scraper_cls.platform}命中30分钟缓存")
            continue
        scraper = scraper_cls()
        platform_offers = scraper.search(query, limit=max_results)
        cache.set(platform_key, query, max_results, platform_offers)
        offers.extend(platform_offers)
    return offers, notes


def format_offers_markdown(offers: list[ProductOffer], notes: list[str] | None = None) -> str:
    notes = notes or []
    ok_offers = [offer for offer in offers if offer.ok]
    failed = [offer for offer in offers if not offer.ok]
    lines = []
    if notes:
        lines.append("缓存说明：" + "；".join(notes))
        lines.append("")
    if ok_offers:
        lines.append("| 平台 | 商品 | 价格 | 店铺 | 销量/评价 | 链接 | 抓取时间 |")
        lines.append("| --- | --- | ---: | --- | --- | --- | --- |")
        for offer in ok_offers:
            price = f"¥{offer.price_cny:g}" if offer.price_cny is not None else "未获取"
            signal = offer.sales_text or offer.rating_text or "-"
            title = offer.title.replace("|", " ").strip()
            shop = offer.shop_name.replace("|", " ").strip() or "-"
            link = f"[打开]({offer.product_url})" if offer.product_url else "-"
            lines.append(
                f"| {offer.platform} | {title} | {price} | {shop} | {signal} | "
                f"{link} | {offer.fetched_at} |"
            )
    else:
        lines.append("未能从公开页面获取到可用商品。")
    if failed:
        lines.append("")
        lines.append("平台异常：")
        for offer in failed:
            lines.append(f"- {offer.platform}: {offer.status}")
    return "\n".join(lines)

