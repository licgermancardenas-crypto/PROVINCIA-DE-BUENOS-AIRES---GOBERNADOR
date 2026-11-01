# -*- coding: utf-8 -*-
"""
ETL 07 · Censos 1991, 2001 y 2010 llevados a los circuitos actuales, con un juego de
indicadores comparable entre los cuatro censos (con 2022).

    python 02_SCRIPTS/etl/07_censos_historicos_circuitos.py

Qué contesta: cómo cambió cada circuito de hoy entre 1991, 2001, 2010 y 2022 —población,
edad, llegada a la universidad, NBI, hacinamiento, cloaca, tenencia, computadora,
materiales, desocupación, migración externa, agua y gas de red, ruralidad—. Deja:
- `01_DATOS/processed/censo{1991,2001,2010}_radio_conteos.parquet` (conteos por radio)
- `01_DATOS/processed/radio_circuito_{1991,2001,2010}.csv` (reparto radio -> circuito)
- `01_DATOS/processed/censos_circuito_serie.csv`: circuito × censo, largo
- `01_DATOS/processed/censos_circuito_cambios.csv`: circuito, ancho, con los cambios entre censos
- `03_OUTPUTS/tablas/control_censos_historicos.csv`: población por censo y partido

Qué supone:
- **Cada censo se reparte sobre sus propios radios** con el mismo método que el 06 (área,
  entero si ≥ 95 %). No se pasa por las tablas de conversión del INDEC: un solo método para
  los cuatro censos y ninguna cadena de conversiones que acumule error. Las tablas de
  conversión quedan para validar.
- **Sólo indicadores que miden lo mismo en todos los censos donde aparecen.** Lo que cambió de
  pregunta queda afuera de ese censo (NA), no se fuerza:
  * agua de red: sólo 2010 y 2022 (en 2001 y 1991 se preguntó si el agua llega por cañería
    dentro de la vivienda, que es otra cosa);
  * país de nacimiento: falta 2001 (la variable que el diccionario llama «lugar de nacimiento»
    da 5.899 nacidos en otro país; no es esa pregunta);
  * educación: falta 1991 (el nivel sólo se registra para quienes estudiaban);
  * NBI, hacinamiento, computadora, materiales, desocupación: faltan en 1991.
- «Llegó a la universidad» = cursa o cursó universitario o posgrado, completo o no, sobre la
  **población total** (el universo de cada pregunta cambia entre censos; el total no).
- Edad en tramos que salen de los grupos quinquenales: 0-14, 15-29, 30-44, 45-64, 65+.
- 1991: las tablas usan el código 02 para Buenos Aires y los polígonos 06; el resto del código
  (departamento, fracción, radio) coincide. Los códigos 1-4 de lugar de nacimiento no traen
  etiqueta: 3 y 4 se leen como «otro país» (suman 6,3 % de la población, en línea con lo
  publicado para PBA). Inferencia: está marcada.

Qué no puede afirmar:
- La desocupación de 2001 (32,9 % en PBA) no es comparable con 2010 ni 2022: ese censo la
  medía muy por encima de la EPH. No se calculan cambios desde 2001 para ese indicador.
- La población de 1991, 2001 y 2010 incluye viviendas colectivas (cárceles, geriátricos); la
  de 2022 por radio, no. Entre 2010 y 2022 eso resta ~0,7 % al crecimiento provincial y mucho
  más en partidos con penales. `crec_pob_10_22` lo arrastra: en esos partidos, no leerlo.
- Los cambios entre censos se anulan (NaN) si el circuito tiene menos de 200 habitantes en
  alguno de los dos censos, y `cambio_confiable_*` marca los de 500+: con menos, el reparto
  por área de radios rurales inventa crecimientos de miles por ciento.
- La capa de radios 2010 está corrida más de 1 km en 5 partidos (Tres Lomas 4,9 km,
  Exaltación de la Cruz, General Rodríguez, Salliqueló, General Alvear): se mide comparando
  el mismo código de radio en 2010 y 2022, y esos circuitos quedan `cambio_confiable_10_22 =
  False` y `geo_2010_corrida = True`.
- Junín rural: las tablas de 2010 dejan sin población radios rurales (0701, 0702) y la cargan
  en otros códigos. Los polígonos coinciden con 2022; el error es de la fuente y lo cubre la
  marca de confiabilidad (son circuitos de menos de 500 habitantes).
- En el campo, un radio grande partido entre circuitos se reparte por área: el pueblo puede
  estar todo de un lado. Los radios de 1991 son más grandes que los de 2022, así que el error
  crece hacia atrás.
"""
import sys
from importlib import import_module
from pathlib import Path

