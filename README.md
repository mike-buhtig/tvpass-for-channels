# tvpass-for-channels

A small “for Channels”-style helper that serves:

- `http://<host>:8181/playlist.m3u`
- `http://<host>:8181/epg.xml`

It periodically fetches an upstream playlist + EPG, then injects a `group_id="..."` attribute into playlist entries using a user-editable CSV mapping file.

## What it does (high level)

- Downloads EPG XMLTV from an upstream URL (default: `https://tvpass.org/epg.xml`)
- Downloads M3U playlist from an upstream URL (default: `https://tvpass.org/playlist/m3u`)
- Injects `group_id="..."` into `#EXTINF` lines based on `group_map.csv`
- Serves the resulting files over HTTP on port **8181**

## Sources / attribution (important)

- **Upstream endpoints used by default**:
  - Playlist: `https://tvpass.org/playlist/m3u`
  - EPG: `https://tvpass.org/epg.xml`

- **Discovery / context**: these upstream links were discovered referenced via **thetvapp.io**.  
  This project does not claim ownership of upstream data or services.

This container is intended to serve playlist/EPG data locally for personal IPTV setups. It does not host or relay video streams itself.

## Web UI

Open:

- `http://<host>:8181/`

You can download/upload the group map CSV from the UI:

- Download current: `/group-map.csv`
- Download baseline: `/group-map-original.csv`
- Download last backup: `/group-map-bak.csv`
- Upload replacement: (UI form)
- Restore baseline: (UI button with confirmation)

### Group map files

The container maintains:

- `/data/config/group_map.csv` (working map, used for injection)
- `/data/config/group_map.original.csv` (baseline shipped with image)
- `/data/config/group_map.bak.csv` (backup created right before changes)

## Docker run (example)

Use a persistent volume so your `group_map.csv` and outputs survive container updates:

```bash
docker run -d --name tvpass-for-channels --restart unless-stopped \
  -p 8181:8181 \
  -v tvpass_data:/data \
  tvpass-for-channels:prod
