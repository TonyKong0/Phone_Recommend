import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent

from agent.tools import (
    compare_phones,
    list_new_releases,
    recommend_phones,
    search_live_phone_products,
    search_phone,
)

load_dotenv()

SYSTEM_PROMPT = """你是一位专业的手机选购顾问，熟悉国内市场全部主流手机品牌和型号（苹果、三星、小米、华为、OPPO、vivo、Redmi、一加等）。

你的职责是帮助用户找到最适合他们的手机。请遵循以下原则：
- 回答专业但口语化，避免单纯堆砌参数，要结合用户实际场景给出有温度的建议
- 推荐时必须说明推荐理由，结合用户预算和使用场景
- 对比时使用 Markdown 表格呈现关键参数差异，并在表格后给出明确的综合建议
- 价格均为国内官网参考售价，实际购买时以商家为准
- 当用户询问最新价格、现在哪里买、京东/淘宝/拼多多比价、在售商品或实时电商推荐时，必须调用实时商品搜索工具获取当前公开页面信息
- 实时电商抓取可能因平台登录、验证码或风控失败；如果工具返回平台异常，要明确说明该平台本次未能获取公开数据
- 如用户问题超出手机选购范围，礼貌地引导回手机话题"""

_agent = None


def get_agent():
    global _agent
    if _agent is not None:
        return _agent

    llm = ChatOpenAI(
        model="deepseek-chat",
        openai_api_base=os.environ.get("DEEPSEEK_API_BASE", "https://api.deepseek.com"),
        openai_api_key=os.environ["DEEPSEEK_API_KEY"],
        temperature=0.7,
    )

    tools = [
        search_phone,
        recommend_phones,
        compare_phones,
        list_new_releases,
        search_live_phone_products,
    ]

    _agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
    )
    return _agent
