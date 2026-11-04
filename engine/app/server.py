"""Local HTTP server for the web app: the page, reference data, quick requests, and background jobs.

Binds to 127.0.0.1 only: the app is for the person running it.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re

from . import api
from .jobs import Jobs

STATIC = Path(__file__).resolve().parent / "static"
MAX_BODY = 1 << 20
JOBS = Jobs({"fight": api.fight, "range": api.fight_range, "day": api.day, "rate": api.rate, "compare": api.compare, "optimize": api.optimize})
QUICK = {"/api/suggest": api.suggest, "/api/build": api.build_sheet, "/api/preset_day": api.preset_day,
         "/api/builder/options": api.builder_options, "/api/builder/preview": api.preview_build, "/api/builder/load": api.load_user_build}
CHANGES = {"/api/builder/save": api.save_build, "/api/builder/delete": api.delete_build}  # these change the build list
_META = None


def meta():
    global _META
    if _META is None: _META = api.meta()
    return _META


class Handler(BaseHTTPRequestHandler):
    server_version = "dnd-tools"

    def log_message(self, fmt, *args):  # quiet: the terminal shows only the start-up line and errors
        pass

    def send_json(self, data, status=200):
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY: raise ValueError("request too large")
        data = json.loads(self.rfile.read(length) or b"{}")
        if not isinstance(data, dict): raise ValueError("expected a JSON object")
        return data

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            body = (STATIC / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif path == "/api/meta": self.send_json(meta())
        elif path == "/api/jobs": self.send_json(JOBS.list())
        elif m := re.fullmatch(r"/api/jobs/(\d+)", path):
            job = JOBS.get(int(m[1]))
            since = int(re.search(r"since=(\d+)", self.path)[1]) if "since=" in self.path else 0
            self.send_json(job.view(since) if job else {"error": "no such job"}, 200 if job else 404)
        else: self.send_json({"error": "not found"}, 404)

    def do_POST(self):
        path = self.path.split("?")[0]
        try:
            req = self.read_json()
            if path in QUICK: self.send_json(QUICK[path](req))
            elif path in CHANGES:
                global _META
                result = CHANGES[path](req)
                _META = None  # the build lists in the page's reference data change
                self.send_json(result)
            elif m := re.fullmatch(r"/api/jobs/([a-z]+)", path): self.send_json(JOBS.start(m[1], req).view(), 202)
            else: self.send_json({"error": "not found"}, 404)
        except (ValueError, json.JSONDecodeError) as exc:
            self.send_json({"error": str(exc)}, 400)


def serve(port=8765, open_browser=True):
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"D&D combat simulator running at {url}  (Ctrl+C to stop)", flush=True)
    if open_browser:
        import webbrowser
        webbrowser.open(url)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
