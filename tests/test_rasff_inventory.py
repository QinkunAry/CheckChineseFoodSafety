from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from food_safety_watch.rasff_inventory import (
    build_inventory_report,
    collect_rasff_notifications,
    inventory_rasff,
    load_inventory_state,
    notification_fingerprint,
    state_entry,
    write_inventory_state,
)
from food_safety_watch.rasff_probe import (
    COUNTRY_URL,
    PRODUCT_TYPE_URL,
    SEARCH_API_URL,
)


def country_payload() -> bytes:
    return json.dumps(
        {
            "countries": [
                {"id": 5075, "englishShortName": "China", "alpha2Code": "CN"},
                {"id": 5118, "englishShortName": "India", "alpha2Code": "IN"},
            ]
        }
    ).encode()


def product_type_payload() -> bytes:
    return json.dumps(
        {"notificationTypes": [{"id": 283, "description": "food"}]}
    ).encode()


def notification(index: int, *, origin: str = "CN") -> dict[str, object]:
    return {
        "notifId": 800000 + index,
        "ecValidationDate": "24-06-2026 12:36:41",
        "reference": f"2026.{index:04d}",
        "notifyingCountry": {
            "organizationName": "Netherlands",
            "isoCode": "NL",
        },
        "subject": f"pesticide in tea sample {index}",
        "productCategory": {"id": 18435, "description": "tea"},
        "productType": {"id": 283, "description": "food"},
        "notificationClassification": {
            "id": 305,
            "description": "border rejection notification",
        },
        "riskDecision": {"id": 18761, "description": "serious"},
        "published": False,
        "originCountries": [
            {
                "organizationName": "China" if origin == "CN" else "India",
                "isoCode": origin,
            }
        ],
    }


def search_page(
    records: list[dict[str, object]], *, total: int, pages: int
) -> bytes:
    return json.dumps(
        {"notifications": records, "totalElements": total, "totalPages": pages}
    ).encode()


def paged_fetcher(
    pages: dict[int, bytes],
):
    def fetch(url: str, payload: dict[str, object] | None) -> bytes:
        if url == COUNTRY_URL:
            return country_payload()
        if url == PRODUCT_TYPE_URL:
            return product_type_payload()
        if url == SEARCH_API_URL and payload:
            page_number = payload["parameters"]["pageNumber"]
            return pages[page_number]
        raise AssertionError((url, payload))

    return fetch


class RasffInventoryTests(unittest.TestCase):
    def test_collects_complete_consistent_pagination(self) -> None:
        records = [notification(index) for index in range(1, 6)]
        fetch = paged_fetcher(
            {
                1: search_page(records[:2], total=5, pages=3),
                2: search_page(records[2:4], total=5, pages=3),
                3: search_page(records[4:], total=5, pages=3),
            }
        )
        current, diagnostics = collect_rasff_notifications(
            fetcher=fetch, page_size=2
        )
        self.assertEqual(len(current), 5)
        self.assertTrue(diagnostics["complete_scan"])
        self.assertEqual(diagnostics["scanned_pages"], 3)

    def test_total_change_during_scan_fails_closed(self) -> None:
        records = [notification(index) for index in range(1, 5)]
        fetch = paged_fetcher(
            {
                1: search_page(records[:2], total=4, pages=2),
                2: search_page(records[2:], total=5, pages=2),
            }
        )
        with self.assertRaisesRegex(ValueError, "pagination changed"):
            collect_rasff_notifications(fetcher=fetch, page_size=2)

    def test_duplicate_reference_across_pages_fails_closed(self) -> None:
        first = [notification(1), notification(2)]
        second = [notification(2), notification(4)]
        second[0]["notifId"] = 900002
        fetch = paged_fetcher(
            {
                1: search_page(first, total=4, pages=2),
                2: search_page(second, total=4, pages=2),
            }
        )
        with self.assertRaisesRegex(ValueError, "duplicate references"):
            collect_rasff_notifications(fetcher=fetch, page_size=2)

    def test_out_of_scope_page_fails_closed(self) -> None:
        records = [notification(1), notification(2, origin="IN")]
        fetch = paged_fetcher({1: search_page(records, total=2, pages=1)})
        with self.assertRaisesRegex(ValueError, "out-of-scope"):
            collect_rasff_notifications(fetcher=fetch, page_size=2)

    def test_report_detects_new_removed_and_changed_references(self) -> None:
        kept = state_entry(notification(1))
        changed_notification = notification(2)
        old_changed = state_entry(changed_notification)
        changed_notification["subject"] = "corrected subject"
        changed = state_entry(changed_notification)
        added = state_entry(notification(3))
        removed = state_entry(notification(4))
        diagnostics = {
            "country_id": 5075,
            "food_type_id": 283,
            "page_size": 100,
            "reported_total": 3,
            "reported_pages": 1,
            "scanned_pages": 1,
            "scanned_record_count": 3,
            "complete_scan": True,
            "page_results": [],
        }
        report = build_inventory_report(
            current_entries=[kept, changed, added],
            previous_entries={
                kept["reference"]: kept,
                old_changed["reference"]: old_changed,
                removed["reference"]: removed,
            },
            diagnostics=diagnostics,
        )
        self.assertEqual(report["status"], "changed")
        self.assertEqual(report["new_reference_samples"], [added["reference"]])
        self.assertEqual(
            report["removed_reference_samples"], [removed["reference"]]
        )
        self.assertEqual(
            report["changed_reference_samples"], [changed["reference"]]
        )

    def test_state_round_trip_preserves_minimal_fingerprints(self) -> None:
        entries = [state_entry(notification(2)), state_entry(notification(1))]
        path = Path("unused-rasff-state.json")
        with patch.object(Path, "write_text") as write_text:
            write_inventory_state(
                entries, path, created_at="2026-06-30T00:00:00+00:00"
            )
        raw = json.loads(write_text.call_args.args[0])
        self.assertEqual(raw["record_count"], 2)
        self.assertNotIn("subject", raw["records"][0])
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "read_text", return_value=json.dumps(raw)),
        ):
            loaded = load_inventory_state(path)
        self.assertEqual(sorted(loaded), ["2026.0001", "2026.0002"])

    def test_inventory_returns_failure_report_for_artifact(self) -> None:
        report, entries = inventory_rasff(
            state_path=Path("unused.json"),
            fetcher=lambda _url, _payload: (_ for _ in ()).throw(
                TimeoutError("timed out")
            ),
        )
        self.assertEqual(report["status"], "failed")
        self.assertEqual(entries, [])
        self.assertIn("timed out", report["blocking_errors"][0])

    def test_fingerprint_changes_when_selected_evidence_changes(self) -> None:
        first = notification(1)
        second = dict(first)
        second["subject"] = "corrected"
        self.assertNotEqual(
            notification_fingerprint(first), notification_fingerprint(second)
        )


if __name__ == "__main__":
    unittest.main()
