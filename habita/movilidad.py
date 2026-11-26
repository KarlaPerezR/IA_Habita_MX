"""Cliente mínimo de OpenTripPlanner con degradación explícita."""
from __future__ import annotations
import json, os
from datetime import date
from urllib.error import URLError
from urllib.request import Request, urlopen

QUERY = """query HabimasPlan($fromPlace:String!,$toPlace:String!,$date:String!,$time:String!){
  plan(fromPlace:$fromPlace,toPlace:$toPlace,date:$date,time:$time,numItineraries:3,
       transportModes:MODES){
    itineraries{duration start end numberOfTransfers walkDistance legs{transitLeg}}
    messageStrings
  }
}"""

def minutos_otp(origen_lat: float, origen_lon: float, destino_lat: float, destino_lon: float,
                hora: str, modo: str, fecha: date | None = None) -> float | None:
    endpoint = os.getenv("OTP_BASE_URL", "http://127.0.0.1:8080/otp/gtfs/v1")
    if endpoint.endswith("/routers/default"):
        endpoint = endpoint.rsplit("/otp/", 1)[0] + "/otp/gtfs/v1"
    variables = {
        "fromPlace": f"Origen::{origen_lat},{origen_lon}",
        "toPlace": f"Destino::{destino_lat},{destino_lon}",
        "date": (fecha or date.today()).isoformat(), "time": hora,
    }
    modes = {"transporte_publico": "[{mode:WALK},{mode:TRANSIT}]", "caminando": "[{mode:WALK}]",
             "bicicleta": "[{mode:BICYCLE}]", "automovil": "[{mode:CAR}]"}.get(modo)
    if modes is None:
        return None
    request = Request(endpoint, data=json.dumps({"query": QUERY.replace("MODES", modes), "variables": variables}).encode(),
                      headers={"Content-Type": "application/json", "User-Agent": "HABIMAS/1.0"})
    try:
        with urlopen(request, timeout=8) as response:
            payload = json.load(response)
        itineraries = payload.get("data", {}).get("plan", {}).get("itineraries", [])
        if modo == "transporte_publico":
            itineraries = [item for item in itineraries if any(leg.get("transitLeg") for leg in item.get("legs", []))]
        durations = [float(item["duration"]) / 60 for item in itineraries if item.get("duration")]
        return round(min(durations), 1) if durations else None
    except (URLError, TimeoutError, ValueError, KeyError, json.JSONDecodeError):
        return None
