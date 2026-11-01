# Plan de trabajo · Atlas PBA

Orden pensado para que cada etapa deje algo usable aunque la siguiente no llegue. Las marcas:
✅ hecho · 🔶 en curso · ⬜ pendiente.

---

## Etapa 1 · La base electoral (columna vertebral)

| | Qué | Script | Estado |
|---|---|---|---|
| 1.1 | Bajar los escrutinios por mesa de la DINE 2011-2025 y el catálogo PBA | `etl/00` | ✅ (falta PASO 2015) |
| 1.2 | Filtrar PBA por mesa, un parquet por elección, con control de totales | `etl/01` | ✅ 15 elecciones |
| 1.3 | Geometrías: partidos, secciones electorales, circuitos + claves DINE↔INDEC | `etl/02` | ✅ |
| 1.4 | Validar el provisorio contra el definitivo por municipio (catálogo PBA 2005-2023) | `etl/06` | ⬜ |
| 1.5 | Mapeo agrupación → espacio político, 2007-2025 (`config/reglas_mapeo.yaml`) | `etl/07` | ⬜ |
| 1.6 | Panel armonizado circuito × elección × categoría × espacio | `etl/08` | ⬜ |
| 1.7 | **Septiembre 2025, provincial desdoblada**: definitivo por municipio ✅ (`etl/05`); por mesa ⬜ (portal dado de baja, buscar en Wayback) | `etl/05` | 🔶 |
| 1.8 | Gobernador 2007 (anterior a la serie por mesa de la DINE) por municipio | — | ⬜ |
| 1.9 | Circuitos estables en el tiempo: tabla de equivalencias 2011-2025 (1.047 circuitos en 2023, 934 en 2011) | — | ⬜ |

Las elecciones a Gobernador con dato por mesa: **2011, 2015, 2019, 2023** (simultáneas con la
nacional, vienen en el archivo de la DINE). Más las legislativas 2013, 2017, 2021, la provincial
desdoblada de septiembre 2025 y la nacional de octubre 2025.

## Etapa 2 · El territorio

| | Qué | Estado |
|---|---|---|
| 2.1 | Censo 2022 por radio (INDEC) → circuito. **Crudo bajado**: 76 variables en conteos por radio | ⬜ ← próximo |
| 2.2 | Censos 2010, 2001 y 1991 por radio, con las tablas de conversión de radios. **Crudo bajado** | ⬜ |
| 2.3 | Indicadores por municipio de MunicipiosArgentinos.net (fiscal, servicios, control, intendente) | ✅ `etl/03` |
| 2.4 | RENABAP: barrios populares → circuito (en PBA son ~1.900) | ⬜ |
| 2.5 | Escuelas (padrón DGCyE) y salud (establecimientos públicos 2025, **bajado**) → circuito | ⬜ |
| 2.6 | Presupuesto: transferencias provinciales a municipios por fondo 2010-2026 (**bajado**), tributos descentralizados, PBG por partido (**bajado**) | ⬜ |
| 2.7 | Delito por partido (SNIC, **bajado**), empleo y salario registrado por partido (SIPA, **bajado**), AUH/planes | ⬜ |
| 2.8 | Proyecciones de población y padrón 2027 | ⬜ |

## Etapa 3 · Análisis con hallazgos probados

Cada pregunta con su batería, los tres filtros y su tabla. Primeras candidatas:

- **Arrastre del intendente**: ¿cuánto mueve un intendente propio el voto a Gobernador? Hay
  Intendente y Gobernador por mesa en 2011, 2015, 2019 y 2023: el corte de boleta es medible.
- **Conurbano contra interior**: ¿es una sola elección o dos?
- **Retención y transferencia 2023 → 2025** (Kicillof → Fuerza Patria; JxC → LLA), con
  inferencia ecológica por circuito.
- **Desdoblamiento**: septiembre contra octubre 2025, mismo año, dos padrones, dos resultados.
- **Lo que el territorio predice y lo que no**: nivel contra cambio, como en CABA.

## Etapa 4 · El motor 2027

Mismo diseño que CABA, adaptado: backtest sobre los pares de elecciones de Gobernador y
legislativas, shock provincial con colas pesadas, ruido por sección / municipio / circuito,
Monte Carlo por escenario. **Simple pluralidad, sin balotaje.** El nivel provincial y la oferta
entran como parámetro. Legislatura por sección electoral con cociente.

## Etapa 5 · Productos

Plataforma web, simulador, informes. Se definen cuando haya resultados.

---

## Pendientes que dependen de un tercero

- Mesa a mesa de la **provincial del 7-09-2025** (Junta Electoral PBA, `resultados.eleccionesbonaerenses.gba.gob.ar`).
- ZIP de **octubre 2025** en la web de la DINE (hoy se usa la copia del Atlas CABA).
- **PASO 2015** por mesa: el enlace del portal de la DINE da 404.
- Proyectos de datos de **Martín Yeza** que mencionó el cliente: falta el enlace.
- **IGN** (capas SIG) y el **portal ArcGIS de Estadística PBA**: no responden a pedidos automáticos desde esta máquina.

El relevamiento completo de fuentes, con veredicto por cada una, está en [`01_DATOS/RELEVAMIENTO.md`](../01_DATOS/RELEVAMIENTO.md).
