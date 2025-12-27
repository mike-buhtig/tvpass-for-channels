#!/usr/bin/env python3
from __future__ import annotations

import csv
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import requests

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
    idx = find_comma_outside_quotes(original_line)
    left = original_line[:idx]
    right = original_line[idx:]  # includes comma
    left = re.sub(r'\s+group_id="[^"]*"', "", left)
    return f'{left} group_id="{group_id}"{right}'

def fetch_m3u(url: str) -> List[str]:
    timeout = float(os.environ.get("HTTP_TIMEOUT", "30"))
    ua = os.environ.get("USER_AGENT", "tvpass-for-channels/1.0 (+local)")
    retries = int(os.environ.get("RETRIES", "3"))
    backoff = float(os.environ.get("BACKOFF_SECONDS", "3"))

    headers = {"User-Agent": ua, "Accept": "*/*"}

    last_err: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            print(f"Playlist download attempt {attempt}/{retries}: {url}")
            r = requests.get(url, headers=headers, timeout=timeout)
            r.raise_for_status()
            text = r.text  # requests will decode content (incl gzip via headers)
            if "#EXTM3U" not in text:
                raise ValueError("Downloaded content does not look like M3U (#EXTM3U missing)")
            return text.splitlines(True)
        except Exception as e:
            last_err = e
            print(f"ERROR: {e}", file=sys.stderr)
            if attempt < retries:
                time.sleep(backoff)

    raise RuntimeError(f"FAILED after {retries} attempts: {last_err}")

def main() -> int:
    playlist_url = (os.environ.get("PLAYLIST_URL") or "").strip()

    in_m3u = Path(os.environ.get("IN_M3U", "/data/in/cable_channel_playlist.m3u"))
    map_csv = Path(os.environ.get("GROUP_MAP_CSV", "/data/in/cable_channel_playlist_group_id_template.csv"))
    out_m3u = Path(os.environ.get("OUT_M3U", "/data/out/playlist.m3u"))
    drop_log = Path(os.environ.get("DROP_LOG", "/data/out/dropped_no_tvg_id.log"))

    if not map_csv.exists():
        print(f"ERROR: missing mapping csv: {map_csv}", file=sys.stderr)
        return 2

    group_map = read_group_map(map_csv)

    # Source lines: URL preferred, fallback to local file
    if playlist_url:
        try:
            lines = fetch_m3u(playlist_url)
        except Exception as e:
            print(f"ERROR: could not download playlist from PLAYLIST_URL: {e}", file=sys.stderr)
            return 2
    else:
        if not in_m3u.exists():
            print(f"ERROR: missing input playlist: {in_m3u}", file=sys.stderr)
            return 2
        text = in_m3u.read_text(encoding="utf-8", errors="replace")
        if "#EXTM3U" not in text:
            print(f"ERROR: input playlist does not look like M3U (#EXTM3U missing): {in_m3u}", file=sys.stderr)
            return 2
        lines = text.splitlines(True)

    kept: List[str] = []
    dropped: List[str] = []

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.lstrip().startswith("#EXTINF"):
            url = lines[i+1] if i+1 < len(lines) else ""
            attrs, display, warn = parse_extinf(line)
            if warn or not attrs:
                kept.append(line)
                if url:
                    kept.append(url)
                i += 2
                continue

            tvg_id = (attrs.get("tvg-id") or "").strip()
            if not tvg_id:
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
