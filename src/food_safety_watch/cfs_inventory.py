from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .cfs import DEFAULT_INDEX_URLS, SOURCE_ID, extract_alert_urls
from .cfs_smoke import fetch_official


Fetcher = Callable[[str], bytes]


def load_url_state(path: Path) -> list[str]:
    if not path.exists():
        return []
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("alert_urls"), list):
        raise ValueError(f"invalid CFS URL state: {path}")
    urls = value["alert_urls"]
    if not all(isinstance(url, str) for url in urls):
        raise ValueError(f"CFS URL state contains a non-string URL: {path}")
    return sorted(set(urls))


def build_inventory_report(
    *,
    current_urls: list[str],
    previous_urls: list[str],
    index_urls: list[str],
) -> dict[str, Any]:
    current = set(current_urls)
    previous = set(previous_urls)
    new_urls = sorted(current - previous)
    removed_urls = sorted(previous - current)
    return {
        "status": "changed" if new_urls or removed_urls else "unchanged",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_id": SOURCE_ID,
        "index_urls": index_urls,
        "baseline_count": len(previous),
        "current_count": len(current),
        "new_url_count": len(new_urls),
        "new_urls": new_urls,
        "removed_url_count": len(removed_urls),
        "removed_urls": removed_urls,
    }


def collect_index_urls(
    *,
    index_urls: list[str],
    fetcher: Fetcher = fetch_official,
) -> list[str]:
    discovered: set[str] = set()
    for index_url in index_urls:
        discovered.update(extract_alert_urls(fetcher(index_url), index_url))
    return sorted(discovered)


def inventory_cfs(
    *,
    state_path: Path,
    index_urls: list[str] | None = None,
    fetcher: Fetcher = fetch_official,
) -> tuple[dict[str, Any], list[str]]:
    indexes = index_urls or DEFAULT_INDEX_URLS
    current_urls = collect_index_urls(index_urls=indexes, fetcher=fetcher)
    report = build_inventory_report(
        current_urls=current_urls,
        previous_urls=load_url_state(state_path),
        index_urls=indexes,
    )
    return report, current_urls


def write_url_state(urls: list[str], path: Path, *, index_urls: list[str] | None = None) -> None:
    value = {
        "source_id": SOURCE_ID,
        "index_urls": index_urls or DEFAULT_INDEX_URLS,
        "alert_urls": sorted(set(urls)),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
