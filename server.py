"""Servidor local de la interfaz Habita MX, sin dependencias web adicionales."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import re
import threading
import time
from datetime import datetime, timezone
from urllib.parse import urlparse
from pydantic import ValidationError
from habita.modelos import Perfil
from habita.motor import analizar_perfil, cargar_zonas, evaluar_zonas, evaluar_finanzas, integrar

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
OUTPUT = ROOT / "salidas"
PROFILE_STORE = ROOT / ".runtime" / "client_profiles.json"
PROFILE_LOCK = threading.Lock()

def profiles():
    if not PROFILE_STORE.exists():
        return []
    return json.loads(PROFILE_STORE.read_text(encoding="utf-8"))

def save_profile(client_id, name, profile):
    client_id, name = str(client_id).strip(), str(name).strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{2,40}", client_id):
        raise ValueError("El ID de cliente debe tener entre 2 y 40 caracteres: letras, números, guion o guion bajo.")
    if not 2 <= len(name) <= 100:
        raise ValueError("El nombre del cliente debe tener entre 2 y 100 caracteres.")
    record = {"client_id": client_id, "name": name, "profile": profile, "updated_at": datetime.now(timezone.utc).isoformat()}
    with PROFILE_LOCK:
        records = [item for item in profiles() if item["client_id"] != client_id]
        records.append(record)
        records.sort(key=lambda item: item["name"].casefold())
        PROFILE_STORE.parent.mkdir(parents=True, exist_ok=True)
        temporary = PROFILE_STORE.with_suffix(".tmp")
        temporary.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(PROFILE_STORE)
    return {key: record[key] for key in ("client_id", "name", "updated_at")}

def dashboard():
    calculations = json.loads((OUTPUT / "calculos.json").read_text(encoding="utf-8"))
    result = json.loads((OUTPUT / "resultado.json").read_text(encoding="utf-8"))["resultado"]
    return {
        **result,
        "perfil": calculations["perfil"]["entrada"],
        "zonas": calculations["zonas"]["zonas"],
        "finanzas": calculations["finanzas"],
    }

def analyze(profile_updates):
    current = dashboard()["perfil"]
    allowed = {"ingreso_mensual", "gastos_mensuales", "deudas_mensuales", "reserva_mensual", "presupuesto_maximo", "enganche_disponible", "ahorro_gastos_iniciales", "pago_maximo_usuario", "habitaciones_minimas", "traslado_maximo_min", "seguridad_minima", "riesgos_minimo", "plazo_anios", "tasa_anual"}
    current.update({key: value for key, value in profile_updates.items() if key in allowed})
    profile = Perfil.model_validate(current)
    zones = cargar_zonas(OUTPUT / "entrada_zonas.csv")
    pipeline = []

    def run(stage, label, operation):
        started = time.perf_counter()
        result = operation()
        pipeline.append({"stage": stage, "label": label, "status": "completed", "duration_ms": round((time.perf_counter() - started) * 1000, 2)})
        return result

    profile_data = run("perfil", "Perfil y capacidad", lambda: analizar_perfil(profile))
    zone_data = run("zonas", "Indicadores de zona", lambda: evaluar_zonas(profile, zones))
    finance_data = run("finanzas", "Escenarios financieros", lambda: evaluar_finanzas(profile, zones, profile_data))
    coordination = run("coordinacion", "Integración y ranking", lambda: integrar(profile, zone_data, finance_data))
    return {**coordination, "perfil": profile_data["entrada"], "zonas": zone_data["zonas"], "finanzas": finance_data, "pipeline": pipeline, "execution_mode": "deterministic"}

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB, **kwargs)

    def do_GET(self):
        path = urlparse(self.path).path
        if path in {"/api/dashboard", "/api/profiles"}:
            response = dashboard() if path == "/api/dashboard" else {"profiles": profiles()}
            payload = json.dumps(response, ensure_ascii=False).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)
            return
        super().do_GET()

    def do_POST(self):
        if self.path != "/api/analyze":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 100_000:
                raise ValueError("La solicitud está vacía o excede el tamaño permitido.")
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError("El perfil debe ser un objeto JSON.")
            response, status = analyze(body), 200
            response["client"] = save_profile(body.get("client_id", ""), body.get("client_name", ""), response["perfil"])
        except (ValueError, ValidationError, json.JSONDecodeError) as error:
            response, status = {"error": "Revisa los valores del perfil.", "detail": str(error)}, 400
        payload = json.dumps(response, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

if __name__ == "__main__":
    print("Habita MX disponible en http://127.0.0.1:8000")
    ThreadingHTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
