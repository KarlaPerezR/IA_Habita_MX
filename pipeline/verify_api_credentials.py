"""Comprueba credenciales oficiales sin mostrar sus valores ni persistir respuestas."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def get_json(url: str, headers: dict[str, str] | None = None) -> object:
    request = Request(url, headers={"User-Agent": "HABIMAS-data-pipeline/1.0", **(headers or {})})
    with urlopen(request, timeout=25) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}")
        return json.loads(response.read().decode("utf-8-sig"))


def checks() -> list[tuple[str, str, dict[str, str]]]:
    banxico = os.environ.get("BANXICO_SIE_TOKEN", "")
    denue = os.environ.get("INEGI_DENUE_TOKEN", "")
    indicadores = os.environ.get("INEGI_INDICADORES_TOKEN", "")
    missing = [name for name, value in {
        "BANXICO_SIE_TOKEN": banxico,
        "INEGI_DENUE_TOKEN": denue,
        "INEGI_INDICADORES_TOKEN": indicadores,
    }.items() if not value]
    if missing:
        raise ValueError("Faltan variables: " + ", ".join(missing))
    return [
        ("Banxico SIE", "https://www.banxico.org.mx/SieAPIRest/service/v1/series/SF60648/datos/oportuno", {"Bmx-Token": banxico}),
        ("INEGI DENUE", f"https://www.inegi.org.mx/app/api/denue/v1/consulta/Ficha/34185/{quote(denue)}", {}),
        ("INEGI Indicadores", f"https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml/INDICATOR/1002000001/es/09/true/BISE/2.0/{quote(indicadores)}?type=json", {}),
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env.data")
    arguments = parser.parse_args()
    load_env(arguments.env_file)
    failures = 0
    for name, url, headers in checks():
        try:
            payload = get_json(url, headers)
            if not isinstance(payload, (dict, list)):
                raise ValueError("respuesta JSON inesperada")
            print(f"OK: {name}")
        except (HTTPError, URLError, TimeoutError, ValueError, RuntimeError) as error:
            failures += 1
            status = error.code if isinstance(error, HTTPError) else type(error).__name__
            print(f"ERROR: {name} ({status})")
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
