from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode

from .china_samr_probe import (
    LIST_ENDPOINT,
    LIST_PAGE_URL,
    LIST_QUERY,
    SOURCE_ID,
    SamrNotice,
    fetch_official,
    parse_listing_response,
)


DEFAULT_PAGE_SIZE = 99
PageFetcher = Callable[[int], bytes]


def listing_page_url(page_number: int, *, page_size: int = DEFAULT_PAGE_SIZE) -> str:
    if page_number < 1 or page_size < 1:
        raise ValueError("page_number and page_size must be at least 1")
    parameters = {
        **LIST_QUERY,
        "paramJson": json.dumps(
            {"pageNo": page_number, "pageSize": page_size},
            separators=(",", ":"),
        ),
    }
    return f"{LIST_ENDPOINT}?{urlencode(parameters)}"


def fetch_listing_page(page_number: int) -> bytes:
    return fetch_official(listing_page_url(page_number))


def _listing_item_count(payload: bytes | str) -> int:
    text = payload.decode("utf-8-sig") if isinstance(payload, bytes) else payload
    value = json.loads(text)
    listing_html = ((value.get("data") or {}).get("html")) if isinstance(value, dict) else None
    if not isinstance(listing_html, str):
        raise ValueError("SAMR listing response does not contain HTML")
    return len(re.findall(r"<li\b", listing_html, flags=re.IGNORECASE))


def collect_samr_notices(
    *,
    page_fetcher: PageFetcher = fetch_listing_page,
    max_pages: int | None = None,
) -> tuple[list[SamrNotice], dict[str, Any]]:
    if max_pages is not None and max_pages < 1:
        raise ValueError("max_pages must be at least 1")

    first_payload = page_fetcher(1)
    reported_total, first_notices = parse_listing_response(first_payload)
    first_page_size = _listing_item_count(first_payload)
    if reported_total < 1 or first_page_size < 1:
        raise ValueError("SAMR listing returned no indexed items")

    expected_page_count = math.ceil(reported_total / first_page_size)
    scanned_page_count = (
        min(expected_page_count, max_pages) if max_pages else expected_page_count
    )
    notices_by_url = {notice.url: notice for notice in first_notices}
    page_results: list[dict[str, Any]] = [
        {
            "page_number": 1,
            "reported_total_count": reported_total,
            "listing_item_count": first_page_size,
            "notice_count": len(first_notices),
        }
    ]
    scanned_listing_item_count = first_page_size

    for page_number in range(2, scanned_page_count + 1):
        payload = page_fetcher(page_number)
        page_total, notices = parse_listing_response(payload)
        item_count = _listing_item_count(payload)
        if page_total != reported_total:
            raise ValueError(
                f"SAMR listing total changed during scan: page {page_number} "
                f"reported {page_total}, expected {reported_total}"
            )
        if item_count < 1:
            raise ValueError(f"SAMR listing page {page_number} contained no items")
        notices_by_url.update((notice.url, notice) for notice in notices)
        scanned_listing_item_count += item_count
        page_results.append(
            {
                "page_number": page_number,
                "reported_total_count": page_total,
                "listing_item_count": item_count,
                "notice_count": len(notices),
            }
        )

    complete_scan = scanned_page_count == expected_page_count
    if complete_scan and scanned_listing_item_count != reported_total:
        raise ValueError(
            "SAMR full listing scan item count mismatch: "
            f"{scanned_listing_item_count} != {reported_total}"
        )

    diagnostics = {
        "list_page_url": LIST_PAGE_URL,
        "list_endpoint": LIST_ENDPOINT,
        "reported_total_count": reported_total,
        "first_page_size": first_page_size,
        "expected_page_count": expected_page_count,
        "scanned_page_count": scanned_page_count,
        "scanned_listing_item_count": scanned_listing_item_count,
        "complete_scan": complete_scan,
        "page_results": page_results,
    }
    notices = sorted(
        notices_by_url.values(),
        key=lambda notice: ((notice.published_date or ""), notice.url),
        reverse=True,
    )
    return notices, diagnostics


def load_url_state(path: Path) -> list[str]:
    if not path.exists():
        return []
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("notice_urls"), list):
        raise ValueError(f"invalid China SAMR URL state: {path}")
    urls = value["notice_urls"]
    if not all(isinstance(url, str) for url in urls):
        raise ValueError(f"China SAMR URL state contains a non-string URL: {path}")
    return sorted(set(urls))


def build_inventory_report(
    *,
    current_urls: list[str],
    previous_urls: list[str],
    diagnostics: dict[str, Any],
) -> dict[str, Any]:
    current = set(current_urls)
    previous = set(previous_urls)
    new_urls = sorted(current - previous)
    removed_urls = sorted(previous - current)
    return {
        "status": "changed" if new_urls or removed_urls else "unchanged",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_id": SOURCE_ID,
        "list_page_url": LIST_PAGE_URL,
        "reported_listing_count": diagnostics["reported_total_count"],
        "expected_page_count": diagnostics["expected_page_count"],
        "scanned_page_count": diagnostics["scanned_page_count"],
        "scanned_listing_item_count": diagnostics["scanned_listing_item_count"],
        "complete_scan": diagnostics["complete_scan"],
        "baseline_count": len(previous),
        "current_count": len(current),
        "new_url_count": len(new_urls),
        "new_urls": new_urls,
        "removed_url_count": len(removed_urls),
        "removed_urls": removed_urls,
    }


def inventory_china_samr(
    *,
    state_path: Path,
    page_fetcher: PageFetcher = fetch_listing_page,
    max_pages: int | None = None,
) -> tuple[dict[str, Any], list[SamrNotice]]:
    notices, diagnostics = collect_samr_notices(
        page_fetcher=page_fetcher,
        max_pages=max_pages,
    )
    current_urls = [notice.url for notice in notices]
    report = build_inventory_report(
        current_urls=current_urls,
        previous_urls=load_url_state(state_path),
        diagnostics=diagnostics,
    )
    return report, notices


def write_url_state(notices: list[SamrNotice], path: Path) -> None:
    unique = {notice.url: notice for notice in notices}
    value = {
        "source_id": SOURCE_ID,
        "list_page_url": LIST_PAGE_URL,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "notice_count": len(unique),
        "notice_urls": sorted(unique),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
