from __future__ import annotations

import html
import json
import re
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import urljoin, urlparse


SOURCE_ID = "jp_caa_recalls"
CAA_FOOD_URL = "https://www.recall.caa.go.jp/result/index.php?screenkbn=01&category=1"
CAA_HOST = "www.recall.caa.go.jp"
MHLW_PUBLIC_HOST = "i2fas.mhlw.go.jp"
USER_AGENT = (
    "FoodSafetyWatch/0.1 "
    "(+https://github.com/QinkunAry/CheckChineseFoodSafety)"
)

Fetcher = Callable[[str], bytes]

LIST_ITEM_RE = re.compile(
    r'<a href="(?P<href>/result/detail\.php\?rcl=(?P<rcl>\d+)&screenkbn=01)"[^>]*>'
    r"(?P<title>.*?)</a>.*?"
    r'<span class="result_list_post_date">(?P<post_date>[^<]+)</span>.*?'
    r'<span class="result_list_start_date">(?P<start_date>[^<]+)</span>',
    re.DOTALL,
)
TOTAL_RE = re.compile(r"(?P<count>\d+)件中")
HIDDEN_TEXT_RE = re.compile(
    r'<input type="hidden" name="(?P<name>_[^"]+_str)" value="(?P<value>.*?)" class="TEXT"',
    re.DOTALL,
)
DETAIL_TITLE_RE = re.compile(r"<h3>(?P<title>.*?)</h3>", re.DOTALL)
MHLW_REF_RE = re.compile(
    r'https://i2fas\.mhlw\.go\.jp/faspub/_link\.do\?i=IO_S020502&amp;p=(?P<rcl>RCL\d+)|'
    r'https://i2fas\.mhlw\.go\.jp/faspub/_link\.do\?i=IO_S020502&p=(?P<rcl_plain>RCL\d+)'
)
CHINA_ORIGIN_RE = re.compile(r"(中国産|中華人民共和国産|原産国[:：]?\s*中国|中国製)")


@dataclass(frozen=True)
class CaaListItem:
    rcl: str
    title: str
    url: str
    post_date: str
    start_date: str

    def to_dict(self) -> dict[str, str]:
        return {
            "rcl": self.rcl,
            "title": self.title,
            "url": self.url,
            "post_date": self.post_date,
            "start_date": self.start_date,
        }


