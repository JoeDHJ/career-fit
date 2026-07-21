from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .dictionary import extract
from .metrics import bundle_metrics


HTML = """<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'><title>SkillBundle</title><style>body{font-family:Inter,system-ui,sans-serif;max-width:980px;margin:32px auto;padding:0 18px;color:#182230;background:#f7f8fb}textarea{width:100%;height:150px;border:1px solid #ccd4e0;border-radius:10px;padding:12px;font-size:15px}button{margin:12px 0;padding:10px 16px;border:0;border-radius:8px;background:#2457d6;color:white;font-weight:600}pre{background:#172033;color:#edf2ff;padding:16px;border-radius:10px;overflow:auto}.muted{color:#66758c}</style></head><body><h1>SkillBundle</h1><p class='muted'>Explainable baseline extraction. Results are not formal human-reviewed annotations.</p><textarea id='text'>Build Python and SQL pipelines, communicate with customers, and manage AI projects.</textarea><br><button onclick='run()'>Extract</button><pre id='out'></pre><script>async function run(){const t=document.getElementById('text').value;const r=await fetch('/api/extract?text='+encodeURIComponent(t));document.getElementById('out').textContent=JSON.stringify(await r.json(),null,2)}run()</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/extract":
            text = parse_qs(parsed.query).get("text", [""])[0]
            items = extract(text)
            payload = {
                "text": text,
                "extractions": items,
                "metrics": bundle_metrics(items),
            }
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        body = HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def serve(host: str = "127.0.0.1", port: int = 8766):
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"SkillBundle running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
