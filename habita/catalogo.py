"""Catálogo inicial de viviendas CDMX y adaptación al motor HABIMAS."""
from __future__ import annotations

import csv
import math
import os
from pathlib import Path
from .modelos import Perfil, Zona
from .movilidad import minutos_otp

ROOT = Path(__file__).resolve().parents[1]
CATALOGO = ROOT / "datos" / "viviendas_simuladas_cdmx.csv"

# Valores iniciales transparentes para probar el flujo; se reemplazarán por el pipeline territorial.
BASE_ALCALDIA = {
    "Benito Juárez": (82, 88, 88, 92, 91), "Cuauhtémoc": (68, 82, 82, 95, 96),
    "Miguel Hidalgo": (78, 86, 88, 91, 93), "Coyoacán": (76, 84, 86, 82, 88),
    "Azcapotzalco": (66, 78, 78, 78, 79), "Gustavo A. Madero": (58, 72, 72, 73, 72),
    "Iztacalco": (62, 70, 74, 80, 76), "Iztapalapa": (52, 65, 68, 66, 64),
    "Tlalpan": (70, 68, 77, 62, 75), "Álvaro Obregón": (67, 65, 74, 70, 78),
}


def distancia_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(a))


def traslado_estimado(perfil: Perfil, lat: float, lon: float) -> float:
    km = distancia_km(lat, lon, perfil.destino_latitud, perfil.destino_longitud)
    velocidad = {"caminando": 4.5, "bicicleta": 14, "automovil": 18, "transporte_publico": 13}[perfil.modo_traslado]
    espera = 8 if perfil.modo_traslado == "transporte_publico" else 3 if perfil.modo_traslado == "automovil" else 0
    return round(km / velocidad * 60 + espera, 1)

def calcular_traslado(perfil: Perfil, lat: float, lon: float) -> tuple[float, str]:
    routed = minutos_otp(lat, lon, perfil.destino_latitud, perfil.destino_longitud,
                         perfil.hora_salida, perfil.modo_traslado)
    if routed is not None:
        source = "GTFS CDMX / OSM" if perfil.modo_traslado == "transporte_publico" else "OSM"
        return routed, f"OpenTripPlanner 2.10 / {source}"
    return traslado_estimado(perfil, lat, lon), "estimacion_geodesica"


def _filas_postgis() -> list[dict[str, object]]:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return []
    try:
        import psycopg
        from psycopg.rows import dict_row
        with psycopg.connect(database_url, row_factory=dict_row, connect_timeout=2) as connection:
            with connection.cursor() as cursor:
                cursor.execute("""SELECT id,nombre,colonia,alcaldia,ST_Y(ubicacion::geometry) latitud,
                    ST_X(ubicacion::geometry) longitud,precio,habitaciones,superficie_m2,tipo,fuente,fecha,simulada
                    FROM vivienda ORDER BY id""")
                return list(cursor.fetchall())
    except Exception:
        return []


def cargar_viviendas(perfil: Perfil, ruta: Path = CATALOGO) -> list[Zona]:
    rows = _filas_postgis()
    if not rows:
        with ruta.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
    result = []
    for row in rows:
        lat, lon = float(row["latitud"]), float(row["longitud"])
        seguridad, riesgos, vivienda, movilidad_base, entorno = BASE_ALCALDIA[row["alcaldia"]]
        traslado, motor_traslado = calcular_traslado(perfil, lat, lon)
        movilidad = round(max(0, min(100, 100 - max(0, traslado - 20) * 100 / 70)) * .7 + movilidad_base * .3, 1)
        result.append(Zona(
            id=row["id"], nombre=row["nombre"], precio=float(row["precio"]),
            habitaciones=int(row["habitaciones"]), traslado_min=traslado,
            seguridad=seguridad, riesgos=riesgos, vivienda=vivienda, movilidad=movilidad, entorno=entorno,
            fuente=str(row["fuente"]) + "; indicadores territoriales provisionales",
            fecha=row["fecha"], nivel_geografico="vivienda simulada / alcaldía", simulado=bool(row["simulada"]),
            colonia=row["colonia"], alcaldia=row["alcaldia"], latitud=lat, longitud=lon,
            superficie_m2=float(row["superficie_m2"]), tipo=row["tipo"],
            motor_traslado=motor_traslado,
        ))
    return result
