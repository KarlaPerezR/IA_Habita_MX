"""Valida y carga en PostGIS el catálogo inicial de viviendas simuladas."""
from __future__ import annotations

import argparse
import csv
import os
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "datos" / "viviendas_simuladas_cdmx.csv"
DEFAULT_SCHEMA = ROOT / "db" / "schema.sql"


def read_and_validate(path: Path) -> list[dict[str, object]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 20:
        raise ValueError(f"Se esperaban 20 viviendas; se encontraron {len(rows)}.")
    required = {"id", "nombre", "colonia", "alcaldia", "latitud", "longitud", "precio", "habitaciones", "superficie_m2", "tipo", "fuente", "fecha", "simulada"}
    if not rows or set(rows[0]) != required:
        raise ValueError("El CSV no tiene el esquema esperado.")
    seen: set[str] = set()
    normalized: list[dict[str, object]] = []
    for number, row in enumerate(rows, start=2):
        identifier = row["id"].strip()
        if identifier in seen:
            raise ValueError(f"ID duplicado en la línea {number}: {identifier}")
        seen.add(identifier)
        lat, lon = float(row["latitud"]), float(row["longitud"])
        if not (19.0 <= lat <= 20.0 and -100.0 <= lon <= -98.0):
            raise ValueError(f"Coordenada fuera del alcance CDMX en {identifier}.")
        price, rooms, surface = float(row["precio"]), int(row["habitaciones"]), float(row["superficie_m2"])
        if price <= 0 or rooms < 1 or surface <= 0:
            raise ValueError(f"Valores inmobiliarios inválidos en {identifier}.")
        normalized.append({
            **row, "id": identifier, "latitud": lat, "longitud": lon,
            "precio": price, "habitaciones": rooms, "superficie_m2": surface,
            "fecha": date.fromisoformat(row["fecha"]),
            "simulada": row["simulada"].strip().lower() in {"1", "true", "sí", "si"},
        })
    return normalized


def load(rows: list[dict[str, object]], database_url: str, schema_path: Path) -> None:
    try:
        import psycopg
    except ImportError as error:
        raise RuntimeError("Instala requirements-data.txt para cargar PostgreSQL.") from error
    statement = """
        INSERT INTO vivienda
          (id,nombre,colonia,alcaldia,precio,habitaciones,superficie_m2,tipo,simulada,ubicacion,fuente,fecha)
        VALUES
          (%(id)s,%(nombre)s,%(colonia)s,%(alcaldia)s,%(precio)s,%(habitaciones)s,%(superficie_m2)s,
           %(tipo)s,%(simulada)s,ST_SetSRID(ST_MakePoint(%(longitud)s,%(latitud)s),4326)::geography,%(fuente)s,%(fecha)s)
        ON CONFLICT (id) DO UPDATE SET
          nombre=EXCLUDED.nombre, colonia=EXCLUDED.colonia, alcaldia=EXCLUDED.alcaldia,
          precio=EXCLUDED.precio, habitaciones=EXCLUDED.habitaciones, superficie_m2=EXCLUDED.superficie_m2,
          tipo=EXCLUDED.tipo, simulada=EXCLUDED.simulada, ubicacion=EXCLUDED.ubicacion,
          fuente=EXCLUDED.fuente, fecha=EXCLUDED.fecha
    """
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(schema_path.read_text(encoding="utf-8"))
            cursor.executemany(statement, rows)


def main() -> None:
    env_path = ROOT / ".env.data"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line and not line.lstrip().startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    parser.add_argument("--validate-only", action="store_true")
    arguments = parser.parse_args()
    rows = read_and_validate(arguments.csv)
    if arguments.validate_only:
        print(f"OK: {len(rows)} viviendas simuladas válidas.")
        return
    if not arguments.database_url:
        parser.error("Define DATABASE_URL o usa --validate-only.")
    load(rows, arguments.database_url, arguments.schema)
    print(f"OK: {len(rows)} viviendas cargadas o actualizadas en PostGIS.")


if __name__ == "__main__":
    main()
