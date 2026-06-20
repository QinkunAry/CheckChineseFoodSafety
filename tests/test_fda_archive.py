from __future__ import annotations

import io
import os
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from food_safety_watch.fda import (
    FdaDownloadError,
    configured_download_url,
    discover_download_url,
    parse_archive,
)
from food_safety_watch.quality import build_quality_report, load_schema
from food_safety_watch.update import QualityCheckFailed, update_fda


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures" / "fda"
SCHEMA = ROOT / "schemas" / "record.schema.json"


def fixture_archive() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for path in FIXTURES.glob("*.csv"):
            archive.writestr(path.name, path.read_bytes())
    return buffer.getvalue()


class FdaArchiveTests(unittest.TestCase):
    def test_empty_github_variable_is_not_treated_as_url(self) -> None:
        with patch.dict(os.environ, {"FOOD_SAFETY_FDA_DOWNLOAD_URL": ""}):
            self.assertIsNone(configured_download_url())

    def test_whitespace_github_variable_is_not_treated_as_url(self) -> None:
        with patch.dict(os.environ, {"FOOD_SAFETY_FDA_DOWNLOAD_URL": "   "}):
            self.assertIsNone(configured_download_url())

    def test_discovers_current_zip_from_official_page(self) -> None:
        page = '<option value="Import_Refusal_2024-present.zip">2024 - Present</option>'
        self.assertEqual(
            discover_download_url(page),
            "https://www.accessdata.fda.gov/scripts/importrefusals/"
            "downloads/Import_Refusal_2024-present.zip",
        )

    def test_rejects_unsafe_discovered_filename(self) -> None:
        page = '<option value="../Import_Refusal_2024-present.zip">bad</option>'
        with self.assertRaises(FdaDownloadError):
            discover_download_url(page)

    def test_parser_keeps_only_cn_human_food(self) -> None:
        records = parse_archive(fixture_archive(), country="CN")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].product_category, "seafood")
        self.assertEqual(records[0].event_date, "2026-01-06")
        self.assertEqual(records[0].hazard_tags, ["microbiological"])

    def test_quality_report_detects_duplicate_ids(self) -> None:
        record = parse_archive(fixture_archive(), country="CN")[0].to_dict()
        report = build_quality_report(
            [record, record],
            load_schema(SCHEMA),
            source_id="test",
            min_records=1,
        )
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["duplicate_id_count"], 1)

    def test_quality_report_rejects_large_count_drop(self) -> None:
        record = parse_archive(fixture_archive(), country="CN")[0].to_dict()
        report = build_quality_report(
            [record],
            load_schema(SCHEMA),
            source_id="test",
            baseline_count=10,
            min_records=1,
            max_drop_fraction=0.25,
        )
        self.assertEqual(report["status"], "failed")
        self.assertTrue(any("dropped" in error for error in report["blocking_errors"]))

    def test_failed_update_does_not_publish_candidate(self) -> None:
        with (
            patch("food_safety_watch.update.write_json_file") as write_report,
            patch("food_safety_watch.update.write_jsonl_file") as publish,
        ):
            with self.assertRaises(QualityCheckFailed):
                update_fda(
                    output=Path("unused-release.jsonl"),
                    report_path=Path("unused-quality.json"),
                    schema_path=SCHEMA,
                    payload=fixture_archive(),
                    min_records=2,
                )
            write_report.assert_called_once()
            publish.assert_not_called()


if __name__ == "__main__":
    unittest.main()
