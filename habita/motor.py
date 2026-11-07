"""Cálculos auditables: no requieren Ollama ni realizan consultas externas."""
import csv
import json
import math
from pathlib import Path
from .modelos import DIMENSIONES, Perfil, Zona


def cargar_perfil(ruta: Path) -> Perfil:
    return Perfil.model_validate_json(ruta.read_text(encoding="utf-8-sig"))


def cargar_zonas(ruta: Path) -> list[Zona]:
    with ruta.open(encoding="utf-8-sig", newline="") as archivo:
        filas = list(csv.DictReader(archivo))
    zonas = [Zona.model_validate({k: None if v == "" else v for k, v in fila.items()}) for fila in filas]
    ids = [zona.id for zona in zonas]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("El catálogo debe contener zonas con identificadores únicos.")
    return zonas


def analizar_perfil(perfil: Perfil) -> dict:
    """Las cifras estructuradas prevalecen sobre el texto libre del perfil."""
    p = perfil
    libre = p.ingreso_mensual - p.gastos_mensuales - p.deudas_mensuales - p.reserva_mensual
    deuda = p.ingreso_mensual * p.limite_deuda_ingreso - p.deudas_mensuales
    limite = max(0.0, min(p.pago_maximo_usuario, libre, deuda))
    return {
        "entrada": p.model_dump(mode="json"),
        "limite_pago": round(limite, 2),
        "disponible_despues_gastos": round(libre, 2),
        "limite_por_deuda": round(deuda, 2),
        "alertas": ["No hay capacidad mensual disponible."] if limite == 0 else [],
        "regla": "min(tope_usuario, ingreso-gastos-deudas-reserva, ingreso*limite_deuda-deudas), piso cero",
    }


def evaluar_zonas(perfil: Perfil, zonas: list[Zona]) -> dict:
    resultados = []
    pesos = perfil.pesos.model_dump()
    for z in zonas:
        indicadores = {d: getattr(z, d) for d in DIMENSIONES}
        cobertura = sum(v is not None for v in indicadores.values()) / len(DIMENSIONES)
        razones = []
        if z.precio > perfil.presupuesto_maximo:
            razones.append("Precio superior al presupuesto máximo")
        if z.habitaciones < perfil.habitaciones_minimas:
            razones.append("Habitaciones insuficientes")
        if z.traslado_min > perfil.traslado_maximo_min:
            razones.append("Traslado superior al máximo")
        if cobertura < perfil.cobertura_minima:
            razones.append("Cobertura de indicadores insuficiente")
        for campo, minimo in (("seguridad", perfil.seguridad_minima), ("riesgos", perfil.riesgos_minimo)):
            valor = indicadores[campo]
            if valor is None:
                razones.append(f"Falta indicador obligatorio: {campo}")
            elif valor < minimo:
                razones.append(f"{campo.capitalize()} inferior al mínimo")
        # Todos los indicadores tienen sentido favorable: 100 = mejor.
        # Un dato ausente aporta cero, no se redistribuye su peso.
        contribucion = sum(pesos[d] * (indicadores[d] or 0) for d in DIMENSIONES)
        resultados.append({
            "id": z.id, "nombre": z.nombre, "precio": z.precio,
            "indicadores": indicadores, "cobertura": cobertura,
            "puntaje_zona": round(contribucion / (1 - pesos["finanzas"]), 4),
            "aporte_territorial": round(contribucion, 6),
            "cumple": not razones, "motivos": razones,
            "fuente": z.fuente, "fecha": z.fecha.isoformat(),
            "nivel_geografico": z.nivel_geografico, "simulado": z.simulado,
        })
    return {"zonas": resultados}


def mensualidad(capital: float, tasa_anual: float, anios: int) -> float:
    """Cuota fija de capital e intereses; tasa NOMINAL anual / 12 (no CAT)."""
    if not all(math.isfinite(v) for v in (capital, tasa_anual, anios)):
        raise ValueError("Los valores deben ser finitos.")
    if capital < 0 or tasa_anual < 0 or anios <= 0 or int(anios) != anios:
        raise ValueError("Capital y tasa no negativos; plazo entero positivo.")
    if capital == 0:
        return 0.0
    n, r = int(anios) * 12, tasa_anual / 12
    return capital / n if r == 0 else capital * r / (1 - (1 + r) ** (-n))


