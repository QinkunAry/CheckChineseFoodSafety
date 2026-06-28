from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from food_safety_watch.quality import load_schema
from food_safety_watch.taiwan_candidates import parse_candidate_record
from food_safety_watch.taiwan_update import (
    _atomic_write_jsonl,
    build_release_metadata,
    build_taiwan_release,
    update_taiwan_tfda,
)
from food_safety_watch.update import QualityCheckFailed


SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "record.schema.json"


def record(
    *,
    origin: str = "中國大陸",
    subject: str = "冷凍草莓",
    reason: str = "農藥殘留含量不符規定",
    detail: str = "檢出農藥不符合規定",
) -> dict[str, str]:
    return {
        "產地": origin, "主旨": subject, "原因": reason, "進口商名稱": "測試進口商",
        "進口商地址": "臺北市", "貨品分類號列": "0811.10.00.00-5", "檢驗方法": "方法",
        "不合格原因暨檢出量詳細說明": detail, "法規限量標準": "標準",
        "製造廠或出口商名稱": "TEST EXPORTER", "製造商代碼": "", "牌名": "",
        "重量": "1 KG", "處置情形": "退運或銷毀", "發布日期": "2026/06/23",
        "報驗受理日期": "2026/06/01", "附圖": "https://www.fda.gov.tw/image",
    }


def payload(*records: dict[str, str]) -> bytes:
    return json.dumps(records, ensure_ascii=False).encode()


class TaiwanUpdateTests(unittest.TestCase):
    def test_full_release_applies_production_quality_gates(self) -> None:
        report, records = build_taiwan_release(
            payload=payload(record(), record(origin="日本", subject="日本草莓")),
            schema=load_schema(SCHEMA),
            retrieved_at="2026-06-29T00:00:00+00:00",
            min_source_records=2,
            min_records=1,
        )
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["source_record_count"], 2)
        self.assertEqual(report["record_count"], 1)
        self.assertEqual(report["unclassified_hazard_count"], 0)
        self.assertEqual(len(records), 1)

    def test_release_preserves_first_retrieval_time(self) -> None:
        source = record()
        baseline = parse_candidate_record(
            source, retrieved_at="2026-06-28T00:00:00+00:00"
        ).to_dict()  # type: ignore[union-attr]
        report, records = build_taiwan_release(
            payload=payload(source),
            schema=load_schema(SCHEMA),
            retrieved_at="2026-06-29T00:00:00+00:00",
            baseline_records=[baseline],
            min_source_records=1,
            min_records=1,
        )
        self.assertEqual(report["baseline_count"], 1)
        self.assertEqual(records[0]["retrieved_at"], "2026-06-28T00:00:00+00:00")

    def test_unclassified_hazard_blocks_release(self) -> None:
        report, _ = build_taiwan_release(
            payload=payload(record(reason="其他衛生項目不符規定", detail="未知項目")),
            schema=load_schema(SCHEMA),
            retrieved_at="2026-06-29T00:00:00+00:00",
            min_source_records=1,
            min_records=1,
            max_unclassified=0,
        )
        self.assertEqual(report["status"], "failed")
        self.assertIn("unclassified hazard count", report["blocking_errors"][0])

    def test_large_drop_from_previous_release_is_blocked(self) -> None:
        report, _ = build_taiwan_release(
            payload=payload(record()),
            schema=load_schema(SCHEMA),
            retrieved_at="2026-06-29T00:00:00+00:00",
            baseline_records=[{}] * 10,
            min_source_records=1,
            min_records=1,
            max_drop_fraction=0.25,
        )
        self.assertEqual(report["status"], "failed")
        self.assertTrue(any("dropped" in error for error in report["blocking_errors"]))

    def test_failed_update_does_not_publish_data_or_metadata(self) -> None:
        with (
            patch.object(Path, "exists", return_value=False),
            patch("food_safety_watch.taiwan_update.write_json_file") as write_report,
            patch("food_safety_watch.taiwan_update._atomic_write_json") as metadata_publish,
            patch("food_safety_watch.taiwan_update._atomic_write_jsonl") as data_publish,
        ):
            with self.assertRaises(QualityCheckFailed):
                update_taiwan_tfda(
                    output=Path("unused.jsonl"),
                    report_path=Path("unused-report.json"),
                    metadata_path=Path("unused-metadata.json"),
                    schema_path=SCHEMA,
                    payload=payload(record()),
                    min_source_records=1,
                    min_records=2,
                )
        write_report.assert_called_once()
        metadata_publish.assert_not_called()
        data_publish.assert_not_called()

    def test_atomic_publication_error_is_written_to_quality_report(self) -> None:
        with (
            patch.object(Path, "exists", return_value=False),
            patch("food_safety_watch.taiwan_update.write_json_file") as write_report,
            patch(
                "food_safety_watch.taiwan_update._atomic_write_json",
                side_effect=PermissionError("replace denied"),
            ),
            patch("food_safety_watch.taiwan_update._atomic_write_jsonl") as data_publish,
        ):
            with self.assertRaisesRegex(QualityCheckFailed, "publication failed"):
                update_taiwan_tfda(
                    output=Path("unused.jsonl"),
                    report_path=Path("unused-report.json"),
                    metadata_path=Path("unused-metadata.json"),
                    schema_path=SCHEMA,
                    payload=payload(record()),
                    min_source_records=1,
                    min_records=1,
                )
        self.assertEqual(write_report.call_count, 2)
        failed_report = write_report.call_args_list[-1].args[0]
        self.assertEqual(failed_report["status"], "failed")
        self.assertIn("publication failed", failed_report["blocking_errors"][-1])
        data_publish.assert_not_called()

    def test_release_metadata_contains_required_attribution(self) -> None:
        metadata = build_release_metadata({
            "generated_at": "2026-06-29T00:00:00+00:00",
            "record_count": 388,
        })
        self.assertIn("衛生福利部食品藥物管理署", metadata["attribution"])
        self.assertIn("不符合食品資訊資料集", metadata["attribution"])
        self.assertEqual(metadata["license_url"], "https://data.gov.tw/license")

    def test_atomic_writer_replaces_only_after_temporary_write(self) -> None:
        output = Path("release.jsonl")
        temporary = Path(".release.jsonl.tmp")
        with (
            patch("food_safety_watch.taiwan_update.write_jsonl_file") as write,
            patch.object(Path, "replace") as replace,
            patch.object(Path, "exists", return_value=False),
        ):
            _atomic_write_jsonl([], output)
        write.assert_called_once_with([], temporary)
        replace.assert_called_once_with(output)


if __name__ == "__main__":
    unittest.main()
