from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .fsanz import (
    SITEMAP_URL,
    SOURCE_ID,
    diagnostic_text_nodes,
    extract_recall_urls,
    inspect_recall_page,
    parse_recall_page,
)
from .fsanz_inventory import load_url_state
from .fsanz_smoke import fetch_official
from .quality import build_quality_report


Fetcher = Callable[[str], bytes]


def new_recall_urls(sitemap_payload: bytes | str, previous_urls: list[str]) -> list[str]:
    current = set(extract_recall_urls(sitemap_payload))
    previous = set(previous_urls)
    return sorted(current - previous)


def build_candidate_report(
    *,
    urls: list[str],
    schema: dict[str, Any],
    fetcher: Fetcher = fetch_official,
    retrieved_at: str | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    generated_at = retrieved_at or datetime.now(timezone.utc).isoformat()
    page_results: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    blocking_errors: list[str] = []

    for url in urls:
        result: dict[str, Any] = {"url": url}
        payload: bytes | None = None
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
        except Exception as error:  # preserve diagnostics for human review
            result["status"] = "error"
            result["error"] = f"{type(error).__name__}: {error}"
            if payload is not None:
                result["text_diagnostics"] = diagnostic_text_nodes(payload)
            blocking_errors.append(f"page parse failed: {url}: {result['error']}")
        page_results.append(result)

    quality = build_quality_report(
        records,
        schema,
        source_id=SOURCE_ID,
        min_records=0,
    )
    blocking_errors.extend(str(error) for error in quality["blocking_errors"])

    return (
        {
            "status": "failed" if blocking_errors else "passed",
            "generated_at": generated_at,
            "source_id": SOURCE_ID,
            "sitemap_url": SITEMAP_URL,
            "candidate_url_count": len(urls),
            "tested_page_count": len(page_results),
            "china_record_count": len(records),
            "page_results": page_results,
            "schema_error_count": quality["schema_error_count"],
            "schema_error_samples": quality["schema_error_samples"],
            "blocking_errors": blocking_errors,
        },
        records,
    )


def candidate_fsanz(
    *,
    state_path: Path,
    schema: dict[str, Any],
    sitemap_path: Path | None = None,
    fetcher: Fetcher = fetch_official,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    sitemap_payload = sitemap_path.read_bytes() if sitemap_path else fetcher(SITEMAP_URL)
    urls = new_recall_urls(sitemap_payload, load_url_state(state_path))
    return build_candidate_report(urls=urls, schema=schema, fetcher=fetcher)
