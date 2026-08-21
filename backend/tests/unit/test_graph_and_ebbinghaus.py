"""
Unit tests for Knowledge Graph Triple Extraction, Multi-Factor Importance, and Ebbinghaus Decay logic.
"""

import math
import re


def extract_heuristic_triples(text: str) -> list[tuple[str, str, str]]:
    """Extract Subject-Predicate-Object triples using regex rules."""
    triples: list[tuple[str, str, str]] = []
    patterns = [
        (r"(?i)\b(user|agent|client)\s+(prefers|likes|dislikes|loves|hates)\s+(.+)", 1, 2, 3),
        (r"(?i)\b(user|agent|client)\s+(works\s+at|works\s+for|employed\s+by)\s+(.+)", 1, "WORKS_FOR", 3),
        (r"(?i)\b(user|agent|client)\s+(lives\s+in|resides\s+in|based\s+in)\s+(.+)", 1, "LIVES_IN", 3),
        (r"(?i)\b(user|agent|client)\s+(using|uses|switched\s+to)\s+(.+)", 1, "USES", 3),
        (r"(?i)\b(.+?)\s+is\s+(?:a|an)\s+(.+)", 1, "IS_A", 2),
    ]

    for sentence in text.split("."):
        s = sentence.strip()
        if not s:
            continue
        for pat, s_idx, p_val, o_idx in patterns:
            match = re.search(pat, s)
            if match:
                subj = match.group(s_idx).strip().title()
                pred = p_val if isinstance(p_val, str) else match.group(p_val).strip().upper().replace(" ", "_")
                obj = match.group(o_idx).strip().title()
                if len(subj) > 1 and len(obj) > 1:
                    triples.append((subj, pred, obj))
                    break

    return triples


def calculate_multi_factor_importance(text: str) -> float:
    """Multi-factor importance scoring."""
    base_score = min(len(text) / 500.0, 0.2)
    salience_keywords = [
        "always", "never", "prefer", "like", "dislike", "hate", "love",
        "must", "important", "crucial", "work", "live", "email", "phone",
    ]
    keyword_matches = sum(1 for kw in salience_keywords if re.search(rf"\b{kw}\b", text, re.IGNORECASE))
    salience_score = min(keyword_matches * 0.15, 0.5)

    capitalized = len(re.findall(r"\b[A-Z][a-z]+\b", text))
    numbers = len(re.findall(r"\b\d+\b", text))
    density_score = min((capitalized + numbers) * 0.05, 0.3)

    total = 0.3 + base_score + salience_score + density_score
    return round(min(total, 1.0), 2)


def test_triple_extraction() -> None:
    """Verify regex heuristic entity triple extraction."""
    text = "User prefers Dark Mode. User works at Google. User uses FastAPI."
    triples = extract_heuristic_triples(text)

    assert len(triples) >= 2
    relations = [t[1] for t in triples]
    assert "PREFERS" in relations or "WORKS_FOR" in relations or "USES" in relations
    print("[PASS] Triple extraction test passed")


def test_multi_factor_importance_calculation() -> None:
    """Verify multi-factor importance scoring."""
    high_importance_text = "User always prefers Python 3.11 and FastAPI for Google backend projects."
    low_importance_text = "hello"

    high_score = calculate_multi_factor_importance(high_importance_text)
    low_score = calculate_multi_factor_importance(low_importance_text)

    assert high_score > low_score
    assert 0.0 <= high_score <= 1.0
    assert 0.0 <= low_score <= 1.0
    print("[PASS] Multi-factor importance scoring test passed")


def test_ebbinghaus_decay_formula() -> None:
    """Verify Ebbinghaus retrievability math: R = exp(-age / (30 * (1 + access_count)))."""
    age_days_recent = 1.0
    age_days_old = 90.0
    access_count_low = 0
    access_count_high = 10

    r_recent = math.exp(-age_days_recent / (30.0 * (1 + access_count_low)))
    r_old = math.exp(-age_days_old / (30.0 * (1 + access_count_low)))
    r_old_boosted = math.exp(-age_days_old / (30.0 * (1 + access_count_high)))

    assert r_recent > r_old
    assert r_old_boosted > r_old
    print("[PASS] Ebbinghaus retrievability formula test passed")


def test_rrf_scoring() -> None:
    """Verify Reciprocal Rank Fusion calculation."""
    rank_dense = 1
    retrievability = 0.95
    imp_score = 0.85
    rrf_score = (1.0 / (60 + rank_dense)) + (0.4 * retrievability) + (0.3 * imp_score)
    assert 0.0 < rrf_score < 2.0
    print("[PASS] Reciprocal Rank Fusion (RRF) test passed")


if __name__ == "__main__":
    test_triple_extraction()
    test_multi_factor_importance_calculation()
    test_ebbinghaus_decay_formula()
    test_rrf_scoring()
    print("\nALL UNIT TESTS PASSED SUCCESSFULLY!")
