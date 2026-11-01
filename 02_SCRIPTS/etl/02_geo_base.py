# -*- coding: utf-8 -*-
"""
ETL 02 · Base geográfica: partidos, secciones electorales y circuitos, con claves normalizadas,
y la tabla de equivalencias municipio DINE <-> código INDEC.

    python 02_SCRIPTS/etl/02_geo_base.py

Qué contesta: deja en `01_DATOS/processed/geo/`
- `partidos.gpkg` (135, clave `cod_indec` de 5 dígitos, `06xxx`)
- `secciones.gpkg` (8, clave `seccion_electoral` 1-8)
- `circuitos.gpkg` (clave `circuito`, normalizada, + `cod_indec`)
y en `01_DATOS/processed/`
- `municipios_claves.csv`: `cod_indec`, nombre, sección electoral, `seccion_id_dine` y si es
  del Conurbano (24 partidos del GBA, definición INDEC).

Qué supone:
- El código de circuito de PBA es único en la provincia y tiene forma «número + letra
  opcional» (`0164A`). Llega en tres formatos: con ceros (`0063`, geojson), sin ceros (`989`,
  CSV del catálogo) y con espacio al final (`0557 `, DINE). `norm_circuito` los lleva a
  4 dígitos + letra.
- El `seccion_id` de la DINE para PBA **no es** el código INDEC: se empareja por nombre
  normalizado contra los partidos, usando el parquet de mesas más reciente que exista.

Qué no puede afirmar: que los polígonos de circuito valgan para todos los años. El catálogo los
actualizó en marzo de 2026; si un circuito se partió o se creó, el mapa de 2011 no coincide.
La tabla de equivalencias en el tiempo es la etapa 1.9.
"""
import re
import unicodedata
from pathlib import Path

import geopandas as gpd
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
GEO = RAIZ / "01_DATOS" / "raw" / "geo"
OUT = RAIZ / "01_DATOS" / "processed"
OUTG = OUT / "geo"
ROMANOS = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8}

# Los 24 partidos del Gran Buenos Aires según el INDEC.
CONURBANO = {
    "06028", "06035", "06260", "06270", "06274", "06371", "06408", "06410", "06412", "06427",
    "06434", "06490", "06515", "06539", "06560", "06568", "06658", "06749", "06756", "06760",
    "06778", "06805", "06840", "06861",
}


def norm_circuito(x) -> str | None:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    m = re.fullmatch(r"0*(\d+)\s*([A-Za-z]?)", str(x).strip())
    return f"{int(m.group(1)):04d}{m.group(2).upper()}" if m else str(x).strip().upper()


# Nombres abreviados de la DINE (ya normalizados) -> nombre normalizado del mapa de ARBA.
ALIAS_DINE = {
    "J C PAZ": "JOSE C PAZ",
    "JUAREZ": "BENITO JUAREZ",
    "F AMEGHINO": "FLORENTINO AMEGHINO",
    "LAMADRID": "MADRID",            # «General La Madrid»: norm_nombre le saca GENERAL y LA
    "GONZALES CHAVES": "ADOLFO GONZALES CHAVES",
    "9 JULIO": "NUEVE JULIO",        # el mapa de ARBA los escribe en letras
    "25 MAYO": "VEINTICINCO MAYO",
}


def corregir_chascomus_lezama(cod: pd.Series, nombre: pd.Series) -> pd.Series:
    # Lezama se separó de Chascomús en 2009 y los mapas de ARBA les dejan a los dos el código
    # viejo 06217. El INDEC 2022 (y el resto de las fuentes) usa 06218 y 06466.
    cod = cod.copy()
    viejo = cod == "06217"
    es_lezama = nombre.map(norm_nombre).eq("LEZAMA")
    cod[viejo & es_lezama] = "06466"
    cod[viejo & ~es_lezama] = "06218"
    return cod


