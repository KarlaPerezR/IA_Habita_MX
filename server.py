"""Servidor local de la interfaz Habita MX, sin dependencias web adicionales."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
OUTPUT = ROOT / "salidas"

def dashboard():
    calculations = json.loads((OUTPUT / "calculos.json").read_text(encoding="utf-8"))
    result = json.loads((OUTPUT / "resultado.json").read_text(encoding="utf-8"))["resultado"]
    return {
        **result,
        "perfil": calculations["perfil"]["entrada"],
        "zonas": calculations["zonas"]["zonas"],
        "finanzas": calculations["finanzas"],
    }

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB, **kwargs)

    def do_GET(self):
        if self.path == "/api/dashboard":
            payload = json.dumps(dashboard(), ensure_ascii=False).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)
            return
        super().do_GET()

if __name__ == "__main__":
    print("Habita MX disponible en http://127.0.0.1:8000")
    ThreadingHTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
