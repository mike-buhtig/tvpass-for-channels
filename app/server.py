from flask import Flask, Response, request, redirect, url_for
from pathlib import Path
import os
import shutil
from datetime import datetime, timezone

app = Flask(__name__)

DATA_DIR = Path("/data")
OUT_DIR = DATA_DIR / "out"
CFG_DIR = DATA_DIR / "config"

PLAYLIST = OUT_DIR / "playlist.m3u"
EPG = OUT_DIR / "epg.xml"

BASE_MAP = Path("/app/assets/group_map.base.csv")
WORKING_MAP = CFG_DIR / "group_map.csv"
ORIGINAL_MAP = CFG_DIR / "group_map.original.csv"
BAK_MAP = CFG_DIR / "group_map.bak.csv"

def utc_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")

def ensure_bootstrap() -> None:
    """
    NEVER overwrite WORKING_MAP on startup.
    Only create files if missing.
    """
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CFG_DIR.mkdir(parents=True, exist_ok=True)

    if BASE_MAP.exists():
        # Create ORIGINAL_MAP once (frozen baseline)
        if not ORIGINAL_MAP.exists():
            shutil.copyfile(BASE_MAP, ORIGINAL_MAP)

        # Create WORKING_MAP once (user-editable)
        if not WORKING_MAP.exists():
            shutil.copyfile(BASE_MAP, WORKING_MAP)
    else:
        # If base is missing, still allow app to run
        if not WORKING_MAP.exists():
            WORKING_MAP.write_text("tvg_id,display_name,group_title,group_id\n", encoding="utf-8")

