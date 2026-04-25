from __future__ import annotations

import re
from dataclasses import asdict, dataclass


COMPARE_PREFIX_RE = re.compile(r"^\s*compare\b\s+", re.IGNORECASE)
DIFFERENCE_PATTERNS = [
    re.compile(r"^\s*(?:what\s+is\s+)?(?:the\s+)?(?:difference|differences)\s+between\s+(?P<a>.+?)\s+and\s+(?P<b>.+?)\s*$", re.IGNORECASE),
    re.compile(r"^\s*(?:what\s+)?differ(?:ence|ences)?\s+between\s+(?P<a>.+?)\s+and\s+(?P<b>.+?)\s*$", re.IGNORECASE),
]
DELIMITER_SPECS = [
    (" versus ", "compare_versus"),
    (" vs ", "compare_vs"),
    (" with ", "compare_with"),
    (" and ", "compare_and"),
]
CLAUSE_CUTOFF_RE = re.compile(
    r"(?:,\s+(?:and|but)\s+(?:what|how|why|which)\b.*$)|"
    r"(?:,\s+(?:what|how|why|which)\b.*$)|"
    r"(?:\s+and\s+(?:what|how|why|which)\b.*$)",
    re.IGNORECASE,
)
TOKEN_RE = re.compile(r"[a-z0-9_]+")
GENERIC_START_TOKENS = {"the", "a", "an"}
WEAK_SIDE_TERMS = {"guidance", "setup", "workflow", "docs", "documentation"}


@dataclass(frozen=True)
class ComparisonTargets:
    side_a: str
    side_b: str
    raw_query: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ComparisonParseResult:
    raw_query: str
    side_a: str = ""
    side_b: str = ""
    pattern_name: str = ""
    failure_reason: str = ""

    @property
    def success(self) -> bool:
        return bool(self.side_a and self.side_b)

    def to_targets(self) -> ComparisonTargets:
        if not self.success:
            raise ValueError("Cannot convert unsuccessful parse result to comparison targets")
        return ComparisonTargets(
            side_a=self.side_a,
            side_b=self.side_b,
            raw_query=self.raw_query,
        )


def parse_comparison_query(query: str) -> ComparisonParseResult:
    raw_query = " ".join(query.strip().split())
    if not raw_query:
        return ComparisonParseResult(raw_query=query, failure_reason="query is empty after whitespace normalization")

    compare_result = parse_compare_prefix_pattern(raw_query)
    if compare_result.success:
        return compare_result

    difference_result = parse_difference_pattern(raw_query)
    if difference_result.success:
        return difference_result

    if compare_result.failure_reason:
        return ComparisonParseResult(
            raw_query=raw_query,
            failure_reason=f"compare-style parsing failed: {compare_result.failure_reason}",
        )
    return ComparisonParseResult(
        raw_query=raw_query,
        failure_reason="no supported comparison pattern matched",
    )


def parse_compare_prefix_pattern(raw_query: str) -> ComparisonParseResult:
    compare_match = COMPARE_PREFIX_RE.match(raw_query)
    if not compare_match:
        return ComparisonParseResult(
            raw_query=raw_query,
            failure_reason="query does not start with the 'Compare' pattern",
        )

    remainder = raw_query[compare_match.end() :].strip()
    if not remainder:
        return ComparisonParseResult(
            raw_query=raw_query,
            failure_reason="query starts with 'Compare' but does not contain two target phrases",
        )

    best_candidate: tuple[int, ComparisonParseResult] | None = None
    for delimiter, pattern_name in DELIMITER_SPECS:
        positions = find_delimiter_positions(remainder, delimiter)
        for position in positions:
            left = remainder[:position]
            right = remainder[position + len(delimiter) :]
            parse_result = build_parse_result(
                raw_query=raw_query,
                side_a_text=left,
                side_b_text=right,
                pattern_name=pattern_name,
            )
            if not parse_result.success:
                continue
            score = score_target_split(parse_result.side_a, parse_result.side_b, delimiter=delimiter)
            if best_candidate is None or score > best_candidate[0]:
                best_candidate = (score, parse_result)

    if best_candidate is not None:
        return best_candidate[1]

    return ComparisonParseResult(
        raw_query=raw_query,
        failure_reason="no valid delimiter split found for Compare A and/with/vs/versus B",
    )


def parse_difference_pattern(raw_query: str) -> ComparisonParseResult:
    for index, pattern in enumerate(DIFFERENCE_PATTERNS, start=1):
        match = pattern.match(raw_query)
        if not match:
            continue
        parse_result = build_parse_result(
            raw_query=raw_query,
            side_a_text=match.group("a"),
            side_b_text=match.group("b"),
            pattern_name=f"difference_pattern_{index}",
        )
        if parse_result.success:
            return parse_result

    return ComparisonParseResult(
        raw_query=raw_query,
        failure_reason="no supported 'difference between A and B' pattern matched",
    )


def build_parse_result(
    *,
    raw_query: str,
    side_a_text: str,
    side_b_text: str,
    pattern_name: str,
) -> ComparisonParseResult:
    side_a = clean_target_text(side_a_text)
    side_b = clean_target_text(side_b_text)

    if not side_a or not side_b:
        return ComparisonParseResult(
            raw_query=raw_query,
            pattern_name=pattern_name,
            failure_reason="one comparison side became empty after trimming",
        )
    if normalize_target(side_a) == normalize_target(side_b):
        return ComparisonParseResult(
            raw_query=raw_query,
            pattern_name=pattern_name,
            failure_reason="the two comparison sides normalized to the same text",
        )

    return ComparisonParseResult(
        raw_query=raw_query,
        side_a=side_a,
        side_b=side_b,
        pattern_name=pattern_name,
    )


def clean_target_text(text: str) -> str:
    cleaned = " ".join(text.strip().split())
    cleaned = CLAUSE_CUTOFF_RE.sub("", cleaned).strip()
    cleaned = cleaned.strip(" ?.,:;()[]{}\"'")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def normalize_target(target: str) -> str:
    return " ".join(target.lower().split())


def find_delimiter_positions(text: str, delimiter: str) -> list[int]:
    positions: list[int] = []
    start = 0
    normalized_text = text.lower()
    normalized_delimiter = delimiter.lower()
    while True:
        position = normalized_text.find(normalized_delimiter, start)
        if position == -1:
            break
        positions.append(position)
        start = position + len(normalized_delimiter)
    return positions


def score_target_split(side_a: str, side_b: str, *, delimiter: str) -> int:
    tokens_a = TOKEN_RE.findall(normalize_target(side_a))
    tokens_b = TOKEN_RE.findall(normalize_target(side_b))
    content_tokens_a = [token for token in tokens_a if token not in GENERIC_START_TOKENS]
    content_tokens_b = [token for token in tokens_b if token not in GENERIC_START_TOKENS]

    score = 0
    score += 2 if len(content_tokens_a) >= 2 else 0
    score += 2 if len(content_tokens_b) >= 2 else 0
    score += 1 if len(side_a) >= 8 else 0
    score += 1 if len(side_b) >= 8 else 0
    score += 2 if delimiter.strip() in {"with", "vs", "versus"} else 1
    score += 1 if content_tokens_a and content_tokens_b else 0
    score += 1 if abs(len(content_tokens_a) - len(content_tokens_b)) <= 6 else 0
    score += 1 if contains_distinguishing_terms(content_tokens_a) else 0
    score += 1 if contains_distinguishing_terms(content_tokens_b) else 0
    return score


def contains_distinguishing_terms(tokens: list[str]) -> bool:
    return any(token not in WEAK_SIDE_TERMS for token in tokens)