def evaluar_finanzas(perfil: Perfil, zonas: list[Zona], datos_perfil: dict) -> dict:
    p, limite = perfil, datos_perfil["limite_pago"]
    resultados = []
    for z in zonas:
        enganche = min(p.enganche_disponible, z.precio)
        capital = z.precio - enganche
        iniciales = round(z.precio * p.gastos_iniciales_pct, 2)
        cuota = round(mensualidad(capital, p.tasa_anual, p.plazo_anios), 2)
        total = round(cuota + p.gasto_vivienda_mensual, 2)
        estres = round(mensualidad(capital, p.tasa_anual + p.incremento_estres, p.plazo_anios)
                       + p.gasto_vivienda_mensual, 2)
        corto = max(1, p.plazo_anios - 5)
        razones = []
        if enganche < round(z.precio * p.enganche_minimo_pct, 2):
            razones.append("Enganche menor al mínimo del escenario")
        if iniciales > p.ahorro_gastos_iniciales:
            razones.append("Ahorro insuficiente para gastos iniciales")
        if total > limite:
            razones.append("Pago mensual superior a la capacidad calculada")
        # La holgura de pago es una utilidad, NO una probabilidad de aprobación.
        puntaje = 100 * max(0, 1 - total / limite) if limite > 0 else 0
        resultados.append({
            "id": z.id, "enganche": enganche, "capital": capital,
            "gastos_iniciales": iniciales, "cuota_credito": cuota,
            "pago_total": total, "pago_estres": estres,
            "pago_plazo_corto": round(mensualidad(capital, p.tasa_anual, corto)
                                      + p.gasto_vivienda_mensual, 2),
            "plazo_corto_anios": corto,
            "deuda_ingreso": round((total + p.deudas_mensuales) / p.ingreso_mensual, 4),
            "puntaje_financiero": round(puntaje, 6),
            "cumple": not razones, "motivos": razones,
            "estres_supera_limite": estres > limite,
        })
    return {"limite_pago": limite, "alternativas": resultados,
            "supuesto": "Tasa, gastos y umbrales simulados; no representan una oferta bancaria."}


def integrar(perfil: Perfil, datos_zonas: dict, datos_finanzas: dict) -> dict:
    """Primero restricciones duras; después utilidad. Ningún peso revoca un veto."""
    finanzas = {z["id"]: z for z in datos_finanzas["alternativas"]}
    if set(finanzas) != {z["id"] for z in datos_zonas["zonas"]}:
        raise ValueError("Zona y finanzas deben evaluar exactamente los mismos identificadores.")
    ranking, descartadas = [], []
    for z in datos_zonas["zonas"]:
        f = finanzas[z["id"]]
        if not z["cumple"] or not f["cumple"]:
            descartadas.append({"id": z["id"], "nombre": z["nombre"], "motivos": z["motivos"] + f["motivos"]})
            continue
        valor = z["aporte_territorial"] + perfil.pesos.finanzas * f["puntaje_financiero"]
        ranking.append({
            "id": z["id"], "nombre": z["nombre"], "puntaje": round(valor, 4),
            "precio": z["precio"], "pago_total": f["pago_total"],
            "pago_estres": f["pago_estres"], "puntaje_zona": z["puntaje_zona"],
            "puntaje_financiero": f["puntaje_financiero"],
            "alertas": ["El escenario de estrés supera el límite mensual"] if f["estres_supera_limite"] else [],
        })
    # Empate: menor pago y luego identificador. Orden reproducible.
    ranking.sort(key=lambda x: (-x["puntaje"], x["pago_total"], x["id"]))
    for posicion, fila in enumerate(ranking, 1):
        fila["posicion"] = posicion
    return {
        "estado": "con_alternativas" if ranking else "sin_alternativas",
        "recomendacion_id": ranking[0]["id"] if ranking else None,
        "ranking": ranking, "descartadas": descartadas,
        "pesos": perfil.pesos.model_dump(),
        "limite_pago": datos_finanzas["limite_pago"],
        "limitaciones": ["Datos y condiciones financieras simulados para clase.",
                         "La evaluación corresponde a la vivienda representativa de cada zona, no a toda su oferta.",
                         "No es una oferta ni una aprobación de crédito.",
                         "Las explicaciones del LLM requieren revisión humana."],
    }


def calcular_todo(perfil: Perfil, zonas: list[Zona]) -> dict:
    """Línea base sin IA; se usa para contrastar el Crew, no para simularlo."""
    p = analizar_perfil(perfil)
    z = evaluar_zonas(perfil, zonas)
    f = evaluar_finanzas(perfil, zonas, p)
    return {"perfil": p, "zonas": z, "finanzas": f, "coordinacion": integrar(perfil, z, f)}

