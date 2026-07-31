from agent import tools


def test_core_phone_tools_still_work_without_ecommerce(monkeypatch):
    monkeypatch.setattr(tools, "_search_phones", lambda _query, top_k: [])

    assert "iPhone 16" in tools.search_phone.invoke({"query": "iPhone 16"})
    assert "推荐" in tools.recommend_phones.invoke({"requirements": "3000元以内日常使用"})
    assert "详细参数" in tools.compare_phones.invoke({"models": "iPhone 15, 小米14"})
    assert "近期发布的新款手机" in tools.list_new_releases.invoke({})
