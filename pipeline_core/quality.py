import math
import re


LOW_QUALITY_DOMAINS = [
    "baike.baidu.com", "baike.sogou.com", "baike.so.com", "wikipedia.org", "wiki.mbalib.com",
    "zhidao.baidu.com", "wenwen.sogou.com", "ask.", "wenda.",
    "bilibili.com/video", "youtube.com/watch", "youku.com/video", "iqiyi.com/v_",
    "v.qq.com/x/", "haokan.baidu.com/v", "tv.sohu.com/", "mgtv.com/",
    "live.bilibili.com", "live.", "/live/", "zhibo",
    "360kuai.com", "sohu.com/a/",
    "chsi.com.cn",
]


INDUSTRY_SOURCES = [
    "cifnews.com", "36kr.com", "ebrun.com", "kuajingyan.com",
    "amz123.com", "dny123.com", "kjds.com",
    "sellercentral.amazon.com", "gs.amazon.cn",
    "customs.gov.cn", "mofcom.gov.cn",
    "mp.weixin.qq.com", "toutiao.com",
    "sohu.com", "163.com", "news.qq.com",
]


GENERIC_TERMS = {
    "最新", "新闻", "动态", "趋势", "分析", "报告", "案例", "指南", "深度",
    "重磅", "政策", "变化", "增长", "运营", "市场", "行业", "发展", "未来",
    "中国", "企业", "公司", "平台",
}


TITLE_BAD_TERMS = [
    "是什么意思", "有什么区别", "意思和区别",
    "百度百科", "维基百科", "百度知道",
    "词的区别", "区别解释",
    "境外、国外、海外", "海外境外国外",
    "中国领事服务网", "海外_百度百科",
    "汉语词典", "新华字典", "的拼音", "的部首",
    "组词_", "怎么读_",
    "网址导航", "友情链接", "广告合作",
]


def keyword_relevance_terms(keyword):
    """Build compact relevance terms from a mixed Chinese/English keyword."""
    terms = []
    kw = (keyword or "").lower().strip()
    if not kw:
        return terms

    for term in re.split(r"[\s,，;；|/]+", kw):
        term = term.strip()
        if len(term) >= 2 and term not in terms:
            terms.append(term)

    cjk_runs = re.findall(r"[一-鿿]{2,}", kw)
    for run in cjk_runs:
        if len(run) <= 4 and run not in terms:
            terms.append(run)
        for i in range(len(run) - 1):
            bg = run[i:i + 2]
            if bg not in terms:
                terms.append(bg)

    return terms


def has_keyword_relevance(item, keyword):
    """Return True when an item matches at least one meaningful keyword signal."""
    terms = keyword_relevance_terms(keyword)
    if not terms:
        return True

    text = " ".join([
        item.get("title", ""),
        item.get("snippet", ""),
        item.get("source", ""),
    ]).lower()
    compact_text = re.sub(r"\s+", "", text)

    strong_hits = 0
    specific_hits = 0
    has_specific_terms = any(t not in GENERIC_TERMS for t in terms)
    for term in terms:
        compact_term = re.sub(r"\s+", "", term.lower())
        if not compact_term:
            continue
        if compact_term in compact_text:
            strong_hits += 1
            if compact_term not in GENERIC_TERMS:
                specific_hits += 1

    if has_specific_terms:
        return specific_hits >= 1
    return strong_hits >= 1


def filter_quality_results(results, keyword="", low_quality_domains=None, industry_sources=None):
    """Filter low-quality or irrelevant search results."""
    low_quality_domains = low_quality_domains or LOW_QUALITY_DOMAINS
    industry_sources = industry_sources or INDUSTRY_SOURCES

    scored = []
    for r in results:
        url = r.get("url", "")
        title = r.get("title", "")

        if not url or len(url) < 15:
            continue
        if any(x in url for x in ("javascript:", "void(0)", "mailto:", "tel:")):
            continue
        if len(url) > 500:
            continue

        if len(title) < 10:
            continue
        if len(title) > 200:
            continue

        meaningful = sum(1 for c in title if c.isalpha() or ('一' <= c <= '鿿'))
        if meaningful < 5:
            continue

        cjk_chars = sum(1 for c in title if '一' <= c <= '鿿' or '぀' <= c <= 'ヿ')
        ascii_chars = sum(1 for c in title if c.isascii() and c.isalpha())
        total_alnum = sum(1 for c in title if c.isalnum() or c.isspace())
        if total_alnum > 0:
            recognizable = (cjk_chars + ascii_chars) / total_alnum
            if recognizable < 0.5:
                continue

        if any(d in url for d in low_quality_domains):
            continue
        if any(s in title for s in TITLE_BAD_TERMS):
            continue
        if keyword and not has_keyword_relevance(r, keyword):
            continue

        source_score = 0
        for d in industry_sources:
            if d in url:
                source_score = 1
                break
        scored.append((source_score, r))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored]
