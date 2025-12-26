#!/usr/bin/env python3
import os
import sys
import gzip
import time
from pathlib import Path
from datetime import datetime, timezone
import requests

def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    line = f"{ts} {msg}\n"
    lf = os.environ.get("LOG_FILE")
    if lf:
        Path(lf).parent.mkdir(parents=True, exist_ok=True)
        with open(lf, "a", encoding="utf-8") as f:
            f.write(line)
    sys.stdout.write(line)
    sys.stdout.flush()

def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)

def main() -> int:
    url = os.environ.get("EPG_URL", "https://tvpass.org/epg.xml")
    out_path = Path(os.environ.get("OUT_EPG", "/data/out/epg.xml"))

    timeout = float(os.environ.get("HTTP_TIMEOUT", "30"))
    ua = os.environ.get("USER_AGENT", "tvpass-for-channels/1.0 (+local)")
    retries = int(os.environ.get("RETRIES", "3"))
    backoff = float(os.environ.get("BACKOFF_SECONDS", "3"))

    headers = {"User-Agent": ua, "Accept": "*/*"}

    last_err = None
    for attempt in range(1, retries + 1):
        try:
            log(f"EPG download attempt {attempt}/{retries}: {url}")
            r = requests.get(url, headers=headers, timeout=timeout)
            r.raise_for_status()
            raw = r.content

            # Handle gzip if server sends compressed bytes without decoding
            if raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)

            # Basic sanity: must contain <tv ...> or <tv>
            if b"<tv" not in raw:
                raise ValueError("Downloaded content does not look like XMLTV (<tv> missing)")

            atomic_write(out_path, raw)
            log(f"Wrote EPG: {out_path} ({len(raw)} bytes)")
            return 0
        except Exception as e:
            last_err = e
            log(f"ERROR: {e}")
            if attempt < retries:
                time.sleep(backoff)

    log(f"FAILED after {retries} attempts: {last_err}")
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
