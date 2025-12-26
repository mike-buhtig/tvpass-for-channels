#!/usr/bin/env python3
from __future__ import annotations

import csv
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional

ATTR_RE = re.compile(r'(\w+(?:-\w+)*)="([^"]*)"')

def find_comma_outside_quotes(s: str) -> int:
    in_quotes = False
    for i, ch in enumerate(s):
        if ch == '"':
            in_quotes = not in_quotes
        elif ch == "," and not in_quotes:
            return i
    return -1

def parse_extinf(line: str) -> Tuple[Optional[Dict[str, str]], Optional[str], Optional[str]]:
    raw = line.rstrip("\r\n")
    if not raw.lstrip().startswith("#EXTINF"):
        return None, None, "Not EXTINF"
    idx = find_comma_outside_quotes(raw)
    if idx == -1:
        return None, None, "Missing comma delimiter"
    left = raw[:idx]
    right = raw[idx+1:]
    display = right.strip()
    if not display:
        return None, None, "Empty display name"
    attrs = {k: v for (k, v) in ATTR_RE.findall(left)}
    return attrs, display, None

def read_group_map(csv_path: Path) -> Dict[str, str]:
    """
    Expect columns: tvg_id, display_name, group_title, group_id
    Uses tvg_id as the key. Blank group_id rows are ignored.
    """
    mapping: Dict[str, str] = {}
    with csv_path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        rdr = csv.DictReader(f)
        if not rdr.fieldnames:
            raise ValueError("CSV has no header")
        if "tvg_id" not in rdr.fieldnames or "group_id" not in rdr.fieldnames:
            raise ValueError("CSV must have columns tvg_id and group_id")
        for row in rdr:
            tvg_id = (row.get("tvg_id") or "").strip()
            group_id = (row.get("group_id") or "").strip()
            if not tvg_id or not group_id:
                continue
            mapping[tvg_id] = group_id
    return mapping

def rebuild_extinf_with_group_id(original_line: str, attrs: Dict[str, str], group_id: str) -> str:
    # Split left/right reliably
    idx = find_comma_outside_quotes(original_line)
    left = original_line[:idx]
    right = original_line[idx:]  # includes comma
    # Remove any existing group_id=... (rare, but safe)
    left = re.sub(r'\s+group_id="[^"]*"', "", left)
    # Insert group_id before the comma (end of left)
    return f'{left} group_id="{group_id}"{right}'

def main() -> int:
    in_m3u = Path(os.environ.get("IN_M3U", "/data/in/cable_channel_playlist.m3u"))
    map_csv = Path(os.environ.get("GROUP_MAP_CSV", "/data/in/cable_channel_playlist_group_id_template.csv"))
    out_m3u = Path(os.environ.get("OUT_M3U", "/data/out/playlist.m3u"))
    drop_log = Path(os.environ.get("DROP_LOG", "/data/out/dropped_no_tvg_id.log"))

    if not in_m3u.exists():
        print(f"ERROR: missing input playlist: {in_m3u}", file=sys.stderr)
        return 2
    if not map_csv.exists():
        print(f"ERROR: missing mapping csv: {map_csv}", file=sys.stderr)
        return 2

    group_map = read_group_map(map_csv)

    lines = in_m3u.read_text(encoding="utf-8", errors="replace").splitlines(True)

    kept: List[str] = []
    dropped: List[str] = []

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.lstrip().startswith("#EXTINF"):
            url = lines[i+1] if i+1 < len(lines) else ""
            attrs, display, warn = parse_extinf(line)
            if warn or not attrs:
                # keep malformed entries but note them
                kept.append(line)
                if url:
                    kept.append(url)
                i += 2
                continue

            tvg_id = (attrs.get("tvg-id") or "").strip()
            if not tvg_id:
                # drop blank tvg-id entries (your 9 sports/event items)
                name = display or "(no name)"
                dropped.append(f"{name} -> {url.strip()}")
                i += 2
                continue

            group_id = group_map.get(tvg_id, "").strip()
            if group_id:
                kept.append(rebuild_extinf_with_group_id(line.rstrip("\n"), attrs, group_id) + "\n")
            else:
                kept.append(line)
            if url:
                kept.append(url)
            i += 2
            continue

        # Non-EXTINF lines (#EXTM3U etc.)
        kept.append(line)
        i += 1

    out_m3u.parent.mkdir(parents=True, exist_ok=True)
    out_m3u.write_text("".join(kept), encoding="utf-8")

    drop_log.parent.mkdir(parents=True, exist_ok=True)
    drop_log.write_text("\n".join(dropped) + ("\n" if dropped else ""), encoding="utf-8")

    print(f"Wrote: {out_m3u}")
    print(f"Dropped entries (blank tvg-id): {len(dropped)} -> {drop_log}")
    print(f"Mapped group_id injected for: {sum(1 for l in kept if ' group_id=' in l)} channels")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
