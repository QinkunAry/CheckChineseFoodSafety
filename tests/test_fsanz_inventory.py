from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from food_safety_watch.fsanz import RECALL_PREFIX
from food_safety_watch.fsanz_inventory import (
    build_inventory_report,
    load_url_state,
    write_url_state,
)


def sitemap(*slugs: str) -> str:
    locations = "".join(f"<url><loc>{RECALL_PREFIX}{slug}</loc></url>" for slug in slugs)
    return (
        '<?xml version="1.0"?><urlset '
        'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{locations}</urlset>"
    )


class FsanzInventoryTests(unittest.TestCase):
    def test_inventory_reports_new_and_removed_urls(self) -> None:
        old = f"{RECALL_PREFIX}old"
        kept = f"{RECALL_PREFIX}kept"
        new = f"{RECALL_PREFIX}new"
        report = build_inventory_report(sitemap("kept", "new"), [old, kept])
        self.assertEqual(report["status"], "changed")
        self.assertEqual(report["new_urls"], [new])
        self.assertEqual(report["removed_urls"], [old])

    def test_inventory_is_unchanged_despite_order(self) -> None:
        urls = [f"{RECALL_PREFIX}a", f"{RECALL_PREFIX}b"]
        report = build_inventory_report(sitemap("b", "a"), urls)
        self.assertEqual(report["status"], "unchanged")
        self.assertEqual(report["new_url_count"], 0)

    def test_state_round_trip_is_sorted_and_deduplicated(self) -> None:
        path = Path("unused-state.json")
        with patch.object(Path, "write_text") as write_text:
            write_url_state(
                [f"{RECALL_PREFIX}b", f"{RECALL_PREFIX}a", f"{RECALL_PREFIX}b"],
                path,
            )
        raw = json.loads(write_text.call_args.args[0])
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "read_text", return_value=json.dumps(raw)),
        ):
            self.assertEqual(
                load_url_state(path),
                [f"{RECALL_PREFIX}a", f"{RECALL_PREFIX}b"],
            )
        self.assertEqual(raw["source_id"], "au_fsanz_recalls")

    def test_invalid_state_is_rejected(self) -> None:
        path = Path("unused-state.json")
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "read_text", return_value='{"recall_urls": "bad"}'),
        ):
            with self.assertRaisesRegex(ValueError, "invalid FSANZ URL state"):
                load_url_state(path)


if __name__ == "__main__":
    unittest.main()
