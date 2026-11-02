# Atlas PBA · Gobernador 2027

Inteligencia electoral de la Provincia de Buenos Aires para la elección de Gobernador de 2027.
Es la versión provincial del Atlas CABA: misma lógica, otra escala. La unidad de trabajo es el
**circuito electoral** y, donde el dato lo permite, la **mesa**; arriba de eso, **municipio**
(135) y **sección electoral** (8).

> Estado: **arranque** (noviembre 2026). Qué está hecho y qué falta, en
> [`00_DOCS/PLAN.md`](00_DOCS/PLAN.md). Cada decisión y cada trampa, en la bitácora
> [`00_DOCS/README.md`](00_DOCS/README.md).

---

## Qué se construye

1. **Una base** que cruza el voto histórico con el territorio a la escala más fina posible:
   mesa → circuito → municipio → sección electoral, contra censo 2022, condiciones de vida,
   servicios y presupuesto.
2. **Análisis con hallazgos probados**: nada se publica sin pasar los tres filtros de la casa.
3. **Un motor de escenarios 2027** que se examina contra elecciones pasadas: se entrena con
   elecciones viejas y se juzga por cómo predice una que no vio.

## Empezar

```bash
pip install pandas numpy scipy scikit-learn geopandas pyarrow duckdb matplotlib openpyxl
python 02_SCRIPTS/etl/00_descargar_fuentes.py --listar   # qué hay y qué falta
python 02_SCRIPTS/etl/00_descargar_fuentes.py            # baja lo automatizable
python 02_SCRIPTS/etl/01_mesas_dine_pba.py               # DINE país -> mesas de PBA (parquet)
python 02_SCRIPTS/etl/02_geo_base.py                     # partidos, secciones, circuitos, claves
python 02_SCRIPTS/etl/03_municipios_argentinos.py        # indicadores por municipio (secundaria)
python 02_SCRIPTS/etl/04_inventario_catalogos.py         # inventario de los catálogos CKAN
python 02_SCRIPTS/etl/05_jep_definitivo_2025.py          # provincial 7-09-2025 por municipio
python 02_SCRIPTS/etl/06_censo2022_circuitos.py          # censo 2022: radio -> circuito
python 02_SCRIPTS/etl/07_censos_historicos_circuitos.py  # censos 1991, 2001, 2010 -> circuitos actuales
python 02_SCRIPTS/etl/08_mapeo_espacios.py              # lista -> espacio político (config/reglas_mapeo.yaml)
python 02_SCRIPTS/etl/09_panel_armonizado.py             # panel por circuito y por municipio
python 02_SCRIPTS/etl/10_circuitos_estables.py           # equivalencias de circuitos 2011-2025
```

`01_DATOS/raw/` **no se versiona** (750 MB: escrutinios de la DINE, cuatro censos por radio).
La receta para volver a bajarlo todo está en [`01_DATOS/FUENTES.md`](01_DATOS/FUENTES.md) y el
veredicto sobre cada portal revisado, en [`01_DATOS/RELEVAMIENTO.md`](01_DATOS/RELEVAMIENTO.md).
Lo derivado sí se versiona, incluidos los parquets de mesas (57 MB).

## Qué hay hoy

