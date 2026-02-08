"""Minimal HTTP server for URI benchmarks.

Provides:
    GET  /status       -> {"status": "ok"}
    POST /data         -> echoes back the JSON body with {"received": <body>}
    GET  /health       -> 200 (used to check server is ready)

Usage:
    python server.py              # starts on port 9199
    python server.py --port 9200  # custom port
"""

import argparse
import json
from http.server import HTTPServer, BaseHTTPRequestHandler


class BenchHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/status" or self.path == "/health":
            self._json_response(200, {"status": "ok"})
        else:
            self._json_response(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/data":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else b""
            try:
                parsed = json.loads(body) if body else None
            except json.JSONDecodeError:
                parsed = body.decode(errors="replace")
            self._json_response(200, {"received": parsed})
        else:
            self._json_response(404, {"error": "not found"})

    def _json_response(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass  # silence request logging


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=9199)
    args = parser.parse_args()

    server = HTTPServer(("127.0.0.1", args.port), BenchHandler)
    print(f"Bench server listening on http://127.0.0.1:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()


if __name__ == "__main__":
    main()
