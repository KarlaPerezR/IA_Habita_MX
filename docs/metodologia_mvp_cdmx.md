# Metodología HABIMAS — MVP Ciudad de México

Versión propuesta: `cdmx-1.0.0`. Unidad de cálculo: **AGEB**; unidad mostrada al usuario: **colonia**. Las viviendas iniciales son simuladas y deben etiquetarse como tales en todas las salidas.

## Principios

1. Separar datos observados, estimados y simulados; nunca presentar un precio de referencia como anuncio disponible.
2. Conservar fuente, fecha de corte, archivo original, hash, cobertura y versión metodológica.
3. Transformar indicadores a una escala favorable 0–100: 100 siempre significa una mejor condición.
4. Aplicar primero restricciones duras del perfil y después ordenar las alternativas elegibles.
5. No imputar silenciosamente. Una alternativa con cobertura menor a 80 % se marca insuficiente y no entra al ranking principal.

## Construcción de indicadores

### Seguridad (0–100)

- Ventana móvil de 12 meses de carpetas FGJ, unidas espacialmente a AGEB.
- Tasas por 10,000 habitantes con población INEGI.
- Componentes: violencia 45 %, patrimonio 35 % y otros delitos 20 %.
- Cada tasa se winsoriza en percentiles 5 y 95 de CDMX y se invierte: `100 × (P95 - valor) / (P95 - P05)`, limitada a 0–100.
- La puntuación es relativa a CDMX y no representa probabilidad individual ni totalidad de delitos.

### Riesgos (0–100)

- Intersección con capas oficiales de inundación, sismo, laderas y otros peligros disponibles.
- Cada peligro conserva su componente y versión. La exposición se normaliza 0–100; el resultado favorable es `100 - exposición`.
- El indicador publicado usa el peor componente como regla conservadora. Un peligro crítico puede excluir una alternativa aunque el promedio sea favorable.

### Movilidad y tiempo de traslado (0–100)

- El perfil guarda destino, coordenadas, modo y hora de salida.
- OpenTripPlanner autohospedado calcula transporte público con GTFS CDMX + red peatonal OpenStreetMap. Para automóvil, bicicleta y caminata se requiere un motor de ruteo compatible; la duración debe registrarse con motor, versión y fecha.
- Componente de traslado: 100 hasta 20 min, decrece linealmente y llega a 0 a los 90 min.
- Acceso a transporte: 100 hasta 300 m de una parada y 0 desde 1,500 m.
- Diversidad: 0 rutas = 0; 3 o más rutas útiles = 100.
- Movilidad = traslado 70 % + acceso 20 % + diversidad 10 %. Además, `traslado_maximo_min` funciona como restricción dura.

### Vivienda (0–100)

- INEGI INV/Censo: servicios, infraestructura vial, alumbrado, banquetas y condiciones habitacionales.
- Componentes con datos faltantes se omiten sólo si la cobertura total permanece en 80 % o más; los pesos restantes se reescalan y se informa el ajuste.

### Entorno (0–100)

- DENUE y datos CDMX: salud, educación, abasto, áreas verdes y empleo.
- Conteos sobre red caminable a 500 m, 1 km y 3 km; mientras no exista red calculada, el radio euclidiano debe quedar identificado como aproximación.
- Densidades normalizadas con percentiles 5–95 para evitar que valores extremos dominen.

### Precio y finanzas

- Las 20 viviendas iniciales son casos simulados calibrables con SNIIV y SHF; no son oferta de mercado.
- Precio y apreciación se actualizan con fecha de corte y fuente. La tasa Banxico alimenta escenarios de referencia, no reemplaza una cotización bancaria.
- El motor financiero conserva sus escenarios base, estrés y plazo alternativo. Elegibilidad considera presupuesto, enganche, gastos iniciales, pago mensual y deuda/ingreso.

## Pipeline y control de calidad

1. **Ingesta:** guardar archivo/respuesta original y metadatos en zona `raw`.
2. **Validación:** esquema, tipos, duplicados, coordenadas, fechas y claves geográficas.
3. **Normalización:** CRS EPSG:4326, catálogo único de alcaldía/colonia/AGEB y categorías homologadas.
4. **Carga:** transacción idempotente en PostgreSQL/PostGIS; registrar filas, hash, estado y error en `pipeline_run`.
5. **Cálculo:** materializar componentes e indicadores con periodo y versión.
6. **Publicación:** exponer sólo corridas exitosas y con cobertura suficiente.
7. **Monitoreo:** comparar volumen, nulos y distribución con la corrida anterior; detener publicación ante cambios anómalos.

## Validación de la metodología

- Revisión experta de categorías y pesos antes del piloto.
- Pruebas retrospectivas con periodos anteriores, sin usar datos futuros.
- Análisis de sensibilidad variando pesos ±10 % y documentando cambios en el top de alternativas.
- Muestreo manual de uniones geográficas y rutas.
- Versionar cualquier cambio de fórmula, fuente, umbral o peso; recalcular el histórico cuando la comparación lo requiera.
