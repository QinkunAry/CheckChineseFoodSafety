from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class RecallPage:
    title: str
    event_date: str
    origin_country_text: str
    product_information: str
    reasons: list[str]


class _RecallPageParser(HTMLParser):
    _text_tags = {"h1", "h2", "h3", "h4", "h5", "h6", "li", "p", "time"}
    _ignored_tags = {"script", "style", "noscript", "svg"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[str] = []
        self.text_nodes: list[str] = []
        self.title = ""
        self.time_values: list[str] = []
        self._captures: list[tuple[str, list[str]]] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._ignored_tags:
            self._ignored_depth += 1
            return
        if self._ignored_depth:
            return
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
            if value:
                self.blocks.append(value)
                if tag == "h1" and not self.title:
                    self.title = value
            break

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        value = _clean_text(data)
        if value:
            self.text_nodes.append(value)
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
        prefixed_label = next(
            (
                label for label in FIELD_LABELS
                if normalized.startswith(f"{label} ")
            ),
            None,
        )
        if prefixed_label:
            current = prefixed_label
            values[current] = _clean_text(block[len(prefixed_label):])
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


def inspect_recall_page(page: bytes | str, source_url: str) -> RecallPage:
    """Extract and validate evidence fields from one official FSANZ recall page."""
    parsed_url = urlparse(source_url)
    if parsed_url.scheme != "https" or parsed_url.netloc != "www.foodstandards.gov.au":
        raise ValueError("FSANZ source URL must use the official HTTPS host")
    if not source_url.startswith(RECALL_PREFIX):
        raise ValueError("FSANZ source URL is not a recall detail URL")

    text = page.decode("utf-8", errors="replace") if isinstance(page, bytes) else page
    parser = _RecallPageParser()
    parser.feed(text)
    fields = _field_values(parser.text_nodes)
    if "country of origin" not in fields or not fields["country of origin"]:
        raise ValueError("FSANZ recall page does not contain a country of origin")
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
    return RecallPage(
        title=parser.title,
        event_date=event_date,
        origin_country_text=fields["country of origin"],
        product_information=fields.get("product information", ""),
        reasons=reasons,
    )


def parse_recall_page(
    page: bytes | str,
    source_url: str,
    *,
    retrieved_at: str | None = None,
) -> SafetyRecord | None:
    """Parse one recall and return it only when FSANZ explicitly names China as origin."""
    detail = inspect_recall_page(page, source_url)
    if not _is_china_origin(detail.origin_country_text):
        return None
    parsed_url = urlparse(source_url)
    source_record_id = unquote(parsed_url.path.rstrip("/").rsplit("/", 1)[-1])
    now = retrieved_at or datetime.now(timezone.utc).isoformat()

    return SafetyRecord(
        id=stable_id(SOURCE_ID, source_record_id),
        source_id=SOURCE_ID,
        source_record_id=source_record_id,
        authority=AUTHORITY,
        authority_region="AU/NZ",
        action_type="recall",
        event_date=detail.event_date,
        origin_country="CN",
        producer_name="",
        producer_location="",
        product_code="",
        product_category=_product_category(
            f"{detail.title} {detail.product_information}"
        ),
        product_name=detail.title,
        reasons=detail.reasons,
        hazard_tags=classify_reasons(detail.reasons),
        source_url=source_url,
        retrieved_at=now,
    )


def diagnostic_text_nodes(page: bytes | str, *, limit: int = 30) -> list[str]:
    """Return a small visible-text sample for diagnosing official page drift."""
    text = page.decode("utf-8", errors="replace") if isinstance(page, bytes) else page
    parser = _RecallPageParser()
    parser.feed(text)
    keywords = ("country", "origin", "problem", "hazard", "product information")
    relevant = [
        node for node in parser.text_nodes
        if any(keyword in node.casefold() for keyword in keywords)
    ]
    if relevant:
        return relevant[:limit]
    return parser.text_nodes[:limit]
