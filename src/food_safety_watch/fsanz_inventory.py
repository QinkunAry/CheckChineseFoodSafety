from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .fsanz import SITEMAP_URL, SOURCE_ID, extract_recall_urls
from .fsanz_smoke import fetch_official


Fetcher = Callable[[str], bytes]


def load_url_state(path: Path) -> list[str]:
    if not path.exists():
        return []
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("recall_urls"), list):
        raise ValueError(f"invalid FSANZ URL state: {path}")
    urls = value["recall_urls"]
    if not all(isinstance(url, str) for url in urls):
        raise ValueError(f"FSANZ URL state contains a non-string URL: {path}")
    return sorted(set(urls))


def build_inventory_report(
    sitemap_payload: bytes | str,
    previous_urls: list[str],
) -> dict[str, object]:
    current = set(extract_recall_urls(sitemap_payload))
    previous = set(previous_urls)
    new_urls = sorted(current - previous)
    removed_urls = sorted(previous - current)
    return {
        "status": "changed" if new_urls or removed_urls else "unchanged",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_id": SOURCE_ID,
        "sitemap_url": SITEMAP_URL,
        "baseline_count": len(previous),
        "current_count": len(current),
        "new_url_count": len(new_urls),
        "new_urls": new_urls,
        "removed_url_count": len(removed_urls),
        "removed_urls": removed_urls,
    }


def inventory_fsanz(
    *,
    state_path: Path,
    sitemap_path: Path | None = None,
    fetcher: Fetcher = fetch_official,
) -> tuple[dict[str, object], list[str]]:
    payload = sitemap_path.read_bytes() if sitemap_path else fetcher(SITEMAP_URL)
    current_urls = extract_recall_urls(payload)
    report = build_inventory_report(payload, load_url_state(state_path))
    return report, current_urls


def write_url_state(urls: list[str], path: Path) -> None:
    value = {
        "source_id": SOURCE_ID,
        "sitemap_url": SITEMAP_URL,
        "recall_urls": sorted(set(urls)),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
