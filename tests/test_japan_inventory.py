from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from food_safety_watch.japan_inventory import (
    build_inventory_report,
    collect_caa_food_urls,
    load_url_state,
    merge_seen_urls,
    write_url_state,
)


DETAIL_PREFIX = "https://www.recall.caa.go.jp/result/detail.php?rcl="


def list_page(total: int, *rcls: str) -> bytes:
    rows = []
    start = 1
    end = len(rcls)
    for rcl in rcls:
        rows.append(
            f"""
            <tr>
              <td><p><a href="/result/detail.php?rcl={rcl}&screenkbn=01">商品 {rcl} - 回収</a></p></td>
              <td><span class="result_list_post_date">2026/06/24</span></td>
              <td><span class="result_list_start_date">2026/06/22</span></td>
            </tr>
            """
        )
    return f"<p>{total}件中　{start}-{end}件を表示中</p>{''.join(rows)}".encode()


class JapanInventoryTests(unittest.TestCase):
    def test_seen_url_state_is_append_only_when_current_list_rolls(self) -> None:
        self.assertEqual(
            merge_seen_urls(["old", "shared"], ["shared", "new"]),
            ["new", "old", "shared"],
        )

    def test_collect_caa_food_urls_scans_all_expected_pages(self) -> None:
        pages = {
            0: list_page(4, "00000000001", "00000000002"),
            1: list_page(4, "00000000003", "00000000004"),
        }
        urls, diagnostics = collect_caa_food_urls(page_fetcher=lambda page: pages[page])
        self.assertEqual(
            urls,
            [
                f"{DETAIL_PREFIX}00000000001&screenkbn=01",
                f"{DETAIL_PREFIX}00000000002&screenkbn=01",
                f"{DETAIL_PREFIX}00000000003&screenkbn=01",
                f"{DETAIL_PREFIX}00000000004&screenkbn=01",
            ],
        )
        self.assertEqual(diagnostics["reported_total_count"], 4)
        self.assertEqual(diagnostics["expected_page_count"], 2)
        self.assertEqual(diagnostics["scanned_page_count"], 2)

    def test_collect_caa_food_urls_can_be_limited_for_diagnostics(self) -> None:
        pages = {
            0: list_page(4, "00000000001", "00000000002"),
            1: list_page(4, "00000000003", "00000000004"),
        }
        urls, diagnostics = collect_caa_food_urls(
            page_fetcher=lambda page: pages[page],
            max_pages=1,
        )
        self.assertEqual(len(urls), 2)
        self.assertEqual(diagnostics["expected_page_count"], 2)
        self.assertEqual(diagnostics["scanned_page_count"], 1)

    def test_inventory_report_reports_new_and_removed_urls(self) -> None:
        old = f"{DETAIL_PREFIX}00000000000&screenkbn=01"
        kept = f"{DETAIL_PREFIX}00000000001&screenkbn=01"
        new = f"{DETAIL_PREFIX}00000000002&screenkbn=01"
        report = build_inventory_report(
            current_urls=[kept, new],
            previous_urls=[old, kept],
            diagnostics={
                "reported_total_count": 2,
                "expected_page_count": 1,
                "scanned_page_count": 1,
                "warnings": [],
            },
        )
        self.assertEqual(report["status"], "changed")
        self.assertEqual(report["new_urls"], [new])
        self.assertEqual(report["removed_urls"], [old])

    def test_state_round_trip_is_sorted_and_deduplicated(self) -> None:
        path = Path("unused-japan-state.json")
        with patch.object(Path, "write_text") as write_text:
            write_url_state(
                [
                    f"{DETAIL_PREFIX}00000000002&screenkbn=01",
                    f"{DETAIL_PREFIX}00000000001&screenkbn=01",
                    f"{DETAIL_PREFIX}00000000002&screenkbn=01",
                ],
                path,
            )
        raw = json.loads(write_text.call_args.args[0])
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "read_text", return_value=json.dumps(raw)),
        ):
            self.assertEqual(
                load_url_state(path),
                [
                    f"{DETAIL_PREFIX}00000000001&screenkbn=01",
                    f"{DETAIL_PREFIX}00000000002&screenkbn=01",
                ],
            )
        self.assertEqual(raw["source_id"], "jp_caa_recalls")

    def test_invalid_state_is_rejected(self) -> None:
        path = Path("unused-japan-state.json")
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "read_text", return_value='{"recall_urls": "bad"}'),
        ):
            with self.assertRaisesRegex(ValueError, "invalid Japan CAA URL state"):
                load_url_state(path)


if __name__ == "__main__":
    unittest.main()
