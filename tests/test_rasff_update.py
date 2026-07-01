from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from food_safety_watch.quality import load_schema
from food_safety_watch.rasff_update import (
    _atomic_publish_pair,
    build_rasff_release,
    build_release_metadata,
    publish_rasff_reviewed,
)
from food_safety_watch.update import QualityCheckFailed


SCHEMA = load_schema(Path("schemas/record.schema.json"))


def record(
    *,
    reference: str = "2026.5752",
    status: str = "active",
    official_status: str = "ec_validated",
    retrieved_at: str = "2026-07-01T00:00:00+00:00",
) -> dict[str, object]:
    return {
        "id": f"eu-rasff-{reference}-stable-id",
        "source_id": "eu_rasff",
        "source_record_id": reference,
        "authority": "European Commission / DG SANTE / RASFF",
        "authority_region": "EU",
        "action_type": "rasff_notification",
        "event_date": "2026-06-29",
        "origin_country": "CN",
        "regulatory_scope": "origin_based",
        "producer_name": "",
        "producer_location": "",
        "product_code": "",
        "product_category": "cereals and bakery products",
        "product_name": "Vermicelli",
        "reasons": ["Consignment possibly subject to veterinary checks"],
        "hazard_tags": ["other_or_unclassified"],
        "source_url": "https://webgate.ec.europa.eu/rasff-window/screen/notification/854651",
        "retrieved_at": retrieved_at,
        "record_status": status,
        "official_notification_classification": "information for attention",
        "official_risk_decision": "not serious",
        "official_notification_basis": "border control - consignment released",
        "official_notification_status": official_status,
        "official_distribution_status": "no distribution",
        "official_last_update": "30-06-2026 12:00:00",
        "official_hazards": [],
        "official_measures": ["informing consignor"],
        "official_followup_types": ["corrigendum"],
    }


class RasffUpdateTests(unittest.TestCase):
    def _test_path(self, name: str) -> Path:
        root = Path(".tmp-test")
        root.mkdir(exist_ok=True)
        return root / name

    def test_reviewed_active_subset_passes_production_gates(self) -> None:
        report, records = build_rasff_release(
            records=[record()],
            approved_references=["2026.5752"],
            schema=SCHEMA,
            generated_at="2026-07-01T01:00:00+00:00",
        )
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["active_record_count"], 1)
        self.assertEqual(report["approved_references"], ["2026.5752"])
        self.assertEqual(len(records), 1)

    def test_approval_allowlist_must_exactly_match_input(self) -> None:
        with self.assertRaisesRegex(ValueError, "must exactly match"):
            build_rasff_release(
                records=[record()],
                approved_references=["2026.9999"],
                schema=SCHEMA,
            )

    def test_withdrawn_record_is_blocked(self) -> None:
        report, _ = build_rasff_release(
            records=[record(status="withdrawn", official_status="ec_withdrawn")],
            approved_references=["2026.5752"],
            schema=SCHEMA,
        )
        self.assertEqual(report["status"], "failed")
        self.assertTrue(any("only active" in item for item in report["blocking_errors"]))

    def test_release_preserves_first_retrieval_time(self) -> None:
        report, records = build_rasff_release(
            records=[record(retrieved_at="2026-07-02T00:00:00+00:00")],
            approved_references=["2026.5752"],
            schema=SCHEMA,
            baseline_records=[record(retrieved_at="2026-07-01T00:00:00+00:00")],
        )
        self.assertEqual(report["status"], "passed")
        self.assertEqual(records[0]["retrieved_at"], "2026-07-01T00:00:00+00:00")

    def test_metadata_contains_attribution_changes_and_per_record_provenance(self) -> None:
        report, records = build_rasff_release(
            records=[record()],
            approved_references=["2026.5752"],
            schema=SCHEMA,
            generated_at="2026-07-01T01:00:00+00:00",
        )
        metadata = build_release_metadata(report, records)
        self.assertEqual(metadata["license_url"], "https://creativecommons.org/licenses/by/4.0/")
        self.assertIn("changes were made", metadata["attribution"])
        self.assertIn("do not endorse", metadata["attribution"])
        self.assertEqual(metadata["record_provenance"][0]["reference"], "2026.5752")

    def test_pair_publication_rolls_back_when_second_replace_fails(self) -> None:
        output = self._test_path("rasff-pair-release.jsonl")
        metadata_path = self._test_path("rasff-pair-release.metadata.json")
        output.write_text("old-data\n", encoding="utf-8")
        metadata_path.write_text("old-metadata\n", encoding="utf-8")
        original_replace = Path.replace

        def replace(path: Path, target: Path) -> Path:
            if path.name == ".rasff-pair-release.metadata.json.tmp":
                raise PermissionError("metadata replace denied")
            return original_replace(path, target)

        with patch.object(Path, "replace", replace):
            with self.assertRaises(PermissionError):
                _atomic_publish_pair([record()], {"record_count": 1}, output, metadata_path)
        self.assertEqual(output.read_text(encoding="utf-8"), "old-data\n")
        self.assertEqual(metadata_path.read_text(encoding="utf-8"), "old-metadata\n")

    def test_failed_input_does_not_publish_data_or_metadata(self) -> None:
        input_path = self._test_path("rasff-failed-candidates.jsonl")
        output = self._test_path("rasff-failed-release.jsonl")
        report_path = self._test_path("rasff-failed-quality.json")
        metadata_path = self._test_path("rasff-failed-metadata.json")
        input_path.write_text(json.dumps(record()) + "\n", encoding="utf-8")
        with self.assertRaises(QualityCheckFailed):
            publish_rasff_reviewed(
                input_path=input_path,
                output=output,
                report_path=report_path,
                metadata_path=metadata_path,
                schema_path=Path("schemas/record.schema.json"),
                approved_references=["2026.9999"],
            )
        self.assertFalse(output.exists())
        self.assertFalse(metadata_path.exists())
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "failed")


if __name__ == "__main__":
    unittest.main()
