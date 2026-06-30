from __future__ import annotations

import json
import unittest
from pathlib import Path

from food_safety_watch.quality import load_schema
from food_safety_watch.rasff_candidates import (
    build_candidate_report,
    candidate_rasff,
    select_candidate_notifications,
)
from food_safety_watch.rasff_inventory import state_entry
from food_safety_watch.rasff_probe import (
    COUNTRY_URL,
    PRODUCT_TYPE_URL,
    SEARCH_API_URL,
)


SCHEMA = load_schema(Path("schemas/record.schema.json"))


def notification(index: int) -> dict[str, object]:
    return {
        "notifId": 800000 + index,
        "ecValidationDate": "24-06-2026 12:36:41",
        "reference": f"2026.{index:04d}",
        "notifyingCountry": {
            "organizationName": "Netherlands",
            "isoCode": "NL",
        },
        "subject": f"pesticide in tea sample {index}",
        "productCategory": {
            "id": 18435,
            "description": "cocoa and cocoa preparations, coffee and tea",
        },
        "productType": {"id": 283, "description": "food"},
        "notificationClassification": {
            "id": 305,
            "description": "border rejection notification",
        },
        "riskDecision": {"id": 18761, "description": "serious"},
        "published": False,
        "originCountries": [
            {"organizationName": "China", "isoCode": "CN"}
        ],
    }


def selection(*, scope: str = "new_or_changed_since_baseline") -> dict[str, object]:
    return {
        "scope": scope,
        "requested_references": [],
        "new_references": [],
        "changed_references": [],
        "removed_references": [],
        "selected_references": [],
    }


def catalog_fetcher(records: list[dict[str, object]]):
    def fetch(url: str, payload: dict[str, object] | None) -> bytes:
        if url == COUNTRY_URL:
            return json.dumps(
                {
                    "countries": [
                        {"id": 5075, "alpha2Code": "CN"},
                        {"id": 5118, "alpha2Code": "IN"},
                    ]
                }
            ).encode()
        if url == PRODUCT_TYPE_URL:
            return json.dumps(
                {"notificationTypes": [{"id": 283, "description": "food"}]}
            ).encode()
        if url == SEARCH_API_URL:
            return json.dumps(
                {
                    "notifications": records,
                    "totalElements": len(records),
                    "totalPages": 1,
                }
            ).encode()
        raise AssertionError((url, payload))

    return fetch


class RasffCandidateTests(unittest.TestCase):
    def test_selects_new_and_changed_records_since_baseline(self) -> None:
        kept = notification(1)
        changed = notification(2)
        old_changed = notification(2)
        old_changed["subject"] = "old subject"
        added = notification(3)
        removed = notification(4)
        baseline = {
            kept["reference"]: state_entry(kept),
            old_changed["reference"]: state_entry(old_changed),
            removed["reference"]: state_entry(removed),
        }
        selected, details = select_candidate_notifications(
            notifications=[kept, changed, added], baseline=baseline
        )
        self.assertEqual(
            [item["reference"] for item in selected],
            [changed["reference"], added["reference"]],
        )
        self.assertEqual(details["new_references"], [added["reference"]])
        self.assertEqual(details["changed_references"], [changed["reference"]])
        self.assertEqual(details["removed_references"], [removed["reference"]])

    def test_explicit_review_selects_only_requested_current_references(self) -> None:
        records = [notification(1), notification(2), notification(3)]
        baseline = {item["reference"]: state_entry(item) for item in records}
        selected, details = select_candidate_notifications(
            notifications=records,
            baseline=baseline,
            review_references=["2026.0003", "2026.0001", "2026.0003"],
        )
        self.assertEqual(
            [item["reference"] for item in selected],
            ["2026.0003", "2026.0001"],
        )
        self.assertEqual(details["scope"], "explicit_review")

    def test_missing_or_invalid_review_reference_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid RASFF reference"):
            select_candidate_notifications(
                notifications=[notification(1)],
                baseline={},
                review_references=["bad"],
            )
        with self.assertRaisesRegex(ValueError, "not in the current"):
            select_candidate_notifications(
                notifications=[notification(1)],
                baseline={},
                review_references=["2026.9999"],
            )

    def test_candidate_report_preserves_evidence_and_validates_schema(self) -> None:
        item = notification(1)
        details = selection(scope="explicit_review")
        details["requested_references"] = [item["reference"]]
        report, candidates = build_candidate_report(
            selected=[item],
            selection=details,
            schema=SCHEMA,
            baseline_count=1,
            current_count=1,
            generated_at="2026-07-01T00:00:00+00:00",
        )
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["schema_error_count"], 0)
        self.assertEqual(report["evidence_samples"][0]["risk_decision"]["description"], "serious")
        self.assertEqual(candidates[0]["source_record_id"], "2026.0001")
        self.assertEqual(candidates[0]["origin_country"], "CN")

    def test_candidate_limit_fails_without_partial_output(self) -> None:
        items = [notification(1), notification(2)]
        report, candidates = build_candidate_report(
            selected=items,
            selection=selection(),
            schema=SCHEMA,
            baseline_count=0,
            current_count=2,
            max_candidates=1,
        )
        self.assertEqual(report["status"], "failed")
        self.assertEqual(candidates, [])
        self.assertIn("exceeds maximum", report["blocking_errors"][0])

    def test_unchanged_baseline_produces_empty_passing_batch(self) -> None:
        records = [notification(1), notification(2)]
        selected, details = select_candidate_notifications(
            notifications=records,
            baseline={item["reference"]: state_entry(item) for item in records},
        )
        report, candidates = build_candidate_report(
            selected=selected,
            selection=details,
            schema=SCHEMA,
            baseline_count=2,
            current_count=2,
        )
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["candidate_record_count"], 0)
        self.assertEqual(candidates, [])

    def test_candidate_pipeline_returns_network_failure_report(self) -> None:
        report, candidates = candidate_rasff(
            state_path=Path("unused.json"),
            schema=SCHEMA,
            fetcher=lambda _url, _payload: (_ for _ in ()).throw(
                TimeoutError("timed out")
            ),
        )
        self.assertEqual(report["status"], "failed")
        self.assertEqual(candidates, [])
        self.assertIn("timed out", report["blocking_errors"][0])

    def test_candidate_pipeline_supports_explicit_review(self) -> None:
        records = [notification(1), notification(2)]
        report, candidates = candidate_rasff(
            state_path=Path("missing-state.json"),
            schema=SCHEMA,
            review_references=["2026.0002"],
            fetcher=catalog_fetcher(records),
            page_size=100,
        )
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["scope"], "explicit_review")
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["source_record_id"], "2026.0002")


if __name__ == "__main__":
    unittest.main()
