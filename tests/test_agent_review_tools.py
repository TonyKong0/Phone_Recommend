from agent.agent import SYSTEM_PROMPT, get_tools


def test_agent_tools_remove_ecommerce_and_add_review_sources():
    tool_names = {tool.name for tool in get_tools()}

    assert "search_live_phone_products" not in tool_names
    assert "summarize_review_sources" in tool_names


def test_system_prompt_no_longer_promises_live_ecommerce_search():
    assert "京东" not in SYSTEM_PROMPT
    assert "淘宝" not in SYSTEM_PROMPT
    assert "拼多多" not in SYSTEM_PROMPT
    assert "实时商品搜索" not in SYSTEM_PROMPT
    assert "评测" in SYSTEM_PROMPT
