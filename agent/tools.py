import json
import re
from pathlib import Path

try:
    from langchain_core.tools import tool
except ImportError:  # pragma: no cover - keeps lightweight tests independent of LangChain
    class _LocalTool:
        def __init__(self, func):
            self.func = func
            self.name = func.__name__
            self.description = func.__doc__ or ""

        def __call__(self, *args, **kwargs):
            return self.func(*args, **kwargs)

    def tool(func):
        return _LocalTool(func)

from agent.review_sources import format_review_context
BASE_DIR = Path(__file__).parent.parent
PHONES_PATH = str(BASE_DIR / "data" / "phones.json")

_phones_cache: list[dict] | None = None


def _load_phones() -> list[dict]:
    global _phones_cache
    if _phones_cache is None:
        _phones_cache = json.loads(Path(PHONES_PATH).read_text(encoding="utf-8"))
    return _phones_cache


def _format_phone(p: dict) -> str:
    features = "、".join(p.get("features", []))
    tags = "、".join(p.get("use_case_tags", []))
    pros = "；".join(p.get("pros", []))
    cons = "；".join(p.get("cons", []))
    storage = "/".join(str(s) for s in p.get("storage_options", []))
    return (
        f"【{p['model']}】\n"
        f"  品牌：{p['brand']} | 价格：¥{p['price_cny']}起 | 发布：{p['release_date']}\n"
        f"  处理器：{p['processor']} | 内存：{p['ram_gb']}GB | 存储：{storage}GB\n"
        f"  屏幕：{p['display']} | 电池：{p['battery_mah']}mAh | 充电：{p['charging_w']}W\n"
        f"  主摄：{p['main_camera_mp']}MP | 系统：{p['os']}\n"
        f"  特色：{features}\n"
        f"  适用场景：{tags}\n"
        f"  优点：{pros}\n"
        f"  缺点：{cons}\n"
        f"  简介：{p['summary']}"
    )


def _find_by_name(name: str, phones: list[dict]) -> dict | None:
    """Fuzzy match a phone by model name."""
    name_norm = name.lower().replace(" ", "")
    # Exact substring match first
    for p in phones:
        model_norm = p["model"].lower().replace(" ", "")
        if name_norm in model_norm or model_norm in name_norm:
            return p
    # RAG fallback
    results = _search_phones(name, top_k=1)
    if results:
        return next((p for p in phones if p["id"] == results[0]["id"]), None)
    return None


@tool
def search_phone(query: str) -> str:
    """查询特定手机型号的详细参数和评价。

    适用场景：用户指定了手机型号，如"查一下iPhone 16 Pro"、"小米15参数"。

    Args:
        query: 手机型号名称，如 "iPhone 16 Pro" 或 "小米15 Ultra"
    """
    phones = _load_phones()
    query_norm = query.lower().replace(" ", "")

    matches = [
        p for p in phones
        if query_norm in p["model"].lower().replace(" ", "")
        or p["model"].lower().replace(" ", "") in query_norm
    ]

    if not matches:
        results = _search_phones(query, top_k=3)
        matched_ids = {r["id"] for r in results}
        matches = [p for p in phones if p["id"] in matched_ids]

    if not matches:
        return f'数据库中未找到与"{query}"相关的手机，请确认型号名称是否正确。'

    header = f"找到 {len(matches)} 款相关手机：\n\n"
    return header + "\n\n---\n\n".join(_format_phone(p) for p in matches[:3])


@tool
def recommend_phones(requirements: str) -> str:
    """根据用户需求推荐合适的手机。

    适用场景：用户描述了购机需求，如"推荐3000元以内拍照好的手机"、"学生党用什么手机好"。

    Args:
        requirements: 用户需求描述，可包含预算、用途、偏好品牌等
    """
    phones = _load_phones()

    # Extract price ceiling from requirements
    price_nums = [int(n) for n in re.findall(r'(\d+)\s*(?:元|块|￥|¥)', requirements)]
    filtered = phones
    if price_nums:
        max_price = max(price_nums)
        min_price = min(price_nums) if len(price_nums) >= 2 else 0
        filtered = [p for p in phones if min_price <= p["price_cny"] <= max_price]
        if not filtered:
            filtered = phones  # No results in range, fall back to all

    # Semantic re-ranking via RAG
    rag_results = _search_phones(requirements, top_k=15)
    rag_ids = [r["id"] for r in rag_results]

    seen: set[str] = set()
    ranked: list[dict] = []
    for rid in rag_ids:
        match = next((p for p in filtered if p["id"] == rid), None)
        if match and rid not in seen:
            ranked.append(match)
            seen.add(rid)
    for p in filtered:
        if p["id"] not in seen:
            ranked.append(p)
            seen.add(p["id"])

    top = ranked[:5]
    header = f"根据您的需求为您推荐以下 {len(top)} 款手机：\n\n"
    return header + "\n\n---\n\n".join(_format_phone(p) for p in top)


@tool
def compare_phones(models: str) -> str:
    """对比多款手机的参数和特性，生成详细对比信息。

    适用场景：用户想比较多款手机，如"对比小米15和iPhone 16"、"华为Mate70和OPPO Find X8哪个好"。

    Args:
        models: 要对比的手机型号，用逗号、"和"或"vs"分隔，如 "小米15, iPhone 16"
    """
    phones = _load_phones()
    model_names = [m.strip() for m in re.split(r'[,，和与vsVS]', models) if m.strip()]

    found: list[dict] = []
    for name in model_names:
        match = _find_by_name(name, phones)
        if match and match not in found:
            found.append(match)

    if len(found) < 2:
        found_names = [p["model"] for p in found]
        return (
            f"未能找到足够手机进行对比（需要至少2款），"
            f"已找到：{found_names}。请检查型号名称是否正确。"
        )

    lines = ["以下是各手机详细参数，请根据这些数据进行对比分析：\n"]
    for p in found:
        lines.append(_format_phone(p))
        lines.append("---")

    return "\n".join(lines)


@tool
def list_new_releases() -> str:
    """获取近期发布的新款手机列表。

    适用场景：用户询问新品，如"最近有什么新机"、"2025年发布了什么手机"。
    """
    phones = _load_phones()
    new_phones = sorted(
        [p for p in phones if p.get("is_new", False)],
        key=lambda p: p["release_date"],
        reverse=True,
    )

    if not new_phones:
        return "暂无新品信息。"

    lines = [f"近期发布的新款手机（共 {len(new_phones)} 款）：\n"]
    for p in new_phones:
        lines.append(
            f"• {p['model']}（{p['brand']}）— ¥{p['price_cny']}起，"
            f"{p['release_date']}发布 — {p['summary']}"
        )
    return "\n".join(lines)


@tool
def summarize_review_sources(
    review_context: str,
) -> str:
    """整理本次用户提供的公开评测资料，作为推荐时的引用证据。

    适用场景：用户要求结合侧边栏提供的评测链接、媒体评测、体验文章或其他
    公开网页来辅助推荐手机。

    Args:
        review_context: 已抽取的本次评测资料 Markdown 摘要。
    """
    if not review_context.strip():
        return format_review_context([])
    return review_context.strip()


def _search_phones(query: str, top_k: int) -> list[dict]:
    from rag.retriever import search

    return search(query, top_k=top_k)