@app.get("/")
def index():
    ensure_bootstrap()
    html = f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>tvpass-for-channels</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 24px; }}
      code {{ background: #f2f2f2; padding: 2px 6px; border-radius: 6px; }}
      .box {{ padding: 12px 14px; border: 1px solid #ddd; border-radius: 10px; margin-top: 14px; }}
      .warn {{ background: #fff6e6; border-color: #ffd28a; }}
      .btn {{ display:inline-block; padding:8px 12px; border-radius:8px; border:1px solid #ccc; text-decoration:none; color:#111; margin-right:8px; }}
      .btn:hover {{ background:#f7f7f7; }}
      .danger {{ border-color:#c55; }}
    </style>
  </head>
  <body>
    <h2>tvpass-for-channels</h2>
    <ul>
      <li><a href="/playlist.m3u">playlist.m3u</a></li>
      <li><a href="/epg.xml">epg.xml</a></li>
      <li><a href="/health">health</a></li>
    </ul>

    <div class="box">
      <h3>Sources / Attribution</h3>
      <ul>
        <li>Playlist upstream (default): <code>https://tvpass.org/playlist/m3u</code></li>
        <li>EPG upstream (default): <code>https://tvpass.org/epg.xml</code></li>
      </ul>
      <p><b>Discovery / context:</b> these upstream links were found referenced via <code>thetvapp.io</code>.
      This project does not claim ownership of upstream data or services.</p>
    </div>

    <div class="box">
      <h3>Group Map (CSV)</h3>
      <p>Working map (used for <code>group_id</code> injection): <code>{WORKING_MAP}</code></p>
      <a class="btn" href="/group-map.csv">Download current group_map.csv</a>
      <a class="btn" href="/group-map-original.csv">Download original (baseline)</a>
      <a class="btn" href="/group-map-bak.csv">Download last backup (.bak)</a>

      <div class="box" style="margin-top:12px;">
        <form action="/upload/group-map" method="post" enctype="multipart/form-data">
          <label><b>Upload replacement group_map.csv</b> (will create/update <code>group_map.bak.csv</code> first):</label><br><br>
          <input type="file" name="file" accept=".csv,text/csv" required>
          <button type="submit" class="btn">Upload</button>
        </form>
      </div>

      <div class="box warn" style="margin-top:12px;">
        <h4>Restore baseline (WARNING)</h4>
        <p>This will overwrite your current <code>group_map.csv</code> with the original baseline that shipped with the container.</p>
        <form action="/restore/group-map-original" method="post">
          <label>
            <input type="checkbox" name="confirm" value="yes">
            I understand this will overwrite my current group_map.csv
          </label><br><br>
          <button type="submit" class="btn danger">Restore Original Baseline</button>
        </form>
      </div>
    </div>
  </body>
</html>"""
    return Response(html, mimetype="text/html")

@app.get("/health")
def health():
    ensure_bootstrap()
    return {"status": "ok", "time_utc": utc_ts()}

@app.get("/playlist.m3u")
def playlist():
    ensure_bootstrap()
    if not PLAYLIST.exists():
        return Response("#EXTM3U\n", mimetype="audio/x-mpegurl")
    return Response(PLAYLIST.read_text(encoding="utf-8", errors="replace"), mimetype="audio/x-mpegurl")

@app.get("/epg.xml")
def epg():
    ensure_bootstrap()
    if not EPG.exists():
        return Response('<?xml version="1.0" encoding="UTF-8"?><tv></tv>', mimetype="application/xml")
    return Response(EPG.read_text(encoding="utf-8", errors="replace"), mimetype="application/xml")

@app.get("/group-map.csv")
def dl_group_map():
    ensure_bootstrap()
    if not WORKING_MAP.exists():
        return Response("tvg_id,display_name,group_title,group_id\n", mimetype="text/csv")
    return Response(WORKING_MAP.read_text(encoding="utf-8", errors="replace"), mimetype="text/csv")

@app.get("/group-map-original.csv")
def dl_group_map_original():
    ensure_bootstrap()
    if not ORIGINAL_MAP.exists():
        return Response("", status=404)
    return Response(ORIGINAL_MAP.read_text(encoding="utf-8", errors="replace"), mimetype="text/csv")

@app.get("/group-map-bak.csv")
def dl_group_map_bak():
    ensure_bootstrap()
    if not BAK_MAP.exists():
        return Response("", status=404)
    return Response(BAK_MAP.read_text(encoding="utf-8", errors="replace"), mimetype="text/csv")

def validate_csv_bytes(data: bytes) -> None:
    # minimal sanity checks
    if not data.strip():
        raise ValueError("Upload is empty")
    # decode as utf-8 (replace), then validate header contains tvg_id and group_id
    text = data.decode("utf-8", errors="replace")
    first_line = text.splitlines()[0].strip().lower()
    if "tvg_id" not in first_line or "group_id" not in first_line:
        raise ValueError("CSV header must include at least 'tvg_id' and 'group_id' columns")

@app.post("/upload/group-map")
def upload_group_map():
    ensure_bootstrap()
    f = request.files.get("file")
    if not f:
        return Response("No file uploaded", status=400)
    data = f.read()
    if len(data) > 2_000_000:
        return Response("File too large (max 2MB)", status=400)
    try:
        validate_csv_bytes(data)
    except Exception as e:
        return Response(f"Invalid CSV: {e}", status=400)

    # Backup current working map (if any) BEFORE replacing
    if WORKING_MAP.exists():
        shutil.copyfile(WORKING_MAP, BAK_MAP)

    # Atomic replace
    tmp = WORKING_MAP.with_suffix(".csv.tmp")
    tmp.write_bytes(data)
    os.replace(tmp, WORKING_MAP)

    return redirect(url_for("index"))

@app.post("/restore/group-map-original")
def restore_original():
    ensure_bootstrap()
    confirm = request.form.get("confirm", "")
    if confirm != "yes":
        return Response("Restore not confirmed (check the box).", status=400)

    if not ORIGINAL_MAP.exists():
        return Response("Original baseline is missing.", status=500)

    # Backup current before restore
    if WORKING_MAP.exists():
        shutil.copyfile(WORKING_MAP, BAK_MAP)

    shutil.copyfile(ORIGINAL_MAP, WORKING_MAP)
    return redirect(url_for("index"))

if __name__ == "__main__":
    ensure_bootstrap()
    app.run(host="0.0.0.0", port=8181, threaded=False, processes=1)
