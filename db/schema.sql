CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS fuente_datos (
  id bigserial PRIMARY KEY, codigo text UNIQUE NOT NULL, nombre text NOT NULL,
  url text NOT NULL, frecuencia text, licencia text, requiere_token boolean DEFAULT false
);
CREATE TABLE IF NOT EXISTS pipeline_run (
  id bigserial PRIMARY KEY, fuente_id bigint REFERENCES fuente_datos(id), inicio timestamptz NOT NULL,
  fin timestamptz, estado text NOT NULL CHECK (estado IN ('running','success','failed')),
  filas bigint DEFAULT 0, sha256 text, error text
);
CREATE TABLE IF NOT EXISTS vivienda (
  id text PRIMARY KEY, nombre text NOT NULL, colonia text NOT NULL, alcaldia text NOT NULL,
  precio numeric(14,2) NOT NULL CHECK (precio > 0), habitaciones smallint NOT NULL,
  superficie_m2 numeric(8,2), tipo text, simulada boolean NOT NULL DEFAULT true,
  ubicacion geography(Point,4326) NOT NULL, fuente text NOT NULL, fecha date NOT NULL
);
CREATE INDEX IF NOT EXISTS vivienda_ubicacion_gix ON vivienda USING gist (ubicacion);
CREATE TABLE IF NOT EXISTS indicador_zona (
  id bigserial PRIMARY KEY, clave_geo text NOT NULL, nivel_geo text NOT NULL,
  periodo date NOT NULL, seguridad numeric(5,2), riesgos numeric(5,2), vivienda numeric(5,2),
  movilidad numeric(5,2), entorno numeric(5,2), cobertura numeric(5,4) NOT NULL,
  metodologia_version text NOT NULL, UNIQUE(clave_geo,nivel_geo,periodo,metodologia_version)
);
CREATE TABLE IF NOT EXISTS tiempo_traslado (
  id bigserial PRIMARY KEY, vivienda_id text REFERENCES vivienda(id), destino geography(Point,4326) NOT NULL,
  modo text NOT NULL, salida time NOT NULL, minutos numeric(8,2) NOT NULL,
  motor text NOT NULL, calculado_en timestamptz NOT NULL DEFAULT now(),
  UNIQUE(vivienda_id,modo,salida,calculado_en)
);
CREATE INDEX IF NOT EXISTS tiempo_traslado_destino_gix ON tiempo_traslado USING gist (destino);
