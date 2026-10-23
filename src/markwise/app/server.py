"""A local HTTP bridge to the same Api the app window uses: for developing the interface in a browser.

It listens on 127.0.0.1 only and answers only requests that carry the header X-Markwise and name a local host,
so that a web page open in a browser cannot call it (the custom header forces a CORS preflight, which this
server never grants, and the host check stops DNS rebinding).
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .api import Api

LOCAL_HOSTS = ("127.0.0.1", "localhost")


def _methods(api: Api) -> dict:
    return {name: getattr(api, name) for name in dir(api) if not name.startswith("_") and callable(getattr(api, name))}


def make_handler(api: Api):
    methods = _methods(api)

    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, body: dict) -> None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self) -> None:  # noqa: N802 (name given by http.server)
            host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
            if host not in LOCAL_HOSTS or self.headers.get("X-Markwise") != "1":
                self._send(403, {"error": "forbidden"})
                return
            if not self.path.startswith("/api/") or self.path[5:] not in methods:
                self._send(404, {"error": f"unknown method {self.path[5:]!r}"})
                return
            length = int(self.headers.get("Content-Length") or 0)
            try:
                payload = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                self._send(400, {"error": "the body is not JSON"})
                return
            self._send(200, methods[self.path[5:]](*payload.get("args", [])))

        def log_message(self, format, *args) -> None:  # noqa: A002
            pass  # keep the terminal quiet; errors reach the interface as answers

    return Handler


def serve(port: int = 8765) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(Api()))
    print(f"Markwise core on http://127.0.0.1:{port}/api/ (local only). Stop with Ctrl+C.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
