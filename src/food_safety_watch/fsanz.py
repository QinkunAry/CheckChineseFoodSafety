from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import unquote, urlparse

from .classification import classify_reasons
from .models import SafetyRecord, stable_id


SOURCE_ID = "au_fsanz_recalls"
AUTHORITY = "Food Standards Australia New Zealand"
SITEMAP_URL = "https://www.foodstandards.gov.au/sitemap.xml"
RECALL_PREFIX = "https://www.foodstandards.gov.au/food-recalls/recall-alert/"

FIELD_LABELS = {
    "date published",
    "product information",
    "date markings",
    "problem",
    "food safety hazard",
    "country of origin",
    "what to do",
    "contact details",
}


class _RecallPageParser(HTMLParser):
    _text_tags = {"h1", "h2", "h3", "h4", "h5", "h6", "li", "p", "time"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[str] = []
        self.title = ""
        self.time_values: list[str] = []
        self._captures: list[tuple[str, list[str]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        is_drupal_field = tag == "div" and bool(
            classes & {"field__label", "field__item", "field__items"}
        )
        if tag in self._text_tags or is_drupal_field:
            self._captures.append((tag, []))
        if tag == "time":
            if attributes.get("datetime"):
                self.time_values.append(attributes["datetime"] or "")

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self._captures) - 1, -1, -1):
            captured_tag, parts = self._captures[index]
            if captured_tag != tag:
                continue
            del self._captures[index]
            value = _clean_text(" ".join(parts))
            if value:
                self.blocks.append(value)
                if tag == "h1" and not self.title:
                    self.title = value
            break

    def handle_data(self, data: str) -> None:
        for _, parts in self._captures:
            parts.append(data)


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def extract_recall_urls(payload: bytes | str) -> list[str]:
    """Return canonical FSANZ recall detail URLs from the official sitemap."""
    root = ET.fromstring(payload)
    urls: set[str] = set()
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] != "loc" or not element.text:
            continue
        url = html.unescape(element.text.strip())
        if url.startswith(RECALL_PREFIX):
            urls.add(url)
    return sorted(urls)


def _field_values(blocks: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    current: str | None = None
    for block in blocks:
        normalized = block.rstrip(":").casefold()
        if normalized in FIELD_LABELS:
            current = normalized
            values.setdefault(current, "")
            continue
        inline = re.match(r"^([^:]{2,40}):\s*(.+)$", block)
        if inline and inline.group(1).strip().casefold() in FIELD_LABELS:
            current = inline.group(1).strip().casefold()
            values[current] = _clean_text(inline.group(2))
            continue
        if current:
            values[current] = _clean_text(f"{values[current]} {block}")
    return values


def _normalize_date(values: list[str]) -> str:
    candidates = [value.strip() for value in values if value.strip()]
    patterns = (
        "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ",
        "%d %B %Y", "%d %b %Y", "%d/%m/%Y",
    )
    for value in candidates:
        value = re.sub(r"^(?:date published|published)\s*:?\s*", "", value, flags=re.I)
        for pattern in patterns:
            try:
                return datetime.strptime(value, pattern).date().isoformat()
            except ValueError:
                continue
    raise ValueError("FSANZ recall page does not contain a supported publication date")


def _is_china_origin(value: str) -> bool:
    return bool(re.search(r"\b(?:china|people's republic of china|prc)\b", value, re.I))


def _product_category(value: str) -> str:
    text = value.casefold()
    rules = {
        "seafood": ("fish", "prawn", "shrimp", "scampi", "seafood", "crab"),
        "meat_and_poultry": ("sausage", "chicken", "duck", "beef", "pork", "meat"),
        "pasta_and_noodles": ("noodle", "vermicelli", "pasta"),
        "vegetables": ("mushroom", "vegetable"),
        "fruit": ("fruit", "berry", "berries"),
        "snacks": ("cracker", "biscuit", "snack"),
        "candy": ("candy", "confection", "liquorice", "gummy", "gummies"),
        "prepared_meals_and_sauces": ("dumpling", "spring roll", "sauce", "meal"),
        "spices_and_salt": ("spice", "seasoning", "salt"),
        "coffee_and_tea": ("tea", "coffee"),
    }
    for category, keywords in rules.items():
        if any(keyword in text for keyword in keywords):
            return category
    return "other_food"


def parse_recall_page(
    page: bytes | str,
    source_url: str,
    *,
    retrieved_at: str | None = None,
) -> SafetyRecord | None:
    """Parse one recall and return it only when FSANZ explicitly names China as origin."""
    parsed_url = urlparse(source_url)
    if parsed_url.scheme != "https" or parsed_url.netloc != "www.foodstandards.gov.au":
        raise ValueError("FSANZ source URL must use the official HTTPS host")
    if not source_url.startswith(RECALL_PREFIX):
        raise ValueError("FSANZ source URL is not a recall detail URL")

    text = page.decode("utf-8", errors="replace") if isinstance(page, bytes) else page
    parser = _RecallPageParser()
    parser.feed(text)
    fields = _field_values(parser.blocks)
    if "country of origin" not in fields or not fields["country of origin"]:
        raise ValueError("FSANZ recall page does not contain a country of origin")
    origin = fields["country of origin"]
    if not _is_china_origin(origin):
        return None
    if not parser.title:
        raise ValueError("FSANZ recall page does not contain an H1 title")

    reasons = [
        value for value in (
            fields.get("problem", ""),
            fields.get("food safety hazard", ""),
        ) if value
    ]
    if not reasons:
        raise ValueError("FSANZ recall page does not contain a problem or food safety hazard")
    event_date = _normalize_date(
        [fields.get("date published", ""), *parser.time_values, *parser.blocks]
    )
    source_record_id = unquote(parsed_url.path.rstrip("/").rsplit("/", 1)[-1])
    now = retrieved_at or datetime.now(timezone.utc).isoformat()
    product_text = fields.get("product information", "")

    return SafetyRecord(
        id=stable_id(SOURCE_ID, source_record_id),
        source_id=SOURCE_ID,
        source_record_id=source_record_id,
        authority=AUTHORITY,
        authority_region="AU/NZ",
        action_type="recall",
        event_date=event_date,
        origin_country="CN",
        producer_name="",
        producer_location="",
        product_code="",
        product_category=_product_category(f"{parser.title} {product_text}"),
        product_name=parser.title,
        reasons=reasons,
        hazard_tags=classify_reasons(reasons),
        source_url=source_url,
        retrieved_at=now,
    )