import duckdb
import geopandas as gpd
import numpy as np
import pandas as pd
import zipfile

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
e06 = import_module("06_censo2022_circuitos")

RAW = RAIZ / "01_DATOS" / "raw"
OUT = RAIZ / "01_DATOS" / "processed"
TABLAS = RAIZ / "03_OUTPUTS" / "tablas"

VARS = {
    "2010": ["PERSONA_P02", "PERSONA_EDADQUI", "PERSONA_P05", "PERSONA_P1909", "PERSONA_CONDACT",
             "HOGAR_ALGUNBI", "HOGAR_INDHAC", "HOGAR_H1409", "HOGAR_H1712", "HOGAR_H2014", "HOGAR_PROP",
             "HOGAR_H2819B", "VIVIENDA_INMAT", "VIVIENDA_URP"],
    "2001": ["PERSONA_P2", "PERSONA_EDADQUI", "PERSONA_CP4", "PERSONA_CP63", "HOGAR_CHNBI", "HOGAR_HACIAGRU",
             "HOGAR_CH9", "HOGAR_CH6", "HOGAR_CH26", "HOGAR_CH28", "VIVIENDA_URP"],
    "1991": ["PERSONA_SEXO", "PERSONA_EDAD", "PERSONA_LUGARNAC", "HOGAR_DESAGUE", "HOGAR_TENENCIA",
             "VIVIENDA_VILLA"],
}
POLIGONOS = {
    "2010": ("radios_2010_pba.zip", "radios-censales.geojson", "link"),
    "2001": ("radios_2001_pais.zip", "radios-censales-2001.shp", "codigo"),
    "1991": ("radios_1991_pais.zip", "radios-censales-1991.shp", "codigo"),
    "2022": ("radios_2022_pba.zip", "radios-censales.geojson", "LINK"),
}
EDADQUI = {"e0_14": range(1, 4), "e15_29": range(4, 7), "e30_44": range(7, 10),
           "e45_64": range(10, 14), "e65_mas": range(14, 23)}
EDAD_SIMPLE = {"e0_14": (0, 14), "e15_29": (15, 29), "e30_44": (30, 44), "e45_64": (45, 64), "e65_mas": (65, 200)}

# indicador común: (numerador, denominador), en conteos
COMUNES = {
    "pct_mujeres": ("mujeres", "pob"),
    "pct_0_14": ("e0_14", "pob"), "pct_15_29": ("e15_29", "pob"), "pct_30_44": ("e30_44", "pob"),
    "pct_45_64": ("e45_64", "pob"), "pct_65_mas": ("e65_mas", "pob"),
    "pct_llego_universidad": ("univ", "pob"),
    "pct_hog_nbi": ("hog_nbi", "hog_nbi_den"),
    "pct_hog_hacinamiento_critico": ("hog_hacin", "hog_hacin_den"),
    "pct_hog_cloaca": ("hog_cloaca", "hog_cloaca_den"),
    "pct_hog_propietario": ("hog_prop", "hog_prop_den"),
    "pct_hog_computadora": ("hog_compu", "hog_compu_den"),
    "pct_materiales_malos": ("mat_malos", "mat_den"),
    "tasa_desocupacion": ("desoc", "activos"),
    "pct_nac_otro_pais": ("nac_otro_pais", "nac_den"),
    "pct_hog_agua_red": ("hog_agua_red", "hog_agua_den"),
    "pct_hog_gas_red": ("hog_gas_red", "hog_gas_den"),
    "pct_viv_rural": ("viv_rural", "viv_den"),
    "pct_viv_villa": ("viv_villa", "viv_villa_den"),
}
CONTEOS = sorted({x for par in COMUNES.values() for x in par})
BASE_MIN = 200  # habitantes mínimos en los dos censos para calcular un cambio


