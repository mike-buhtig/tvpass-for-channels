#!/usr/bin/env bash
set -euo pipefail
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="$BASE_DIR/data/out"
mkdir -p "$OUT_DIR"

EPG_URL="${EPG_URL:-https://tvpass.org/epg.xml}"
OUT_EPG="${OUT_EPG:-$OUT_DIR/epg.xml}"
LOG_FILE="${LOG_FILE:-$OUT_DIR/epg_update.log}"

IN_M3U="${IN_M3U:-$BASE_DIR/data/in/cable_channel_playlist.m3u}"
GROUP_MAP_CSV="${GROUP_MAP_CSV:-$BASE_DIR/data/in/cable_channel_playlist_group_id_template.csv}"
OUT_M3U="${OUT_M3U:-$OUT_DIR/playlist.m3u}"
DROP_LOG="${DROP_LOG:-$OUT_DIR/dropped_no_tvg_id.log}"

EPG_URL="$EPG_URL" OUT_EPG="$OUT_EPG" LOG_FILE="$LOG_FILE" python3 "$BASE_DIR/app/update_epg.py"
IN_M3U="$IN_M3U" GROUP_MAP_CSV="$GROUP_MAP_CSV" OUT_M3U="$OUT_M3U" DROP_LOG="$DROP_LOG" python3 "$BASE_DIR/app/update_playlist.py"