| Tabla | Qué es |
|---|---|
| `01_DATOS/processed/panel_circuito.parquet` | **El panel**: voto por espacio político, circuito × elección × categoría, 2011-2025, con electores y votantes nativos y extranjeros |
| `01_DATOS/processed/panel_municipio.parquet` | Lo mismo por municipio, con el definitivo de la Provincia (2005-2023, incluye Gobernador 2007) y la Junta 2025 |
| `01_DATOS/processed/circuitos_equivalencias.csv` · `circuitos_estables_serie.csv` | **Circuitos estables**: cada código de circuito → su CE en cuatro ventanas (2011, 2015, 2019 y 2023 a 2025), y el padrón por CE y año. Polígonos en `geo/circuitos_estables.gpkg` |
| `03_OUTPUTS/tablas/motor_2027_*.csv` | **Motor 2027**: escenarios de Gobernador con Monte Carlo, por sección, municipio y circuito, y la grilla de margen (`analisis/106`) |
| `00_DOCS/HALLAZGOS.md` | Los hallazgos de los análisis, con estado, script y tabla |
| `config/mapeo_espacios.csv` · `00_DOCS/mapeo_espacios.md` | Cada lista con su espacio, y las decisiones validadas |
| `01_DATOS/processed/mesas_dine_pba_<año>_<tipo>.parquet` | 15 elecciones por mesa, 2011-2025: Gobernador 2011-2023, Intendente, Legislatura, nacionales |
| `03_OUTPUTS/tablas/control_dine_pba.csv` | Totales por elección y categoría: mesas, electores, mesas de extranjeros, circuitos |
| `01_DATOS/processed/jep_2025_municipio*.csv` | Provincial 7-09-2025, definitivo por municipio |
| `01_DATOS/processed/geo/*.gpkg` | 135 partidos, 8 secciones, 1.146 circuitos |
| `01_DATOS/processed/censo2022_circuito.csv` | **Censo 2022 por circuito**: 43 indicadores (edad, educación, empleo, salud, migración, NBI, privación, servicios, hacinamiento, conectividad, tenencia) con sus conteos, y `calidad_cruce` contra el padrón |
| `01_DATOS/processed/censo2022_radio.csv` · `radio_circuito_2022.csv` | Lo mismo por radio, y el reparto radio → circuito con su peso |
| `01_DATOS/processed/censo2022_radio_conteos.parquet` | Las 32 variables en conteos por radio y categoría, para armar indicadores nuevos |
| `01_DATOS/processed/censos_circuito_serie.csv` | **Cuatro censos (1991-2022) en los circuitos de hoy**: circuito × censo, 19 indicadores comparables |
| `01_DATOS/processed/censos_circuito_cambios.csv` | Un circuito por fila: los indicadores de cada censo, crecimiento y cambios entre censos, y `cambio_confiable_*` |
| `01_DATOS/processed/municipios_claves.csv` | Código INDEC ↔ `seccion_id` DINE ↔ distrito de la Junta, sección y Conurbano |
| `01_DATOS/processed/municipios_ma.csv` | 135 municipios × 186 columnas: fiscal, servicios, control, intendente |
| `01_DATOS/inventario_catalogos.csv` | Todo lo publicado en los catálogos CKAN de PBA y Nación |

## Cómo está organizado

| Carpeta | Qué hay |
|---|---|
| `00_DOCS/` | Bitácora (`README.md`), plan de trabajo (`PLAN.md`) y, cuando haya, `HALLAZGOS.md` |
| `01_DATOS/` | `raw/` sin versionar · `processed/` con las tablas intermedias · `FUENTES.md` |
| `02_SCRIPTS/` | `etl/` · `analisis/` · `mapas/` · `docs/`. Numerados en orden de escritura |
| `03_OUTPUTS/` | Tablas de resultado y láminas |
| `04_REPORTES/` · `05_ENTREGABLES/` | HTML de cada informe y los PDF que se entregan |
| `06_ACTORES/` | Competencia: candidatos, intendentes, alianzas |
| `07_PEDIDOS_INFO/` | Pedidos de acceso a la información (Ley 12.475 PBA, Ley 27.275) |
| `src/` · `config/` | El motor 2027 (Monte Carlo, backtest, escenarios) |
| `10_PRODUCTOS/` | Lo que se entrega del escenario 2027 |

Cada script abre con un encabezado que dice **qué pregunta contesta, qué supone y qué no puede
afirmar**.

---

## Reglas de la casa

Heredadas del Atlas CABA, donde cada una se rompió al menos una vez.

**El denominador es el padrón que corresponde a la categoría.** En PBA los extranjeros
residentes votan en las categorías provinciales y municipales, no en las nacionales. Una
elección provincial desdoblada (2025) y una nacional (octubre 2025) no tienen el mismo padrón:
compararlas sin separarlo inventa caídas de participación que no existen.

**Toda correlación va sobre rangos y con la clase descontada.** Spearman parcial controlando
composición social (NBI, educación, edad), siempre con `log(electores)`: en PBA un circuito de
La Matanza puede tener cien veces el padrón de uno del interior.

**Nada se publica sin pasar tres filtros**: Benjamini-Hochberg sobre la batería entera, control
de composición social y prueba de fragilidad por distancia de Cook (sin el caso más influyente y
sin los tres).

**Se valida por grupo, no por caso.** Con circuitos como unidad, `GroupKFold` por municipio: si
no, el modelo reconoce el municipio en vez de predecir.

**Los resultados negativos se publican.** Cierran hipótesis que un rival va a proponer.

**El nivel provincial entra como parámetro, no sale del modelo.** El motor dice **dónde** va a
estar el voto; cuánto va a ser —desdoblar o no, PASO o no, la oferta— lo decide quien lo usa.

---

## Lo que distingue a PBA de CABA

- **Gobernador se elige por simple pluralidad, sin balotaje.** La pregunta del motor no es
  «quién pasa al 50 %» sino «quién saca un voto más».
- **El Conurbano pesa ~64 % del padrón** y el interior es otro país: 135 municipios con
  intendentes propios, cuyo arrastre sobre la boleta provincial hay que medir, no suponer.
- **La Legislatura se elige por sección electoral** (8), con renovación por mitades.
- **La geografía no es una sola ciudad**: densidad, distancia y ruralidad son variables, no
  ruido.