def extraer(anio: str) -> pd.DataFrame:
    destino = OUT / f"censo{anio}_radio_conteos.parquet"
    inter = RAIZ / "01_DATOS" / "interim" / f"censo{anio}"
    inter.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(RAW / "censo" / f"c{anio}_pba.zip") as z:
        for n in z.namelist():
            if not (inter / n).exists():
                z.extract(n, inter)
    archivos = [p.as_posix() for p in sorted(inter.glob("*.csv"))]
    lista = ", ".join(f"'{v}'" for v in VARS[anio])
    con = duckdb.connect()
    con.execute("SET memory_limit='1500MB'")
    # Las etiquetas traen comas adentro: comillas explícitas, o DuckDB detecta mal el formato.
    con.execute(f"""
        COPY (SELECT codigo, cod_variable, CAST(cod_categoria AS VARCHAR) AS cod_categoria,
                     ANY_VALUE(categoria) AS categoria, SUM(CAST(cantidad AS BIGINT))::BIGINT AS cantidad
              FROM read_csv({archivos}, header=true, union_by_name=true, all_varchar=true,
                            quote='"', escape='"', delim=',')
              WHERE cod_variable IN ({lista})
              GROUP BY codigo, cod_variable, cod_categoria)
        TO '{destino.as_posix()}' (FORMAT parquet, COMPRESSION zstd)""")
    c = pd.read_parquet(destino)
    assert set(VARS[anio]) <= set(c.cod_variable), set(VARS[anio]) - set(c.cod_variable)
    return c


def ancho(c: pd.DataFrame) -> pd.DataFrame:
    return c.assign(col=c.cod_variable + "__" + c.cod_categoria).pivot_table(
        index="codigo", columns="col", values="cantidad", aggfunc="sum", fill_value=0)


def s(w, var, cats=None):
    return e06.suma(w, var, cats)


def edad_quinquenal(w, var):
    return {k: s(w, var, list(r)) for k, r in EDADQUI.items()}


def edad_simple(w, var):
    edades = {int(k.split("__")[1]): w[k] for k in w.columns
              if k.startswith(var + "__") and k.split("__")[1].isdigit()}
    return {k: sum(v for e, v in edades.items() if a <= e <= b) for k, (a, b) in EDAD_SIMPLE.items()}


def comunes_2022(w):
    hog = s(w, "HOGAR_NBI_TOT")
    return {"pob": s(w, "PERSONA_P02"), "mujeres": s(w, "PERSONA_P02", [1]), **edad_simple(w, "PERSONA_EDAD"),
            "univ": s(w, "PERSONA_MNI", [8, 9, 10, 11]),
            "hog_nbi": s(w, "HOGAR_NBI_TOT", [1]), "hog_nbi_den": hog,
            "hog_hacin": s(w, "HOGAR_H20CP", [6]), "hog_hacin_den": s(w, "HOGAR_H20CP"),
            "hog_cloaca": s(w, "HOGAR_H18", [1]), "hog_cloaca_den": hog,
            "hog_prop": s(w, "HOGAR_H22", [1]), "hog_prop_den": s(w, "HOGAR_H22"),
            "hog_compu": s(w, "HOGAR_H24C", [1]), "hog_compu_den": s(w, "HOGAR_H24C"),
            "mat_malos": s(w, "HOGAR_INMAT", [3, 4]), "mat_den": s(w, "HOGAR_INMAT", [1, 2, 3, 4]),
            "desoc": s(w, "PERSONA_CONDACT", [2]), "activos": s(w, "PERSONA_CONDACT", [1, 2]),
            "nac_otro_pais": s(w, "PERSONA_P13", [3]), "nac_den": s(w, "PERSONA_P13"),
            "hog_agua_red": s(w, "HOGAR_H14", [1]), "hog_agua_den": s(w, "HOGAR_H14"),
            "hog_gas_red": s(w, "HOGAR_H19", [2]), "hog_gas_den": s(w, "HOGAR_H19"),
            "viv_rural": s(w, "VIVIENDA_URP", [2, 3]), "viv_den": s(w, "VIVIENDA_URP", [1, 2, 3])}


