# Relevamiento de fuentes

Qué se revisó, qué sirve y qué se hizo con cada fuente. Los catálogos CKAN se recorren enteros
con `02_SCRIPTS/etl/04_inventario_catalogos.py` → `inventario_catalogos.csv` (una fila por
archivo, con marcas de escala municipal, censal y geográfica). Lo que no es CKAN se relevó a
mano y está acá. Relevado el 01-11-2026.

---

## Veredicto por fuente

| Fuente | Qué tiene | Sirve | Qué se hizo |
|---|---|---|---|
| **DINE** · argentina.gob.ar/dine | Provisorio por mesa 2011-2023, todo el país; en PBA trae Gobernador, Legislatura e Intendente | **Columna vertebral** | `etl/00` + `etl/01`: 15 elecciones por mesa |
| **Junta Electoral PBA** · juntaelectoral.gba.gov.ar | Definitivo 2025 por municipio (HTML) y concejales en PDF | Sí | `etl/05`: 135 municipios, cierra al voto |
| resultados.eleccionesbonaerenses.gba.gob.ar | Provisorio 2025 por mesa | Era la única mesa a mesa de 2025 | **Dado de baja**. Hay rastros en la Wayback Machine (pendiente) |
| **Catálogo PBA** · catalogo.datos.gba.gob.ar | 102 datasets: resultados por municipio 2005-2023, partidos, secciones, circuitos, radios 2010/2022, transferencias a municipios 2010-2026, salud | Sí | Bajado lo clave; inventario completo |
| **Estadística PBA** · datos.estadistica.ec.gba.gov.ar | 225 datasets: series censales 1869-2022, NBI, PBG por partido 2021-23, defunciones y natalidad por municipio, delito, educación, EHE municipal | Sí, a nivel municipio | Inventario completo; PBG bajado |
| estadistica.ec.gba.gov.ar | Portal institucional de la DPE | Sólo enlaza a los otros dos | — |
| mapas.estadistica.ec.gba.gov.ar | Portal ArcGIS de mapas estadísticos | Probablemente capas por radio | **No responde a consultas automáticas** (búsqueda REST vacía). Revisar en navegador |
| **datos.gob.ar** (Nación) | **Censos 1991, 2001, 2010, 2022 por radio censal** (todas las variables, en conteos), radios de los 4 censos, tablas de conversión 2001→2010→2022, códigos INDEC, empleo y salarios por partido (SIPA), delito por partido (SNIC), registro de gobiernos locales | **Clave para el territorio** | Bajado todo |
| **MunicipiosArgentinos.net** | 135 municipios × ~50 indicadores fiscales, de servicios y control, con fuente; intendente y espacio | Sí, **secundaria** | `etl/03` |
| **datosgobar** (GitHub) | Georef (normalizar direcciones, localidades, asentamientos), series de tiempo, ETL de Georef | Sí, como herramienta | Georef para geocodificar escuelas de votación (etapa 1.9) |
| **ArgentinaDatos** · argentinadatos.com | API de datos económicos; votaciones nominales de Diputados y Senado | Para `06_ACTORES` | Pendiente: votaciones de los legisladores bonaerenses |
| **DataCP** · datacp.ar | Resultados electorales agregados (provincia/sección), monitor del Congreso, simulador PBA 2025 | Poco: duplica a la DINE con menos detalle | Referencia para contrastar |
| IGN · Capas SIG | Localidades, rutas, ferrocarril, hidrografía, equipamiento | Sí, para distancia y accesibilidad | **El sitio no responde desde esta máquina** (ni WFS). Probar en navegador o desde otra red |
| simplemaps.com | Puntos de ciudades de todo el país | No: IGN, BAHRA y los radios del INDEC lo cubren con más detalle y fuente oficial | — |
| Proyectos de Martín Yeza | — | — | **Falta el enlace**: no aparecen en la web ni en GitHub |

## Trampas que dejaron los portales

- **Censos 2010 y 2001 en datos.gob.ar**: el catálogo publica la URL `…/06-buenos-aires-2022.zip`
  y da 404. El archivo real es `…/06-buenos-aires-2010.zip` y `…-2001.zip`.
- **Censo 1991**: Buenos Aires es la jurisdicción **02** (no 06).
- **PASO 2015 de la DINE**: el enlace del portal da 404.
- **Mapas de ARBA**: Chascomús y Lezama comparten el código viejo 06217; la capa de circuitos
  trae códigos de partido viejos en 8 partidos (Cañuelas, Pilar, Morón…). Ver `etl/02`.
