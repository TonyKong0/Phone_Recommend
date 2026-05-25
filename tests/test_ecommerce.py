from datetime import datetime, timedelta, timezone

import pytest

from agent.ecommerce.cache import EcommerceCache
from agent.ecommerce.models import ProductOffer
from agent.ecommerce.scrapers.base import parse_price_cny
from agent.ecommerce.scrapers.jd import JdScraper
from agent.ecommerce.search import format_offers_markdown, parse_platforms


def test_parse_price_cny_handles_common_formats():
    assert parse_price_cny("¥3,999") == 3999
    assert parse_price_cny("到手价3999.00元") == 3999
    assert parse_price_cny(2999) == 2999
    assert parse_price_cny("") is None


def test_cache_returns_none_after_ttl(tmp_path):
    cache = EcommerceCache(path=tmp_path / "cache.json", ttl_minutes=30)
    cache.set("jd", "iPhone 16", 3, [ProductOffer(platform="京东", title="iPhone 16")])
    assert cache.get("jd", "iPhone 16", 3)[0].title == "iPhone 16"

    old_time = datetime.now(timezone.utc) - timedelta(minutes=31)
    data = cache._read()
    data[cache.make_key("jd", "iPhone 16", 3)]["fetched_at"] = old_time.isoformat()
    cache.path.write_text(__import__("json").dumps(data), encoding="utf-8")

    assert cache.get("jd", "iPhone 16", 3) is None


def test_parse_platforms_dedupes_aliases():
    assert parse_platforms("京东,jd,淘宝,pdd") == ["jd", "taobao", "pdd"]


def test_jd_parser_extracts_offer_from_static_html():
    pytest.importorskip("bs4")
    html = """
    <ul>
      <li class="gl-item" data-sku="1001">
        <div class="p-img"><a href="//item.jd.com/1001.html"><img data-lazy-img="//img.example/1.jpg"></a></div>
        <div class="p-price"><strong><i>3999.00</i></strong></div>
        <div class="p-name"><a href="//item.jd.com/1001.html"><em>Apple iPhone 16 256GB</em></a></div>
        <div class="p-shop"><a>京东自营</a></div>
        <div class="p-commit"><strong><a>10万+评价</a></strong></div>
      </li>
    </ul>
    """
    offers = JdScraper().parse_html(html, "iPhone 16", 5)
    assert len(offers) == 1
    assert offers[0].platform == "京东"
    assert offers[0].title == "Apple iPhone 16 256GB"
    assert offers[0].price_cny == 3999
    assert offers[0].shop_name == "京东自营"
    assert offers[0].product_url == "https://item.jd.com/1001.html"


def test_format_offers_markdown_keeps_failed_platforms_visible():
    text = format_offers_markdown([
        ProductOffer(platform="京东", title="iPhone 16", price_cny=4999, product_url="https://item.jd.com/1.html"),
        ProductOffer(platform="淘宝", status="blocked_or_failed"),
    ])
    assert "| 京东 | iPhone 16 | ¥4999 |" in text
    assert "淘宝: blocked_or_failed" in text
