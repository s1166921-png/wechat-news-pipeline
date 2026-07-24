import re


def is_wechat_url(url):
    return "mp.weixin.qq.com/" in (url or "") or "weixin.sogou.com/link" in (url or "")


def strip_extractor_metadata(content):
    """Remove extractor-generated metadata blocks from article body text."""
    text = (content or "").strip()
    block_re = re.compile(r"(?ms)^---\s*\n(?=.*?(?:title|author|url|hostname|description):).*?\n---\s*\n?")
    text = block_re.sub("", text).strip()
    embedded_block_re = re.compile(r"(?ms)---\s*\n(?=.*?(?:title|author|url|hostname|description):).*?\n---\s*\n?")
    text = embedded_block_re.sub("", text).strip()
    return text


def is_usable_article_content(content, source_url="", min_chars=200):
    """Return whether extracted content is enough to use as source material."""
    return assess_article_quality(content, source_url=source_url, min_chars=min_chars)["usable"]


def assess_article_quality(content, source_url="", min_chars=200):
    """Assess whether extracted content is complete enough for rewriting."""
    cleaned = strip_extractor_metadata(content)
    reasons = []

    if len(cleaned) < min_chars:
        reasons.append("too_short")

    if "title:" in cleaned[:500] or "hostname:" in cleaned[:500] or "description:" in cleaned[:500]:
        reasons.append("metadata_residue")

    if is_wechat_url(source_url):
        restricted_signals = [
            "微信扫一扫关注该公众号",
            "微信扫一扫可打开此内容",
            "使用完整服务",
        ]
        if any(sig in cleaned for sig in restricted_signals):
            reasons.append("wechat_restricted_tail")
        if len(cleaned) < 600:
            reasons.append("wechat_too_short")

    return {
        "usable": not reasons,
        "needs_fallback": bool(reasons),
        "reasons": reasons,
        "char_count": len(cleaned),
        "min_chars": 600 if is_wechat_url(source_url) else min_chars,
    }


def article_success(title, content, source_url, extraction_method, author=""):
    clean_content = strip_extractor_metadata(content)
    quality = assess_article_quality(clean_content, source_url=source_url)
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
        "quality": quality,
    }


def article_failure(source_url, status="extract_failed", error_hint="", extraction_method="none"):
    hint = error_hint or "无法提取文章内容，请检查链接是否正确，或改用全文粘贴导入"
    quality = assess_article_quality("", source_url=source_url)
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
        "quality": quality,
    }


def normalize_article_result(result, fallback_url=""):
    if not result:
        return article_failure(fallback_url)
    if result.get("ok") is False:
        return result
    if result.get("ok") is True and "quality" in result:
        return result

    return article_success(
        title=result.get("title") or "未知标题",
        content=result.get("content") or "",
        author=result.get("author") or "",
        source_url=result.get("source_url") or fallback_url,
        extraction_method=result.get("extraction_method") or "unknown",
    )
