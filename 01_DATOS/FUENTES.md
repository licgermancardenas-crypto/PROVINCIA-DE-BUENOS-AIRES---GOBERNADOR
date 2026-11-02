# De dónde sale cada dato

`01_DATOS/raw/` no está en el repo. Este archivo es la receta para volver a bajarlo.

```bash
python 02_SCRIPTS/etl/00_descargar_fuentes.py            # baja lo automatizable
python 02_SCRIPTS/etl/00_descargar_fuentes.py --listar   # sólo muestra qué falta
python 02_SCRIPTS/etl/03_municipios_argentinos.py --bajar
```

Si el Atlas CABA está en la misma máquina (`ATLAS_CABA_RAW`), el 00 copia de ahí los ZIP de la
DINE que ya estén, en lugar de rebajarlos. Sólo lee esa carpeta.

---

## Electoral

| Archivo (`raw/`) | Fuente | Notas |
|---|---|---|
| `electoral/dine/AAAA_{generales,paso,balotaje}.zip` | DINE · [resultados electorales](https://www.argentina.gob.ar/dine/resultados-electorales/elecciones-2023), una página por año | Provisorio **por mesa, todo el país**. 2011-2023. Para PBA incluye Gobernador, Legislatura e Intendente cuando fueron simultáneas. Codificación variable (ver bitácora) |
| `electoral/dine/2025_generales.zip` | DINE (copia del Atlas CABA) | Nacional 26-10-2025, provisorio por mesa, con `localesDeVotacionyMesas.csv` (mesa → escuela) |
| `electoral/gba/generales_provinciales_2005_2023.csv` | [Catálogo PBA · Resultados Electorales Provinciales](https://catalogo.datos.gba.gob.ar/dataset/resultados-electorales-provinciales) | **Definitivo** por municipio, categorías provinciales. Incluye Gobernador 2007 |
| `electoral/gba/paso_provinciales_2011_2021.csv` | ídem | PASO, definitivo por municipio |
| `electoral/gba/nacionales_paso_generales_2015_2023.csv` | [Catálogo PBA · Resultados Electorales Nacionales](https://catalogo.datos.gba.gob.ar/dataset/resultados-electorales-nacionales) | Definitivo por municipio, categorías nacionales. El dataset trae además ZIP por categoría 2011-2023 |

### Pendientes

| Qué | Dónde | Estado |
|---|---|---|
| Provincial 7-09-2025 por mesa | Junta Electoral PBA · `resultados.eleccionesbonaerenses.gba.gob.ar` y `juntaelectoral.gba.gob.ar` | por explorar |
| PASO 2015 por mesa | DINE: `dine-resultados/2015-PROVISORIOS_PASO.zip` | **404 en el portal** |

## Geografía

| Archivo | Fuente | Notas |
|---|---|---|
| `geo/limite_partidos_pba.zip` | [Catálogo PBA · Límites de los partidos](https://catalogo.datos.gba.gob.ar/dataset/partidos) | 135 partidos |
| `geo/secciones_electorales_pba.zip` | [Catálogo PBA · Secciones electorales](https://catalogo.datos.gba.gob.ar/dataset/secciones-electorales) | 8 secciones. Origen: WFS de IDEBA |
| `geo/circuitos_electorales_pba.{zip,csv}` | [Catálogo PBA · Circuitos electorales](https://catalogo.datos.gba.gob.ar/dataset/circuitos-electorales) | Actualizado 12-03-2026 |

## Territorio

| Archivo | Fuente | Notas |
|---|---|---|
| `social/municipiosargentinos/*.js` | [MunicipiosArgentinos.net](https://municipiosargentinos.net/) (JS estáticos del sitio) | **Secundaria.** 135 municipios, ~50 indicadores con período y fuente; las fuentes primarias en `processed/municipios_ma_fuentes.csv`. Foto fechada en `FOTO.txt` |
| `social/renabap.geojson` | [archivo.infraestructura.gob.ar](https://archivo.infraestructura.gob.ar/dataset/ssisu/20231205_info_publica.geojson) | Barrios populares, país |
| `social/pbg_partidos_2021_2023.xlsx` | Estadística PBA · desagregación municipal del PBG | PBG por partido |
| `social/empleo_*`, `social/salario_mediano_depto.csv` | Ministerio de Producción · CEP, vía datos.gob.ar | Puestos asalariados registrados y salario por partido (SIPA) |
| `social/snic_departamentos_anual.csv` | Ministerio de Seguridad · SNIC | Delitos por partido y año, 70 MB |
| `social/refeglo_gobiernos_locales.csv` | Ministerio del Interior · ReFeGLo | Registro de gobiernos locales |
| `presupuesto/transferencias_municipios_mensual.csv` | Catálogo PBA · Transferencias a municipios | Mensual 2010-07/2026, por fondo |
| `presupuesto/tributos_descentralizados_anual.csv` | ídem | 2003-2025 |
| `servicios/salud_establecimientos_2025.csv` | Catálogo PBA · Establecimientos de salud | Públicos, 2025 |
| `servicios/establecimientos_educativos.csv` | Catálogo PBA · Establecimientos educativos (DGCyE) | 21.592 con coordenadas, matrícula, nivel y sector (publicación 26/10/2026) |

## Censos (INDEC vía datos.gob.ar)

| Archivo | Qué es | Notas |
|---|---|---|
| `censo/c2022_pba.zip` | Censo 2022, PBA: vivienda, hogar, persona | **Por radio censal**, todas las variables en conteos (`codigo` de 9 dígitos). Diccionarios al lado |
| `censo/c2010_pba.zip`, `c2001_pba.zip` | Ídem 2010 y 2001 | El catálogo publica la URL con `-2022` y da 404: la real termina en `-2010` / `-2001` |
| `censo/c1991_pba.zip` | Ídem 1991 | PBA es la jurisdicción **02** en ese censo |
| `geo/radios_{2022,2010}_pba.zip` | Polígonos de radios, recorte PBA | Catálogo PBA |
| `geo/radios_{2001,1991}_pais.zip` | Polígonos de radios, país | datos.gob.ar |
| `geo/conversion_radios_{2010_2022,2001_2010}.zip` | Conversión de radios entre censos | INDEC |
| `geo/indec_codigos_*.xlsx` | Códigos INDEC 2022: departamentos, gobiernos locales, aglomerados, localidades | INDEC |

## Provincial 2025 (Junta Electoral)

| Archivo | Fuente | Notas |
|---|---|---|
| `electoral/jep2025/distrito_NNN.html` | [Junta Electoral · escrutinio definitivo 2025](https://www.juntaelectoral.gba.gov.ar/escrutinio-definitivo-2025/) | 135 páginas, una por municipio. Las lee `etl/05` |
