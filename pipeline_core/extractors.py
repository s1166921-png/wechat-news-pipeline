def is_wechat_url(url):
    return "mp.weixin.qq.com/" in (url or "") or "weixin.sogou.com/link" in (url or "")


def article_success(title, content, source_url, extraction_method, author=""):
    clean_content = (content or "").strip()
    return {
        "ok": True,
        "status": "ok",
        "title": (title or "未知标题").strip(),
        "author": (author or "").strip(),
        "content": clean_content,
        "char_count": len(clean_content),
        "source_url": source_url or "",
        "extraction_method": extraction_method or "unknown",
        "error_hint": "",
        "manual_import_recommended": False,
    }


def article_failure(source_url, status="extract_failed", error_hint="", extraction_method="none"):
    hint = error_hint or "无法提取文章内容，请检查链接是否正确，或改用全文粘贴导入"
    return {
        "ok": False,
        "status": status,
        "title": "",
        "author": "",
        "content": "",
        "char_count": 0,
        "source_url": source_url or "",
        "extraction_method": extraction_method,
        "error_hint": hint,
        "manual_import_recommended": is_wechat_url(source_url),
    }


def normalize_article_result(result, fallback_url=""):
    if not result:
        return article_failure(fallback_url)
    if result.get("ok") is False:
        return result

    return article_success(
        title=result.get("title") or "未知标题",
        content=result.get("content") or "",
        author=result.get("author") or "",
        source_url=result.get("source_url") or fallback_url,
        extraction_method=result.get("extraction_method") or "unknown",
    )
