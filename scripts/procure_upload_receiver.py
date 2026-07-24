#!/usr/bin/env python3
"""Tiny upload receiver for browser-side fetch → POST after WAF clearance.

Run on the procure host, then from a cleared browser context:

    const b = await (await fetch(fileUrl)).arrayBuffer();
    await fetch('http://HOST:8765/upload?source_id=ID&name=file.pdf&url='+encodeURIComponent(fileUrl), {
      method: 'POST', body: b
    });

Files land in data/manual_inbox/_downloads/ ready for batch import.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

REPO = Path(__file__).resolve().parent.parent
DOWNLOADS = REPO / "data" / "manual_inbox" / "_downloads"
PORT = 8765


def _unwrap_multipart(body: bytes) -> bytes:
    """Extract the first file part payload from a multipart/form-data body."""
    # Boundary is the first line (e.g. ------WebKitFormBoundary...).
    first_nl = body.find(b"\r\n")
    if first_nl < 0:
        return body
    boundary = body[:first_nl]
    parts = body.split(boundary)
    for part in parts:
        if b"Content-Disposition:" not in part:
            continue
        # Headers end at blank line
        sep = part.find(b"\r\n\r\n")
        if sep < 0:
            continue
        payload = part[sep + 4 :]
        # Trim trailing CRLF and optional closing dashes leftover
        if payload.endswith(b"\r\n"):
            payload = payload[:-2]
        if payload.endswith(b"--"):
            payload = payload[:-2]
            if payload.endswith(b"\r\n"):
                payload = payload[:-2]
        if payload:
            return payload
    return body


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:  # quieter
        print(f"upload: {args[0] if args else fmt}", flush=True)

    def _cors(self) -> None:
        # Allow browser uploads from public HTTPS origins (Private Network Access).
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS, GET")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Private-Network", "true")

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:
        if self.path.startswith("/health"):
            body = b'{"ok":true}\n'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._cors()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/upload":
            self.send_error(404)
            return
        qs = parse_qs(parsed.query)
        source_id = (qs.get("source_id") or ["unknown"])[0]
        name = Path(unquote((qs.get("name") or ["download.bin"])[0])).name
        source_url = unquote((qs.get("url") or [""])[0])
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        ctype = (self.headers.get("Content-Type") or "").lower()
        # Browsers often POST FormData; unwrap the first file part. Prefer raw
        # ArrayBuffer bodies (see module docstring) when the client can send them.
        if "multipart/form-data" in ctype and body.startswith(b"----"):
            body = _unwrap_multipart(body)
        DOWNLOADS.mkdir(parents=True, exist_ok=True)
        # Prefer multi-file naming when name isn't already prefixed
        if not name.startswith(source_id):
            out_name = f"{source_id}__{name}"
        else:
            out_name = name
        path = DOWNLOADS / out_name
        path.write_bytes(body)
        if source_url:
            path.with_name(path.name + ".url").write_text(source_url + "\n", encoding="utf-8")
        meta = {"source_id": source_id, "path": str(path.relative_to(REPO)), "bytes": len(body), "url": source_url}
        resp = json.dumps(meta).encode() + b"\n"
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self._cors()
        self.send_header("Content-Length", str(len(resp)))
        self.end_headers()
        self.wfile.write(resp)
        print(f"saved {path} ({len(body)} bytes)", flush=True)


def main() -> None:
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"listening on 0.0.0.0:{PORT} → {DOWNLOADS}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
