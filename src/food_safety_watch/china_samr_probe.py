from __future__ import annotations

import html
import io
import json
import re
import shutil
import subprocess
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any, Callable
from urllib.parse import quote, urlencode, urljoin, urlparse
from xml.etree import ElementTree


SOURCE_ID = "cn_samr_sampling"
AUTHORITY = "State Administration for Market Regulation"
SAMR_HOST = "www.samr.gov.cn"
LIST_PAGE_URL = "https://www.samr.gov.cn/spcjs/xxfb/index.html"
LIST_ENDPOINT = (
    "https://www.samr.gov.cn/api-gateway/jpaas-publish-server/front/page/build/unit"
)
QUERY_SYSTEM_URL = "https://spcjsac.gsxt.gov.cn/"
USER_AGENT = (
    "FoodSafetyWatch/0.1 "
    "(+https://github.com/QinkunAry/CheckChineseFoodSafety)"
)
LIST_QUERY = {
    "parseType": "bulidstatic",
    "webId": "29e9522dc89d4e088a953d8cede72f4c",
    "tplSetId": "5c30fb89ae5e48b9aefe3cdf49853830",
    "pageType": "column",
    "tagId": "ajax分页",
    "editType": "null",
    "pageId": "6695899db9f8455187259c43b72d2e1c",
}
LIST_URL = f"{LIST_ENDPOINT}?{urlencode(LIST_QUERY)}"

CORE_HEADERS = {
    "标称生产企业名称",
    "被抽样单位名称",
    "样品名称",
    "不合格项目",
    "检验值",
    "标准值",
    "食品细类",
    "抽样编号",
}
INSPECTION_NOTICE_RE = re.compile(
    r"\d+批次食品抽检不合格情况的(?:通报|通告)"
)

Fetcher = Callable[[str], bytes]


class SamrFetchError(RuntimeError):
    pass


@dataclass(frozen=True)
class SamrNotice:
    title: str
    url: str
    published_date: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "title": self.title,
            "url": self.url,
            "published_date": self.published_date,
        }


