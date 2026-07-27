import re


FACT_PATTERNS = [
    # Policy and formal document identifiers.
    r"\d{4}年第\d+号公告",
    r"第\d+号公告",
    r"第[一二三四五六七八九十百千零〇两\d]+条",
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

SOFT_CLAIM_PATTERNS = [
    "近期发布",
    "最新发布",
    "正式发布",
    "落地实施",
    "释放出明确信号",
    "明确信号",
    "底层逻辑",
    "本质上是",
    "意味着",
    "直接冲击",
    "直接影响",
    "监管升级",
    "审核收紧",
    "政策收紧",
    "全面收紧",
    "显著提升",
    "明显增加",
    "核心原因",
    "主要原因",
]

SOFT_CLAIM_NEUTRAL_REPLACEMENTS = {
    "近期发布": "原文提到",
    "最新发布": "原文提到",
    "正式发布": "原文提到",
    "落地实施": "提到",
    "释放出明确信号": "提示",
    "明确信号": "相关提示",
    "底层逻辑": "需要关注的背景",
    "本质上是": "可以理解为",
    "意味着": "可能意味着",
    "直接冲击": "可能影响",
    "直接影响": "可能影响",
    "监管升级": "合规要求变化",
    "审核收紧": "审核要求变化",
    "政策收紧": "政策要求变化",
    "全面收紧": "要求变化",
    "显著提升": "有所提升",
    "明显增加": "有所增加",
    "核心原因": "需要关注的原因",
    "主要原因": "需要关注的原因",
}


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
    return _drop_redundant_subtokens(tokens)


def _drop_redundant_subtokens(tokens):
    filtered = []
    for token in tokens:
        is_redundant = any(token != other and token in other for other in tokens)
        if not is_redundant:
            filtered.append(token)
    return filtered


def find_unsupported_fact_tokens(output_text, source_text):
    """Return concrete fact tokens in output that are absent from the source."""
    source_tokens = set(extract_fact_tokens(source_text))
    unsupported = []
    for token in extract_fact_tokens(output_text):
        if token not in source_tokens:
            unsupported.append(token)
    return unsupported


def remove_unsupported_fact_sentences(output_text, source_text):
    """Remove sentences or markdown table/list lines that contain unsupported hard facts."""
    unsupported = find_unsupported_fact_tokens(output_text, source_text)
    if not unsupported:
        return output_text or ""

    cleaned_lines = []
    for line in (output_text or "").splitlines():
        if not line.strip():
            cleaned_lines.append(line)
            continue
        if line.lstrip().startswith("|") or line.lstrip().startswith(("- ", "* ", "+ ")) or re.match(r"^\s*\d+[\.\)]\s+", line):
            if any(token in line for token in unsupported):
                continue
            cleaned_lines.append(line)
            continue

        parts = re.split(r"(?<=[。！？!?；;])", line)
        kept_parts = []
        for part in parts:
            if part and any(token in part for token in unsupported):
                continue
            kept_parts.append(part)
        cleaned_line = "".join(kept_parts).strip()
        if cleaned_line:
            cleaned_lines.append(cleaned_line)

    return "\n".join(cleaned_lines)


def extract_soft_claims(text):
    """Extract interpretation-heavy claims that should be grounded by source wording."""
    text = text or ""
    claims = []
    seen = set()
    for sentence in re.split(r"(?<=[。！？!?；;])\s*|\n+", text):
        sentence = sentence.strip()
        if not sentence:
            continue
        for marker in SOFT_CLAIM_PATTERNS:
            if marker in sentence and marker not in seen:
                seen.add(marker)
                claims.append({"marker": marker, "sentence": sentence[:160]})
    return claims


def find_unsupported_soft_claims(output_text, source_text):
    """Return soft interpretation markers absent from the source text."""
    source_text = source_text or ""
    unsupported = []
    for claim in extract_soft_claims(output_text):
        marker = claim["marker"]
        if marker not in source_text:
            unsupported.append(f"{marker}: {claim['sentence']}")
    return unsupported


def neutralize_unsupported_soft_claims(output_text, source_text):
    """Soften unsupported interpretation markers without changing hard facts."""
    source_text = source_text or ""
    neutralized = output_text or ""
    for marker, replacement in SOFT_CLAIM_NEUTRAL_REPLACEMENTS.items():
        if marker not in source_text:
            neutralized = neutralized.replace(marker, replacement)
    return neutralized
