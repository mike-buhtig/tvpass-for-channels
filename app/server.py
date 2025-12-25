from flask import Flask, Response
from pathlib import Path
from flask import Flask, Response

app = Flask(__name__)

OUT_DIR = Path("/data/out")
PLAYLIST = OUT_DIR / "playlist.m3u"
EPG = OUT_DIR / "epg.xml"

@app.get("/")
def index():
    html = """<!doctype html>
<html>
  <head><meta charset="utf-8"><title>tvpass-for-channels</title></head>
  <body style="font-family: Arial, sans-serif; margin: 24px;">
    <h2>tvpass-for-channels</h2>
    <ul>
      <li><a href="/playlist.m3u">playlist.m3u</a></li>
      <li><a href="/epg.xml">epg.xml</a></li>
      <li><a href="/health">health</a></li>
    </ul>
  </body>
</html>"""
    return Response(html, mimetype="text/html")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/playlist.m3u")
def playlist():
    if not PLAYLIST.exists():
        return Response("#EXTM3U\n", mimetype="audio/x-mpegurl")
    return Response(PLAYLIST.read_text(encoding="utf-8", errors="replace"), mimetype="audio/x-mpegurl")

@app.get("/epg.xml")
def epg():
    if not EPG.exists():
        return Response('<?xml version="1.0" encoding="UTF-8"?><tv></tv>', mimetype="application/xml")
    return Response(EPG.read_text(encoding="utf-8", errors="replace"), mimetype="application/xml")

if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    app.run(host="0.0.0.0", port=8181, threaded=False, processes=1)
