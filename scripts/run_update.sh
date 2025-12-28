#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="${OUT_DIR:-/data/out}"
CFG_DIR="${CFG_DIR:-/data/config}"
mkdir -p "$OUT_DIR" "$CFG_DIR"

# Upstreams
EPG_URL="${EPG_URL:-https://tvpass.org/epg.xml}"
PLAYLIST_URL="${PLAYLIST_URL:-https://tvpass.org/playlist/m3u}"

# Outputs
OUT_EPG="${OUT_EPG:-$OUT_DIR/epg.xml}"
OUT_M3U="${OUT_M3U:-$OUT_DIR/playlist.m3u}"
DROP_LOG="${DROP_LOG:-$OUT_DIR/dropped_no_tvg_id.log}"
LOG_FILE="${LOG_FILE:-$OUT_DIR/epg_update.log}"

# Group map (persisted in /data/config)
GROUP_MAP_CSV="${GROUP_MAP_CSV:-$CFG_DIR/group_map.csv}"

EPG_URL="$EPG_URL" OUT_EPG="$OUT_EPG" LOG_FILE="$LOG_FILE" python3 /app/update_epg.py
IN_M3U_URL="$PLAYLIST_URL" GROUP_MAP_CSV="$GROUP_MAP_CSV" OUT_M3U="$OUT_M3U" DROP_LOG="$DROP_LOG" python3 /app/update_playlist.py
