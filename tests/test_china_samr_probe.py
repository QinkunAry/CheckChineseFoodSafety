from __future__ import annotations

import io
import json
import unittest
import zipfile

from food_safety_watch.china_samr_probe import (
    CORE_HEADERS,
    LIST_URL,
    build_china_samr_probe_report,
    inspect_attachment,
    inspect_xlsx,
    parse_listing_response,
    parse_notice_page,
)


NOTICE_URL = (
    "https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/spcjs/art/2026/"
    "art_example.html"
)
ATTACHMENT_URL = (
    "https://www.samr.gov.cn/cms_files/filemanager/example/attach/2026/sample.zip"
)


def xlsx_bytes(*, missing_header: str | None = None) -> bytes:
    headers = [
        "序号",
        "标称生产企业名称",
        "被抽样单位名称",
        "样品名称",
        "不合格项目",
        "检验值",
        "标准值",
        "食品细类",
        "抽样编号",
    ]
    if missing_header:
        headers.remove(missing_header)

    def row_xml(number: int, values: list[str]) -> str:
        cells = []
        for index, value in enumerate(values):
            column = chr(ord("A") + index)
            cells.append(
                f'<c r="{column}{number}" t="inlineStr"><is><t>{value}</t></is></c>'
            )
        return f'<row r="{number}">{"".join(cells)}</row>'

    sheet = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetData>'
        + row_xml(1, ["市场监督管理总局食品安全监督抽检结果"])
        + row_xml(2, headers)
        + row_xml(3, ["1", "生产者", "商店", "食品", "铅", "1", "0.5", "调味品", "GBJ1"])
        + "</sheetData></worksheet>"
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("xl/worksheets/sheet1.xml", sheet)
    return output.getvalue()


def listing_payload() -> bytes:
    listing_html = f'''
    <div id="ajax分页"><div class="page-content"><ul>
      <li><a href="{NOTICE_URL}" title="市场监管总局办公厅关于46批次食品抽检不合格情况的通报">通报</a><div>2026-02-09</div></li>
      <li><a href="/zw/zfxxgk/fdzdgknr/spcjs/art/2026/art_two.html" title="市场监管总局办公厅关于47批次食品抽检不合格情况的通报">通报</a><div>2026-01-30</div></li>
      <li><a href="/spcjs/method.html" title="食品检验方法公告">公告</a></li>
    </ul></div><div class="pagination" count="259"></div></div>
    '''
    return json.dumps({"success": True, "data": {"html": listing_html}}).encode()


def notice_payload() -> bytes:
    return f'''
    <html><body>
      <h1>市场监管总局办公厅关于46批次食品抽检不合格情况的通报</h1>
      <p>发布时间：2026-02-09 06:39</p>
      <p>检出46批次样品不合格。</p>
      <a href="{ATTACHMENT_URL}">附件2-22 监督抽检不合格产品信息.zip</a>
    </body></html>
    '''.encode()


def attachment_zip() -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("附件2 调味品监督抽检不合格产品信息.xlsx", xlsx_bytes())
    return output.getvalue()


class ChinaSamrProbeTests(unittest.TestCase):
    def test_listing_parser_filters_batch_notices(self) -> None:
        count, notices = parse_listing_response(listing_payload())
        self.assertEqual(count, 259)
        self.assertEqual(len(notices), 2)
        self.assertEqual(notices[0].published_date, "2026-02-09")

    def test_notice_parser_extracts_batch_count_and_attachment(self) -> None:
        result = parse_notice_page(notice_payload(), url=NOTICE_URL)
        self.assertEqual(result["declared_noncompliant_batch_count"], 46)
        self.assertEqual(result["published_date"], "2026-02-09")
        self.assertEqual(result["attachments"][0]["type"], "zip")

    def test_notice_parser_percent_encodes_attachment_filename(self) -> None:
        payload = b'''
        <h1>\xe5\xb8\x82\xe5\x9c\xba\xe7\x9b\x91\xe7\xae\xa1\xe6\x80\xbb\xe5\xb1\x80\xe5\x8a\x9e\xe5\x85\xac\xe5\x8e\x85\xe5\x85\xb3\xe4\xba\x8e46\xe6\x89\xb9\xe6\xac\xa1\xe9\xa3\x9f\xe5\x93\x81\xe6\x8a\xbd\xe6\xa3\x80\xe4\xb8\x8d\xe5\x90\x88\xe6\xa0\xbc\xe6\x83\x85\xe5\x86\xb5\xe7\x9a\x84\xe9\x80\x9a\xe6\x8a\xa5</h1>
        <p>\xe6\xa3\x80\xe5\x87\xba46\xe6\x89\xb9\xe6\xac\xa1\xe6\xa0\xb7\xe5\x93\x81\xe4\xb8\x8d\xe5\x90\x88\xe6\xa0\xbc\xe3\x80\x82</p>
        <a href="/cms_files/sample.zip?fileName=\xe9\x99\x84\xe4\xbb\xb6 2.zip">ZIP</a>
        '''
        result = parse_notice_page(payload, url=NOTICE_URL)
        attachment_url = result["attachments"][0]["url"]
        self.assertIn("%E9%99%84%E4%BB%B6%202.zip", attachment_url)

    def test_xlsx_inspection_requires_core_headers(self) -> None:
        result = inspect_xlsx(xlsx_bytes(), filename="sample.xlsx")
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["unique_sampling_number_count"], 1)
        self.assertTrue(CORE_HEADERS.issubset(set(result["headers"])))

        missing = inspect_xlsx(
            xlsx_bytes(missing_header="抽样编号"), filename="missing.xlsx"
        )
        self.assertEqual(missing["status"], "failed")
        self.assertEqual(missing["missing_core_headers"], ["抽样编号"])

    def test_zip_inspection_reads_nested_workbooks(self) -> None:
        results = inspect_attachment(attachment_zip(), filename="sample.zip")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "passed")

    def test_probe_combines_listing_notice_and_archive_checks(self) -> None:
        responses = {
            LIST_URL: listing_payload(),
            NOTICE_URL: notice_payload(),
            ATTACHMENT_URL: attachment_zip(),
        }
        report = build_china_samr_probe_report(
            fetcher=responses.__getitem__,
            min_listing_count=100,
            min_discovered_notices=2,
            min_workbooks=1,
        )
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["listing_count"], 259)
        self.assertEqual(report["inspected_workbook_count"], 1)
        self.assertEqual(report["unique_sampling_number_count"], 1)

    def test_probe_fails_closed_on_non_official_notice_url(self) -> None:
        report = build_china_samr_probe_report(
            fetcher=lambda _: b"",
            listing_payload=listing_payload(),
            notice_urls=["https://example.com/notice"],
            min_discovered_notices=2,
        )
        self.assertEqual(report["status"], "failed")
        self.assertTrue(
            any("official HTTPS host" in error for error in report["blocking_errors"])
        )


if __name__ == "__main__":
    unittest.main()
