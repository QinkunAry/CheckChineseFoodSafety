from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from food_safety_watch.china_samr_inventory import (
    build_inventory_report,
    collect_samr_notices,
    listing_page_url,
    load_url_state,
    write_url_state,
)
from food_safety_watch.china_samr_probe import SamrNotice


PREFIX = "https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/spcjs/art/2026/"


def listing_page(total: int, page_number: int, *items: tuple[str, str]) -> bytes:
    rows = []
    for slug, title in items:
        rows.append(
            f'''<li><a href="{PREFIX}{slug}.html" title="{title}">{title}</a>
            <div>2026-06-{30 - page_number:02d}</div></li>'''
        )
    body = "".join(rows)
    page = (
        f'<div><ul>{body}</ul><div class="pagination" count="{total}" '
        f'pageNo="{page_number}"></div></div>'
    )
    return json.dumps({"success": True, "data": {"html": page}}).encode()


class ChinaSamrInventoryTests(unittest.TestCase):
    def test_listing_page_url_contains_encoded_page_parameters(self) -> None:
        query = parse_qs(urlparse(listing_page_url(3, page_size=99)).query)
        self.assertEqual(
            json.loads(query["paramJson"][0]),
            {"pageNo": 3, "pageSize": 99},
        )

    def test_collect_scans_all_pages_and_accepts_notice_wording(self) -> None:
        pages = {
            1: listing_page(
                4,
                1,
                ("one", "市场监管总局关于10批次食品抽检不合格情况的通告"),
                ("method", "市场监管总局关于食品检验方法的公告"),
            ),
            2: listing_page(
                4,
                2,
                ("two", "市场监管总局办公厅关于11批次食品抽检不合格情况的通报"),
                ("quarter", "2026年第一季度监督抽检情况通报"),
            ),
        }
        notices, diagnostics = collect_samr_notices(page_fetcher=pages.__getitem__)
        self.assertEqual({notice.url for notice in notices}, {f"{PREFIX}one.html", f"{PREFIX}two.html"})
        self.assertEqual(diagnostics["expected_page_count"], 2)
        self.assertEqual(diagnostics["scanned_listing_item_count"], 4)
        self.assertTrue(diagnostics["complete_scan"])

    def test_collect_can_limit_pages_for_diagnostics(self) -> None:
        first = listing_page(
            4,
            1,
            ("one", "市场监管总局关于10批次食品抽检不合格情况的通告"),
            ("method", "食品检验方法公告"),
        )
        notices, diagnostics = collect_samr_notices(
            page_fetcher=lambda _: first,
            max_pages=1,
        )
        self.assertEqual(len(notices), 1)
        self.assertFalse(diagnostics["complete_scan"])

    def test_collect_fails_when_full_scan_count_does_not_match(self) -> None:
        pages = {
            1: listing_page(
                3,
                1,
                ("one", "市场监管总局关于10批次食品抽检不合格情况的通告"),
                ("method", "食品检验方法公告"),
            ),
            2: listing_page(
                3,
                2,
                ("two", "市场监管总局关于11批次食品抽检不合格情况的通报"),
                ("extra", "额外公告"),
            ),
        }
        with self.assertRaisesRegex(ValueError, "item count mismatch"):
            collect_samr_notices(page_fetcher=pages.__getitem__)

    def test_inventory_report_tracks_new_and_removed_urls(self) -> None:
        report = build_inventory_report(
            current_urls=[f"{PREFIX}kept.html", f"{PREFIX}new.html"],
            previous_urls=[f"{PREFIX}old.html", f"{PREFIX}kept.html"],
            diagnostics={
                "reported_total_count": 2,
                "expected_page_count": 1,
                "scanned_page_count": 1,
                "scanned_listing_item_count": 2,
                "complete_scan": True,
            },
        )
        self.assertEqual(report["status"], "changed")
        self.assertEqual(report["new_urls"], [f"{PREFIX}new.html"])
        self.assertEqual(report["removed_urls"], [f"{PREFIX}old.html"])

    def test_state_round_trip_is_sorted_and_deduplicated(self) -> None:
        path = Path("unused-china-state.json")
        notices = [
            SamrNotice("two", f"{PREFIX}two.html"),
            SamrNotice("one", f"{PREFIX}one.html"),
            SamrNotice("duplicate", f"{PREFIX}two.html"),
        ]
        with patch.object(Path, "write_text") as write_text:
            write_url_state(notices, path)
        raw = json.loads(write_text.call_args.args[0])
        self.assertEqual(raw["notice_count"], 2)
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "read_text", return_value=json.dumps(raw)),
        ):
            self.assertEqual(
                load_url_state(path),
                [f"{PREFIX}one.html", f"{PREFIX}two.html"],
            )

    def test_invalid_state_is_rejected(self) -> None:
        path = Path("unused-china-state.json")
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "read_text", return_value='{"notice_urls":"bad"}'),
        ):
            with self.assertRaisesRegex(ValueError, "invalid China SAMR URL state"):
                load_url_state(path)


if __name__ == "__main__":
    unittest.main()
