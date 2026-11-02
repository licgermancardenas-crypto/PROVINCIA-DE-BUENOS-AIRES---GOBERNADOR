"""
11 · Capas territoriales por circuito: barrios populares, escuelas y salud.

FUENTES
-------
- **RENABAP** (Registro Nacional de Barrios Populares, info pública 12/2023): polígonos con
  familias y viviendas aproximadas, año de creación y servicios. 2.065 barrios en PBA.
- **Establecimientos educativos** (DGCyE, catálogo PBA, publicación 26/10/2026): un registro por
  establecimiento con coordenadas, matrícula, nivel, sector y edificio (CUI).
- **Establecimientos de salud públicos 2025** (catálogo PBA): coordenadas, dependencia y si tienen
  internación.

CÓMO
----
- Puntos (escuelas, salud) -> circuito por ubicación (polígono que los contiene). Control: el
  municipio del polígono contra el municipio que declara el registro; los que caen en otro municipio
  o fuera de la provincia se reportan y se ubican en el circuito más cercano **de su municipio**.
- Barrios populares -> circuito por superposición de áreas (proyección de áreas iguales del
  proyecto): familias y viviendas se reparten por la fracción de superficie del barrio en cada
  circuito, como el censo en el `etl/06`.
- Todo se agrega también por circuito estable (ventanas 2011-2025, 2019-2025 y 2023-2025), con los circuitos
  absorbidos asignados al que los absorbió (como en las láminas).

INDICADORES
-----------
Barrios populares: barrios, familias, viviendas, **% de hogares en barrios populares** (familias
RENABAP / hogares del censo 2022), familias en barrios creados desde 2010, % de familias sin agua de
red formal y sin cloaca. Escuelas: establecimientos, edificios, matrícula total y por nivel,
% de matrícula estatal, matrícula por 1.000 habitantes. Salud: establecimientos, sin internación
(CAPS y similares), con internación, por dependencia, por 10.000 habitantes.

Salidas (01_DATOS/processed/)
- capas_circuito.csv     : un circuito electoral por fila (1.146 polígonos)
- capas_ce.csv           : por circuito estable, ventanas 2011_2025, 2019_2025 y 2023_2025
- escuelas_puntos.csv, salud_puntos.csv : cada punto con su circuito y su control
- 03_OUTPUTS/tablas/control_capas.csv
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
RAW = RAIZ / "01_DATOS" / "raw"
PROC = RAIZ / "01_DATOS" / "processed"
TABLAS = RAIZ / "03_OUTPUTS" / "tablas"
ALBERS = "+proj=aea +lat_1=-34 +lat_2=-39 +lat_0=-36.5 +lon_0=-60 +datum=WGS84 +units=m"


def norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", str(t)).encode("ascii", "ignore").decode().upper()
    return re.sub(r"[^A-Z0-9]", "", t)


def circuitos() -> gpd.GeoDataFrame:
    return gpd.read_file(PROC / "geo" / "circuitos.gpkg").to_crs(ALBERS)[["circuito", "cod_indec", "geometry"]]


def ubicar(pts: gpd.GeoDataFrame, circ: gpd.GeoDataFrame, muni_decl: pd.Series) -> gpd.GeoDataFrame:
    """Circuito de cada punto, con control contra el municipio declarado."""
    j = gpd.sjoin(pts, circ, how="left", predicate="within").drop(columns="index_right")
    j = j[~j.index.duplicated()]
    j["municipio_declarado"] = muni_decl.reindex(j.index)
    j["control"] = np.where(j.circuito.isna(), "fuera de la provincia",
                            np.where(j.cod_indec == j.municipio_declarado, "ok", "otro municipio"))
    malos = j.index[(j.control != "ok") & j.municipio_declarado.notna()]
    for i in malos:
        c = circ[circ.cod_indec == j.at[i, "municipio_declarado"]]
        if len(c):
            k = c.distance(j.at[i, "geometry"]).idxmin()
            j.at[i, "circuito"], j.at[i, "cod_indec"] = c.at[k, "circuito"], c.at[k, "cod_indec"]
    return j


def escuelas(circ, claves) -> gpd.GeoDataFrame:
    e = pd.read_csv(RAW / "servicios" / "establecimientos_educativos.csv", dtype={"municipio_id": str, "cui": str})
    e = e.dropna(subset=["latitud", "longitud"])
    e = e[(e.latitud.between(-42, -32)) & (e.longitud.between(-64, -56))]
    g = gpd.GeoDataFrame(e, geometry=gpd.points_from_xy(e.longitud, e.latitud), crs=4326).to_crs(ALBERS)
    g = ubicar(g, circ, g.municipio_id.str.zfill(5))
    return g


def salud(circ, claves) -> gpd.GeoDataFrame:
    s = pd.read_csv(RAW / "servicios" / "salud_establecimientos_2025.csv", sep=None, engine="python", encoding="utf-8-sig")
    s = s.rename(columns=lambda c: c.strip())
    s["lat"] = pd.to_numeric(s.lat.astype(str).str.replace(",", "."), errors="coerce")
    s["long"] = pd.to_numeric(s.long.astype(str).str.replace(",", "."), errors="coerce")
    s = s.dropna(subset=["lat", "long"])
    s = s[(s.lat.between(-42, -32)) & (s.long.between(-64, -56))]
    nombre = claves.assign(k=claves.municipio_nombre.map(norm)).set_index("k").cod_indec
    decl = s.nde.map(norm).map(nombre)
    g = gpd.GeoDataFrame(s, geometry=gpd.points_from_xy(s.long, s.lat), crs=4326).to_crs(ALBERS)
    return ubicar(g, circ, decl)


def barrios(circ) -> pd.DataFrame:
    r = gpd.read_file(RAW / "social" / "renabap.geojson")
    r = r[r.provincia == "Buenos Aires"].to_crs(ALBERS)
    r["geometry"] = r.geometry.make_valid()
    r["area_b"] = r.area
    r["desde_2010"] = r.decada_de_creacion.astype(str).str.contains("2010|2020")
    # Con acceso: conexión formal o regular a la red (ojo: «irregular» contiene «regular»).
    r["sin_agua"] = ~r.agua_corriente.isin(["Conexión formal a la red de agua con factura",
                                            "Conexión regular a la red de agua pero sin factura"])
    r["sin_cloaca"] = r.efluentes_cloacales != "Conexión formal a la red cloacal"
    x = gpd.overlay(r[["id_renabap", "cantidad_familias_aproximada", "cantidad_viviendas_aproximadas", "area_b",
                       "desde_2010", "sin_agua", "sin_cloaca", "geometry"]], circ, how="intersection", keep_geom_type=True)
    x["frac"] = x.area / x.area_b
    x["familias"] = x.cantidad_familias_aproximada * x.frac
    x["viviendas"] = x.cantidad_viviendas_aproximadas * x.frac
    agg = x.groupby("circuito").agg(barrios_populares=("id_renabap", "nunique"), familias_bp=("familias", "sum"),
                                    viviendas_bp=("viviendas", "sum"))
    for col in ("desde_2010", "sin_agua", "sin_cloaca"):
        agg[f"familias_bp_{col}"] = x[x[col]].groupby("circuito").familias.sum().reindex(agg.index).fillna(0)
    ctl = {"barrios_pba": len(r), "familias_pba": float(r.cantidad_familias_aproximada.sum()),
           "familias_asignadas": float(x.familias.sum())}
    return agg, ctl


def a_ce(df: pd.DataFrame, ventana: str, circ: gpd.GeoDataFrame) -> pd.Series:
    """Circuito -> circuito estable de la ventana, con los absorbidos asignados al que los absorbió."""
    eq = pd.read_csv(PROC / "circuitos_equivalencias.csv", dtype=str)
    ce = eq[eq.ventana == ventana].set_index("circuito").ce_id
    mot = pd.read_csv(TABLAS / "circuitos_uniones_motivos.csv", dtype=str)
    destino = mot[mot.motivo.str.startswith("desaparece")].drop_duplicates("circuito_a", keep="last").set_index("circuito_a").circuito_b
    out = {}
    for c in df.index:
        x, vistos = c, set()
        while x not in ce.index and x in destino.index and x not in vistos:
            vistos.add(x)
            x = destino[x]
        out[c] = ce.get(x)
    s = pd.Series(out)
    # resto: vecino del mismo municipio con más borde compartido
    g = circ.set_index("circuito")
    for c in s.index[s.isna()]:
        if c not in g.index:
            continue
        geo, mun = g.at[c, "geometry"], g.at[c, "cod_indec"]
        cand = g[(g.cod_indec == mun) & g.index.isin(s.dropna().index) & g.intersects(geo.buffer(200))]
        if len(cand):
            s[c] = s[cand.geometry.intersection(geo.buffer(200)).length.idxmax()]
    return s


def main() -> None:
    TABLAS.mkdir(parents=True, exist_ok=True)
    claves = pd.read_csv(PROC / "municipios_claves.csv", dtype=str)
    circ = circuitos()
    censo = pd.read_csv(PROC / "censo2022_circuito.csv", dtype={"circuito": str, "cod_indec": str}).set_index("circuito")

    esc = escuelas(circ, claves)
    sal = salud(circ, claves)
    bp, ctl_bp = barrios(circ)

    esc.drop(columns="geometry").to_csv(PROC / "escuelas_puntos.csv", index=False, encoding="utf-8")
    sal.drop(columns="geometry").to_csv(PROC / "salud_puntos.csv", index=False, encoding="utf-8")

    # Conteos por circuito (todo en conteos para poder agregar).
    d = pd.DataFrame(index=circ.circuito)
    d["cod_indec"] = circ.set_index("circuito").cod_indec
    d = d.join(bp)
    e = esc.dropna(subset=["circuito"])
    e["mat"] = pd.to_numeric(e.matricula, errors="coerce").fillna(0)
    d["escuelas"] = e.groupby("circuito").size()
    d["edificios_escolares"] = e.groupby("circuito").cui.nunique()
    d["matricula"] = e.groupby("circuito").mat.sum()
    d["matricula_estatal"] = e[e.sector.astype(str).str.contains("Estatal", case=False)].groupby("circuito").mat.sum()
    for nivel, patron in [("inicial", "Inicial"), ("primaria", "Primari"), ("secundaria", "Secundari")]:
        d[f"matricula_{nivel}"] = e[e.nivel.astype(str).str.contains(patron, case=False)].groupby("circuito").mat.sum()
    s = sal.dropna(subset=["circuito"])
    d["salud"] = s.groupby("circuito").size()
    d["salud_con_internacion"] = s[s["mod"].astype(str).str.contains("CON INTERNACION", case=False)].groupby("circuito").size()
    d["salud_sin_internacion"] = s[s["mod"].astype(str).str.upper() == "ASISTENCIAL SIN INTERNACION"].groupby("circuito").size()
    for dep in ("Municipal", "Provincial", "Nacional"):
        d[f"salud_{dep.lower()}"] = s[s.tes.astype(str).str.contains(dep, case=False)].groupby("circuito").size()
    conteos = [c for c in d.columns if c != "cod_indec"]
    d[conteos] = d[conteos].fillna(0)
    d["pob"] = censo.pob.reindex(d.index)
    d["hogares"] = censo.hogares.reindex(d.index)

    def indicadores(x: pd.DataFrame) -> pd.DataFrame:
        x = x.copy()
        x["pct_hogares_barrio_popular"] = 100 * x.familias_bp / x.hogares.where(x.hogares > 0)
        x["pct_hogares_bp_desde_2010"] = 100 * x.familias_bp_desde_2010 / x.hogares.where(x.hogares > 0)
        x["pct_familias_bp_desde_2010"] = 100 * x.familias_bp_desde_2010 / x.familias_bp.where(x.familias_bp > 0)
        x["pct_familias_bp_sin_agua"] = 100 * x.familias_bp_sin_agua / x.familias_bp.where(x.familias_bp > 0)
        x["pct_familias_bp_sin_cloaca"] = 100 * x.familias_bp_sin_cloaca / x.familias_bp.where(x.familias_bp > 0)
        x["pct_matricula_estatal"] = 100 * x.matricula_estatal / x.matricula.where(x.matricula > 0)
        x["matricula_por_1000_hab"] = 1000 * x.matricula / x.pob.where(x.pob > 0)
        x["salud_por_10000_hab"] = 10000 * x.salud / x.pob.where(x.pob > 0)
        x["caps_por_10000_hab"] = 10000 * x.salud_sin_internacion / x.pob.where(x.pob > 0)
        return x.round(3)

    indicadores(d).to_csv(PROC / "capas_circuito.csv", encoding="utf-8")
    ces = []
    for v in ("2011_2025", "2019_2025", "2023_2025"):
        m = a_ce(d, v, circ)
        x = d.drop(columns="cod_indec").groupby(m.reindex(d.index)).sum(min_count=1)
        x.index.name = "ce_id"
        ces.append(indicadores(x).assign(ventana=v).reset_index())
    pd.concat(ces).to_csv(PROC / "capas_ce.csv", index=False, encoding="utf-8")

    # Controles
    ctl = {**ctl_bp,
           "escuelas_registros": len(esc), "escuelas_ok": int((esc.control == "ok").sum()),
           "escuelas_otro_municipio": int((esc.control == "otro municipio").sum()),
           "escuelas_fuera": int((esc.control == "fuera de la provincia").sum()),
           "salud_registros": len(sal), "salud_ok": int((sal.control == "ok").sum()),
           "salud_otro_municipio": int((sal.control == "otro municipio").sum()),
           "salud_fuera": int((sal.control == "fuera de la provincia").sum()),
           "matricula_total": float(d.matricula.sum()),
           "pct_hogares_pba_en_barrio_popular": float(100 * d.familias_bp.sum() / d.hogares.sum())}
    ok = d.hogares > 200
    x = indicadores(d)[ok]
    x = x.join(censo[["pct_hog_nbi"]])
    ctl["spearman_bp_vs_nbi"] = float(x[["pct_hogares_barrio_popular", "pct_hog_nbi"]].corr(method="spearman").iloc[0, 1])
    pd.Series(ctl).to_csv(TABLAS / "control_capas.csv", header=["valor"], encoding="utf-8")
    for k, v in ctl.items():
        print(f"  {k}: {v:,.3f}" if isinstance(v, float) else f"  {k}: {v}")


if __name__ == "__main__":
    main()
