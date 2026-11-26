"""Descarga muestras oficiales y conserva respuesta raw, hash y manifiesto."""
from __future__ import annotations
import hashlib, json, os
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from verify_api_credentials import ROOT, load_env

RAW = ROOT / "datos" / "raw"

def fetch(name: str, url: str, headers: dict[str, str] | None = None) -> dict:
    request = Request(url, headers={"User-Agent": "HABIMAS-data-pipeline/1.0", **(headers or {})})
    with urlopen(request, timeout=30) as response:
        body = response.read()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = RAW / name / f"{stamp}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body)
    return {"fuente": name, "archivo": str(target.relative_to(ROOT)), "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body), "capturado_en": stamp}

def main() -> None:
    load_env(ROOT / ".env.data")
    banxico, inegi = os.environ["BANXICO_SIE_TOKEN"], os.environ["INEGI_INDICADORES_TOKEN"]
    runs = [
        fetch("banxico_tiie28", "https://www.banxico.org.mx/SieAPIRest/service/v1/series/SF60648/datos/oportuno", {"Bmx-Token": banxico}),
        fetch("inegi_poblacion_cdmx", f"https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml/INDICATOR/1002000001/es/09/true/BISE/2.0/{inegi}?type=json"),
    ]
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "manifest.json").write_text(json.dumps(runs, ensure_ascii=False, indent=2), encoding="utf-8")
    for run in runs: print(f"OK: {run['fuente']} ({run['bytes']} bytes)")

if __name__ == "__main__": main()
