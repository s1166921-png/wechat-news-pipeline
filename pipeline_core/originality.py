import re

from pipeline_core.facts import extract_fact_tokens


def _normalize_text(text):
    text = re.sub(r"\s+", "", text or "")
    text = re.sub(r"[，。！？、；：,.!?;:《》“”\"'（）()\[\]{}\-—_`~#*>|]", "", text)
    return text


def _mask_allowed_verbatim(text, peer_text):
    masked = text or ""
    combined = f"{text or ''}\n{peer_text or ''}"
    allowed = set(extract_fact_tokens(combined))
    allowed.update(re.findall(r"《[^》]{4,80}》", combined))
    for token in sorted(allowed, key=len, reverse=True):
        if token:
            masked = masked.replace(token, "FACT")
    return masked


def _longest_common_substring(a, b):
    if not a or not b:
        return ""
    previous = [0] * (len(b) + 1)
    best_len = 0
    best_end = 0
    for i, ca in enumerate(a, 1):
        current = [0] * (len(b) + 1)
        for j, cb in enumerate(b, 1):
            if ca == cb:
                current[j] = previous[j - 1] + 1
                if current[j] > best_len:
                    best_len = current[j]
                    best_end = i
        previous = current
    return a[best_end - best_len:best_end]


def _copied_passages(output_text, source_text, min_len):
    source = _normalize_text(source_text)
    passages = []
    seen = set()
    for raw_sentence in re.split(r"(?<=[。！？!?；;])\s*|\n+", output_text or ""):
        sentence = _normalize_text(raw_sentence)
        if len(sentence) < min_len:
            continue
        copied = _longest_common_substring(sentence, source)
        if len(copied) >= min_len and copied not in seen:
            seen.add(copied)
            passages.append(copied[:120])
    return passages


def assess_rewrite_originality(output_text, source_text, max_copied_run=30):
    """Assess whether a rewrite is too close to the source wording."""
    output_for_similarity = _mask_allowed_verbatim(output_text, source_text)
    source_for_similarity = _mask_allowed_verbatim(source_text, output_text)
    output = _normalize_text(output_for_similarity)
    source = _normalize_text(source_for_similarity)
    copied_run = _longest_common_substring(output, source)
    copied_passages = _copied_passages(output_for_similarity, source_for_similarity, min_len=max(24, max_copied_run))
    max_run = len(copied_run)
    copied_ratio = round(max_run / max(1, len(output)), 4)
    acceptable = max_run < max_copied_run
    return {
        "acceptable": acceptable,
        "max_copied_run": max_run,
        "copied_ratio": copied_ratio,
        "copied_passages": copied_passages,
    }
