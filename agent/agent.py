import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from agent.tools import search_phone, recommend_phones, compare_phones, list_new_releases

load_dotenv()

SYSTEM_PROMPT = """你是一位专业的手机选购顾问，熟悉国内市场全部主流手机品牌和型号（苹果、三星、小米、华为、OPPO、vivo、Redmi、一加等）。

你的职责是帮助用户找到最适合他们的手机。请遵循以下原则：
- 回答专业但口语化，避免单纯堆砌参数，要结合用户实际场景给出有温度的建议
- 推荐时必须说明推荐理由，结合用户预算和使用场景
- 对比时使用 Markdown 表格呈现关键参数差异，并在表格后给出明确的综合建议
- 价格均为国内官网参考售价，实际购买时以商家为准
- 如用户问题超出手机选购范围，礼貌地引导回手机话题"""

_agent_executor: AgentExecutor | None = None


def get_agent() -> AgentExecutor:
    global _agent_executor
    if _agent_executor is not None:
        return _agent_executor

    llm = ChatOpenAI(
        model="deepseek-v4-flash",
        openai_api_base=os.environ.get("DEEPSEEK_API_BASE", "https://api.deepseek.com"),
        openai_api_key=os.environ["DEEPSEEK_API_KEY"],
        temperature=0.7,
    )

    tools = [search_phone, recommend_phones, compare_phones, list_new_releases]

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    _agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=False,
        max_iterations=5,
        handle_parsing_errors=True,
    )
    return _agent_executor
