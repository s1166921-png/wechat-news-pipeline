from datetime import datetime, timezone, timedelta
import urllib.request


CST = timezone(timedelta(hours=8))


def today_cst_label(now=None):
    """Return today's date in Chinese format for prompts."""
    current = now or datetime.now(CST)
    if current.tzinfo is None:
        current = current.replace(tzinfo=CST)
    else:
        current = current.astimezone(CST)
    return f"{current.year}年{current.month}月{current.day}日"


def urlopen_final_url(url, timeout=10, headers=None):
    """Open a URL and return the final URL after redirects."""
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.geturl()


def resolve_wechat_url(url, timeout=10, urlopen_func=None):
    """Normalize WeChat article URLs, including Sogou WeChat redirect links."""
    if not url:
        return url
    clean_url = url.strip()
    if "mp.weixin.qq.com/" in clean_url:
        return clean_url
    if "weixin.sogou.com/link" not in clean_url:
        return clean_url

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    try:
        opener = urlopen_func or urlopen_final_url
        final_url = opener(clean_url, timeout=timeout, headers=headers)
        if final_url and "mp.weixin.qq.com/" in final_url:
            return final_url
    except Exception as e:
        print(f"  [WeChatURL] resolve failed: {e}")
    return clean_url


def classify_article_import(url="", raw_content=""):
    """Describe how an article should enter the rewrite pipeline."""
    clean_url = (url or "").strip()
    clean_content = (raw_content or "").strip()

    if clean_content:
        return {
            "mode": "raw_content",
            "recommendation": "rewrite_directly",
            "message": "已使用粘贴全文作为原文素材",
        }
    if "weixin.sogou.com/link" in clean_url:
        return {
            "mode": "wechat_sogou_redirect",
            "recommendation": "resolve_then_fetch",
            "message": "搜狗微信跳转链接会先解析为公众号原文链接",
        }
    if "mp.weixin.qq.com/" in clean_url:
        return {
            "mode": "wechat_direct",
            "recommendation": "fetch_or_paste",
            "message": "公众号原文链接可尝试抓取；失败时建议粘贴全文",
        }
    if clean_url:
        return {
            "mode": "url",
            "recommendation": "fetch_directly",
            "message": "普通网页链接会尝试自动提取正文",
        }
    return {
        "mode": "empty",
        "recommendation": "provide_input",
        "message": "请提供文章链接或粘贴全文",
    }