def norm_nombre(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().upper()
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = re.sub(r"\b(PARTIDO DE|GENERAL|GRAL|CORONEL|CNEL|DE|DEL|LA|LAS|LOS|EL)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def main() -> None:
    OUTG.mkdir(parents=True, exist_ok=True)

    # --- partidos -----------------------------------------------------------------------------
    p = gpd.read_file(f"zip://{GEO / 'limite_partidos_pba.zip'}!partidos-pba.geojson")
    p["cod_indec"] = p["municipio_id"].astype(int).map(lambda v: f"{v:05d}")
    p["cod_indec"] = corregir_chascomus_lezama(p["cod_indec"], p["municipio_nombre"])
    p = p.dissolve(by="cod_indec", aggfunc={"municipio_nombre": "first", "area_legal": "first"}).reset_index()
    p["conurbano"] = p.cod_indec.isin(CONURBANO)
    assert len(p) == 135, len(p)
    assert p.conurbano.sum() == 24, p.conurbano.sum()

    # --- secciones electorales ----------------------------------------------------------------
    s = gpd.read_file(f"zip://{GEO / 'secciones_electorales_pba.zip'}!secciones-electorales-pba.geojson")
    s["geometry"] = s.geometry.make_valid()
    s["seccion_electoral"] = s["seccion"].str.strip().map(ROMANOS)
    s = s[["seccion_electoral", "geometry"]].sort_values("seccion_electoral")
    assert s.seccion_electoral.tolist() == list(range(1, 9))

    # partido -> sección por mayor superposición. Con un punto interior fallan La Costa, Pinamar
    # y Villa Gesell: la costa de la capa de secciones no coincide con la de ARBA.
    ov = gpd.overlay(p[["cod_indec", "geometry"]].to_crs(5347), s.to_crs(5347), how="intersection")
    ov["a"] = ov.area
    ps = ov.sort_values("a").drop_duplicates("cod_indec", keep="last")[["cod_indec", "seccion_electoral"]]
    p = p.merge(ps, on="cod_indec", how="left")
    assert p.seccion_electoral.notna().all(), p[p.seccion_electoral.isna()].municipio_nombre.tolist()

    # --- circuitos ----------------------------------------------------------------------------
    c = gpd.read_file(f"zip://{GEO / 'circuitos_electorales_pba.zip'}!circuitos-electorales-pba.geojson")
    c["circuito"] = c["circuito"].map(norm_circuito)
    c["cod_indec"] = "06" + c["indec_d"].astype(str).str.zfill(3)
    c["cod_indec"] = corregir_chascomus_lezama(c["cod_indec"], c["departamen"])
    c["geometry"] = c.geometry.make_valid()
    c = c.dissolve(by="circuito", aggfunc={"cod_indec": "first", "cabecera": "first"}).reset_index()
    # El código de partido de la capa de circuitos está viejo o mal en 8 partidos (Cañuelas
    # 06133, Pilar 06637, Morón 06567…): manda la ubicación. Se guarda el código original.
    c = c.rename(columns={"cod_indec": "cod_indec_capa"})
    pts = c[["circuito", "geometry"]].copy()
    pts["geometry"] = pts.representative_point()
    loc = gpd.sjoin(pts, p[["cod_indec", "geometry"]], how="left", predicate="within")
    c = c.merge(loc[["circuito", "cod_indec"]].drop_duplicates("circuito"), on="circuito", how="left")
    c["cod_indec"] = c["cod_indec"].fillna(c["cod_indec_capa"])
    print(f"  circuitos: {(c.cod_indec != c.cod_indec_capa).sum()} con código de partido corregido por ubicación")
    c = c.merge(p[["cod_indec", "seccion_electoral", "conurbano"]], on="cod_indec", how="left")
    sin_muni = c.cod_indec[~c.cod_indec.isin(p.cod_indec)].unique()

    # --- municipio DINE <-> INDEC -------------------------------------------------------------
    claves = p[["cod_indec", "municipio_nombre", "seccion_electoral", "conurbano"]].copy()
    # Los nombres de la DINE cambian de un año a otro («Rosales» / «Coronel Rosales»), el
    # seccion_id no: se juntan los nombres de todos los años y alcanza con que uno empareje.
    mesas = sorted(OUT.glob("mesas_dine_pba_*_generales.parquet"))
    if mesas:
        d = pd.concat(pd.read_parquet(m, columns=["seccion_id", "seccion_nombre", "seccionprovincial_id"])
                      .drop_duplicates("seccion_id") for m in mesas)
        d["k"] = d.seccion_nombre.map(norm_nombre).replace(ALIAS_DINE)
        d = d[d.k.isin(set(claves.municipio_nombre.map(norm_nombre)))].drop_duplicates("seccion_id")
        ids = d.groupby("k").seccion_id.nunique()
        assert (ids == 1).all(), f"un nombre con dos seccion_id: {ids[ids > 1].index.tolist()}"
        d = d.drop_duplicates("k")
        claves["k"] = claves.municipio_nombre.map(norm_nombre)
        claves = claves.merge(d[["k", "seccion_id", "seccion_nombre", "seccionprovincial_id"]], on="k", how="left")
        claves = claves.rename(columns={"seccion_id": "seccion_id_dine", "seccion_nombre": "nombre_dine"})
        sin = claves[claves.seccion_id_dine.isna()]
        if len(sin):
            print(f"  ⚠ {len(sin)} partidos sin par en la DINE ({mesas[-1].name}): "
                  + ", ".join(sin.municipio_nombre))
        dif = claves[claves.seccionprovincial_id.notna() & (claves.seccionprovincial_id != claves.seccion_electoral)]
        if len(dif):
            print(f"  ⚠ {len(dif)} partidos con sección distinta entre mapa y DINE: "
                  + ", ".join(dif.municipio_nombre))
        claves = claves.drop(columns=["k", "seccionprovincial_id"])

    p.to_file(OUTG / "partidos.gpkg", driver="GPKG")
    s.to_file(OUTG / "secciones.gpkg", driver="GPKG")
    c.to_file(OUTG / "circuitos.gpkg", driver="GPKG")
    claves.sort_values("cod_indec").to_csv(OUT / "municipios_claves.csv", index=False, encoding="utf-8")

    print(f"partidos {len(p)} (Conurbano {p.conurbano.sum()}) · secciones {len(s)} · circuitos {len(c)}"
          + (f" · {len(sin_muni)} códigos de partido de circuitos sin par: {list(sin_muni)}" if len(sin_muni) else ""))
    print(p.groupby("seccion_electoral").size().rename("partidos").to_frame().T.to_string())


if __name__ == "__main__":
    main()
