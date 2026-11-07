"""Contratos de entrada. Los montos son MXN y las tasas son fracciones."""
from datetime import date
import json
from math import isclose
from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field, model_validator

Monto = Annotated[float, Field(ge=0, allow_inf_nan=False)]
Puntaje = Annotated[float, Field(ge=0, le=100, allow_inf_nan=False)]
Fraccion = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
DIMENSIONES = ("seguridad", "riesgos", "vivienda", "movilidad", "entorno")


class Contrato(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Pesos(Contrato):
    finanzas: Fraccion
    seguridad: Fraccion
    riesgos: Fraccion
    vivienda: Fraccion
    movilidad: Fraccion
    entorno: Fraccion

    @model_validator(mode="after")
    def suma_uno(self):
        if not isclose(sum(self.model_dump().values()), 1.0, abs_tol=1e-8):
            raise ValueError("Los seis pesos deben sumar 1.0 (100 %).")
        if self.finanzas == 1:
            raise ValueError("Asigna peso positivo al menos a una dimensión territorial.")
        return self


class Perfil(Contrato):
    descripcion: str = Field(min_length=1, max_length=1200)
    ingreso_mensual: Annotated[float, Field(gt=0)]
    gastos_mensuales: Monto
    deudas_mensuales: Monto
    reserva_mensual: Monto
    presupuesto_maximo: Annotated[float, Field(gt=0)]
    enganche_disponible: Monto
    ahorro_gastos_iniciales: Monto
    pago_maximo_usuario: Monto
    habitaciones_minimas: int = Field(ge=1, le=20)
    traslado_maximo_min: Annotated[float, Field(gt=0)]
    seguridad_minima: Puntaje
    riesgos_minimo: Puntaje
    plazo_anios: int = Field(ge=1, le=40)
    tasa_anual: Fraccion
    incremento_estres: Fraccion
    limite_deuda_ingreso: Annotated[float, Field(gt=0, le=1)]
    enganche_minimo_pct: Fraccion
    gastos_iniciales_pct: Fraccion
    gasto_vivienda_mensual: Monto
    cobertura_minima: Annotated[float, Field(gt=0, le=1)]
    pesos: Pesos

    @model_validator(mode="after")
    def tasa_estres_valida(self):
        if self.tasa_anual + self.incremento_estres > 1:
            raise ValueError("La tasa anual de estrés debe ser menor o igual a 100 %.")
        return self


class Zona(Contrato):
    id: str = Field(pattern=r"^Z[0-9]{2,4}$")
    nombre: str = Field(min_length=1)
    precio: Annotated[float, Field(gt=0)]
    habitaciones: int = Field(ge=1)
    traslado_min: Monto
    seguridad: Puntaje | None
    riesgos: Puntaje | None
    vivienda: Puntaje | None
    movilidad: Puntaje | None
    entorno: Puntaje | None
    fuente: str = Field(min_length=1)
    fecha: date
    nivel_geografico: str = Field(min_length=1)
    simulado: bool


class Conclusion(Contrato):
    """Única parte redactada por el LLM; los cálculos se anexan desde Python."""
    resumen: str = Field(min_length=20, max_length=1800)
    ids_revisados: list[str]
    ranking_ids: list[str] = Field(default_factory=list)
    recomendacion_id: str | None = None


def validar_conclusion(texto: str, etapa: str, datos: dict, ids: list[str]) -> Conclusion:
    """Valida la salida del LLM sin importar CrewAI ni realizar llamadas al modelo."""
    limpio = texto.strip()
    if limpio.startswith("```") and limpio.endswith("```"):
        limpio = "\n".join(limpio.splitlines()[1:-1])
    contenido = json.loads(limpio)
    # Llama pequeño puede envolver el esquema en su etiqueta; esto solo corrige formato.
    if isinstance(contenido, dict) and set(contenido) == {"formato_respuesta"}:
        contenido = contenido["formato_respuesta"]
    conclusion = Conclusion.model_validate(contenido)
    if any(moneda in conclusion.resumen.lower() for moneda in ("dólar", "dolar", "usd", "euro")):
        raise ValueError("Todos los importes están en pesos mexicanos MXN. Corrige la moneda del resumen.")
    esperados = [] if etapa == "perfil" else ids
    if sorted(conclusion.ids_revisados) != sorted(esperados):
        raise ValueError(f"ids_revisados debe incluir exactamente {esperados}.")
    ranking = [z["id"] for z in datos["ranking"]] if etapa == "coordinacion" else []
    recomendacion = datos["recomendacion_id"] if etapa == "coordinacion" else None
    if conclusion.ranking_ids != ranking or conclusion.recomendacion_id != recomendacion:
        raise ValueError(f"ranking_ids debe ser {ranking} y recomendacion_id debe ser {recomendacion}.")
    return conclusion

