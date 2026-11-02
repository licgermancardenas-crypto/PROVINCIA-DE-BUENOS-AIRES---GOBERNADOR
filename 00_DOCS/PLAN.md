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
| 1.4 | Validar el provisorio contra el definitivo por municipio: ≤ 0,17 pp por espacio en todas las categorías provinciales | `etl/08` | ✅ |
| 1.5 | Mapeo agrupación → espacio político, 2005-2025, validado (D1-D9) | `etl/08` | ✅ |
| 1.6 | Panel armonizado circuito × elección × categoría × espacio, y por municipio con todas las fuentes | `etl/09` | ✅ |
| 1.7 | **Septiembre 2025, provincial desdoblada**: definitivo por municipio ✅ (`etl/05`); por mesa ⬜ (portal dado de baja, buscar en Wayback) | `etl/05` | 🔶 |
| 1.8 | Gobernador 2007 (anterior a la serie por mesa de la DINE) por municipio | `etl/09` | ✅ en `panel_municipio` |
| 1.9 | Circuitos estables en el tiempo: tabla de equivalencias 2011-2025, en cuatro ventanas (919 CE en 2011-2025, 1.033 en 2023-2025) | `etl/10` | ✅ |

Las elecciones a Gobernador con dato por mesa: **2011, 2015, 2019, 2023** (simultáneas con la
nacional, vienen en el archivo de la DINE). Más las legislativas 2013, 2017, 2021, la provincial
desdoblada de septiembre 2025 y la nacional de octubre 2025.

## Etapa 2 · El territorio

| | Qué | Estado |
|---|---|---|
| 2.1 | Censo 2022 por radio (INDEC) → circuito: 43 indicadores, validado contra INDEC y padrón | ✅ `etl/06` |
| 2.2 | Censos 2010, 2001 y 1991 → circuitos actuales: 19 indicadores comparables, cambios entre censos con marca de confiabilidad | ✅ `etl/07` |
| 2.3 | Indicadores por municipio de MunicipiosArgentinos.net (fiscal, servicios, control, intendente) | ✅ `etl/03` |
| 2.4 | RENABAP: barrios populares → circuito (en PBA son ~1.900) | ⬜ |
| 2.5 | Escuelas (padrón DGCyE) y salud (establecimientos públicos 2025, **bajado**) → circuito | ⬜ |
| 2.6 | Presupuesto: transferencias provinciales a municipios por fondo 2010-2026 (**bajado**), tributos descentralizados, PBG por partido (**bajado**) | ⬜ |
| 2.7 | Delito por partido (SNIC, **bajado**), empleo y salario registrado por partido (SIPA, **bajado**), AUH/planes | ⬜ |
| 2.8 | Proyecciones de población y padrón 2027 | ⬜ |

## Etapa 3 · Análisis con hallazgos probados

Cada pregunta con su batería, los tres filtros y su tabla. Primeras candidatas:

- ✅ **Arrastre del intendente** (`analisis/100`): ganar la intendencia no mueve el voto a
  Gobernador siguiente (efecto 0, IC ±4 pp) aunque sí el de Intendente (+7 pp). El arrastre va
  de arriba hacia abajo. Ver bitácora y `HALLAZGOS.md`.
- ✅ **Conurbano contra interior** (`analisis/101`): dos electorados en el nivel (+4 a +6 pp
  peronistas con la misma composición), una sola elección en el cambio (los movimientos son
  provinciales y parejos).
- ✅ **Retención y transferencia 2023 → 2025** (`analisis/102`): Kicillof → Fuerza Patria 82 %
  (79-84), Santilli → LLA-PRO 77 % (75-79), Píparo → no votó 22 % (15-29).
- ✅ **Desdoblamiento** (`analisis/103`): de septiembre a octubre LLA-PRO sumó 957.000 votos y
  Fuerza Patria perdió 140.000. No es el padrón extranjero (0,5 pp). Fuerza Patria cayó donde
  gobierna un intendente peronista; LLA-PRO creció en el interior y donde había voto vecinal.
- ✅ **Lo que el territorio predice y lo que no** (`analisis/104`): el nivel lo predice la
  inercia (R² 0,90-0,96) y el censo casi no agrega; el cambio es sobre todo proporcional al nivel
  de partida, y el censo agrega poco (+0,03 a +0,14).

## Etapa 4 · El motor 2027

Mismo diseño que CABA, adaptado: backtest sobre los pares de elecciones de Gobernador y
legislativas, shock provincial con colas pesadas, ruido por sección / municipio / circuito,
Monte Carlo por escenario. **Simple pluralidad, sin balotaje.** El nivel provincial y la oferta
entran como parámetro. Legislatura por sección electoral con cociente.

| | Qué | Estado |
|---|---|---|
| 4.1 | Backtest de la regla de traslado (13 pares 2011-2025) y calibración del ruido | ✅ `analisis/105` |
| 4.2 | Motor de escenarios con Monte Carlo: base octubre o septiembre 2025, padrón 2027, extranjeros, participación | ✅ `analisis/106` |
| 4.3 | Derecha dividida (LLA y PRO por separado, patrón de 2023) | ✅ `analisis/107` |
| 4.4 | Legislatura 2027 por sección (cociente y renovación por mitades) | ✅ `analisis/108` |
| 4.5 | Movilización diferencial: quién va a votar, no sólo cuántos (perfil del votante marginal como parámetro) | ✅ `analisis/109` |
| 4.6 | Autocorrelación espacial: ruido por sección en el motor y hallazgos con modelo de error espacial | ✅ `analisis/110` |

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
