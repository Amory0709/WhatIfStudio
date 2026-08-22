#!/usr/bin/env python3
"""Serve prototype/facefusion eval UI on :8766."""
from __future__ import annotations

import http.server
import socketserver
from pathlib import Path

PROTO = Path(__file__).resolve().parent
PORT = 8766


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PROTO), **kwargs)


def main() -> None:
    with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
        print(f"PROTOTYPE facefusion eval -> http://127.0.0.1:{PORT}/eval.html")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
