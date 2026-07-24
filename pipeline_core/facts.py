import re


FACT_PATTERNS = [
    # Policy and formal document identifiers.
    r"\d{4}年第\d+号公告",
    r"第\d+号公告",
    r"公告第\d+号",
    r"税总\d{4}年第\d+号公告",
    r"国税发\[\d{4}\]\d+号",
    # Absolute dates.
    r"\d{4}年\d{1,2}月\d{1,2}日",
    r"\d{4}-\d{1,2}-\d{1,2}",
    r"\d{1,2}月\d{1,2}日",
    # Ranges and durations.
    r"\d+(?:-\d+|到\d+|至\d+)(?:天|日|个月|月|年|周|小时)",
    r"\d+(?:天|日|个月|月|年|周|小时)",
    # Percentages and rates.
    r"\d+(?:\.\d+)?%",
    r"\d+(?:\.\d+)?％",
    # Money and quantities with common business units.
    r"\d+(?:\.\d+)?(?:万|亿)?(?:元|美元|美金|人民币|欧元)",
    r"\d+(?:\.\d+)?(?:万|亿)?(?:单|票|家|个|件|人|SKU|sku)",
]


def normalize_fact_token(token):
    token = (token or "").strip()
    token = token.replace("％", "%")
    token = re.sub(r"\s+", "", token)
    return token


def extract_fact_tokens(text):
    """Extract concrete fact tokens that should be grounded in source material."""
    tokens = []
    seen = set()
    text = text or ""
    for pattern in FACT_PATTERNS:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            token = normalize_fact_token(match.group(0))
            if token and token not in seen:
                seen.add(token)
                tokens.append(token)
    return tokens


def find_unsupported_fact_tokens(output_text, source_text):
    """Return concrete fact tokens in output that are absent from the source."""
    source_tokens = set(extract_fact_tokens(source_text))
    unsupported = []
    for token in extract_fact_tokens(output_text):
        if token not in source_tokens:
            unsupported.append(token)
    return unsupported
