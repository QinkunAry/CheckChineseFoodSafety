from __future__ import annotations

import urllib.request
from datetime import datetime, timezone
from typing import Callable
from urllib.parse import urlparse

from .cfs import (
    ALERT_INDEX_URL,
    SOURCE_ID,
    extract_alert_urls,
    inspect_alert_page,
    parse_alert_page,
)
from .quality import build_quality_report


USER_AGENT = (
    "FoodSafetyWatch/0.1 "
    "(+https://github.com/QinkunAry/CheckChineseFoodSafety)"
)
Fetcher = Callable[[str], bytes]


def fetch_official(url: str, *, timeout: float = 45) -> bytes:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "www.cfs.gov.hk":
        raise ValueError("CFS smoke requests are restricted to the official HTTPS host")
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "text/html,*/*;q=0.8",
            "User-Agent": USER_AGENT,
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def build_smoke_report(
    *,
    urls: list[str],
    schema: dict[str, object],
    index_urls: list[str] | None = None,
    fetcher: Fetcher = fetch_official,
    min_index_alerts: int = 1,
    min_china_records: int = 1,
) -> dict[str, object]:
    if min_china_records < 0:
        raise ValueError("min_china_records must not be negative")
    generated_at = datetime.now(timezone.utc).isoformat()
    blocking_errors: list[str] = []
    page_results: list[dict[str, object]] = []
    records: list[dict[str, object]] = []
    indexes = index_urls or [ALERT_INDEX_URL]
    discovered: set[str] = set()

    for index_url in indexes:
        try:
            payload = fetcher(index_url)
            discovered.update(extract_alert_urls(payload, index_url))
        except Exception as error:
            blocking_errors.append(
                f"index request failed: {index_url}: {type(error).__name__}: {error}"
            )

    if len(discovered) < min_index_alerts:
        blocking_errors.append(
            f"index alert count {len(discovered)} is below minimum {min_index_alerts}"
        )

    for url in urls:
        result: dict[str, object] = {"url": url}
        if url not in discovered:
            result["status"] = "not_in_index"
            result["error"] = "candidate URL is absent from the configured official index pages"
            blocking_errors.append(f"candidate is absent from configured CFS index pages: {url}")
            page_results.append(result)
            continue
        try:
            payload = fetcher(url)
            detail = inspect_alert_page(payload, url)
            result["origin_country_text"] = detail.origin_text
            result["event_date"] = detail.event_date
            record = parse_alert_page(payload, url, retrieved_at=generated_at)
            if record is None:
                result["status"] = "parsed_non_china"
            else:
                normalized = record.to_dict()
                records.append(normalized)
                result.update({
                    "status": "parsed_china",
                    "record_id": normalized["id"],
                })
        except Exception as error:
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
        "index_urls": indexes,
        "index_alert_count": len(discovered),
        "tested_page_count": len(page_results),
        "china_record_count": len(records),
        "minimum_china_records": min_china_records,
        "page_results": page_results,
        "schema_error_count": quality["schema_error_count"],
        "schema_error_samples": quality["schema_error_samples"],
        "blocking_errors": blocking_errors,
    }
