from __future__ import annotations

import urllib.request
from datetime import datetime, timezone
from typing import Callable
from urllib.parse import urlparse

from .fsanz import (
    SITEMAP_URL,
    SOURCE_ID,
    extract_recall_urls,
    inspect_recall_page,
    parse_recall_page,
)
from .quality import build_quality_report


USER_AGENT = (
    "FoodSafetyWatch/0.1 "
    "(+https://github.com/QinkunAry/CheckChineseFoodSafety)"
)
Fetcher = Callable[[str], bytes]


def fetch_official(url: str, *, timeout: float = 45) -> bytes:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "www.foodstandards.gov.au":
        raise ValueError("FSANZ smoke requests are restricted to the official HTTPS host")
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "text/html,application/xml;q=0.9,*/*;q=0.8",
            "User-Agent": USER_AGENT,
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def build_smoke_report(
    *,
    urls: list[str],
    schema: dict[str, object],
    fetcher: Fetcher = fetch_official,
    min_sitemap_recalls: int = 100,
    min_china_records: int = 0,
) -> dict[str, object]:
    if min_china_records < 0:
        raise ValueError("min_china_records must not be negative")
    generated_at = datetime.now(timezone.utc).isoformat()
    page_results: list[dict[str, object]] = []
    blocking_errors: list[str] = []
    records: list[dict[str, object]] = []

    try:
        sitemap_payload = fetcher(SITEMAP_URL)
        discovered = set(extract_recall_urls(sitemap_payload))
    except Exception as error:  # report network/parser diagnostics before failing CI
        return {
            "status": "failed",
            "generated_at": generated_at,
            "source_id": SOURCE_ID,
            "sitemap_url": SITEMAP_URL,
            "sitemap_recall_count": 0,
            "china_record_count": 0,
            "page_results": [],
            "blocking_errors": [f"sitemap request failed: {type(error).__name__}: {error}"],
        }

    if len(discovered) < min_sitemap_recalls:
        blocking_errors.append(
            f"sitemap recall count {len(discovered)} is below minimum {min_sitemap_recalls}"
        )

    for url in urls:
        result: dict[str, object] = {"url": url}
        if url not in discovered:
            result["status"] = "not_in_sitemap"
            result["error"] = "candidate URL is absent from the official sitemap"
            blocking_errors.append(f"candidate is absent from sitemap: {url}")
            page_results.append(result)
            continue
        try:
            payload = fetcher(url)
            detail = inspect_recall_page(payload, url)
            result["origin_country_text"] = detail.origin_country_text
            result["event_date"] = detail.event_date
            result["product_name"] = detail.title
            record = parse_recall_page(payload, url, retrieved_at=generated_at)
            if record is None:
                result["status"] = "parsed_non_china"
            else:
                normalized = record.to_dict()
                records.append(normalized)
                result.update({
                    "status": "parsed_china",
                    "record_id": normalized["id"],
                })
        except Exception as error:  # keep testing the remaining diagnostic pages
            result["status"] = "error"
            result["error"] = f"{type(error).__name__}: {error}"
            blocking_errors.append(f"page parse failed: {url}: {result['error']}")
        page_results.append(result)

    quality = build_quality_report(
        records,
        schema,
        source_id=SOURCE_ID,
        min_records=min_china_records,
    )
    blocking_errors.extend(str(error) for error in quality["blocking_errors"])
    return {
        "status": "failed" if blocking_errors else "passed",
        "generated_at": generated_at,
        "source_id": SOURCE_ID,
        "sitemap_url": SITEMAP_URL,
        "sitemap_recall_count": len(discovered),
        "tested_page_count": len(page_results),
        "china_record_count": len(records),
        "minimum_china_records": min_china_records,
        "page_results": page_results,
        "schema_error_count": quality["schema_error_count"],
        "schema_error_samples": quality["schema_error_samples"],
        "blocking_errors": blocking_errors,
    }
