import os
import warnings

# 必须在导入任何 HuggingFace 相关库之前设置
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"

# Suppress transformers warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="transformers")

import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage

load_dotenv()

st.set_page_config(
    page_title="手机选购助手",
    page_icon="📱",
    layout="wide",
)

# ── API Key guard ──────────────────────────────────────────────────────────────
if not os.environ.get("DEEPSEEK_API_KEY"):
    st.error(
        "⚠️ 未检测到 DEEPSEEK_API_KEY。\n\n"
        "请将 `.env.example` 复制为 `.env`，并填入你的 DeepSeek API Key，然后重启应用。"
    )
    st.stop()

# Lazy import after env check to avoid errors at import time
from agent.agent import get_agent  # noqa: E402

# ── Session state init ─────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages: list[dict] = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history: list = []

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📱 手机选购助手")
    st.caption("AI 驱动的专业手机顾问")
    st.divider()

    st.subheader("⚡ 快捷提问")
    quick_queries = {
        "🆕 近期有哪些新品？": "最近发布了哪些新款手机？帮我列一下。",
        "🏆 旗舰机怎么选？": "目前有哪些值得推荐的顶级旗舰手机？各有什么优势？",
        "💰 2000元内推荐": "2000元以内有哪些性价比高的手机？我平时刷视频、打游戏为主。",
        "📷 拍照最好的手机": "目前拍照效果最好的手机有哪些？价格不限。",
    }
    for label, query in quick_queries.items():
        if st.button(label, use_container_width=True):
            st.session_state["_pending"] = query

    st.divider()
    if st.button("🗑️ 清空对话", use_container_width=True):
        st.session_state.messages = []
        st.session_state.chat_history = []
        st.rerun()

    st.divider()
    st.caption("数据覆盖：Apple · 三星 · 小米 · 华为\nOPPO · vivo · Redmi · 一加")
    st.caption("价格均为国内官网参考售价")

# ── Main area ──────────────────────────────────────────────────────────────────
st.title("📱 手机选购助手")
st.caption("描述你的需求，我来帮你找到最合适的手机 ✨")

# Render existing chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Collect input: quick-button press OR typed message
pending = st.session_state.pop("_pending", None)
typed = st.chat_input("例如：推荐一款3000元以内拍照好的手机")
prompt = typed or pending

if prompt:
    # Show user bubble
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Call agent and stream into assistant bubble
    with st.chat_message("assistant"):
        with st.spinner("正在为您查询..."):
            try:
                agent = get_agent()
                # Build messages list with full history
                messages = st.session_state.chat_history + [HumanMessage(content=prompt)]
                response = agent.invoke({"messages": messages})

                # Extract answer and preserve full response for reasoning_content
                last_msg = response["messages"][-1]
                answer = last_msg.content

                # Store the full AI message for next round
                st.session_state.chat_history.extend([
                    HumanMessage(content=prompt),
                    last_msg,  # Keep full message object with reasoning_content
                ])
            except Exception as exc:
                answer = f"抱歉，处理您的请求时出现了问题：{exc}"
                st.session_state.chat_history.extend([
                    HumanMessage(content=prompt),
                    AIMessage(content=answer),
                ])
        st.markdown(answer)

    # Persist to session state (display only)
    st.session_state.messages.append({"role": "assistant", "content": answer})

    # Re-render so quick-button input also shows up cleanly
    if pending:
        st.rerun()
