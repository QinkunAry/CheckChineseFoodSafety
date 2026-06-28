from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from food_safety_watch.taiwan_inventory import (
    build_inventory_report,
    load_record_state,
    new_records,
    write_record_state,
)
from food_safety_watch.taiwan_probe import stable_record_id


def record(subject: str) -> dict[str, str]:
    return {
        "產地": "中國大陸", "主旨": subject, "原因": "農藥殘留含量不符規定",
        "進口商名稱": "測試進口商", "貨品分類號列": "0902.10",
        "不合格原因暨檢出量詳細說明": "檢出不符合規定", "處置情形": "退運或銷毀",
        "發布日期": "2026/06/23", "報驗受理日期": "2026/06/01",
    }


class TaiwanInventoryTests(unittest.TestCase):
    def test_inventory_reports_new_and_removed_hashes(self) -> None:
        kept = record("茶葉")
        added = record("桂花")
        removed = stable_record_id(record("舊產品"))
        report = build_inventory_report([kept, added], [stable_record_id(kept), removed])
        self.assertEqual(report["status"], "changed")
        self.assertEqual(report["new_record_ids"], [stable_record_id(added)])
        self.assertEqual(report["removed_record_ids"], [removed])

    def test_new_records_uses_hash_baseline(self) -> None:
        kept = record("茶葉")
        added = record("桂花")
        self.assertEqual(new_records([kept, added], [stable_record_id(kept)]), [added])

    def test_state_round_trip_is_sorted_and_deduplicated(self) -> None:
        path = Path("unused-state.json")
        with patch.object(Path, "write_text") as write_text:
            write_record_state(["b", "a", "b"], path, created_at="2026-06-28T00:00:00+00:00")
        raw = json.loads(write_text.call_args.args[0])
        self.assertEqual(raw["record_count"], 2)
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "read_text", return_value=json.dumps(raw)),
        ):
            self.assertEqual(load_record_state(path), ["a", "b"])

    def test_invalid_state_is_rejected(self) -> None:
        path = Path("unused-state.json")
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "read_text", return_value='{"record_ids":"bad"}'),
        ):
            with self.assertRaisesRegex(ValueError, "invalid Taiwan TFDA record state"):
                load_record_state(path)


if __name__ == "__main__":
    unittest.main()
