from __future__ import annotations

import json
import unittest

from food_safety_watch.taiwan_probe import (
    build_taiwan_probe_report,
    is_china_origin,
    is_human_food_candidate,
    parse_dataset,
    stable_record_id,
)


def record(origin: str, subject: str, tariff: str, reason: str = "農藥殘留含量不符規定") -> dict[str, str]:
    return {
        "產地": origin, "主旨": subject, "原因": reason, "進口商名稱": "測試進口商",
        "進口商地址": "臺北市", "貨品分類號列": tariff, "檢驗方法": "方法",
        "不合格原因暨檢出量詳細說明": "檢出不符合規定", "法規限量標準": "標準",
        "製造廠或出口商名稱": "EXPORTER", "製造商代碼": "", "牌名": "",
        "重量": "1 KG", "處置情形": "退運或銷毀", "發布日期": "2026/06/23",
        "報驗受理日期": "2026/06/01", "附圖": "https://www.fda.gov.tw/image",
    }


class TaiwanProbeTests(unittest.TestCase):
    def test_china_origin_uses_explicit_origin_field(self) -> None:
        self.assertTrue(is_china_origin(record("中國大陸", "桂花", "1211.90")))
        self.assertFalse(is_china_origin(record("日本", "中國風茶", "0902.10")))

    def test_food_scope_uses_tariff_chapters_and_excludes_feed(self) -> None:
        self.assertTrue(is_human_food_candidate(record("中國", "桂花", "1211.90")))
        self.assertFalse(is_human_food_candidate(record("中國", "砧板", "3924.10", "容器具-溶出試驗不符規定")))
        self.assertFalse(is_human_food_candidate(record("中國", "飼料", "2309.90")))

    def test_stable_id_is_deterministic(self) -> None:
        value = record("中國", "桂花", "1211.90")
        self.assertEqual(stable_record_id(value), stable_record_id(dict(value)))

    def test_dataset_parser_requires_official_fields(self) -> None:
        payload = json.dumps([record("中國", "桂花", "1211.90")], ensure_ascii=False).encode()
        self.assertEqual(len(parse_dataset(payload)), 1)
        with self.assertRaisesRegex(ValueError, "missing fields"):
            parse_dataset('[{"產地":"中國"}]'.encode())

    def test_probe_reports_china_and_non_china_samples(self) -> None:
        records = [
            record("中國大陸", "桂花", "1211.90"),
            record("日本", "藍莓", "0810.40"),
            record("中國大陸", "蛋糕盒", "4823.69", "其他衛生項目不符規定"),
        ]
        report = build_taiwan_probe_report(
            payload=json.dumps(records, ensure_ascii=False).encode(),
            limit=2,
            min_records=3,
            min_china_records=2,
        )
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["china_record_count"], 2)
        self.assertEqual(report["china_human_food_candidate_count"], 1)
        self.assertEqual(len(report["china_samples"]), 1)
        self.assertEqual(len(report["non_china_samples"]), 1)

    def test_probe_fails_count_gate(self) -> None:
        payload = json.dumps([record("日本", "藍莓", "0810.40")], ensure_ascii=False).encode()
        report = build_taiwan_probe_report(payload=payload, min_records=2, min_china_records=1)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(len(report["blocking_errors"]), 2)


if __name__ == "__main__":
    unittest.main()
