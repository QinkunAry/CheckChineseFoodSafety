from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from .rasff_probe import (
    COUNTRY_URL,
    PRODUCT_TYPE_URL,
    SEARCH_API_URL,
    SOURCE_ID,
    JsonFetcher,
    build_search_payload,
    fetch_public_json,
    is_china_food_notification,
    parse_country_catalog,
    parse_product_type_catalog,
    parse_search_page,
)


DEFAULT_PAGE_SIZE = 100
FINGERPRINT_FIELDS = (
    "reference",
    "ecValidationDate",
    "subject",
    "notifyingCountry",
    "productCategory",
    "productType",
    "notificationClassification",
    "riskDecision",
    "published",
    "originCountries",
)


def notification_fingerprint(notification: dict[str, Any]) -> str:
    evidence = {field: notification.get(field) for field in FINGERPRINT_FIELDS}
    canonical = json.dumps(
        evidence,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


def state_entry(notification: dict[str, Any]) -> dict[str, Any]:
    return {
        "notification_id": notification["notifId"],
        "reference": str(notification["reference"]).strip(),
        "fingerprint": notification_fingerprint(notification),
    }


def collect_rasff_notifications(
    *,
    fetcher: JsonFetcher = fetch_public_json,
    page_size: int = DEFAULT_PAGE_SIZE,
    max_pages: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not 1 <= page_size <= 100:
        raise ValueError("RASFF inventory page_size must be between 1 and 100")
    if max_pages is not None and max_pages < 1:
        raise ValueError("RASFF inventory max_pages must be at least 1")

    countries = parse_country_catalog(fetcher(COUNTRY_URL, None))
    product_types = parse_product_type_catalog(fetcher(PRODUCT_TYPE_URL, None))
    country_id = countries["CN"]
    food_type_id = product_types["food"]

    def fetch_page(page_number: int) -> tuple[int, int, list[dict[str, Any]]]:
        return parse_search_page(
            fetcher(
                SEARCH_API_URL,
                build_search_payload(
                    origin_country_id=country_id,
                    food_type_id=food_type_id,
                    items_per_page=page_size,
                    page_number=page_number,
                ),
            )
        )

    total, reported_pages, first_records = fetch_page(1)
    expected_pages = math.ceil(total / page_size) if total else 0
    if total < 1 or reported_pages < 1:
        raise ValueError("RASFF inventory returned no China-origin food records")
    if reported_pages != expected_pages:
        raise ValueError(
            "RASFF reported page count does not match total and page size: "
            f"{reported_pages} != {expected_pages}"
        )
    scanned_pages = min(reported_pages, max_pages) if max_pages else reported_pages
    records: list[dict[str, Any]] = []
    page_results: list[dict[str, int]] = []

    for page_number in range(1, scanned_pages + 1):
        if page_number == 1:
            page_total, page_count, page_records = total, reported_pages, first_records
        else:
            page_total, page_count, page_records = fetch_page(page_number)
        if page_total != total or page_count != reported_pages:
            raise ValueError(
                f"RASFF pagination changed during scan on page {page_number}: "
                f"total/pages {page_total}/{page_count}, expected "
                f"{total}/{reported_pages}"
            )
        expected_items = (
            page_size
            if page_number < reported_pages
            else total - page_size * (reported_pages - 1)
        )
        if len(page_records) != expected_items:
            raise ValueError(
                f"RASFF page {page_number} returned {len(page_records)} records; "
                f"expected {expected_items}"
            )
        invalid_scope = sum(
            not is_china_food_notification(record) for record in page_records
        )
        if invalid_scope:
            raise ValueError(
                f"RASFF page {page_number} returned {invalid_scope} "
                "out-of-scope records"
            )
        records.extend(page_records)
        page_results.append(
            {
                "page_number": page_number,
                "record_count": len(page_records),
                "reported_total": page_total,
                "reported_pages": page_count,
            }
        )

    notification_ids = [record["notifId"] for record in records]
    references = [str(record["reference"]).strip() for record in records]
    if len(notification_ids) != len(set(notification_ids)):
        raise ValueError("RASFF inventory contains duplicate notification IDs")
    if len(references) != len(set(references)):
        raise ValueError("RASFF inventory contains duplicate references")

    complete_scan = scanned_pages == reported_pages
    if complete_scan and len(records) != total:
        raise ValueError(
            f"RASFF complete scan count mismatch: {len(records)} != {total}"
        )
    return records, {
        "country_id": country_id,
        "food_type_id": food_type_id,
        "page_size": page_size,
        "reported_total": total,
        "reported_pages": reported_pages,
        "scanned_pages": scanned_pages,
        "scanned_record_count": len(records),
        "complete_scan": complete_scan,
        "page_results": page_results,
    }


def load_inventory_state(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("records"), list):
        raise ValueError(f"invalid RASFF inventory state: {path}")
    result: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(value["records"]):
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("notification_id"), int)
            or not isinstance(entry.get("reference"), str)
            or not entry["reference"]
            or not isinstance(entry.get("fingerprint"), str)
            or len(entry["fingerprint"]) != 64
        ):
            raise ValueError(f"invalid RASFF state entry {index}: {path}")
        if entry["reference"] in result:
            raise ValueError(f"duplicate RASFF state reference: {entry['reference']}")
        result[entry["reference"]] = entry
    declared_count = value.get("record_count")
    if not isinstance(declared_count, int) or declared_count != len(result):
        raise ValueError(f"RASFF state count mismatch: {path}")
    return result