def fetch_official(url: str, *, timeout: float = 45) -> bytes:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc not in {CAA_HOST, MHLW_PUBLIC_HOST}:
        raise ValueError("Japan probe requests are restricted to official HTTPS hosts")
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "text/html,*/*;q=0.8",
            "User-Agent": USER_AGENT,
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def clean_html_text(value: str) -> str:
    value = re.sub(r"(?is)<script\b.*?</script>", " ", value)
    value = re.sub(r"(?is)<style\b.*?</style>", " ", value)
    value = re.sub(r"(?s)<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def parse_caa_food_list(payload: bytes, *, base_url: str = CAA_FOOD_URL) -> tuple[int | None, list[CaaListItem]]:
    text = payload.decode("utf-8", errors="ignore")
    total_match = TOTAL_RE.search(text)
    total_count = int(total_match.group("count")) if total_match else None
    items: list[CaaListItem] = []
    for match in LIST_ITEM_RE.finditer(text):
        items.append(
            CaaListItem(
                rcl=match.group("rcl"),
                title=clean_html_text(match.group("title")),
                url=urljoin(base_url, match.group("href")),
                post_date=match.group("post_date"),
                start_date=match.group("start_date"),
            )
        )
    return total_count, items


def has_china_origin_evidence(text: str) -> bool:
    return bool(CHINA_ORIGIN_RE.search(text))


def select_probe_items(items: list[CaaListItem], *, limit: int, china_mention_limit: int) -> list[CaaListItem]:
    if limit < 1:
        raise ValueError("limit must be at least 1")
    if china_mention_limit < 0:
        raise ValueError("china_mention_limit must not be negative")
    selected: list[CaaListItem] = []
    seen: set[str] = set()

    def append(item: CaaListItem) -> None:
        if item.rcl not in seen:
            selected.append(item)
            seen.add(item.rcl)

    for item in items[:limit]:
        append(item)

    count = 0
    for item in items:
        if not china_mention_limit:
            break
        if "中国" not in item.title:
            continue
        append(item)
        count += 1
        if count >= china_mention_limit:
            break
    return selected


def extract_hidden_text_fields(payload: bytes) -> dict[str, str]:
    text = payload.decode("utf-8", errors="ignore")
    fields: dict[str, str] = {}
    for match in HIDDEN_TEXT_RE.finditer(text):
        fields[match.group("name")] = html.unescape(match.group("value")).strip()
    return fields


def inspect_caa_detail(payload: bytes) -> dict[str, Any]:
    text = payload.decode("utf-8", errors="ignore")
    fields = extract_hidden_text_fields(payload)
    title_match = DETAIL_TITLE_RE.search(text)
    mhlw_match = MHLW_REF_RE.search(text)
    product = fields.get("_rcl_product_str") or ""
    specific_info = fields.get("_rcl_info_str") or ""
    reason_type = fields.get("_rcl_rsn_type_str") or ""
    reason_memo = fields.get("_rcl_rsn_memo_str") or ""
    evidence_text = "\n".join([
        clean_html_text(title_match.group("title")) if title_match else "",
        product,
        specific_info,
        reason_memo,
    ])
    mhlw_reference_id = None
    if mhlw_match:
        mhlw_reference_id = mhlw_match.group("rcl") or mhlw_match.group("rcl_plain")
    return {
        "title": clean_html_text(title_match.group("title")) if title_match else None,
        "product": product,
        "specific_info_excerpt": specific_info[:300],
        "reason_type": reason_type,
        "reason_excerpt": reason_memo[:300],
        "mhlw_reference_id": mhlw_reference_id,
        "china_origin_evidence": has_china_origin_evidence(evidence_text),
    }


def inspect_mhlw_detail(payload: bytes) -> dict[str, Any]:
    fields = extract_hidden_text_fields(payload)
    evidence_text = "\n".join([
        fields.get("_rcl_product_str") or "",
        fields.get("_rcl_info_str") or "",
        fields.get("_rcl_rsn_memo_str") or "",
    ])
    return {
        "rcl_no": fields.get("_rcl_no_str"),
        "product": fields.get("_rcl_product_str"),
        "specific_info_excerpt": (fields.get("_rcl_info_str") or "")[:300],
        "reason_type": fields.get("_rcl_rsn_type_str"),
        "reason_excerpt": (fields.get("_rcl_rsn_memo_str") or "")[:300],
        "china_origin_evidence": has_china_origin_evidence(evidence_text),
    }


def build_japan_probe_report(
    *,
    limit: int = 10,
    china_mention_limit: int = 5,
    fetcher: Fetcher = fetch_official,
    list_payload: bytes | None = None,
) -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).isoformat()
    blocking_errors: list[str] = []
    page_results: list[dict[str, Any]] = []

    try:
        payload = list_payload if list_payload is not None else fetcher(CAA_FOOD_URL)
        total_count, items = parse_caa_food_list(payload)
    except Exception as error:
        return {
            "status": "failed",
            "generated_at": generated_at,
            "source_id": SOURCE_ID,
            "list_url": CAA_FOOD_URL,
            "blocking_errors": [f"CAA food list fetch/parse failed: {type(error).__name__}: {error}"],
            "list_total_count": None,
            "list_item_count": 0,
            "sampled_record_count": 0,
            "china_origin_evidence_page_count": 0,
            "mhlw_reference_count": 0,
            "page_results": [],
        }

    sampled = select_probe_items(
        items,
        limit=limit,
        china_mention_limit=china_mention_limit,
    )

    for item in sampled:
        result: dict[str, Any] = item.to_dict()
        result["list_title_china_mention"] = "中国" in item.title
        try:
            detail = inspect_caa_detail(fetcher(item.url))
            result.update({
                "status": "parsed",
                "detail": detail,
            })
            if detail.get("mhlw_reference_id"):
                mhlw_url = (
                    "https://i2fas.mhlw.go.jp/faspub/_link.do?"
                    f"i=IO_S020502&p={detail['mhlw_reference_id']}"
                )
                result["mhlw_url"] = mhlw_url
                try:
                    result["mhlw_detail"] = inspect_mhlw_detail(fetcher(mhlw_url))
                except Exception as error:
                    result["mhlw_error"] = f"{type(error).__name__}: {error}"
        except Exception as error:
            result["status"] = "error"
            result["error"] = f"{type(error).__name__}: {error}"
            blocking_errors.append(f"CAA detail fetch/parse failed: {item.url}: {result['error']}")
        page_results.append(result)

    china_origin_pages = sum(
        1
        for result in page_results
        if result.get("detail", {}).get("china_origin_evidence")
        or result.get("mhlw_detail", {}).get("china_origin_evidence")
    )
    mhlw_reference_count = sum(
        1 for result in page_results if result.get("detail", {}).get("mhlw_reference_id")
    )

    return {
        "status": "failed" if blocking_errors else "passed",
        "generated_at": generated_at,
        "source_id": SOURCE_ID,
        "list_url": CAA_FOOD_URL,
        "list_total_count": total_count,
        "list_item_count": len(items),
        "latest_sample_limit": limit,
        "china_mention_sample_limit": china_mention_limit,
        "sampled_record_count": len(sampled),
        "china_origin_evidence_page_count": china_origin_pages,
        "mhlw_reference_count": mhlw_reference_count,
        "page_results": page_results,
        "blocking_errors": blocking_errors,
    }
