from __future__ import annotations

import html
import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse


SOURCE_ID = "kr_food_safety_korea"
PORTAL_HOST = "www.foodsafetykorea.go.kr"
PORTAL_LIST_URL = (
    "https://www.foodsafetykorea.go.kr/portal/fooddanger/suspension.do"
    "?menu_grp=MENU_NEW02&menu_no=2713"
)
PORTAL_LIST_ENDPOINT = (
    "https://www.foodsafetykorea.go.kr/portal/fooddanger/searchSuspensionList.do"
)
DETAIL_URL_TEMPLATE = (
    "https://www.foodsafetykorea.go.kr/layer/suspensionDetail.do"
    "?search_keyword={record_id}"
)
API_METADATA_URL = (
    "https://www.foodsafetykorea.go.kr/api/openApiInfo.do?"
    "menu_grp=MENU_GRP31&menu_no=661&show_cnt=10&start_idx=1&"
    "svc_no=I0490&svc_type_cd=API_TYPE06"
)
USER_AGENT = (
    "FoodSafetyWatch/0.1 "
    "(+https://github.com/QinkunAry/CheckChineseFoodSafety)"
)

DetailFetcher = Callable[[str], bytes]

CHINA_ORIGIN_RE = re.compile(
    r"(?:중국산|중화인민공화국산)(?=$|[\s()\[\],/·])|"
    r"(?:원산지|제조국)\s*[:：]?\s*(?:중국|중화인민공화국)"
)
ORIGIN_MENTION_RE = re.compile(
    r"(?:(?:중국|베트남|미국|일본|태국|프랑스|호주|캐나다)산|국내산|국산)"
    r"(?=$|[\s()\[\],/·])|(?:원산지|제조국)\s*[:：]"
)
H1_RE = re.compile(r"<h1\b[^>]*>(?P<value>.*?)</h1>", re.DOTALL | re.IGNORECASE)
META_RE = re.compile(
    r'<span\b[^>]*class="[^"]*\bmeta\b[^"]*"[^>]*>(?P<value>.*?)</span>',
    re.DOTALL | re.IGNORECASE,
)
FIELD_RE = re.compile(
    r"<dt\b[^>]*>(?P<label>.*?)</dt>\s*<dd\b[^>]*>(?P<value>.*?)</dd>",
    re.DOTALL | re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class KoreaRecallDetail:
    source_record_id: str
    product_name: str
    event_date: str
    reason: str
    business_name: str
    business_address: str
    food_category: str
    china_origin_evidence: bool
    source_url: str

    def to_dict(self) -> dict[str, object]:
        return {
            "source_record_id": self.source_record_id,
            "product_name": self.product_name,
            "event_date": self.event_date,
            "reason": self.reason,
            "business_name": self.business_name,
            "business_address": self.business_address,
            "food_category": self.food_category,
            "china_origin_evidence": self.china_origin_evidence,
            "source_url": self.source_url,
        }


def clean_html_text(value: str) -> str:
    value = re.sub(r"(?is)<script\b.*?</script>", " ", value)
    value = re.sub(r"(?is)<style\b.*?</style>", " ", value)
    value = re.sub(r"(?s)<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def has_china_origin_evidence(value: str) -> bool:
    return bool(CHINA_ORIGIN_RE.search(value))


def has_origin_mention(value: str) -> bool:
    return bool(ORIGIN_MENTION_RE.search(value))


def detail_url(record_id: str) -> str:
    if not re.fullmatch(r"\d+", record_id):
        raise ValueError("Korea recall record ID must be numeric")
    return DETAIL_URL_TEMPLATE.format(record_id=record_id)


def fetch_recall_list(
    *,
    page: int = 1,
    show_count: int = 400,
    search_keyword: str = "",
    timeout: float = 45,
) -> bytes:
    if page < 1:
        raise ValueError("page must be at least 1")
    if show_count < 1:
        raise ValueError("show_count must be at least 1")
    form = urllib.parse.urlencode(
        {
            "menu_no": "2713",
            "menu_grp": "MENU_NEW02",
            "start_idx": str(page),
            "show_cnt": str(show_count),
            "search_type": "01",
            "search_keyword": search_keyword,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        PORTAL_LIST_ENDPOINT,
        data=form,
        headers={
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": PORTAL_LIST_URL,
            "User-Agent": USER_AGENT,
            "X-Requested-With": "XMLHttpRequest",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def fetch_official_detail(url: str, *, timeout: float = 45) -> bytes:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != PORTAL_HOST:
        raise ValueError("Korea recall detail requests require the official HTTPS host")
    if parsed.path != "/layer/suspensionDetail.do":
        raise ValueError("Korea recall detail URL uses an unexpected path")
    query = parse_qs(parsed.query)
    record_ids = query.get("search_keyword") or []
    if len(record_ids) != 1 or not re.fullmatch(r"\d+", record_ids[0]):
        raise ValueError("Korea recall detail URL requires one numeric search_keyword")
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "text/html,*/*;q=0.8",
            "Referer": PORTAL_LIST_URL,
            "User-Agent": USER_AGENT,
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def parse_recall_list(payload: bytes | str) -> tuple[int, list[dict[str, Any]]]:
    text = payload.decode("utf-8") if isinstance(payload, bytes) else payload
    value = json.loads(text)
    if not isinstance(value, dict) or not isinstance(value.get("list"), list):
        raise ValueError("Korea recall list response does not contain a list")
    try:
        total_count = int(value["total_cnt"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("Korea recall list response has no valid total count") from error

    records: list[dict[str, Any]] = []
    for index, record in enumerate(value["list"]):
        if not isinstance(record, dict):
            raise ValueError(f"Korea recall list item {index} is not an object")
        record_id = str(record.get("rtrvldsuse_seq") or "")
        product_name = str(record.get("prdtnm") or "").strip()
        if not re.fullmatch(r"\d+", record_id) or not product_name:
            raise ValueError(f"Korea recall list item {index} lacks ID or product name")
        records.append(record)
    return total_count, records


def select_probe_records(
    records: list[dict[str, Any]],
    *,
    limit: int,
    origin_mention_limit: int,
) -> list[dict[str, Any]]:
    if limit < 1:
        raise ValueError("limit must be at least 1")
    if origin_mention_limit < 0:
        raise ValueError("origin_mention_limit must not be negative")
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()

    def append(record: dict[str, Any]) -> None:
        record_id = str(record["rtrvldsuse_seq"])
        if record_id not in seen:
            selected.append(record)
            seen.add(record_id)

    for record in records[:limit]:
        append(record)

    china_records = [
        record
        for record in records
        if has_china_origin_evidence(str(record.get("prdtnm") or ""))
    ]
    other_origin_records = [
        record
        for record in records
        if has_origin_mention(str(record.get("prdtnm") or ""))
        and not has_china_origin_evidence(str(record.get("prdtnm") or ""))
    ]
    for record in (china_records + other_origin_records)[:origin_mention_limit]:
        append(record)
    return selected


def _normalize_date(value: str) -> str:
    candidate = value.strip().rstrip(".")
    for pattern in ("%Y.%m.%d", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(candidate, pattern).date().isoformat()
        except ValueError:
            continue
    raise ValueError("Korea recall detail has no supported registration date")


def inspect_recall_detail(payload: bytes | str, source_url: str) -> KoreaRecallDetail:
    parsed_url = urlparse(source_url)
    if parsed_url.scheme != "https" or parsed_url.netloc != PORTAL_HOST:
        raise ValueError("Korea recall source URL must use the official HTTPS host")
    if parsed_url.path != "/layer/suspensionDetail.do":
        raise ValueError("Korea recall source URL is not a detail page")
    query = parse_qs(parsed_url.query)
    record_ids = query.get("search_keyword") or []
    if len(record_ids) != 1 or not re.fullmatch(r"\d+", record_ids[0]):
        raise ValueError("Korea recall source URL requires one numeric record ID")

    text = payload.decode("utf-8", errors="replace") if isinstance(payload, bytes) else payload
    title_match = H1_RE.search(text)
    if not title_match:
        raise ValueError("Korea recall detail has no H1 product title")
    title = clean_html_text(title_match.group("value"))
    product_name = re.sub(r"^제품명\s*[:：]\s*", "", title).strip()
    if not product_name:
        raise ValueError("Korea recall detail has no product name")

    fields: dict[str, str] = {}
    for match in FIELD_RE.finditer(text):
        label = clean_html_text(match.group("label"))
        value = clean_html_text(match.group("value"))
        if label:
            fields[label] = value
    reason = fields.get("회수사유", "")
    if not reason:
        raise ValueError("Korea recall detail has no recall reason")
    meta_match = META_RE.search(text)
    date_text = fields.get("등록일", "")
    if meta_match:
        date_text = clean_html_text(meta_match.group("value")) or date_text

    evidence_text = "\n".join([
        product_name,
        f"원산지: {fields.get('원산지', '')}",
        f"제조국: {fields.get('제조국', '')}",
    ])
    return KoreaRecallDetail(
        source_record_id=record_ids[0],
        product_name=product_name,
        event_date=_normalize_date(date_text),
        reason=reason,
        business_name=fields.get("회수영업자", ""),
        business_address=fields.get("영업자주소", ""),
        food_category=fields.get("식품분류", ""),
        china_origin_evidence=has_china_origin_evidence(evidence_text),
        source_url=source_url,
    )


def build_korea_probe_report(
    *,
    limit: int = 10,
    origin_mention_limit: int = 20,
    min_china_records: int = 0,
    list_payload: bytes | None = None,
    detail_fetcher: DetailFetcher = fetch_official_detail,
) -> dict[str, Any]:
    if min_china_records < 0:
        raise ValueError("min_china_records must not be negative")
    generated_at = datetime.now(timezone.utc).isoformat()
    blocking_errors: list[str] = []
    warnings: list[str] = []
    page_results: list[dict[str, Any]] = []

    try:
        payload = list_payload if list_payload is not None else fetch_recall_list()
        total_count, records = parse_recall_list(payload)
    except Exception as error:
        return {
            "status": "failed",
            "generated_at": generated_at,
            "source_id": SOURCE_ID,
            "portal_list_url": PORTAL_LIST_URL,
            "portal_list_endpoint": PORTAL_LIST_ENDPOINT,
            "api_metadata_url": API_METADATA_URL,
            "blocking_errors": [
                f"Korea recall list fetch/parse failed: {type(error).__name__}: {error}"
            ],
            "warnings": [],
            "portal_total_count": None,
            "portal_returned_count": 0,
            "sampled_record_count": 0,
            "china_origin_evidence_page_count": 0,
            "minimum_china_records": min_china_records,
            "page_results": [],
        }

    if len(records) < total_count:
        warnings.append(
            f"portal returned {len(records)} of {total_count} records; probe coverage is partial"
        )
    selected = select_probe_records(
        records,
        limit=limit,
        origin_mention_limit=origin_mention_limit,
    )

    for record in selected:
        record_id = str(record["rtrvldsuse_seq"])
        url = detail_url(record_id)
        result: dict[str, Any] = {
            "source_record_id": record_id,
            "source_url": url,
            "list_product_name": record.get("prdtnm"),
            "list_reason": record.get("rtrvlprvns"),
            "list_event_date": record.get("hmpgpblict_prcsdtm"),
            "list_food_category": record.get("food_type_nm"),
            "list_china_origin_evidence": has_china_origin_evidence(
                str(record.get("prdtnm") or "")
            ),
        }
        try:
            detail = inspect_recall_detail(detail_fetcher(url), url)
            result.update({"status": "parsed", "detail": detail.to_dict()})
        except Exception as error:
            result["status"] = "error"
            result["error"] = f"{type(error).__name__}: {error}"
            blocking_errors.append(f"detail fetch/parse failed: {url}: {result['error']}")
        page_results.append(result)

    china_pages = sum(
        1
        for result in page_results
        if result.get("detail", {}).get("china_origin_evidence")
    )
    if china_pages < min_china_records:
        blocking_errors.append(
            f"China-origin evidence pages {china_pages} below minimum {min_china_records}"
        )
    explicit_origin_records = sum(
        1 for record in records if has_origin_mention(str(record.get("prdtnm") or ""))
    )
    china_list_records = sum(
        1
        for record in records
        if has_china_origin_evidence(str(record.get("prdtnm") or ""))
    )
    return {
        "status": "failed" if blocking_errors else "passed",
        "generated_at": generated_at,
        "source_id": SOURCE_ID,
        "portal_list_url": PORTAL_LIST_URL,
        "portal_list_endpoint": PORTAL_LIST_ENDPOINT,
        "api_metadata_url": API_METADATA_URL,
        "portal_total_count": total_count,
        "portal_returned_count": len(records),
        "portal_explicit_origin_mention_count": explicit_origin_records,
        "portal_china_origin_product_count": china_list_records,
        "portal_manufacturing_country_field_count": sum(
            1 for record in records if str(record.get("mnf_natncd") or "").strip()
        ),
        "portal_import_product_code_count": sum(
            1 for record in records if str(record.get("incmfood_prdtcd") or "").strip()
        ),
        "portal_report_number_count": sum(
            1 for record in records if str(record.get("prdlst_report_ledg_no") or "").strip()
        ),
        "latest_sample_limit": limit,
        "origin_mention_sample_limit": origin_mention_limit,
        "sampled_record_count": len(selected),
        "china_origin_evidence_page_count": china_pages,
        "minimum_china_records": min_china_records,
        "page_results": page_results,
        "warnings": warnings,
        "blocking_errors": blocking_errors,
    }
