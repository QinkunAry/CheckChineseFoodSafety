from __future__ import annotations

import json
import math
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .japan_probe import (
    CAA_FOOD_URL,
    CAA_HOST,
    CaaListItem,
    SOURCE_ID,
    USER_AGENT,
    parse_caa_food_list,
)


CAA_INDEX_URL = "https://www.recall.caa.go.jp/result/index.php"
DEFAULT_PAGE_SIZE = 15

PageFetcher = Callable[[int], bytes]


def fetch_caa_food_page(page_index: int, *, timeout: float = 45) -> bytes:
    if page_index < 0:
        raise ValueError("page_index must not be negative")
    if page_index == 0:
        request = urllib.request.Request(
            CAA_FOOD_URL,
            headers={
                "Accept": "text/html,*/*;q=0.8",
                "User-Agent": USER_AGENT,
            },
        )
    else:
        form = urllib.parse.urlencode(
            {
                "screenkbn": "01",
                "category": "1",
                "viewCountdden": str(DEFAULT_PAGE_SIZE),
                "portarorder": "2",
                "actionorder": "0",
                "pagingHidden": str(page_index),
            }
        ).encode("ascii")
        request = urllib.request.Request(
            CAA_INDEX_URL,
            data=form,
            headers={
                "Accept": "text/html,*/*;q=0.8",
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": f"https://{CAA_HOST}",
                "Referer": CAA_FOOD_URL,
                "User-Agent": USER_AGENT,
            },
            method="POST",
        )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def load_url_state(path: Path) -> list[str]:
    if not path.exists():
        return []
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("recall_urls"), list):
        raise ValueError(f"invalid Japan CAA URL state: {path}")
    urls = value["recall_urls"]
    if not all(isinstance(url, str) for url in urls):
        raise ValueError(f"Japan CAA URL state contains a non-string URL: {path}")
    return sorted(set(urls))


def merge_seen_urls(previous_urls: list[str], current_urls: list[str]) -> list[str]:
    return sorted(set(previous_urls) | set(current_urls))


def collect_caa_food_items(
    *,
    page_fetcher: PageFetcher = fetch_caa_food_page,
    max_pages: int | None = None,
) -> tuple[list[CaaListItem], dict[str, Any]]:
    if max_pages is not None and max_pages < 1:
        raise ValueError("max_pages must be at least 1")

    first_total, first_items = parse_caa_food_list(page_fetcher(0), base_url=CAA_FOOD_URL)
    if first_total is None:
        raise ValueError("CAA food list did not expose a total recall count")
    if not first_items:
        raise ValueError("CAA food list parsed zero recall URLs on the first page")

    first_page_size = len(first_items)
    expected_page_count = math.ceil(first_total / first_page_size)
    page_count = min(expected_page_count, max_pages) if max_pages else expected_page_count
    items_by_url: dict[str, CaaListItem] = {item.url: item for item in first_items}
    page_results: list[dict[str, Any]] = [
        {
            "page_index": 0,
            "total_count": first_total,
            "item_count": len(first_items),
            "first_rcl": first_items[0].rcl,
            "last_rcl": first_items[-1].rcl,
        }
    ]
    warnings: list[str] = []

    for page_index in range(1, page_count):
        total_count, items = parse_caa_food_list(page_fetcher(page_index), base_url=CAA_FOOD_URL)
        items_by_url.update((item.url, item) for item in items)
        page_results.append(
            {
                "page_index": page_index,
                "total_count": total_count,
                "item_count": len(items),
                "first_rcl": items[0].rcl if items else None,
                "last_rcl": items[-1].rcl if items else None,
            }
        )
        if total_count is not None and total_count != first_total:
            warnings.append(
                f"page {page_index} total count changed during scan: {total_count} != {first_total}"
            )
        if not items:
            warnings.append(f"page {page_index} parsed zero recall URLs")

    diagnostics = {
        "list_url": CAA_FOOD_URL,
        "reported_total_count": first_total,
        "first_page_size": first_page_size,
        "expected_page_count": expected_page_count,
        "scanned_page_count": page_count,
        "page_results": page_results,
        "warnings": warnings,
    }
    return sorted(items_by_url.values(), key=lambda item: item.url), diagnostics


def collect_caa_food_urls(
    *,
    page_fetcher: PageFetcher = fetch_caa_food_page,
    max_pages: int | None = None,
) -> tuple[list[str], dict[str, Any]]:
    items, diagnostics = collect_caa_food_items(
        page_fetcher=page_fetcher,
        max_pages=max_pages,
    )
    return [item.url for item in items], diagnostics


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
        "list_url": CAA_FOOD_URL,
        "reported_total_count": diagnostics["reported_total_count"],
        "expected_page_count": diagnostics["expected_page_count"],
        "scanned_page_count": diagnostics["scanned_page_count"],
        "baseline_count": len(previous),
        "current_count": len(current),
        "new_url_count": len(new_urls),
        "new_urls": new_urls,
        "removed_url_count": len(removed_urls),
        "removed_urls": removed_urls,
        "removed_url_semantics": "previously_seen_but_not_currently_listed",
        "warnings": diagnostics.get("warnings", []),
    }


def inventory_japan_caa(
    *,
    state_path: Path,
    page_fetcher: PageFetcher = fetch_caa_food_page,
    max_pages: int | None = None,
) -> tuple[dict[str, Any], list[str]]:
    current_urls, diagnostics = collect_caa_food_urls(
        page_fetcher=page_fetcher,
        max_pages=max_pages,
    )
    report = build_inventory_report(
        current_urls=current_urls,
        previous_urls=load_url_state(state_path),
        diagnostics=diagnostics,
    )
    return report, current_urls


def write_url_state(urls: list[str], path: Path) -> None:
    value = {
        "source_id": SOURCE_ID,
        "list_url": CAA_FOOD_URL,
        "recall_urls": sorted(set(urls)),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