def comunes_2010(w):
    hog = s(w, "HOGAR_ALGUNBI", [0, 1])
    return {"pob": s(w, "PERSONA_P02"), "mujeres": s(w, "PERSONA_P02", [2]), **edad_quinquenal(w, "PERSONA_EDADQUI"),
            "univ": s(w, "PERSONA_P1909", [7, 8]),
            "hog_nbi": s(w, "HOGAR_ALGUNBI", [1]), "hog_nbi_den": hog,
            "hog_hacin": s(w, "HOGAR_INDHAC", [6]), "hog_hacin_den": s(w, "HOGAR_INDHAC", [1, 2, 3, 4, 5, 6]),
            "hog_cloaca": s(w, "HOGAR_H1712", [1]), "hog_cloaca_den": hog,
            "hog_prop": s(w, "HOGAR_PROP", [1, 2]), "hog_prop_den": s(w, "HOGAR_PROP", [1, 2, 3, 4, 5, 6]),
            "hog_compu": s(w, "HOGAR_H2819B", [1]), "hog_compu_den": s(w, "HOGAR_H2819B", [1, 2]),
            "mat_malos": s(w, "VIVIENDA_INMAT", [3, 4]), "mat_den": s(w, "VIVIENDA_INMAT", [1, 2, 3, 4]),
            "desoc": s(w, "PERSONA_CONDACT", [2]), "activos": s(w, "PERSONA_CONDACT", [1, 2]),
            "nac_otro_pais": s(w, "PERSONA_P05", [2]), "nac_den": s(w, "PERSONA_P05", [1, 2]),
            "hog_agua_red": s(w, "HOGAR_H1409", [1]), "hog_agua_den": s(w, "HOGAR_H1409", [1, 2, 3, 4, 5, 6]),
            "hog_gas_red": s(w, "HOGAR_H2014", [1]), "hog_gas_den": s(w, "HOGAR_H2014", [1, 2, 3, 4, 5, 6, 7]),
            "viv_rural": s(w, "VIVIENDA_URP", [2, 3]), "viv_den": s(w, "VIVIENDA_URP", [1, 2, 3])}


def comunes_2001(w):
    hog = s(w, "HOGAR_CHNBI", [1, 2])
    return {"pob": s(w, "PERSONA_P2"), "mujeres": s(w, "PERSONA_P2", [2]), **edad_quinquenal(w, "PERSONA_EDADQUI"),
            # asiste universitario (11, 12) o asistió (32, 35, 36), completo o no
            "univ": s(w, "PERSONA_CP4", [11, 12, 32, 35, 36]),
            "hog_nbi": s(w, "HOGAR_CHNBI", [2]), "hog_nbi_den": hog,
            "hog_hacin": s(w, "HOGAR_HACIAGRU", [6]), "hog_hacin_den": s(w, "HOGAR_HACIAGRU", [1, 2, 3, 4, 5, 6]),
            "hog_cloaca": s(w, "HOGAR_CH9", [1]), "hog_cloaca_den": hog,
            "hog_prop": s(w, "HOGAR_CH6", [1, 2]), "hog_prop_den": s(w, "HOGAR_CH6", [1, 2, 3, 4, 5, 6]),
            "hog_compu": s(w, "HOGAR_CH26", [1, 2]), "hog_compu_den": s(w, "HOGAR_CH26", [1, 2, 3]),
            "mat_malos": s(w, "HOGAR_CH28", [3, 4, 5]), "mat_den": s(w, "HOGAR_CH28", [1, 2, 3, 4, 5]),
            # condición combinada: 1-4 trabaja, 5-8 busca trabajo
            "desoc": s(w, "PERSONA_CP63", [5, 6, 7, 8]), "activos": s(w, "PERSONA_CP63", [1, 2, 3, 4, 5, 6, 7, 8]),
            "viv_rural": s(w, "VIVIENDA_URP", [2, 3]), "viv_den": s(w, "VIVIENDA_URP", [1, 2, 3])}


def comunes_1991(w):
    return {"pob": s(w, "PERSONA_SEXO"), "mujeres": s(w, "PERSONA_SEXO", [2]), **edad_simple(w, "PERSONA_EDAD"),
            "hog_cloaca": s(w, "HOGAR_DESAGUE", [1]), "hog_cloaca_den": s(w, "HOGAR_DESAGUE"),
            "hog_prop": s(w, "HOGAR_TENENCIA", [1, 2]), "hog_prop_den": s(w, "HOGAR_TENENCIA", [1, 2, 3, 4, 5, 6, 7]),
            # códigos 1-4 sin etiqueta: 3 y 4 = otro país (inferido, ver encabezado)
            "nac_otro_pais": s(w, "PERSONA_LUGARNAC", [3, 4]), "nac_den": s(w, "PERSONA_LUGARNAC", [1, 2, 3, 4]),
            "viv_villa": s(w, "VIVIENDA_VILLA", [1]), "viv_villa_den": s(w, "VIVIENDA_VILLA", [1, 2])}