def _clean_text(value: str) -> str:
    value = re.sub(r"(?is)<script\b.*?</script>", " ", value)
    value = re.sub(r"(?is)<style\b.*?</style>", " ", value)
    value = re.sub(r"(?s)<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != SAMR_HOST:
        raise ValueError("SAMR probe requests are restricted to the official HTTPS host")


def _normalize_url(url: str) -> str:
    return quote(url, safe=":/?&=%+#")


def fetch_official(url: str, *, timeout: int = 90) -> bytes:
    _validate_url(url)
    curl = shutil.which("curl")
    if not curl:
        raise SamrFetchError("curl is required for SAMR requests")
    command = [
        curl,
        "-L",
        "--fail",
        "--silent",
        "--show-error",
        "--ipv4",
        "--http1.1",
        "--retry",
        "3",
        "--retry-all-errors",
        "--connect-timeout",
        "20",
        "--max-time",
        str(timeout),
        "--user-agent",
        USER_AGENT,
        "--referer",
        LIST_PAGE_URL,
        url,
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True)
    except subprocess.CalledProcessError as error:
        detail = error.stderr.decode("utf-8", errors="replace").strip()
        raise SamrFetchError(f"SAMR request failed for {url}: {detail or error}") from error
    if not result.stdout:
        raise SamrFetchError(f"SAMR returned an empty response for {url}")
    return result.stdout


def parse_listing_response(payload: bytes | str) -> tuple[int, list[SamrNotice]]:
    text = payload.decode("utf-8-sig") if isinstance(payload, bytes) else payload
    value = json.loads(text)
    if not isinstance(value, dict) or not value.get("success"):
        raise ValueError("SAMR listing endpoint did not return a successful object")
    listing_html = ((value.get("data") or {}).get("html"))
    if not isinstance(listing_html, str) or not listing_html.strip():
        raise ValueError("SAMR listing response does not contain HTML")

    count_match = re.search(r'\bcount="(?P<count>\d+)"', listing_html)
    if not count_match:
        raise ValueError("SAMR listing response does not contain a total count")

    notices: list[SamrNotice] = []
    seen: set[str] = set()
    item_re = re.compile(
        r"<li\b[^>]*>(?P<body>.*?)</li>",
        re.IGNORECASE | re.DOTALL,
    )
    anchor_re = re.compile(
        r'<a\b[^>]*href="(?P<href>[^"]+)"[^>]*title="(?P<title>[^"]*)"[^>]*>'
        r"(?P<body>.*?)</a>",
        re.IGNORECASE | re.DOTALL,
    )
    date_re = re.compile(r"\b(?P<date>20\d{2}-\d{2}-\d{2})\b")
    for item_match in item_re.finditer(listing_html):
        item = item_match.group("body")
        anchor_match = anchor_re.search(item)
        if not anchor_match:
            continue
        title = _clean_text(anchor_match.group("title") or anchor_match.group("body"))
        if not INSPECTION_NOTICE_RE.search(title):
            continue
        url = _normalize_url(
            urljoin(LIST_PAGE_URL, html.unescape(anchor_match.group("href")))
        )
        _validate_url(url)
        if url in seen:
            continue
        date_match = date_re.search(item)
        notices.append(
            SamrNotice(
                title=title,
                url=url,
                published_date=date_match.group("date") if date_match else None,
            )
        )
        seen.add(url)
    return int(count_match.group("count")), notices


def parse_notice_page(payload: bytes | str, *, url: str) -> dict[str, Any]:
    _validate_url(url)
    text = payload.decode("utf-8", errors="replace") if isinstance(payload, bytes) else payload
    visible_text = _clean_text(text)
    title_match = re.search(
        r"市场监管总局[^。]{0,30}?关于\d+批次食品抽检不合格情况的(?:通报|通告)",
        visible_text,
    )
    if not title_match:
        raise ValueError("SAMR page is not a batch food-inspection notice")
    batch_match = re.search(r"检出\s*(\d+)\s*批次样品不合格", visible_text)
    date_match = re.search(r"发布时间[：:]\s*(20\d{2}-\d{2}-\d{2})", visible_text)

    attachments: list[dict[str, str]] = []
    seen: set[str] = set()
    anchor_re = re.compile(
        r'<a\b[^>]*href="(?P<href>[^"]+)"[^>]*>(?P<body>.*?)</a>',
        re.IGNORECASE | re.DOTALL,
    )
    for match in anchor_re.finditer(text):
        href = html.unescape(match.group("href")).strip()
        label = _clean_text(match.group("body"))
        absolute = _normalize_url(urljoin(url, href))
        parsed = urlparse(absolute)
        suffix = PurePosixPath(parsed.path).suffix.lower()
        if suffix not in {".xlsx", ".zip"}:
            continue
        _validate_url(absolute)
        if absolute in seen:
            continue
        attachments.append({"label": label, "url": absolute, "type": suffix[1:]})
        seen.add(absolute)
    return {
        "title": title_match.group(0),
        "url": url,
        "published_date": date_match.group(1) if date_match else None,
        "declared_noncompliant_batch_count": int(batch_match.group(1)) if batch_match else None,
        "attachments": attachments,
    }


def _xlsx_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    return ["".join(node.text or "" for node in item.iter() if node.tag.endswith("}t")) for item in root]


def _column_index(reference: str) -> int:
    match = re.match(r"([A-Z]+)", reference.upper())
    if not match:
        raise ValueError(f"invalid XLSX cell reference: {reference}")
    value = 0
    for character in match.group(1):
        value = value * 26 + ord(character) - ord("A") + 1
    return value - 1


def _xlsx_rows(payload: bytes) -> list[list[str]]:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = archive.namelist()
        if "xl/worksheets/sheet1.xml" not in names:
            raise ValueError("XLSX does not contain xl/worksheets/sheet1.xml")
        shared = _xlsx_shared_strings(archive)
        root = ElementTree.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        rows: list[list[str]] = []
        for row in (node for node in root.iter() if node.tag.endswith("}row")):
            values: dict[int, str] = {}
            for cell in (node for node in row if node.tag.endswith("}c")):
                reference = cell.attrib.get("r", "")
                index = _column_index(reference)
                cell_type = cell.attrib.get("t")
                value_node = next((node for node in cell if node.tag.endswith("}v")), None)
                if cell_type == "inlineStr":
                    value = "".join(
                        node.text or "" for node in cell.iter() if node.tag.endswith("}t")
                    )
                else:
                    raw = value_node.text if value_node is not None and value_node.text else ""
                    if cell_type == "s" and raw:
                        value = shared[int(raw)]
                    else:
                        value = raw
                values[index] = re.sub(r"\s+", "", value).strip()
            if values:
                width = max(values) + 1
                rows.append([values.get(index, "") for index in range(width)])
        return rows


def inspect_xlsx(payload: bytes, *, filename: str) -> dict[str, Any]:
    rows = _xlsx_rows(payload)
    header_index = None
    headers: list[str] = []
    for index, row in enumerate(rows[:12]):
        if len(CORE_HEADERS.intersection(row)) >= 4:
            header_index = index
            headers = row
            break
    if header_index is None:
        raise ValueError(f"{filename} does not contain a recognizable SAMR header row")
    missing = sorted(CORE_HEADERS - set(headers))
    data_rows = [row for row in rows[header_index + 1 :] if any(row)]
    sample_id_index = headers.index("抽样编号") if "抽样编号" in headers else None
    sample_ids = {
        row[sample_id_index]
        for row in data_rows
        if sample_id_index is not None
        and sample_id_index < len(row)
        and row[sample_id_index]
    }
    return {
        "filename": filename,
        "status": "passed" if not missing else "failed",
        "header_row": header_index + 1,
        "column_count": len(headers),
        "headers": headers,
        "missing_core_headers": missing,
        "data_row_count": len(data_rows),
        "unique_sampling_number_count": len(sample_ids),
    }


def inspect_attachment(payload: bytes, *, filename: str) -> list[dict[str, Any]]:
    suffix = PurePosixPath(filename).suffix.lower()
    if suffix == ".xlsx":
        return [inspect_xlsx(payload, filename=filename)]
    if suffix != ".zip":
        raise ValueError(f"unsupported SAMR attachment type: {filename}")
    results: list[dict[str, Any]] = []
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        workbook_names = [name for name in archive.namelist() if name.lower().endswith(".xlsx")]
        if not workbook_names:
            raise ValueError(f"{filename} does not contain XLSX workbooks")
        for name in workbook_names:
            results.append(inspect_xlsx(archive.read(name), filename=name))
    return results


def build_china_samr_probe_report(
    *,
    fetcher: Fetcher = fetch_official,
    listing_payload: bytes | None = None,
    notice_urls: list[str] | None = None,
    max_notices: int = 1,
    max_attachments: int = 2,
    min_listing_count: int = 100,
    min_discovered_notices: int = 2,
    min_workbooks: int = 1,
) -> dict[str, Any]:
    if max_notices < 1 or max_attachments < 1:
        raise ValueError("max_notices and max_attachments must be at least 1")
    if min_listing_count < 0 or min_discovered_notices < 0 or min_workbooks < 0:
        raise ValueError("minimum gates must not be negative")

    generated_at = datetime.now(timezone.utc).isoformat()
    blocking_errors: list[str] = []
    try:
        payload = listing_payload if listing_payload is not None else fetcher(LIST_URL)
        listing_count, discovered = parse_listing_response(payload)
    except Exception as error:
        return {
            "status": "failed",
            "generated_at": generated_at,
            "source_id": SOURCE_ID,
            "list_page_url": LIST_PAGE_URL,
            "list_endpoint": LIST_ENDPOINT,
            "query_system_url": QUERY_SYSTEM_URL,
            "listing_count": 0,
            "discovered_notice_count": 0,
            "inspected_workbook_count": 0,
            "notice_results": [],
            "blocking_errors": [
                f"listing fetch/parse failed: {type(error).__name__}: {error}"
            ],
        }

    if listing_count < min_listing_count:
        blocking_errors.append(
            f"listing count {listing_count} below minimum {min_listing_count}"
        )
    if len(discovered) < min_discovered_notices:
        blocking_errors.append(
            f"discovered inspection notice count {len(discovered)} below minimum "
            f"{min_discovered_notices}"
        )

    targets = notice_urls or [notice.url for notice in discovered[:max_notices]]
    notice_results: list[dict[str, Any]] = []
    workbooks: list[dict[str, Any]] = []
    for notice_url in targets[:max_notices]:
        try:
            notice = parse_notice_page(fetcher(notice_url), url=notice_url)
            attachments = notice["attachments"][:max_attachments]
            if not attachments:
                raise ValueError("notice does not expose an XLSX or ZIP attachment")
            attachment_results: list[dict[str, Any]] = []
            for attachment in attachments:
                attachment_workbooks = inspect_attachment(
                    fetcher(attachment["url"]),
                    filename=PurePosixPath(urlparse(attachment["url"]).path).name,
                )
                attachment_results.append(
                    {
                        **attachment,
                        "workbook_count": len(attachment_workbooks),
                        "workbooks": attachment_workbooks,
                    }
                )
                workbooks.extend(attachment_workbooks)
            notice_results.append({**notice, "status": "passed", "attachments": attachment_results})
        except Exception as error:
            blocking_errors.append(
                f"notice fetch/parse failed: {notice_url}: {type(error).__name__}: {error}"
            )
            notice_results.append(
                {
                    "url": notice_url,
                    "status": "error",
                    "error": f"{type(error).__name__}: {error}",
                }
            )

    failed_workbooks = [item["filename"] for item in workbooks if item["status"] != "passed"]
    if len(workbooks) < min_workbooks:
        blocking_errors.append(
            f"inspected workbook count {len(workbooks)} below minimum {min_workbooks}"
        )
    if failed_workbooks:
        blocking_errors.append(
            f"workbooks missing core headers: {', '.join(failed_workbooks[:5])}"
        )

    return {
        "status": "failed" if blocking_errors else "passed",
        "generated_at": generated_at,
        "source_id": SOURCE_ID,
        "authority": AUTHORITY,
        "list_page_url": LIST_PAGE_URL,
        "list_endpoint": LIST_ENDPOINT,
        "query_system_url": QUERY_SYSTEM_URL,
        "listing_count": listing_count,
        "minimum_listing_count": min_listing_count,
        "discovered_notice_count": len(discovered),
        "minimum_discovered_notices": min_discovered_notices,
        "discovered_notice_samples": [item.to_dict() for item in discovered[:5]],
        "tested_notice_count": len(notice_results),
        "inspected_workbook_count": len(workbooks),
        "minimum_workbook_count": min_workbooks,
        "workbook_data_row_count": sum(item["data_row_count"] for item in workbooks),
        "unique_sampling_number_count": sum(
            item["unique_sampling_number_count"] for item in workbooks
        ),
        "notice_results": notice_results,
        "blocking_errors": blocking_errors,
        "warnings": [
            "The public product-result query requires a slider challenge; this probe uses "
            "the official announcement index and attachments instead."
        ],
    }
