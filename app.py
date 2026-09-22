from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import Supli
import state

ROOT = Path(__file__).resolve().parent
UI = ROOT / "UI" / "index.html"

class Handler(BaseHTTPRequestHandler):
    def send_json(self, data, status=200):
        raw = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type","application/json")
        self.send_header("Access-Control-Allow-Origin","*")
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Access-Control-Allow-Methods","GET,POST,OPTIONS")
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/platform":
            return self.send_json(Supli.get_platform_info())
        if self.path == "/api/providers":
            import ai_manager
            return self.send_json(ai_manager.get_provider_status())
        if self.path == "/api/approvals":
            return self.send_json(state.get_pending_approvals())
        if self.path == "/":
            data = UI.read_bytes()
            self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8")
            self.end_headers(); self.wfile.write(data); return
        self.send_error(404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length","0"))
        body = json.loads(self.rfile.read(length) or b"{}")
        if self.path == "/api/chat":
            try: return self.send_json({"response": Supli.run_agent(body.get("message",""))})
            except Exception as exc: return self.send_json({"error":str(exc)},500)
        if self.path == "/api/preview-file":
            p = body.get("path","")
            return self.send_json(Supli.read_file(p))
        self.send_error(404)

if __name__ == "__main__":
    print("Supli Milestone 8 recovery")
    print("UI: http://127.0.0.1:8080")
    ThreadingHTTPServer(("127.0.0.1",8080), Handler).serve_forever()
