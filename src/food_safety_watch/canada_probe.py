from __future__ import annotations

import html
import json
import re
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import urlparse


SOURCE_ID = "ca_recalls_safety_alerts"
OPEN_DATA_JSON_URL = (
    "https://recalls-rappels.canada.ca/sites/default/files/"
    "opendata-donneesouvertes/HCRSAMOpenData.json"
)
OFFICIAL_HOST = "recalls-rappels.canada.ca"
USER_AGENT = (
    "FoodSafetyWatch/0.1 "
    "(+https://github.com/QinkunAry/CheckChineseFoodSafety)"
)

Fetcher = Callable[[str], bytes]

ORIGIN_PATTERNS = [
    re.compile(r"\bcountry\s+of\s+origin\b[:\s-]*(.{0,120})", re.IGNORECASE),
    re.compile(r"\bproduct\s+of\b[:\s-]*(.{0,120})", re.IGNORECASE),
    re.compile(r"\bimported\s+from\b[:\s-]*(.{0,120})", re.IGNORECASE),
    re.compile(r"\bmanufactured\s+in\b[:\s-]*(.{0,120})", re.IGNORECASE),
    re.compile(r"\bmade\s+in\b[:\s-]*(.{0,120})", re.IGNORECASE),
]
CHINA_ORIGIN_PATTERN = re.compile(
    r"\b(china|people's republic of china|people’s republic of china|prc)\b",
    re.IGNORECASE,
)
CHINA_MENTION_PATTERN = re.compile(
    r"\b(china|chinese|people's republic of china|people’s republic of china|prc)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class OriginEvidence:
    pattern: str
    snippet: str
    mentions_china: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "pattern": self.pattern,
            "snippet": self.snippet,
            "mentions_china": self.mentions_china,
        }


