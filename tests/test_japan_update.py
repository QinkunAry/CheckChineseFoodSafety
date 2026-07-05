from __future__ import annotations

import unittest
from pathlib import Path

from food_safety_watch.japan_update import build_japan_release, build_release_metadata
from food_safety_watch.quality import load_schema


SCHEMA = load_schema(Path("schemas/record.schema.json"))


def record(
    *,
    reference: str = "RCL202601519",
    authority: str = "Ministry of Health, Labour and Welfare, Japan",
    source_url: str | None = None,
    hazard_tags: list[str] | None = None,
) -> dict[str, object]:
    return {
        "id": "d8439896d81621df96586f7e95180567f37d5b9711dfa64400125c6214566ee8",
        "source_id": "jp_caa_recalls",
        "source_record_id": reference,
        "authority": authority,
        "authority_region": "JP",
        "action_type": "recall",
        "event_date": "2026-06-12",
        "origin_country": "CN",
        "producer_name": "",
        "producer_location": "",
        "product_code": "",
        "product_category": "vegetables",
        "product_name": "とんぶり瓶詰（中国産）",
        "reasons": [
            "食品衛生法違反のおそれ",
            "芽胞菌（クロストリジウム属菌）が検出された",
        ],
        "hazard_tags": hazard_tags or ["microbiological"],
        "source_url": source_url or (
            "https://i2fas.mhlw.go.jp/faspub/_link.do?"
            f"i=IO_S020502&p={reference}"
        ),
        "retrieved_at": "2026-07-05T00:00:00+00:00",
    }


class JapanUpdateTests(unittest.TestCase):
    def test_reviewed_mhlw_record_passes_release_gates(self) -> None:
        report, records = build_japan_release(
            records=[record()],
            approved_references=["RCL202601519"],
            schema=SCHEMA,
            generated_at="2026-07-05T01:00:00+00:00",
        )
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["unclassified_hazard_count"], 0)
        self.assertEqual(len(records), 1)

    def test_approval_must_exactly_match_release(self) -> None:
        with self.assertRaisesRegex(ValueError, "must exactly match"):
            build_japan_release(
                records=[record()],
                approved_references=["RCL202699999"],
                schema=SCHEMA,
            )

    def test_caa_authority_or_url_cannot_enter_mhlw_release(self) -> None:
        report, _ = build_japan_release(
            records=[record(
                authority="Consumer Affairs Agency, Japan",
                source_url=(
                    "https://www.recall.caa.go.jp/result/detail.php?"
                    "rcl=00000035471&screenkbn=01"
                ),
            )],
            approved_references=["RCL202601519"],
            schema=SCHEMA,
        )
        self.assertEqual(report["status"], "failed")
        self.assertTrue(any("MHLW authority" in item for item in report["blocking_errors"]))
        self.assertTrue(any("source URL" in item for item in report["blocking_errors"]))

    def test_mhlw_url_reference_mismatch_is_blocked(self) -> None:
        report, _ = build_japan_release(
            records=[record(source_url=(
                "https://i2fas.mhlw.go.jp/faspub/_link.do?"
                "i=IO_S020502&p=RCL202600001"
            ))],
            approved_references=["RCL202601519"],
            schema=SCHEMA,
        )
        self.assertEqual(report["status"], "failed")
        self.assertTrue(any("mismatch" in item for item in report["blocking_errors"]))

    def test_unclassified_hazard_is_blocked(self) -> None:
        report, _ = build_japan_release(
            records=[record(hazard_tags=["other_or_unclassified"])],
            approved_references=["RCL202601519"],
            schema=SCHEMA,
        )
        self.assertEqual(report["status"], "failed")
        self.assertTrue(any("unclassified" in item for item in report["blocking_errors"]))

    def test_metadata_contains_pdl_processing_and_provenance(self) -> None:
        report, records = build_japan_release(
            records=[record()],
            approved_references=["RCL202601519"],
            schema=SCHEMA,
            generated_at="2026-07-05T01:00:00+00:00",
        )
        metadata = build_release_metadata(report, records)
        self.assertIn("公共データ利用規約", metadata["license"])
        self.assertIn("加工・作成", metadata["attribution_ja"])
        self.assertIn("not created or endorsed", metadata["attribution_en"])
        self.assertEqual(metadata["record_provenance"][0]["reference"], "RCL202601519")


if __name__ == "__main__":
    unittest.main()
