from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, urlparse

from .japan_probe import (
    CAA_FOOD_URL,
    CAA_HOST,
    Fetcher,
    SOURCE_ID,
    fetch_official,
    inspect_caa_detail,
    inspect_mhlw_detail,
    parse_caa_food_list,
)


MHLW_DETAIL_URL_TEMPLATE = "https://i2fas.mhlw.go.jp/faspub/_link.do?i=IO_S020502&p={rcl}"


def caa_rcl_from_detail_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != CAA_HOST:
        raise ValueError("Japan smoke URLs must use the official CAA HTTPS host")
    if parsed.path != "/result/detail.php":
        raise ValueError("Japan smoke URLs must be CAA recall detail pages")

    query = parse_qs(parsed.query)
    rcl_values = query.get("rcl") or []
    screen_values = query.get("screenkbn") or []
    if len(rcl_values) != 1 or not re.fullmatch(r"\d+", rcl_values[0]):
        raise ValueError("CAA detail URL must contain exactly one numeric rcl parameter")
    if screen_values and screen_values != ["01"]:
        raise ValueError("CAA detail URL screenkbn must be 01 for the food recall view")
    return rcl_values[0]


def mhlw_detail_url(rcl_id: str) -> str:
    if not re.fullmatch(r"RCL\d+", rcl_id):
        raise ValueError("MHLW recall ID must look like RCL followed by digits")
    return MHLW_DETAIL_URL_TEMPLATE.format(rcl=rcl_id)


def build_japan_smoke_report(
    *,
    urls: list[str],
    min_list_total: int = 100,
    min_china_records: int = 1,
    min_mhlw_references: int = 1,
    fetcher: Fetcher = fetch_official,
    list_payload: bytes | None = None,
) -> dict[str, Any]:
    if not urls:
        raise ValueError("at least one CAA detail URL is required")
    if min_list_total < 0:
        raise ValueError("min_list_total must not be negative")
    if min_china_records < 0:
        raise ValueError("min_china_records must not be negative")
    if min_mhlw_references < 0:
        raise ValueError("min_mhlw_references must not be negative")

    generated_at = datetime.now(timezone.utc).isoformat()
    blocking_errors: list[str] = []
    page_results: list[dict[str, Any]] = []
    total_count: int | None = None
    list_item_count = 0

    try:
        payload = list_payload if list_payload is not None else fetcher(CAA_FOOD_URL)
        total_count, list_items = parse_caa_food_list(payload)
        list_item_count = len(list_items)
        if total_count is None:
            blocking_errors.append("CAA food list did not expose a total recall count")
        elif total_count < min_list_total:
            blocking_errors.append(
                f"CAA food list count {total_count} is below minimum {min_list_total}"
            )
        if list_item_count == 0:
            blocking_errors.append("CAA food list parsed zero visible recall entries")
    except Exception as error:
        blocking_errors.append(
            f"CAA food list fetch/parse failed: {type(error).__name__}: {error}"
        )

    for url in urls:
        result: dict[str, Any] = {"url": url}
        try:
            caa_rcl = caa_rcl_from_detail_url(url)
            detail = inspect_caa_detail(fetcher(url))
            result.update(
                {
                    "status": "parsed",
                    "caa_rcl": caa_rcl,
                    "title": detail.get("title"),
                    "product": detail.get("product"),
                    "reason_type": detail.get("reason_type"),
                    "caa_china_origin_evidence": detail.get("china_origin_evidence"),
                    "mhlw_reference_id": detail.get("mhlw_reference_id"),
                }
            )

            if not detail.get("title") and not detail.get("product"):
                blocking_errors.append(f"CAA detail has neither title nor product: {url}")

            mhlw_reference_id = detail.get("mhlw_reference_id")
            if mhlw_reference_id:
                result["mhlw_url"] = mhlw_detail_url(mhlw_reference_id)
                try:
                    mhlw_detail = inspect_mhlw_detail(fetcher(result["mhlw_url"]))
                    result["mhlw_detail"] = {
                        "rcl_no": mhlw_detail.get("rcl_no"),
                        "product": mhlw_detail.get("product"),
                        "reason_type": mhlw_detail.get("reason_type"),
                        "china_origin_evidence": mhlw_detail.get("china_origin_evidence"),
                    }
                    if mhlw_detail.get("rcl_no") and mhlw_detail["rcl_no"] != mhlw_reference_id:
                        blocking_errors.append(
                            f"MHLW recall ID mismatch for {url}: "
                            f"{mhlw_detail['rcl_no']} != {mhlw_reference_id}"
                        )
                except Exception as error:
                    result["mhlw_error"] = f"{type(error).__name__}: {error}"
                    blocking_errors.append(
                        f"MHLW detail fetch/parse failed for {mhlw_reference_id}: "
                        f"{result['mhlw_error']}"
                    )

            result["china_origin_evidence"] = bool(
                result.get("caa_china_origin_evidence")
                or result.get("mhlw_detail", {}).get("china_origin_evidence")
            )
        except Exception as error:
            result["status"] = "error"
            result["error"] = f"{type(error).__name__}: {error}"
            result["china_origin_evidence"] = False
            blocking_errors.append(f"CAA detail fetch/parse failed: {url}: {result['error']}")
        page_results.append(result)

    china_origin_pages = sum(1 for result in page_results if result.get("china_origin_evidence"))
    mhlw_reference_count = sum(1 for result in page_results if result.get("mhlw_reference_id"))
    if china_origin_pages < min_china_records:
        blocking_errors.append(
            f"China-origin evidence pages {china_origin_pages} below minimum {min_china_records}"
        )
    if mhlw_reference_count < min_mhlw_references:
        blocking_errors.append(
            f"MHLW reference count {mhlw_reference_count} below minimum {min_mhlw_references}"
        )

    return {
        "status": "failed" if blocking_errors else "passed",
        "generated_at": generated_at,
        "source_id": SOURCE_ID,
        "list_url": CAA_FOOD_URL,
        "list_total_count": total_count,
        "minimum_list_total": min_list_total,
        "list_item_count": list_item_count,
        "tested_page_count": len(page_results),
        "china_origin_evidence_page_count": china_origin_pages,
        "minimum_china_records": min_china_records,
        "mhlw_reference_count": mhlw_reference_count,
        "minimum_mhlw_references": min_mhlw_references,
        "page_results": page_results,
        "blocking_errors": blocking_errors,
    }