def fetch_official(url: str, *, timeout: float = 60) -> bytes:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != OFFICIAL_HOST:
        raise ValueError("Canada probe requests are restricted to the official HTTPS host")
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json,text/html,*/*;q=0.8",
            "User-Agent": USER_AGENT,
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def parse_open_data(payload: bytes) -> list[dict[str, Any]]:
    value = json.loads(payload.decode("utf-8-sig"))
    if not isinstance(value, list):
        raise ValueError("Canada open data JSON must be a list")
    records: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, dict):
            records.append(item)
    return records


def is_official_detail_url(url: str) -> bool:
    parsed = urlparse(url)
    return (
        parsed.scheme == "https"
        and parsed.netloc == OFFICIAL_HOST
        and parsed.path.startswith("/en/alert-recall/")
    )


def is_cfia_food_record(record: dict[str, Any]) -> bool:
    return (
        record.get("Organization") == "CFIA"
        and isinstance(record.get("URL"), str)
        and is_official_detail_url(record["URL"])
    )


def select_cfia_food_records(records: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    if limit < 1:
        raise ValueError("limit must be at least 1")
    return [record for record in records if is_cfia_food_record(record)][:limit]


def html_to_text(payload: bytes) -> str:
    text = payload.decode("utf-8", errors="ignore")
    text = re.sub(r"(?is)<script\b.*?</script>", " ", text)
    text = re.sub(r"(?is)<style\b.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _snippet(text: str, start: int, end: int, *, radius: int = 80) -> str:
    left = max(0, start - radius)
    right = min(len(text), end + radius)
    return text[left:right].strip()


def find_china_mentions(text: str, *, max_mentions: int = 5) -> list[str]:
    mentions: list[str] = []
    for match in CHINA_MENTION_PATTERN.finditer(text):
        mentions.append(_snippet(text, match.start(), match.end(), radius=60))
        if len(mentions) >= max_mentions:
            break
    return mentions


def find_origin_evidence(text: str, *, max_matches: int = 8) -> list[OriginEvidence]:
    evidence: list[OriginEvidence] = []
    seen: set[str] = set()
    for pattern in ORIGIN_PATTERNS:
        for match in pattern.finditer(text):
            snippet = _snippet(text, match.start(), match.end())
            normalized = snippet.lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            evidence.append(
                OriginEvidence(
                    pattern=pattern.pattern,
                    snippet=snippet,
                    mentions_china=bool(CHINA_ORIGIN_PATTERN.search(snippet)),
                )
            )
            if len(evidence) >= max_matches:
                return evidence
    return evidence


def record_text(record: dict[str, Any]) -> str:
    fields = [
        "Title",
        "Product",
        "Issue",
        "What you should do",
        "Category",
        "Recall class",
    ]
    return " ".join(str(record.get(field) or "") for field in fields)


def has_china_mention(record: dict[str, Any]) -> bool:
    return bool(CHINA_MENTION_PATTERN.search(record_text(record)))


def select_probe_records(
    records: list[dict[str, Any]],
    *,
    latest_limit: int,
    china_mention_limit: int,
) -> list[dict[str, Any]]:
    if latest_limit < 1:
        raise ValueError("latest_limit must be at least 1")
    if china_mention_limit < 0:
        raise ValueError("china_mention_limit must not be negative")

    selected: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    def append(record: dict[str, Any]) -> None:
        url = str(record.get("URL") or "")
        if url and url not in seen_urls:
            selected.append(record)
            seen_urls.add(url)

    for record in select_cfia_food_records(records, limit=latest_limit):
        append(record)

    count = 0
    for record in records:
        if not china_mention_limit:
            break
        if not is_cfia_food_record(record) or not has_china_mention(record):
            continue
        append(record)
        count += 1
        if count >= china_mention_limit:
            break

    return selected


def build_origin_probe_report(
    *,
    limit: int = 20,
    china_mention_limit: int = 20,
    fetcher: Fetcher = fetch_official,
    source_url: str = OPEN_DATA_JSON_URL,
    open_data_payload: bytes | None = None,
) -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).isoformat()
    blocking_errors: list[str] = []
    page_results: list[dict[str, Any]] = []

    try:
        payload = open_data_payload if open_data_payload is not None else fetcher(source_url)
        records = parse_open_data(payload)
    except Exception as error:
        return {
            "status": "failed",
            "generated_at": generated_at,
            "source_id": SOURCE_ID,
            "source_url": source_url,
            "blocking_errors": [f"open data fetch/parse failed: {type(error).__name__}: {error}"],
            "total_record_count": 0,
            "cfia_food_record_count": 0,
            "sampled_record_count": 0,
            "origin_evidence_page_count": 0,
            "china_origin_evidence_page_count": 0,
            "page_results": [],
        }

    cfia_records = [record for record in records if is_cfia_food_record(record)]
    china_mention_records = [record for record in cfia_records if has_china_mention(record)]
    sampled = select_probe_records(
        records,
        latest_limit=limit,
        china_mention_limit=china_mention_limit,
    )

    for record in sampled:
        url = str(record["URL"])
        result: dict[str, Any] = {
            "nid": record.get("NID"),
            "title": record.get("Title"),
            "url": url,
            "last_updated": record.get("Last updated"),
            "category": record.get("Category"),
            "issue": record.get("Issue"),
            "open_data_china_mention": has_china_mention(record),
        }
        try:
            text = html_to_text(fetcher(url))
            evidence = find_origin_evidence(text)
            china_mentions = find_china_mentions(text)
            result["origin_evidence_matches"] = [item.to_dict() for item in evidence]
            result["origin_evidence_count"] = len(evidence)
            result["china_origin_evidence_count"] = sum(
                1 for item in evidence if item.mentions_china
            )
            result["china_mentions"] = china_mentions
            if result["china_origin_evidence_count"]:
                result["status"] = "china_origin_evidence"
            elif evidence:
                result["status"] = "origin_evidence_no_china"
            else:
                result["status"] = "no_origin_evidence"
        except Exception as error:
            result["status"] = "error"
            result["error"] = f"{type(error).__name__}: {error}"
            blocking_errors.append(f"detail fetch/parse failed: {url}: {result['error']}")
        page_results.append(result)

    origin_pages = sum(
        1 for result in page_results if result.get("origin_evidence_count", 0) > 0
    )
    china_origin_pages = sum(
        1 for result in page_results if result.get("china_origin_evidence_count", 0) > 0
    )

    return {
        "status": "failed" if blocking_errors else "passed",
        "generated_at": generated_at,
        "source_id": SOURCE_ID,
        "source_url": source_url,
        "total_record_count": len(records),
        "cfia_food_record_count": len(cfia_records),
        "open_data_china_mention_record_count": len(china_mention_records),
        "latest_sample_limit": limit,
        "china_mention_sample_limit": china_mention_limit,
        "sampled_record_count": len(sampled),
        "origin_evidence_page_count": origin_pages,
        "china_origin_evidence_page_count": china_origin_pages,
        "page_results": page_results,
        "blocking_errors": blocking_errors,
    }
