"""Entrada común para terminal y Jupyter; persiste la evidencia de cada corrida."""
import hashlib
import json
import os
import platform
import time
import urllib.error
import urllib.request
from datetime import datetime
from importlib.metadata import version
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv
from .motor import cargar_perfil, cargar_zonas, calcular_todo

RAIZ = Path(__file__).resolve().parents[1]
load_dotenv(RAIZ / ".env")


def configuracion():
    base = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    parsed = urlparse(base)
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"} or parsed.scheme != "http":
        raise ValueError("Este prototipo solo permite Ollama local por HTTP en localhost.")
    return base, os.getenv("OLLAMA_MODEL", "llama3.2:latest")


def diagnosticar() -> dict:
    base, modelo = configuracion()
    try:
        # No usar proxy del sistema para las llamadas de diagnóstico a localhost.
        cliente = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with cliente.open(base + "/api/tags", timeout=10) as respuesta:
            modelos = json.load(respuesta)["models"]
        nombres = [m["name"] for m in modelos]
        nombre = modelo if ":" in modelo else modelo + ":latest"
        if nombre not in nombres:
            raise ValueError(f"No está instalado {nombre}. Ejecuta: ollama pull {modelo}")
        elegido = next(m for m in modelos if m["name"] == nombre)
        if "cloud" in nombre.lower() or elegido.get("remote_host") or elegido.get("remote_model"):
            raise ValueError("Usa un modelo descargado localmente, no un modelo cloud.")
        with cliente.open(base + "/api/version", timeout=10) as respuesta:
            servidor = json.load(respuesta)
        return {"base_url": base, "modelo": nombre, "digest": elegido.get("digest"),
                "detalles": elegido.get("details"), "ollama": servidor.get("version"),
                "python": platform.python_version(), "crewai": version("crewai")}
    except (urllib.error.URLError, TimeoutError) as error:
        raise RuntimeError("Ollama no responde. Abre Ollama o ejecuta 'ollama serve'; "
                           "después verifica con 'ollama list'.") from error


def reporte_markdown(resultado: dict) -> str:
    datos = resultado["resultado"]
    partes = ["# Habita MX - resultado", "", f"Modo: **{resultado['modo']}**. Datos de demostración simulados.", "",
              f"Capacidad mensual: **${datos['limite_pago']:,.2f} MXN**.", "",
              "| Posición | Zona | Puntaje / 100 | Pago total MXN | Pago en estrés MXN |",
              "|---|---|---:|---:|---:|"]
    for z in datos["ranking"]:
        partes.append(f"| {z['posicion']} | {z['id']} - {z['nombre']} | {z['puntaje']:.2f} | "
                      f"{z['pago_total']:,.2f} | {z['pago_estres']:,.2f} |")
    if not datos["ranking"]:
        partes.append("\nNo existen alternativas que cumplan todas las restricciones; no se relajan automáticamente.")
    partes += ["", "## Explicación del coordinador", "", resultado.get("conclusion", "Modo de cálculo sin intervención de agentes."),
               "", "## Alertas y descartes", ""]
    for z in datos["ranking"]:
        partes += [f"- {z['id']}: {a}." for a in z["alertas"]]
    partes += [f"- {z['id']}: {'; '.join(z['motivos'])}." for z in datos["descartadas"]]
    partes += ["", "## Alcance", ""] + [f"- {s}" for s in datos["limitaciones"]]
    return "\n".join(partes) + "\n"


def ejecutar(perfil_path=None, zonas_path=None, modo="crew", salida=None):
    if modo not in {"crew", "calculo"}:
        raise ValueError("Modo permitido: crew o calculo.")
    perfil_path = Path(perfil_path or RAIZ / "datos/perfil_demo.json").resolve()
    zonas_path = Path(zonas_path or RAIZ / "datos/zonas_demo.csv").resolve()
    perfil, zonas = cargar_perfil(perfil_path), cargar_zonas(zonas_path)
    carpeta = Path(salida or RAIZ / "salidas" / datetime.now().strftime("ejecucion_%Y%m%d_%H%M%S_%f"))
    carpeta.mkdir(parents=True, exist_ok=False)
    inicio = time.perf_counter()
    # Copias y hashes permiten repetir el caso incluso si luego se editan las entradas.
    for origen, destino in [(perfil_path, "entrada_perfil.json"), (zonas_path, "entrada_zonas.csv")]:
        (carpeta / destino).write_bytes(origen.read_bytes())
    metadatos = {"fecha_local": datetime.now().astimezone().isoformat(), "modo": modo,
                 "sha256_entradas": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (perfil_path, zonas_path)}}
    try:
        if modo == "calculo":
            estado = calcular_todo(perfil, zonas)
            conclusion = "Línea base determinista. No se ejecutó CrewAI ni se generaron conclusiones de agentes."
        else:
            metadatos.update(diagnosticar())
            from .equipo import Bitacora, LLM, construir_crew
            bitacora = Bitacora(carpeta)
            bitacora.registrar("inicio", configuracion=metadatos)
            base, modelo = configuracion()
            # LiteLLM usa la API nativa de Ollama y permite configurar num_ctx.
            import litellm
            litellm.register_model(model_cost={f"ollama_chat/{modelo}": {
                "supports_function_calling": True, "max_input_tokens": int(os.getenv("OLLAMA_NUM_CTX", "8192")),
                "max_output_tokens": 900, "litellm_provider": "ollama_chat", "mode": "chat"}})
            llm = LLM(model=f"ollama_chat/{modelo}", is_litellm=True, base_url=base, api_key="ollama",
                      temperature=0, timeout=int(os.getenv("OLLAMA_TIMEOUT", "240")),
                      num_ctx=int(os.getenv("OLLAMA_NUM_CTX", "8192")),
                      context_window_size=int(os.getenv("OLLAMA_NUM_CTX", "8192")), max_tokens=900)
            crew, estado = construir_crew(perfil, zonas, llm, bitacora)
            salida_crew = crew.kickoff()
            final = json.loads(salida_crew.raw)
            conclusion = final["conclusion"]["resumen"]
            bitacora.registrar("fin", recomendacion_id=estado["coordinacion"]["recomendacion_id"])
        metadatos["duracion_segundos"] = round(time.perf_counter() - inicio, 3)
        resultado = {**metadatos, "resultado": estado["coordinacion"], "conclusion": conclusion}
        (carpeta / "resultado.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
        (carpeta / "calculos.json").write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")
        (carpeta / "reporte.md").write_text(reporte_markdown(resultado), encoding="utf-8")
        return resultado, carpeta.resolve()
    except Exception as error:
        metadatos.update(error=str(error), duracion_segundos=round(time.perf_counter() - inicio, 3))
        (carpeta / "error.json").write_text(json.dumps(metadatos, ensure_ascii=False, indent=2), encoding="utf-8")
        # No sustituir silenciosamente la ejecución fallida por una respuesta simulada.
        raise

