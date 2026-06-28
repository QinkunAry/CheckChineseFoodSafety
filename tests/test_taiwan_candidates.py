from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from food_safety_watch.quality import load_schema
from food_safety_watch.taiwan_candidates import (
    build_candidate_report,
    candidate_taiwan_tfda,
    parse_candidate_record,
    product_category,
)
from food_safety_watch.taiwan_probe import stable_record_id


SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "record.schema.json"


def record(
    origin: str = "中國大陸",
    subject: str = "冷凍草莓",
    tariff: str = "0811.10.00.00-5",
    reason: str = "農藥殘留含量不符規定",
) -> dict[str, str]:
    return {
        "產地": origin, "主旨": subject, "原因": reason, "進口商名稱": "測試進口商",
        "進口商地址": "臺北市", "貨品分類號列": tariff, "檢驗方法": "方法",
        "不合格原因暨檢出量詳細說明": "檢出農藥不符合規定", "法規限量標準": "標準",
        "製造廠或出口商名稱": "TEST EXPORTER", "製造商代碼": "", "牌名": "",
        "重量": "1 KG", "處置情形": "退運或銷毀", "發布日期": "2026/06/23",
        "報驗受理日期": "2026/06/01", "附圖": "https://www.fda.gov.tw/image",
    }


class TaiwanCandidateTests(unittest.TestCase):
    def test_china_food_normalizes_to_schema_record(self) -> None:
        candidate = parse_candidate_record(
            record(), retrieved_at="2026-06-28T00:00:00+00:00"
        )
        self.assertIsNotNone(candidate)
        value = candidate.to_dict()  # type: ignore[union-attr]
        self.assertEqual(value["origin_country"], "CN")
        self.assertEqual(value["action_type"], "inspection_failure")
        self.assertEqual(value["product_category"], "fruit")
        self.assertEqual(value["hazard_tags"], ["chemical"])

    def test_non_china_and_non_food_records_are_excluded(self) -> None:
        retrieved_at = "2026-06-28T00:00:00+00:00"
        self.assertIsNone(parse_candidate_record(record(origin="日本"), retrieved_at=retrieved_at))
        self.assertIsNone(
            parse_candidate_record(
                record(tariff="3924.10", reason="容器具-溶出試驗不符規定"),
                retrieved_at=retrieved_at,
            )
        )

    def test_candidate_report_validates_and_counts_exclusions(self) -> None:
        report, candidates = build_candidate_report(
            records=[
                record(),
                record(origin="日本", subject="日本草莓"),
                record(subject="餐盒", tariff="3924.10", reason="容器具不符規定"),
            ],
            schema=load_schema(SCHEMA),
            retrieved_at="2026-06-28T00:00:00+00:00",
            baseline_count=10,
            current_count=13,
        )
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["china_human_food_candidate_count"], 1)
        self.assertEqual(report["excluded_non_china_count"], 1)
        self.assertEqual(report["excluded_china_non_food_count"], 1)
        self.assertEqual(report["schema_error_count"], 0)
        self.assertEqual(len(candidates), 1)

    def test_empty_increment_is_a_passing_candidate_batch(self) -> None:
        report, candidates = build_candidate_report(
            records=[],
            schema=load_schema(SCHEMA),
            retrieved_at="2026-06-28T00:00:00+00:00",
        )
        self.assertEqual(report["status"], "passed")
        self.assertEqual(candidates, [])

    def test_invalid_candidate_date_fails_closed_with_diagnostic(self) -> None:
        invalid = record()
        invalid["發布日期"] = "not-a-date"
        report, candidates = build_candidate_report(
            records=[invalid],
            schema=load_schema(SCHEMA),
            retrieved_at="2026-06-28T00:00:00+00:00",
        )
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["parse_error_count"], 1)
        self.assertIn("record parse failed", report["blocking_errors"][0])
        self.assertEqual(candidates, [])

    def test_tariff_category_is_deterministic(self) -> None:
        self.assertEqual(product_category(record(tariff="0306.17")), "seafood")
        self.assertEqual(product_category(record(tariff="2106.90")), "prepared_foods")

    def test_candidate_pipeline_selects_only_hashes_after_baseline(self) -> None:
        existing = record(subject="既有草莓")
        added = record(subject="新增草莓")
        payload = json.dumps([existing, added], ensure_ascii=False).encode()
        with patch(
            "food_safety_watch.taiwan_candidates.load_record_state",
            return_value=[stable_record_id(existing)],
        ):
            report, candidates = candidate_taiwan_tfda(
                state_path=Path("unused-state.json"),
                schema=load_schema(SCHEMA),
                payload=payload,
            )
        self.assertEqual(report["scope"], "new_since_baseline")
        self.assertEqual(report["new_record_count"], 1)
        self.assertEqual([item["product_name"] for item in candidates], ["新增草莓"])


if __name__ == "__main__":
    unittest.main()
