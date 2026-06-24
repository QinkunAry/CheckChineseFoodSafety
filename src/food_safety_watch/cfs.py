from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import unquote, urljoin, urlparse

from .classification import classify_reasons
from .models import SafetyRecord, stable_id


SOURCE_ID = "hk_cfs_alerts"
AUTHORITY = "Hong Kong Centre for Food Safety"
AUTHORITY_REGION = "HK"
ALERT_INDEX_URL = "https://www.cfs.gov.hk/english/whatsnew/whatsnew_fa/whatsnew_fa.html"
ALERT_PREFIX = "https://www.cfs.gov.hk/english/whatsnew/whatsnew_fa/"


@dataclass(frozen=True, slots=True)
class AlertPage:
    title: str
    event_date: str
    food_product: str
    product_description: str
    origin_text: str
    reasons: list[str]


class _DetailParser(HTMLParser):
    _ignored_tags = {"script", "style", "noscript", "svg"}
    _capture_tags = {"h1", "h2", "th", "td"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.rows: list[tuple[str, str]] = []
        self._captures: list[tuple[str, list[str]]] = []
        self._active_row: dict[str, str] = {}
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._ignored_tags:
            self._ignored_depth += 1
            return
        if self._ignored_depth:
            return
        if tag == "tr":
            self._active_row = {}
        if tag in self._capture_tags:
            self._captures.append((tag, []))

    def handle_endtag(self, tag: str) -> None:
        if tag in self._ignored_tags and self._ignored_depth:
            self._ignored_depth -= 1
            return
        if self._ignored_depth:
            return
        for index in range(len(self._captures) - 1, -1, -1):
            captured_tag, parts = self._captures[index]
            if captured_tag != tag:
                continue
            del self._captures[index]
            value = _clean_text(" ".join(parts))
            if captured_tag in {"h1", "h2"} and value and not self.title:
                self.title = value
            if captured_tag in {"th", "td"} and value:
                self._active_row[captured_tag] = value
            break
        if tag == "tr":
            label = self._active_row.get("th", "")
            value = self._active_row.get("td", "")
            if label and value:
                self.rows.append((label, value))
            self._active_row = {}

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        for _, parts in self._captures:
            parts.append(data)


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def _assert_official_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "www.cfs.gov.hk":
        raise ValueError("CFS source URL must use the official HTTPS host")
    if not url.startswith(ALERT_PREFIX):
        raise ValueError("CFS source URL is not a food alert detail URL")


def extract_alert_urls(page: bytes | str, base_url: str = ALERT_INDEX_URL) -> list[str]:
    text = page.decode("utf-8", errors="replace") if isinstance(page, bytes) else page
    urls: set[str] = set()
    for href in re.findall(r'''href=["']([^"']*\d{4}_\d+\.html)["']''', text, flags=re.I):
        url = urljoin(base_url, html.unescape(href))
        if url.startswith(ALERT_PREFIX):
            urls.add(url)
    return sorted(urls)


def _normalize_date(value: str) -> str:
    value = value.strip()
    for pattern in ("%d.%m.%Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(value, pattern).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"CFS alert page does not contain a supported issue date: {value!r}")


def _field(rows: list[tuple[str, str]], label: str) -> str:
    wanted = label.casefold()
    for key, value in rows:
        if key.casefold() == wanted:
            return value
    return ""


def _extract_origin(product_description: str) -> str:
    labels = (
        "product name", "produce name", "brand", "place of origin", "packer",
        "net weight", "pack size", "best-before date", "best before date",
        "best by date", "manufacture date", "importer", "distributor",
        "batch number", "jan code", "use-by date", "expiry date",
    )
    pattern = (
        r"place of origin\s*[:：]\s*(.*?)"
        rf"(?=\s+(?:{'|'.join(re.escape(label) for label in labels)})\s*[:：]|$)"
    )
    match = re.search(pattern, product_description, flags=re.I)
    if not match:
        raise ValueError("CFS alert page does not contain a place of origin")
    return _clean_text(match.group(1))


_CHINA_ORIGIN_TERMS = {
    "anhui", "beijing", "chongqing", "fujian", "gansu", "guangdong",
    "guangxi", "guizhou", "hainan", "hebei", "heilongjiang", "henan",
    "hubei", "hunan", "inner mongolia", "jiangsu", "jiangxi", "jilin",
    "liaoning", "mainland china", "ningxia", "qinghai", "sichuan",
    "shaanxi", "shandong", "shanghai", "shanxi", "tianjin", "tibet",
    "xinjiang", "yunnan", "zhejiang",
}


def _is_china_origin(value: str) -> bool:
    normalized = value.casefold()
    if re.search(r"\b(?:china|people's republic of china|prc)\b", normalized):
        return True
    return any(re.search(rf"\b{re.escape(term)}\b", normalized) for term in _CHINA_ORIGIN_TERMS)


def _product_category(value: str) -> str:
    text = value.casefold()
    rules = {
        "baby_food": ("infant formula", "growing up formula", "baby food"),
        "seafood": ("fish", "grouper", "shrimp", "prawn", "seafood"),
        "meat_and_poultry": ("sausage", "salami", "beef", "pork", "chicken", "turkey"),
        "vegetables": ("mushroom", "fungi", "vegetable", "bamboo"),
        "fruit": ("fruit", "jam", "apple"),
        "dairy": ("cheese", "yoghurt", "milk", "cream"),
        "candy": ("chocolate", "confection"),
        "spices_and_salt": ("pepper", "cumin", "seasoning", "spice"),
        "prepared_meals_and_sauces": ("bean curd", "sauce", "preserved"),
        "soft_drinks_and_water": ("water", "juice"),
        "grains_and_starches": ("rice",),
    }
    for category, keywords in rules.items():
        if any(keyword in text for keyword in keywords):
            return category
    return "other_food"


def inspect_alert_page(page: bytes | str, source_url: str) -> AlertPage:
    _assert_official_url(source_url)
    text = page.decode("utf-8", errors="replace") if isinstance(page, bytes) else page
    parser = _DetailParser()
    parser.feed(text)
    if not parser.title:
        raise ValueError("CFS alert page does not contain a title")

    event_date = _normalize_date(_field(parser.rows, "Issue Date"))
    food_product = _field(parser.rows, "Food Product")
    product_description = _field(parser.rows, "Product Name and Description")
    origin_text = _extract_origin(product_description)
    reason_text = _field(parser.rows, "Reason For Issuing Alert")
    reasons = [reason_text] if reason_text else []
    if not food_product:
        raise ValueError("CFS alert page does not contain a food product")
    if not reasons:
        raise ValueError("CFS alert page does not contain a reason for issuing alert")
    return AlertPage(
        title=parser.title,
        event_date=event_date,
        food_product=food_product,
        product_description=product_description,
        origin_text=origin_text,
        reasons=reasons,
    )


def parse_alert_page(
    page: bytes | str,
    source_url: str,
    *,
    retrieved_at: str | None = None,
) -> SafetyRecord | None:
    detail = inspect_alert_page(page, source_url)
    if not _is_china_origin(detail.origin_text):
        return None
    parsed_url = urlparse(source_url)
    source_record_id = unquote(parsed_url.path.rstrip("/").rsplit("/", 1)[-1])
    now = retrieved_at or datetime.now(timezone.utc).isoformat()
    return SafetyRecord(
        id=stable_id(SOURCE_ID, source_record_id),
        source_id=SOURCE_ID,
        source_record_id=source_record_id,
        authority=AUTHORITY,
        authority_region=AUTHORITY_REGION,
        action_type="safety_alert",
        event_date=detail.event_date,
        origin_country="CN",
        producer_name="",
        producer_location=detail.origin_text,
        product_code="",
        product_category=_product_category(f"{detail.food_product} {detail.product_description}"),
        product_name=detail.title,
        reasons=detail.reasons,
        hazard_tags=classify_reasons(detail.reasons),
        source_url=source_url,
        retrieved_at=now,
    )
