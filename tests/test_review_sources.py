from agent.review_sources import (
    ReviewSource,
    extract_review_from_html,
    format_review_context,
    parse_review_urls,
)


def test_parse_review_urls_dedupes_and_rejects_unsafe_targets():
    raw = """
    https://example.com/review
    http://example.com/review-2
    https://example.com/review
    file:///C:/secret.txt
    http://localhost:8501
    http://127.0.0.1/admin
    http://192.168.1.2/page
    ftp://example.com/file
    """

    urls, errors = parse_review_urls(raw)

    assert urls == [
        "https://example.com/review",
        "http://example.com/review-2",
    ]
    assert "file:///C:/secret.txt: 仅支持 http/https 链接" in errors
    assert "http://localhost:8501: 不支持本地或内网地址" in errors
    assert "http://127.0.0.1/admin: 不支持本地或内网地址" in errors
    assert "http://192.168.1.2/page: 不支持本地或内网地址" in errors
    assert "ftp://example.com/file: 仅支持 http/https 链接" in errors


def test_extract_review_from_html_removes_noise_and_limits_text():
    html = """
    <html>
      <head><title>小米15 Ultra 深度评测</title><script>bad()</script></head>
      <body>
        <nav>首页 导航</nav>
        <article>
          <h1>小米15 Ultra 深度评测</h1>
          <p>影像表现稳定，长焦解析力优秀，夜景色彩也更自然。</p>
          <p>机身偏重，长时间握持会有负担，游戏发热需要注意。</p>
        </article>
      </body>
    </html>
    """

    source = extract_review_from_html("https://example.com/review", html, max_chars=35)

    assert source.ok
    assert source.title == "小米15 Ultra 深度评测"
    assert "影像表现稳定" in source.content
    assert "bad()" not in source.content
    assert "首页 导航" not in source.content
    assert len(source.content) <= 35


def test_format_review_context_keeps_success_and_failure_visible():
    context = format_review_context([
        ReviewSource(
            url="https://example.com/a",
            title="A评测",
            content="续航强，屏幕亮度高。",
            status="ok",
        ),
        ReviewSource(
            url="https://example.com/b",
            title="",
            content="",
            status="内容过短，未作为评测资料使用",
        ),
    ])

    assert "A评测" in context
    assert "https://example.com/a" in context
    assert "续航强，屏幕亮度高。" in context
    assert "未使用来源" in context
    assert "内容过短" in context
