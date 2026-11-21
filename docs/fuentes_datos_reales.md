# Fuentes de datos reales para HABIMAS

Investigación realizada el 21 de noviembre de 2026. Alcance inicial: Ciudad de México.

## Conclusión ejecutiva

Las fuentes públicas permiten construir indicadores territoriales reales y precios de referencia, pero no un inventario completo de anuncios inmobiliarios individuales. El primer producto debe evaluar colonias o AGEB con viviendas representativas. Para mostrar inmuebles específicos será necesario contratar una fuente comercial, celebrar un convenio o recibir inventario de una inmobiliaria; no se recomienda extraer portales mediante scraping sin autorización.

## Matriz de fuentes

| Dimensión HABIMAS | Fuente recomendada | Acceso | Granularidad | Actualización | Uso propuesto |
|---|---|---|---|---|---|
| Oferta, recámaras, tipo y segmento | [SNIIV / SEDATU](https://sniiv.sedatu.gob.mx/Reporte/Datos_abiertos) | API JSON, CSV, XLSX | Municipio/alcaldía | Mensual | Obtener producción, registro e inventario; construir vivienda representativa por alcaldía y segmento. |
| Precio y apreciación | [Índice SHF](https://www.gob.mx/shf/documentos/indice-shf-de-precios-de-la-vivienda-en-mexico-2025-a-2026) | Datos abiertos descargables | Entidad, zona metropolitana y alcaldías seleccionadas | Trimestral | Actualizar precios de referencia e inflación inmobiliaria. No equivale a precio de anuncio. |
| Valores de avalúos | [Indicadores SHF](https://www.gob.mx/shf/documentos/indicadores-sociedad-hipotecaria-federal) | Archivos descargables | Agregada por clase y tipología | Trimestral | Mediana y promedio para casa, condominio y departamento. |
| Tasas de referencia | [API SIE Banxico](https://www.banxico.org.mx/SieAPIRest/swagger/index.html) | API con token | Serie temporal nacional | Según serie | Alimentar tasa base y escenarios; conservar la tasa capturada por el usuario para cotizaciones particulares. |
| Créditos y financiamiento | [API SNIIV Financiamientos/CNBV](https://sniiv.sedatu.gob.mx/Reporte/Datos_abiertos) | API JSON, CSV, XLSX | Municipio/alcaldía | Mensual | Caracterizar montos y segmentos financiados; no representa una oferta bancaria vigente. |
| Seguridad | [Carpetas FGJ CDMX](https://datos.cdmx.gob.mx/dataset/carpetas-de-investigacion-fgj-de-la-ciudad-de-mexico) | CSV | Coordenada, colonia y alcaldía | Mensual | Calcular tasas móviles por colonia y categoría delictiva. |
| Seguridad comparable nacional | [SESNSP municipal](https://www.datos.gob.mx/dataset/incidencia_delictiva) | CSV, CC BY 4.0 | Municipio | Mensual | Respaldo nacional y comparación entre municipios; menos granular que FGJ. |
| Población denominadora | [Censo 2020 por AGEB/manzana](https://www.inegi.org.mx/app/descarga/) | Descarga masiva | AGEB y manzana | Censal | Convertir delitos absolutos en tasas; controlar densidad poblacional. |
| Riesgos naturales | [Atlas de Riesgos CDMX](https://www.datos.cdmx.gob.mx/es/dataset/?_groups_limit=0&organization=secretaria-de-gestion-integral-de-riesgos-y-proteccion-civil) | CSV, SHP, XML | AGEB | Por capa | Integrar inundación, sismo, laderas, precipitación y tormentas. |
| Transporte público | [GTFS CDMX](https://datos.cdmx.gob.mx/dataset/gtfs) | ZIP GTFS | Paradas, rutas y horarios | Publicación continua | Distancia a paradas, cobertura y cálculo de rutas con un motor GTFS. |
| Servicios y empleo | [API DENUE](https://www.inegi.org.mx/servicios/api-denue/) | API con token | Establecimiento y coordenada | Versiones periódicas | Contar hospitales, escuelas, comercios y empleos en radios caminables. |
| Vivienda y entorno urbano | [Inventario Nacional de Viviendas 2020](https://inegi.org.mx/app/mapa/inv/) | Microdatos y capas | AGEB, manzana y vialidad | Censal | Banquetas, alumbrado, infraestructura vial, servicios y características de vivienda. |
| Colonias y unión espacial | [Catálogo de colonias ADIP](https://datos.cdmx.gob.mx/dataset/catalogo-de-colonias-datos-abiertos) | GeoJSON, SHP; CC BY 4.0 | Colonia | Sin periodicidad | Geocodificación común y agregación de todas las fuentes. |
| Áreas verdes | [Portal de Datos Abiertos CDMX](https://datos.cdmx.gob.mx/) | SHP/GeoJSON según recurso | Polígono | Según recurso | Distancia y superficie verde en el indicador de entorno. |

## Traducción a indicadores de HABIMAS

### Precio

1. SNIIV aporta rangos de valor, recámaras, superficie y volumen de vivienda.
2. SHF aporta índice de apreciación y valores de avalúo.
3. La base almacenará `precio_referencia`, no `precio_oferta`, mientras no exista proveedor de anuncios.

### Seguridad

- Ventana móvil de 12 meses de carpetas FGJ.
- Tasas por 10,000 habitantes usando población de INEGI.
- Subíndices separados para delitos contra la vida, integridad y patrimonio.
- Transformación robusta a 0–100 por percentiles; 100 significa menor incidencia relativa.
- Mostrar siempre fecha, cobertura y advertencia de que una carpeta no equivale a una sentencia ni a todos los delitos ocurridos.

### Riesgos

- Unión espacial de cada colonia/AGEB con capas de inundación, sismo, laderas y otros peligros.
- Normalizar cada peligro a 0–100.
- El indicador `riesgos` mantiene sentido favorable: 100 significa menor exposición.
- Conservar también cada componente para evitar ocultar un riesgo alto bajo un promedio.

### Movilidad y traslado

- GTFS permite medir cobertura, distancia a paradas y rutas programadas.
- El tiempo de traslado exige agregar al perfil un destino: coordenadas de trabajo/estudio o centro de interés.
- Para tiempos multimodales reproducibles se recomienda desplegar OpenTripPlanner con GTFS CDMX y una red peatonal de OpenStreetMap.
- Sin destino configurado, sólo debe publicarse un índice de accesibilidad, no minutos de traslado.

### Vivienda y entorno

- `vivienda`: características del parque habitacional, servicios, infraestructura y habitabilidad de INEGI.
- `entorno`: densidad de escuelas, salud, abasto, áreas verdes y empleo mediante DENUE y datos CDMX.
- Usar radios de 500 m, 1 km y 3 km, ajustados por red peatonal cuando sea posible.

## Arquitectura recomendada

```text
APIs y archivos oficiales
        ↓
Landing / raw (archivo original + hash + fecha)
        ↓
Validación de esquema y calidad
        ↓
Normalización de claves geográficas
        ↓
PostgreSQL + PostGIS
        ↓
Agregaciones por colonia y AGEB
        ↓
Indicadores versionados 0–100
        ↓
API HABIMAS
        ↓
Motor de restricciones y ranking
```

## Tablas mínimas

- `geo_colonia`: claves, nombre, alcaldía, geometría.
- `geo_ageb`: clave INEGI, población, geometría.
- `vivienda_oferta_agregada`: periodo, geografía, segmento, recámaras, superficie, volumen.
- `precio_referencia`: periodo, geografía, tipología, valor medio/mediano, índice SHF.
- `seguridad_evento`: fecha, categoría, colonia/AGEB, coordenada anonimizada o agregada.
- `riesgo_capa`: tipo, versión, nivel, geometría.
- `transporte_parada` y `transporte_ruta`: versión GTFS y geometrías.
- `servicio_denue`: clase SCIAN, coordenada y versión.
- `indicador_zona`: valores publicados, cobertura, fecha y versión metodológica.
- `pipeline_run`: fuente, inicio, fin, estado, filas, hash y errores.

## Frecuencia sugerida

| Proceso | Frecuencia |
|---|---|
| FGJ y SNIIV | Mensual |
| SHF | Trimestral |
| GTFS | Semanal, comprobando si cambió el archivo |
| DENUE | Trimestral o cuando se publique una versión |
| Atlas de Riesgos | Mensual, comprobando versiones; recalcular sólo si cambió |
| INEGI Censo/INV | Anual para comprobar publicación; cargar al existir nueva edición |

## Dependencias y decisiones pendientes

1. Conseguir tokens de INEGI DENUE, Banco de Indicadores y Banxico SIE.
2. Confirmar que el MVP seguirá limitado a Ciudad de México.
3. Definir si la unidad de comparación será colonia o AGEB. Se recomienda colonia para la interfaz y AGEB para cálculo interno.
4. Definir el destino de traslado en el perfil del cliente.
5. Elegir si se contratará un proveedor de anuncios inmobiliarios. Sin él, HABIMAS debe hablar de zonas y viviendas representativas, no de inmuebles disponibles.
6. Aprobar PostgreSQL + PostGIS como almacén principal.