DEF = {"2022": comunes_2022, "2010": comunes_2010, "2001": comunes_2001, "1991": comunes_1991}


def poligonos(anio: str) -> gpd.GeoDataFrame:
    z, n, col = POLIGONOS[anio]
    g = gpd.read_file(f"zip://{RAW / 'geo' / z}!{n}")
    g = g.rename(columns={col: "codigo"})
    g["codigo"] = g.codigo.astype(str).str.zfill(9)
    return g[g.codigo.str.startswith("06")][["codigo", "geometry"]]


def indicadores(d: pd.DataFrame) -> pd.DataFrame:
    nuevos = {k: (100 * d[n] / d[den].where(d[den] > 0)).round(2) if n in d and den in d else np.nan
              for k, (n, den) in COMUNES.items()}
    return pd.concat([d.reset_index(drop=True), pd.DataFrame(nuevos, index=range(len(d)))], axis=1)


def por_circuito(anio: str, controles: list) -> pd.DataFrame:
    c = pd.read_parquet(OUT / "censo2022_radio_conteos.parquet") if anio == "2022" else extraer(anio)
    if anio == "1991":
        c["codigo"] = "06" + c.codigo.str[2:]
    w = ancho(c)
    radio = pd.DataFrame(DEF[anio](w)).reset_index()
    g = poligonos(anio)
    rep, _ = e06.repartir(g)
    sin_pol = radio[~radio.codigo.isin(g.codigo)]
    cols = [k for k in radio.columns if k != "codigo"]
    x = rep.merge(radio, on="codigo")
    x[cols] = x[cols].mul(x.peso, axis=0)
    x["pob_en_radios_partidos"] = np.where(x.partido_entre_circuitos, x.pob, 0)
    circ = x.groupby(["circuito", "cod_indec"])[cols + ["pob_en_radios_partidos"]].sum().reset_index()
    circ.insert(0, "censo", int(anio))
    if anio != "2022":
        rep.to_csv(OUT / f"radio_circuito_{anio}.csv", index=False, encoding="utf-8")
    controles.append({"censo": int(anio), "pob_tablas": int(radio.pob.sum()),
                      "pob_en_circuitos": round(circ.pob.sum()),
                      "radios_tabla": len(radio), "radios_poligono": g.codigo.nunique(),
                      "radios_sin_poligono": len(sin_pol), "pob_sin_poligono": int(sin_pol.pob.sum()),
                      "pob_en_radios_partidos_pct": round(100 * circ.pob_en_radios_partidos.sum() / circ.pob.sum(), 2)})
    print(f"  {anio}: {len(radio):,} radios con tabla · {g.codigo.nunique():,} polígonos · sin polígono "
          f"{len(sin_pol)} ({int(sin_pol.pob.sum()):,} personas) · pob {radio.pob.sum():,.0f} -> circuitos {circ.pob.sum():,.0f}")
    return circ


def desplazamiento_2010() -> pd.DataFrame:
    """Los radios urbanos suelen conservar el código entre 2010 y 2022: la distancia entre los
    dos polígonos del mismo código mide si la capa de 2010 de un partido está corrida. Mediana
    provincial: ~100 m. (Con 2001 no sirve: el INDEC renumeró los radios del Conurbano.)"""
    g22 = poligonos("2022").to_crs(e06.AEA).dissolve("codigo").reset_index()
    g10 = poligonos("2010").to_crs(e06.AEA).dissolve("codigo").reset_index()
    m = g22.merge(g10, on="codigo", suffixes=("_22", "_10"))
    d = gpd.GeoSeries(m.geometry_22).representative_point().distance(gpd.GeoSeries(m.geometry_10).representative_point())
    out = pd.DataFrame({"cod_indec": "06" + m.codigo.str[2:5], "dist": d.values}).groupby("cod_indec").dist.agg(
        radios_mismo_codigo="size", desplazamiento_mediano_m="median").reset_index()
    out["geo_2010_corrida"] = out.desplazamiento_mediano_m > 1000
    return out


