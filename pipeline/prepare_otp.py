"""Descarga y valida insumos reproducibles para OpenTripPlanner CDMX."""
from __future__ import annotations
import hashlib, json, shutil, urllib.request, zipfile
import csv, io
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".runtime" / "otp"
SOURCES = {
    "cdmx-gtfs.source": "https://datos.cdmx.gob.mx/dataset/75538d96-3ade-4bc5-ae7d-d85595e4522d/resource/32ed1b6b-41cd-49b3-b7f0-b57acb0eb819/download/32ed1b6b-41cd-49b3-b7f0-b57acb0eb819.zip",
    "mexico-city.osm.pbf": "https://download.bbbike.org/osm/bbbike/MexicoCity/MexicoCity.osm.pbf",
    "otp-shaded-2.10.0.jar": "https://github.com/opentripplanner/OpenTripPlanner/releases/download/v2.10.0/otp-shaded-2.10.0.jar",
}

def download(name: str, url: str) -> dict[str, object]:
    target = RUNTIME / name
    if not target.exists():
        request = urllib.request.Request(url, headers={"User-Agent": "HABIMAS-data-pipeline/1.0"})
        with urllib.request.urlopen(request, timeout=120) as response, target.open("wb") as output:
            shutil.copyfileobj(response, output)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    return {"archivo": name, "url": url, "bytes": target.stat().st_size, "sha256": digest}

def validate_gtfs(path: Path) -> dict[str, int]:
    required = {"agency.txt", "stops.txt", "routes.txt", "trips.txt", "stop_times.txt"}
    with zipfile.ZipFile(path) as archive:
        names = {Path(name).name for name in archive.namelist()}
        missing = required - names
        if missing:
            raise ValueError("GTFS incompleto: " + ", ".join(sorted(missing)))
        counts = {}
        for filename in required:
            member = next(name for name in archive.namelist() if Path(name).name == filename)
            with archive.open(member) as handle:
                counts[filename] = max(0, sum(1 for _ in handle) - 1)
        return counts

def normalize_gtfs(source: Path, target: Path) -> list[str]:
    """Crea una copia OTP-compatible sin alterar el ZIP oficial descargado."""
    with zipfile.ZipFile(source) as archive:
        agencies = list(csv.DictReader(io.TextIOWrapper(archive.open("agency.txt"), encoding="utf-8-sig")))
        routes = list(csv.DictReader(io.TextIOWrapper(archive.open("routes.txt"), encoding="utf-8-sig")))
        existing = {row["agency_id"] for row in agencies}
        missing = sorted({row["agency_id"] for row in routes} - existing)
        agency_buffer = io.StringIO(newline="")
        fields = ["agency_id", "agency_name", "agency_url", "agency_timezone", "agency_lang"]
        writer = csv.DictWriter(agency_buffer, fieldnames=fields, lineterminator="\n")
        writer.writeheader(); writer.writerows(agencies)
        for agency_id in missing:
            writer.writerow({"agency_id": agency_id, "agency_name": agency_id,
                             "agency_url": "https://www.semovi.cdmx.gob.mx/",
                             "agency_timezone": "America/Mexico_City", "agency_lang": "es"})
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as output:
            for member in archive.infolist():
                data = agency_buffer.getvalue().encode() if Path(member.filename).name == "agency.txt" else archive.read(member)
                output.writestr(member.filename, data)
    return missing

def main() -> None:
    RUNTIME.mkdir(parents=True, exist_ok=True)
    for config in (ROOT / "otp").glob("*.json"):
        shutil.copy2(config, RUNTIME / config.name)
    files = [download(name, url) for name, url in SOURCES.items()]
    missing = normalize_gtfs(RUNTIME / "cdmx-gtfs.source", RUNTIME / "cdmx-gtfs.zip")
    gtfs = validate_gtfs(RUNTIME / "cdmx-gtfs.zip")
    manifest = {"capturado_en": datetime.now(timezone.utc).isoformat(), "archivos": files,
                "gtfs_registros": gtfs, "normalizacion": {"agencias_agregadas": missing}}
    (RUNTIME / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print("OK: insumos OTP preparados")
    print("GTFS:", ", ".join(f"{name}={count}" for name, count in sorted(gtfs.items())))

if __name__ == "__main__": main()
