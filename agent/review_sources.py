from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from urllib.parse import urlparse

import requests

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover - dependency is declared in requirements
    BeautifulSoup = None


MIN_REVIEW_CHARS = 30
MAX_REVIEW_CHARS = 6000


@dataclass(slots=True)
class ReviewSource:
    url: str
    title: str = ""
    content: str = ""
    status: str = "ok"

    @property
    def ok(self) -> bool:
        return self.status == "ok" and bool(self.content)


def parse_review_urls(raw: str) -> tuple[list[str], list[str]]:
    urls: list[str] = []
    errors: list[str] = []
    seen: set[str] = set()
    for value in raw.splitlines():
        url = value.strip()
        if not url:
            continue
        error = validate_public_http_url(url)
        if error:
            errors.append(f"{url}: {error}")
            continue
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls, errors


def validate_public_http_url(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return "仅支持 http/https 链接"
    if not parsed.netloc or not parsed.hostname:
        return "链接缺少有效域名"
    if _is_local_or_private_host(parsed.hostname):
        return "不支持本地或内网地址"
    return None


def fetch_review_source(url: str, timeout: int = 12, max_chars: int = MAX_REVIEW_CHARS) -> ReviewSource:
    error = validate_public_http_url(url)
    if error:
        return ReviewSource(url=url, status=error)
    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
            timeout=timeout,
        )
        response.raise_for_status()
        response.encoding = response.apparent_encoding or response.encoding or "utf-8"
    except requests.RequestException as exc:
        return ReviewSource(url=url, status=f"读取失败：{exc.__class__.__name__}")
    return extract_review_from_html(url, response.text, max_chars=max_chars)


def extract_review_from_html(url: str, html: str, max_chars: int = MAX_REVIEW_CHARS) -> ReviewSource:
    if BeautifulSoup is None:
        return ReviewSource(url=url, status="缺少 beautifulsoup4，无法解析网页")
    soup = BeautifulSoup(html, "lxml")
    title = _extract_title(soup) or url
    for node in soup.select("script, style, noscript, iframe, svg, nav, header, footer, aside"):
        node.decompose()
    root = soup.select_one("article, main, [role=main]") or soup.body or soup
    text = _clean_text(root.get_text(" ", strip=True))
    if len(text) < MIN_REVIEW_CHARS:
        return ReviewSource(url=url, title=title, status="内容过短，未作为评测资料使用")
    return ReviewSource(url=url, title=title, content=text[:max_chars], status="ok")


def format_review_context(sources: list[ReviewSource]) -> str:
    if not sources:
        return "本次没有可用评测资料。"
    lines = ["本次评测参考资料："]
    ok_sources = [source for source in sources if source.ok]
    failed_sources = [source for source in sources if not source.ok]
    for idx, source in enumerate(ok_sources, start=1):
        lines.extend([
            "",
            f"### 来源 {idx}: {source.title}",
            f"- 链接：{source.url}",
            f"- 摘要材料：{source.content}",
        ])
    if failed_sources:
        lines.extend(["", "未使用来源："])
        for source in failed_sources:
            label = source.title or source.url
            lines.append(f"- {label}: {source.status}")
    return "\n".join(lines)


def build_review_context(raw_urls: str) -> tuple[list[ReviewSource], list[str], str]:
    urls, errors = parse_review_urls(raw_urls)
    sources = [fetch_review_source(url) for url in urls]
    for error in errors:
        url, status = error.rsplit(": ", 1)
        sources.append(ReviewSource(url=url, status=status))
    return sources, errors, format_review_context(sources)


def _is_local_or_private_host(hostname: str) -> bool:
    host = hostname.strip().strip("[]").lower()
    if host in {"localhost"} or host.endswith(".localhost") or host.endswith(".local"):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _extract_title(soup) -> str:
    meta = soup.select_one("meta[property='og:title'], meta[name='twitter:title']")
    if meta and meta.get("content"):
        return _clean_text(meta["content"])
    if soup.title:
        return _clean_text(soup.title.get_text(" ", strip=True))
    heading = soup.select_one("h1")
    return _clean_text(heading.get_text(" ", strip=True)) if heading else ""


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()
