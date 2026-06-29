from __future__ import annotations

import io
import unittest
import zipfile
from pathlib import Path

from food_safety_watch.china_samr_candidates import (
    build_candidate_report,
    has_mainland_producer_evidence,
    normalize_excel_date,
    parse_attachment_samples,
    parse_workbook_samples,
    product_category,
)
from food_safety_watch.quality import load_schema


SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "record.schema.json"
HEADERS = [
    "序号", "标称生产企业名称", "标称生产企业地址", "被抽样单位名称",
    "被抽样单位地址", "样品名称", "规格型号", "商标", "生产日期", "保质期",
    "不合格项目", "检验值", "标准值", "标签标注要求", "备注", "检验机构",
    "食品细类", "抽样编号", "备注",
]


def _column(index: int) -> str:
    result = ""
    value = index + 1
    while value:
        value, remainder = divmod(value - 1, 26)
        result = chr(ord("A") + remainder) + result
    return result


def _row_xml(number: int, values: list[str]) -> str:
    cells = []
    for index, value in enumerate(values):
        if value == "":
            continue
        cells.append(
            f'<c r="{_column(index)}{number}" t="inlineStr"><is><t>{value}</t></is></c>'
        )
    return f'<row r="{number}">{"".join(cells)}</row>'


def workbook_bytes(*, missing_sampling_number: bool = False) -> bytes:
    headers = list(HEADERS)
    first = [
        "1", "新疆测试酒业有限公司", "新疆维吾尔自治区测试路1号", "测试商店",
        "北京市测试路2号", "测试葡萄酒", "500mL", "测试牌", "45306", "3年",
        "胭脂红", "0.01g/kg", "不得使用", "/", "/", "测试检验院", "葡萄酒",
        "" if missing_sampling_number else "GBJ001", "手机APP",
    ]
    continuation = ["" for _ in HEADERS]
    continuation[10:14] = ["苋菜红", "0.02g/kg", "不得使用", "/"]
    repeated_sequence = ["" for _ in HEADERS]
    repeated_sequence[0] = "1"
    repeated_sequence[10:14] = ["三氯蔗糖", "0.03g/kg", "不得使用", "/"]
    second = [
        "2", "FOREIGN PRODUCER", "California, USA", "进口商店", "上海市测试路",
        "测试饼干", "100g", "TEST", "2025/01/02", "12个月", "过氧化值",
        "1.0g/100g", "≤0.25g/100g", "/", "产品真实性提出异议", "测试院",
        "饼干", "GBJ002", "/",
    ]
    sheet = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetData>'
        + _row_xml(1, ["附件2"])
        + _row_xml(2, ["酒类监督抽检不合格产品信息"])
        + _row_xml(3, headers)
        + _row_xml(4, first)
        + _row_xml(5, continuation)
        + _row_xml(6, repeated_sequence)
        + _row_xml(7, second)
        + "</sheetData></worksheet>"
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("xl/worksheets/sheet1.xml", sheet)
    return output.getvalue()


class ChinaSamrCandidateTests(unittest.TestCase):
    def test_excel_dates_normalize_from_serial_and_text(self) -> None:
        self.assertEqual(normalize_excel_date("45306"), "2024-01-15")
        self.assertEqual(normalize_excel_date("2025/01/02"), "2025-01-02")
        self.assertEqual(normalize_excel_date("购进日期：2025/4/12"), "2025-04-12")
        self.assertIsNone(normalize_excel_date("/"))

    def test_workbook_groups_continuation_and_repeated_sequence_rows(self) -> None:
        samples, diagnostic = parse_workbook_samples(
            workbook_bytes(), filename="酒类.xlsx"
        )
        self.assertEqual(len(samples), 2)
        self.assertEqual(samples[0]["sampling_number"], "GBJ001")
        self.assertEqual(len(samples[0]["failures"]), 3)
        self.assertEqual(samples[0]["production_date"], "2024-01-15")
        self.assertEqual(diagnostic["physical_row_count"], 4)
        self.assertEqual(diagnostic["continuation_row_count"], 2)

    def test_missing_sampling_number_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "has no sampling number"):
            parse_workbook_samples(
                workbook_bytes(missing_sampling_number=True), filename="bad.xlsx"
            )

    def test_zip_attachment_reads_nested_workbook(self) -> None:
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("附件2 酒类.xlsx", workbook_bytes())
        samples, diagnostics = parse_attachment_samples(
            output.getvalue(), filename="notice.zip"
        )
        self.assertEqual(len(samples), 2)
        self.assertEqual(len(diagnostics), 1)

    def test_scope_evidence_and_category_are_deterministic(self) -> None:
        self.assertTrue(has_mainland_producer_evidence("新疆维吾尔自治区测试路"))
        self.assertFalse(has_mainland_producer_evidence("California, USA"))
        self.assertEqual(product_category("葡萄酒"), "alcoholic_beverages")
        self.assertEqual(product_category("饼干"), "bakery_and_cereal_products")

    def test_candidate_report_is_schema_valid_and_marks_domestic_scope(self) -> None:
        samples, diagnostic = parse_workbook_samples(
            workbook_bytes(), filename="酒类.xlsx"
        )
        report, candidates = build_candidate_report(
            samples=samples,
            diagnostics=[diagnostic],
            notice_url="https://www.samr.gov.cn/spcjs/xxfb/art/2026/art_test.html",
            event_date="2026-04-24",
            schema=load_schema(SCHEMA),
            retrieved_at="2026-06-30T00:00:00+00:00",
        )
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["candidate_count"], 2)
        self.assertEqual(report["schema_error_count"], 0)
        self.assertEqual(report["origin_country_counts"], {"unknown": 2})
        self.assertEqual(report["mainland_producer_location_count"], 1)
        self.assertEqual(candidates[0]["regulatory_scope"], "domestic_market")
        self.assertEqual(candidates[0]["market_country"], "CN")
        self.assertEqual(len(candidates[0]["reasons"]), 4)


if __name__ == "__main__":
    unittest.main()
