from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from food_safety_watch.cfs import ALERT_INDEX_URL, ALERT_PREFIX
from food_safety_watch.cfs_inventory import (
    build_inventory_report,
    collect_index_urls,
    load_url_state,
    write_url_state,
)


def index_page(*slugs: str) -> str:
    return "".join(f'<a href="/english/whatsnew/whatsnew_fa/{slug}.html">Alert</a>' for slug in slugs)


class CfsInventoryTests(unittest.TestCase):
    def test_inventory_reports_new_and_removed_urls(self) -> None:
        old = f"{ALERT_PREFIX}2025_001.html"
        kept = f"{ALERT_PREFIX}2025_002.html"
        new = f"{ALERT_PREFIX}2025_003.html"
        report = build_inventory_report(
            current_urls=[kept, new],
            previous_urls=[old, kept],
            index_urls=[ALERT_INDEX_URL],
        )
        self.assertEqual(report["status"], "changed")
        self.assertEqual(report["new_urls"], [new])
        self.assertEqual(report["removed_urls"], [old])

    def test_collect_index_urls_combines_year_pages(self) -> None:
        pages = {
            ALERT_INDEX_URL: index_page("2025_001", "2025_002"),
            f"{ALERT_PREFIX}whatsnew_fa_2026.html": index_page("2025_002", "2026_001"),
        }
        self.assertEqual(
            collect_index_urls(index_urls=list(pages), fetcher=lambda url: pages[url].encode()),
            [
                f"{ALERT_PREFIX}2025_001.html",
                f"{ALERT_PREFIX}2025_002.html",
                f"{ALERT_PREFIX}2026_001.html",
            ],
        )

    def test_state_round_trip_is_sorted_and_deduplicated(self) -> None:
        path = Path("unused-cfs-state.json")
        with patch.object(Path, "write_text") as write_text:
            write_url_state(
                [f"{ALERT_PREFIX}2025_002.html", f"{ALERT_PREFIX}2025_001.html"],
                path,
                index_urls=[ALERT_INDEX_URL],
            )
        raw = json.loads(write_text.call_args.args[0])
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "read_text", return_value=json.dumps(raw)),
        ):
            self.assertEqual(
                load_url_state(path),
                [f"{ALERT_PREFIX}2025_001.html", f"{ALERT_PREFIX}2025_002.html"],
            )
        self.assertEqual(raw["source_id"], "hk_cfs_alerts")

    def test_invalid_state_is_rejected(self) -> None:
        path = Path("unused-cfs-state.json")
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "read_text", return_value='{"alert_urls": "bad"}'),
        ):
            with self.assertRaisesRegex(ValueError, "invalid CFS URL state"):
                load_url_state(path)


if __name__ == "__main__":
    unittest.main()
