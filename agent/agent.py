import os

from dotenv import load_dotenv

from agent.tools import (
    compare_phones,
    list_new_releases,
    recommend_phones,
    search_phone,
    summarize_review_sources,
)

load_dotenv()

SYSTEM_PROMPT = """你是一位专业的手机选购顾问，熟悉国内市场全部主流手机品牌和型号（苹果、三星、小米、华为、OPPO、vivo、Redmi、一加等）。

你的职责是帮助用户找到最适合他们的手机。请遵循以下原则：
- 回答专业但口语化，避免单纯堆砌参数，要结合用户实际场景给出有温度的建议
- 推荐时必须说明推荐理由，结合用户预算和使用场景
- 对比时使用 Markdown 表格呈现关键参数差异，并在表格后给出明确的综合建议
- 价格均为国内官网参考售价，实际购买时以商家为准
- 当用户提供评测链接或要求结合评测资料时，必须使用本次评测参考资料来辅助判断
- 引用评测观点时要标注来源标题或链接；不要复述整篇文章，只提炼与选购相关的优缺点、适用场景和争议点
- 如果本次没有可用评测资料，要明确说明建议主要基于本地参数数据和常识判断
- 如用户问题超出手机选购范围，礼貌地引导回手机话题"""

_agent = None


def get_tools():
    return [
        search_phone,
        recommend_phones,
        compare_phones,
        list_new_releases,
        summarize_review_sources,
    ]


def get_agent():
    global _agent
    if _agent is not None:
        return _agent

    from langchain.agents import create_agent
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        model="deepseek-chat",
        openai_api_base=os.environ.get("DEEPSEEK_API_BASE", "https://api.deepseek.com"),
        openai_api_key=os.environ["DEEPSEEK_API_KEY"],
        temperature=0.7,
    )

    _agent = create_agent(
        model=llm,
        tools=get_tools(),
        system_prompt=SYSTEM_PROMPT,
    )
    return _agent