def main() -> None:
    controles = []
    serie = pd.concat([por_circuito(a, controles) for a in ("1991", "2001", "2010", "2022")], ignore_index=True)
    serie = indicadores(serie)
    serie.to_csv(OUT / "censos_circuito_serie.csv", index=False, encoding="utf-8")

    # ancho: un circuito por fila, indicadores por censo y los cambios
    ind = list(COMUNES)
    a = serie.pivot_table(index=["circuito", "cod_indec"], columns="censo", values=["pob"] + ind)
    a.columns = [f"{v}_{c}" for v, c in a.columns]
    a = a.reset_index()
    for c0, c1 in ((1991, 2001), (2001, 2010), (2010, 2022), (1991, 2022)):
        # Con menos de 200 habitantes en alguno de los dos censos, el cambio es ruido del reparto
        # por área (Junín rural: 1.132 -> 331 -> 1.624 en el mismo circuito). Queda NaN.
        base = a[[f"pob_{c0}", f"pob_{c1}"]].min(axis=1)
        a[f"crec_pob_{str(c0)[2:]}_{str(c1)[2:]}"] = (100 * (a[f"pob_{c1}"] / a[f"pob_{c0}"] - 1)).where(base >= BASE_MIN).round(2)
    for k in ind:
        for c0, c1 in ((2001, 2010), (2010, 2022), (2001, 2022), (1991, 2022)):
            # El censo 2001 medía la desocupación muy por encima de la EPH (32,9 % en PBA): sirve
            # para ordenar circuitos dentro de 2001, no para medir el cambio contra otro censo.
            if k == "tasa_desocupacion" and c0 == 2001:
                continue
            if f"{k}_{c0}" in a and f"{k}_{c1}" in a and a[f"{k}_{c0}"].notna().any() and a[f"{k}_{c1}"].notna().any():
                base = a[[f"pob_{c0}", f"pob_{c1}"]].min(axis=1)
                a[f"d_{k}_{str(c0)[2:]}_{str(c1)[2:]}"] = (a[f"{k}_{c1}"] - a[f"{k}_{c0}"]).where(base >= BASE_MIN).round(2)
    # Cambio leíble con tranquilidad: 500+ habitantes en los dos censos.
    a["cambio_confiable_10_22"] = a[["pob_2010", "pob_2022"]].min(axis=1) >= 500
    a["cambio_confiable_01_22"] = a[["pob_2001", "pob_2022"]].min(axis=1) >= 500
    desp = desplazamiento_2010()
    desp.round(1).to_csv(TABLAS / "control_desplazamiento_radios_2010.csv", index=False, encoding="utf-8")
    a = a.merge(desp[["cod_indec", "geo_2010_corrida"]], on="cod_indec", how="left")
    a["geo_2010_corrida"] = a.geo_2010_corrida.fillna(False).astype(bool)
    a.loc[a.geo_2010_corrida, "cambio_confiable_10_22"] = False
    print(f"  capa 2010 corrida > 1 km en {desp.geo_2010_corrida.sum()} partidos "
          f"({a.geo_2010_corrida.sum()} circuitos): no confiables para 2010-2022")
    a.to_csv(OUT / "censos_circuito_cambios.csv", index=False, encoding="utf-8")

    # control: población por partido y censo, contra los totales de las tablas por departamento
    ctl = pd.DataFrame(controles)
    porp = serie.groupby(["censo", "cod_indec"]).pob.sum().unstack(0).round()
    porp.columns = [f"pob_{c}" for c in porp.columns]
    porp.reset_index().to_csv(TABLAS / "control_censos_historicos.csv", index=False, encoding="utf-8")
    ctl.to_csv(TABLAS / "control_censos_historicos_resumen.csv", index=False, encoding="utf-8")
    print("\n" + ctl.to_string(index=False))
    print("\n  provincia (comparable entre censos):")
    prov = serie.groupby("censo")[CONTEOS].sum(min_count=1)  # sin dato queda NaN, no 0
    print(indicadores(prov.reset_index())[["censo", "pob"] + ind].set_index("censo").T.round(1).to_string())


if __name__ == "__main__":
    main()
