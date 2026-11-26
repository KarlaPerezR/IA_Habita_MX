"""Servidor local de la interfaz Habita MX, sin dependencias web adicionales."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import re
import threading
import time
import os
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse
from pydantic import ValidationError
from habita.modelos import Perfil
from habita.motor import analizar_perfil, cargar_zonas, evaluar_zonas, evaluar_finanzas, integrar
from habita.catalogo import cargar_viviendas

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
OUTPUT = ROOT / "salidas"
PROFILE_STORE = ROOT / ".runtime" / "client_profiles.json"
PROFILE_LOCK = threading.Lock()
AGENT_LOCK = threading.Lock()

def load_local_env():
    path = ROOT / ".env.data"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line and not line.lstrip().startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())

load_local_env()

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
    profile = Perfil.model_validate(calculations["perfil"]["entrada"])
    zones = cargar_viviendas(profile)
    profile_data = analizar_perfil(profile)
    zone_data = evaluar_zonas(profile, zones)
    finance_data = evaluar_finanzas(profile, zones, profile_data)
    return {**integrar(profile, zone_data, finance_data), "perfil": profile_data["entrada"],
            "zonas": zone_data["zonas"], "finanzas": finance_data}

def analyze(profile_updates):
    current = dashboard()["perfil"]
    allowed = {"ingreso_mensual", "gastos_mensuales", "deudas_mensuales", "reserva_mensual", "presupuesto_maximo", "enganche_disponible", "ahorro_gastos_iniciales", "pago_maximo_usuario", "habitaciones_minimas", "traslado_maximo_min", "destino_nombre", "destino_latitud", "destino_longitud", "modo_traslado", "hora_salida", "seguridad_minima", "riesgos_minimo", "plazo_anios", "tasa_anual"}
    current.update({key: value for key, value in profile_updates.items() if key in allowed})
    profile = Perfil.model_validate(current)
    zones = cargar_viviendas(profile)
    from habita.aplicacion import configuracion, diagnosticar
    from habita.equipo import Bitacora, LLM, construir_crew
    import litellm
    metadata = diagnosticar()
    base, model = configuracion()
    litellm.register_model(model_cost={f"ollama_chat/{model}": {
        "supports_function_calling": True, "max_input_tokens": int(os.getenv("OLLAMA_NUM_CTX", "8192")),
        "max_output_tokens": 900, "litellm_provider": "ollama_chat", "mode": "chat"}})
    llm = LLM(model=f"ollama_chat/{model}", is_litellm=True, base_url=base, api_key="ollama",
              temperature=0, timeout=int(os.getenv("OLLAMA_TIMEOUT", "240")),
              num_ctx=int(os.getenv("OLLAMA_NUM_CTX", "8192")),
              context_window_size=int(os.getenv("OLLAMA_NUM_CTX", "8192")), max_tokens=900)
    run_dir = ROOT / ".runtime" / "web_agent_runs" / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    log = Bitacora(run_dir)
    started = time.perf_counter()
    with AGENT_LOCK:
        crew, state = construir_crew(profile, zones, llm, log)
        crew.kickoff()
    duration = round((time.perf_counter() - started) * 1000, 2)
    conclusions = {}
    for stage in ("perfil", "zonas", "finanzas", "coordinacion"):
        evidence = json.loads((run_dir / f"{stage}.json").read_text(encoding="utf-8"))
        conclusions[stage] = evidence["conclusion"]["resumen"]
    pipeline = [{"stage": stage, "label": label, "status": "completed", "agent": True}
                for stage, label in (("perfil", "Agente de perfil"), ("zonas", "Agente territorial"),
                                     ("finanzas", "Agente financiero"), ("coordinacion", "Agente coordinador"))]
    profile_data, zone_data, finance_data, coordination = (state[key] for key in ("perfil", "zonas", "finanzas", "coordinacion"))
    return {**coordination, "perfil": profile_data["entrada"], "zonas": zone_data["zonas"],
            "finanzas": finance_data, "pipeline": pipeline, "execution_mode": "crewai_ollama",
            "agent_conclusions": conclusions, "agent_run_id": run_dir.name,
            "model": metadata["modelo"], "duration_ms": duration}

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
        except Exception as error:
            response, status = {"error": "La ejecución de agentes no pudo completarse.", "detail": str(error)}, 500
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