def build_inventory_report(
    *,
    current_entries: list[dict[str, Any]],
    previous_entries: dict[str, dict[str, Any]],
    diagnostics: dict[str, Any],
) -> dict[str, Any]:
    current = {entry["reference"]: entry for entry in current_entries}
    current_refs = set(current)
    previous_refs = set(previous_entries)
    new_refs = sorted(current_refs - previous_refs)
    removed_refs = sorted(previous_refs - current_refs)
    changed_refs = sorted(
        reference
        for reference in current_refs & previous_refs
        if current[reference]["fingerprint"]
        != previous_entries[reference]["fingerprint"]
        or current[reference]["notification_id"]
        != previous_entries[reference]["notification_id"]
    )
    complete_scan = bool(diagnostics["complete_scan"])
    status = (
        "partial"
        if not complete_scan
        else "changed"
        if new_refs or removed_refs or changed_refs
        else "unchanged"
    )
    return {
        "status": status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_id": SOURCE_ID,
        "search_api_url": SEARCH_API_URL,
        "identity_model": "official_reference_plus_selected_field_sha256",
        "country_id": diagnostics["country_id"],
        "food_type_id": diagnostics["food_type_id"],
        "page_size": diagnostics["page_size"],
        "reported_total": diagnostics["reported_total"],
        "reported_pages": diagnostics["reported_pages"],
        "scanned_pages": diagnostics["scanned_pages"],
        "scanned_record_count": diagnostics["scanned_record_count"],
        "complete_scan": complete_scan,
        "baseline_count": len(previous_entries),
        "current_count": len(current),
        "new_record_count": len(new_refs),
        "new_reference_samples": new_refs[:50],
        "removed_record_count": len(removed_refs) if complete_scan else None,
        "removed_reference_samples": removed_refs[:50] if complete_scan else [],
        "changed_record_count": len(changed_refs),
        "changed_reference_samples": changed_refs[:50],
        "page_results": diagnostics["page_results"],
        "warnings": [
            "A changed fingerprint means selected public search fields changed; "
            "it does not by itself identify the legal correction semantics."
        ],
    }


def inventory_rasff(
    *,
    state_path: Path,
    fetcher: JsonFetcher = fetch_public_json,
    page_size: int = DEFAULT_PAGE_SIZE,
    max_pages: int | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    generated_at = datetime.now(timezone.utc).isoformat()
    try:
        notifications, diagnostics = collect_rasff_notifications(
            fetcher=fetcher,
            page_size=page_size,
            max_pages=max_pages,
        )
        entries = sorted(
            (state_entry(notification) for notification in notifications),
            key=lambda entry: entry["reference"],
        )
        report = build_inventory_report(
            current_entries=entries,
            previous_entries=load_inventory_state(state_path),
            diagnostics=diagnostics,
        )
        return report, entries
    except Exception as error:
        return (
            {
                "status": "failed",
                "generated_at": generated_at,
                "source_id": SOURCE_ID,
                "search_api_url": SEARCH_API_URL,
                "complete_scan": False,
                "blocking_errors": [
                    f"RASFF inventory failed: {type(error).__name__}: {error}"
                ],
            },
            [],
        )


def write_inventory_state(
    entries: list[dict[str, Any]],
    path: Path,
    *,
    created_at: str | None = None,
) -> None:
    unique = {entry["reference"]: entry for entry in entries}
    if len(unique) != len(entries):
        raise ValueError("cannot write RASFF state with duplicate references")
    value = {
        "source_id": SOURCE_ID,
        "search_api_url": SEARCH_API_URL,
        "created_at": created_at or datetime.now(timezone.utc).isoformat(),
        "scope": {
            "origin_country": "CN",
            "product_type": "food",
        },
        "identity_model": "official_reference_plus_selected_field_sha256",
        "fingerprint_fields": list(FINGERPRINT_FIELDS),
        "record_count": len(entries),
        "records": sorted(entries, key=lambda entry: entry["reference"]),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
