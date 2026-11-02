"""
p04 · Datos del tablero electoral de la Provincia (versión web y Power BI).

Una sola exportación para los dos productos:

- 03_OUTPUTS/tablero/tablero_datos.json : todo lo que usa la página web (municipios, intendentes,
  elecciones, escenarios 2027, circuitos, escuelas y salud), con geometrías GeoJSON simplificadas
  en lon/lat e imágenes incrustadas (fotos con licencia libre y logos de partidos).
- 03_OUTPUTS/powerbi/datos/*.csv          : el mismo contenido en tablas planas para el modelo
  de Power BI (dimensiones y hechos), más los GeoJSON para el visual de mapa de formas.

INTENDENTES
-----------
Dos capas: el **intendente en ejercicio** (octubre 2026, `municipios_ma`, con situación titular /
interino y fecha) y el **electo en 2023** (`etl/12`, Wikipedia). La foto es la del electo en 2023 y
sólo se muestra si el que ejerce es la misma persona (mismo apellido): nunca se pone la cara de uno
con el nombre de otro.

ELECCIONES
----------
Por municipio, % de cada espacio sobre los votos positivos, participación y ganador:
Gobernador 2007-2023 y Diputados provinciales 2025 (septiembre, Junta Electoral), Intendente
2015-2023, Presidente 2015-2023 y segunda vuelta 2023, Diputados nacionales 2013-2025 (DINE).
"""
from __future__ import annotations

import base64
import json
import unicodedata
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
PROC = RAIZ / "01_DATOS" / "processed"
TABLAS = RAIZ / "03_OUTPUTS" / "tablas"
WEB = RAIZ / "03_OUTPUTS" / "tablero"
PBI = RAIZ / "03_OUTPUTS" / "powerbi" / "datos"
NO_POS = {"BLANCO", "NULO", "RECURRIDO", "IMPUGNADO", "COMANDO", "SIN_REGLA"}

ESPACIOS = {"PERONISMO": "Peronismo", "PRO_JXC": "PRO / JxC", "LLA": "La Libertad Avanza", "LLA_PRO": "LLA + PRO",
            "CENTRO_UCR": "UCR / centro", "TERCERA_VIA": "Tercera vía", "IZQUIERDA": "Izquierda",
            "VECINAL": "Vecinalismo", "OTROS": "Otros"}
# (clave, rótulo, fuente, año, tipo, cargos)
ELECCIONES = [
    ("D2025", "Diputados nacionales 2025", "dine_mesa", 2025, "GENERALES", ["DIPUTADOS NACIONALES"]),
    ("S2025", "Legislativa provincial sep. 2025", "jep_definitivo", 2025, "PROVINCIAL", ["DIPUTADOS PROVINCIALES", "SENADORES PROVINCIALES"]),
    ("G2023", "Gobernador 2023", "gba_definitivo", 2023, "GENERALES", ["GOBERNADOR"]),
    ("I2023", "Intendente 2023", "gba_definitivo", 2023, "GENERALES", ["INTENDENTE"]),
    ("P2023", "Presidente 2023", "dine_mesa", 2023, "GENERALES", ["PRESIDENTE"]),
    ("B2023", "Presidente 2023, segunda vuelta", "dine_mesa", 2023, "SEGUNDA VUELTA", ["PRESIDENTE"]),
    ("D2021", "Diputados nacionales 2021", "dine_mesa", 2021, "GENERALES", ["DIPUTADOS NACIONALES"]),
    ("G2019", "Gobernador 2019", "gba_definitivo", 2019, "GENERALES", ["GOBERNADOR"]),
    ("I2019", "Intendente 2019", "gba_definitivo", 2019, "GENERALES", ["INTENDENTE"]),
    ("P2019", "Presidente 2019", "dine_mesa", 2019, "GENERALES", ["PRESIDENTE"]),
    ("D2017", "Diputados nacionales 2017", "dine_mesa", 2017, "GENERALES", ["DIPUTADOS NACIONALES"]),
    ("G2015", "Gobernador 2015", "gba_definitivo", 2015, "GENERALES", ["GOBERNADOR"]),
    ("I2015", "Intendente 2015", "gba_definitivo", 2015, "GENERALES", ["INTENDENTE"]),
    ("P2015", "Presidente 2015", "dine_mesa", 2015, "GENERALES", ["PRESIDENTE"]),
    ("D2013", "Diputados nacionales 2013", "dine_mesa", 2013, "GENERALES", ["DIPUTADOS NACIONALES"]),
    ("G2011", "Gobernador 2011", "gba_definitivo", 2011, "GENERALES", ["GOBERNADOR"]),
    ("G2007", "Gobernador 2007", "gba_definitivo", 2007, "GENERALES", ["GOBERNADOR"]),
]


def b64(f: Path) -> str | None:
    if not f.exists():
        return None
    tipo = "png" if f.suffix == ".png" else "jpeg"
    return f"data:image/{tipo};base64," + base64.b64encode(f.read_bytes()).decode()


def apellido(s) -> str:
    if not isinstance(s, str):
        return ""
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().split()[-1]


def num(x, d=2):
    return None if pd.isna(x) else round(float(x), d)


# ----------------------------------------------------------------------------- municipios
def municipios() -> pd.DataFrame:
    ma = pd.read_csv(PROC / "municipios_ma.csv", dtype={"cod_indec": str})
    cl = pd.read_csv(PROC / "municipios_claves.csv", dtype=str).set_index("cod_indec")
    m = ma[["cod_indec", "municipio", "seccion_electoral", "region", "pob", "pob26", "km2", "dens", "agua", "cloaca",
            "gas", "nbi", "trh", "gph", "asap", "tsem", "flo", "deu", "per", "pub",
            "tasa_homicidios_dolosos_prom3", "tasa_delitos_totales_prom3", "tasa_mortalidad_infantil_trienio",
            "intendente", "intendente_espacio", "intendente_partido", "intendente_situacion", "intendente_desde"]].copy()
    m["conurbano"] = m.cod_indec.map(cl.conurbano) == "True"
    m["seccion_electoral"] = m.seccion_electoral.astype(str)
    # Censo 2022 por municipio (suma de circuitos).
    c = pd.read_csv(PROC / "censo2022_circuito.csv", dtype={"circuito": str, "cod_indec": str})
    g = c.groupby("cod_indec")[["pob", "hogares", "hog_nbi", "mni_validos", "mni_univ_completo", "e65_mas", "e18_29",
                                 "nac_total", "nac_otro_pais", "hog_internet", "hog_inet_total", "jubilados",
                                 "jub_total", "salud_sin_obra_social", "salud_total"]].sum()
    m = m.set_index("cod_indec")
    m["pct_univ"] = 100 * g.mni_univ_completo / g.mni_validos
    m["pct_65"] = 100 * g.e65_mas / g.pob
    m["pct_18_29"] = 100 * g.e18_29 / g.pob
    m["pct_extranjeros"] = 100 * g.nac_otro_pais / g.nac_total
    m["pct_internet"] = 100 * g.hog_internet / g.hog_inet_total
    m["pct_sin_obra_social"] = 100 * g.salud_sin_obra_social / g.salud_total
    m["hogares"] = g.hogares
    cap = pd.read_csv(PROC / "capas_circuito.csv", dtype={"circuito": str, "cod_indec": str}).groupby("cod_indec")[
        ["barrios_populares", "familias_bp", "escuelas", "matricula", "salud", "salud_sin_internacion"]].sum()
    m = m.join(cap)
    m["pct_barrio_popular"] = 100 * m.familias_bp / m.hogares
    # Intendente electo 2023 y foto.
    it = pd.read_csv(PROC / "intendentes_2023.csv", dtype={"cod_indec": str}).set_index("cod_indec")
    m = m.join(it[["intendente", "partido", "alianza", "reelecto", "wikipedia", "foto", "foto_licencia", "foto_autor",
                   "foto_fuente"]].add_prefix("electo_"))
    m["misma_persona"] = [apellido(a) == apellido(b) for a, b in zip(m.intendente, m.electo_intendente)]
    m.loc[~m.misma_persona, ["electo_foto", "electo_foto_licencia", "electo_foto_autor", "electo_foto_fuente"]] = None
    return m.reset_index()


# ----------------------------------------------------------------------------- elecciones
def elecciones() -> pd.DataFrame:
    p = pd.read_parquet(PROC / "panel_municipio.parquet")
    filas = []
    for clave, rot, fuente, anio, tipo, cargos in ELECCIONES:
        x = p[(p.fuente == fuente) & (p.anio == anio) & (p.tipo == tipo) & p.cargo.isin(cargos)]
        if x.empty:
            print("sin datos:", clave)
            continue
        pos = x[~x.espacio.isin(NO_POS)].groupby(["cod_indec", "espacio"]).votos.sum().unstack(fill_value=0)
        tot = pos.sum(axis=1)
        sh = 100 * pos.div(tot, axis=0)
        # Participación: un cargo (el primero) para no sumar el padrón dos veces.
        pad = x[x.cargo == cargos[0]].drop_duplicates("cod_indec").set_index("cod_indec")
        part = 100 * pad.votantes / pad.electores
        for cod in sh.index:
            fila = {"eleccion": clave, "cod_indec": cod, "votos_positivos": int(tot[cod]),
                    "electores": None if pd.isna(pad.electores.get(cod)) else int(pad.electores[cod]),
                    "participacion": num(part.get(cod), 1), "ganador": sh.loc[cod].idxmax()}
            orden = sh.loc[cod].sort_values(ascending=False)
            fila["margen"] = num(orden.iloc[0] - (orden.iloc[1] if len(orden) > 1 else 0), 1)
            for e in sh.columns:
                fila[e] = num(sh.loc[cod, e], 2)
            filas.append(fila)
    return pd.DataFrame(filas)


# ----------------------------------------------------------------------------- circuitos
def circuitos() -> gpd.GeoDataFrame:
    g = gpd.read_file(PROC / "geo" / "circuitos.gpkg")
    p = pd.read_parquet(PROC / "panel_circuito.parquet",
                        columns=["anio", "tipo", "cargo", "circuito", "espacio", "votos", "electores_nativos", "votantes_nativos"])
    out = pd.DataFrame(index=g.circuito)
    for clave, anio, cargo in [("D2025", 2025, "DIPUTADOS NACIONALES"), ("G2023", 2023, "GOBERNADOR")]:
        x = p[(p.anio == anio) & (p.tipo == "GENERALES") & (p.cargo == cargo)]
        pos = x[~x.espacio.isin(NO_POS)].groupby(["circuito", "espacio"]).votos.sum().unstack(fill_value=0)
        sh = 100 * pos.div(pos.sum(axis=1), axis=0)
        out[f"per_{clave}"] = sh.get("PERONISMO")
        der = [c for c in ("LLA_PRO", "LLA", "PRO_JXC") if c in sh]
        out[f"der_{clave}"] = sh[der].sum(axis=1)
        pad = x.drop_duplicates("circuito").set_index("circuito")
        out[f"part_{clave}"] = 100 * pad.votantes_nativos / pad.electores_nativos
        out[f"votos_{clave}"] = pos.sum(axis=1)
    c = pd.read_csv(PROC / "censo2022_circuito.csv", dtype={"circuito": str}).set_index("circuito")
    out["nbi"] = c.pct_hog_nbi
    out["univ"] = c.pct_univ_completo
    out["pob"] = c.pob
    cap = pd.read_csv(PROC / "capas_circuito.csv", dtype={"circuito": str}).set_index("circuito")
    out["bp"] = cap.pct_hogares_barrio_popular
    g = g.set_index("circuito").join(out.round(1)).reset_index()
    return g


def simplificar(g: gpd.GeoDataFrame, tol_m: float) -> gpd.GeoDataFrame:
    g = g.to_crs("+proj=aea +lat_1=-34 +lat_2=-39 +lat_0=-36.5 +lon_0=-60")
    from shapely.ops import unary_union

    def solo_poligonos(geom):
        if geom.geom_type == "GeometryCollection":
            return unary_union([p for p in geom.geoms if p.geom_type in ("Polygon", "MultiPolygon")])
        return geom
    g["geometry"] = g.geometry.map(solo_poligonos).simplify(tol_m, preserve_topology=True)
    return g.to_crs(4326)


def geojson(g: gpd.GeoDataFrame, props: list[str]) -> dict:
    gj = json.loads(g[props + ["geometry"]].to_json(drop_id=True))

    def rd(c):
        return [rd(x) for x in c] if isinstance(c[0], list) else [round(c[0], 4), round(c[1], 4)]
    for f in gj["features"]:
        f["geometry"]["coordinates"] = rd(f["geometry"]["coordinates"])
    return gj


# ----------------------------------------------------------------------------- main
def main() -> None:
    WEB.mkdir(parents=True, exist_ok=True)
    PBI.mkdir(parents=True, exist_ok=True)
    m = municipios()
    e = elecciones()
    mot = pd.read_csv(TABLAS / "motor_2027_municipio.csv", dtype={"cod_indec": str})
    mot["esc"] = mot.escenario.str[0]
    mot = mot[mot.esc.isin(["A", "B", "C"])]
    sec = pd.read_csv(TABLAS / "motor_2027_seccion.csv", dtype={"seccion": str})
    sec = sec[sec.escenario.str[0].isin(["A", "B", "C"])]
    logos = pd.read_csv(PROC / "logos_partidos.csv")
    circ = circuitos()

    part = gpd.read_file(PROC / "geo" / "partidos.gpkg")[["cod_indec", "geometry"]]
    secc = gpd.read_file(PROC / "geo" / "secciones.gpkg")
    gj_m = geojson(simplificar(part, 250).rename(columns={"cod_indec": "name"}), ["name"])
    gj_s = geojson(simplificar(secc.assign(name=secc.seccion_electoral.astype(str)), 800), ["name"])
    gj_c = geojson(simplificar(circ.rename(columns={"circuito": "name"}), 120), ["name"])

    esc = pd.read_csv(PROC / "escuelas_puntos.csv", dtype={"cod_indec": str},
                      usecols=["establecimiento_nombre", "nivel", "sector", "ambito", "matricula", "latitud", "longitud", "cod_indec"])
    esc = esc.dropna(subset=["latitud", "longitud"])
    sal = pd.read_csv(PROC / "salud_puntos.csv", dtype={"cod_indec": str}, usecols=["lat", "long", "nor", "mod", "Dep", "cod_indec"])
    sal = sal.dropna(subset=["lat", "long"])

    datos = {
        "generado": pd.Timestamp.now().strftime("%Y-%m-%d"),
        "espacios": ESPACIOS,
        "elecciones": [{"clave": k, "rotulo": r, "anio": a} for k, r, _, a, _, _ in ELECCIONES if k in set(e.eleccion)],
        "municipios": [{
            "cod": r.cod_indec, "nombre": r.municipio, "seccion": r.seccion_electoral, "conurbano": bool(r.conurbano),
            "region": r.region, "pob": num(r.pob, 0), "pob26": num(r.pob26, 0), "km2": num(r.km2, 1), "dens": num(r.dens, 1),
            "hogares": num(r.hogares, 0), "agua": num(r.agua, 1), "cloaca": num(r.cloaca, 1), "gas": num(r.gas, 1),
            "nbi": num(r.nbi, 1), "univ": num(r.pct_univ, 1), "p65": num(r.pct_65, 1), "p1829": num(r.pct_18_29, 1),
            "extr": num(r.pct_extranjeros, 1), "inet": num(r.pct_internet, 1), "sinos": num(r.pct_sin_obra_social, 1),
            "bp": num(r.pct_barrio_popular, 1), "nbp": num(r.barrios_populares, 0), "esc": num(r.escuelas, 0),
            "mat": num(r.matricula, 0), "salud": num(r.salud, 0), "caps": num(r.salud_sin_internacion, 0),
            "trh": num(r.trh, 0), "gph": num(r.gph, 0), "asap": num(r.asap, 0), "tsem": r.tsem if isinstance(r.tsem, str) else None,
            "hom": num(r.tasa_homicidios_dolosos_prom3, 1), "del": num(r.tasa_delitos_totales_prom3, 0),
            "mi": num(r.tasa_mortalidad_infantil_trienio, 1),
            "int": {"nombre": r.intendente, "espacio": r.intendente_espacio, "partido": r.intendente_partido,
                    "situacion": r.intendente_situacion, "desde": r.intendente_desde,
                    "electo": r.electo_intendente, "electo_partido": r.electo_partido, "electo_alianza": r.electo_alianza,
                    "reelecto": bool(r.electo_reelecto) if not pd.isna(r.electo_reelecto) else False,
                    "misma": bool(r.misma_persona),
                    "wiki": r.electo_wikipedia if r.misma_persona and isinstance(r.electo_wikipedia, str) else None,
                    "foto": b64(PROC / r.electo_foto) if isinstance(r.electo_foto, str) else None,
                    "foto_cred": (f"{r.electo_foto_autor} · {r.electo_foto_licencia}" if isinstance(r.electo_foto, str) else None),
                    "foto_url": r.electo_foto_fuente if isinstance(r.electo_foto, str) else None},
        } for r in m.itertuples()],
        "votos": {k: {r.cod_indec: {"p": r.participacion, "g": r.ganador, "m": r.margen, "v": r.votos_positivos,
                                    "e": None if pd.isna(r.electores) else int(r.electores),
                                    "s": {s: getattr(r, s) for s in ESPACIOS if s in g.columns and not pd.isna(getattr(r, s))
                                          and getattr(r, s) > 0}}
                      for r in g.itertuples()} for k, g in e.groupby("eleccion")},
        "motor": {esc_: {r.cod_indec: [round(r.pct_peronismo, 1), round(r.p_gana_peronismo, 3)] for r in g.itertuples()}
                  for esc_, g in mot.groupby("esc")},
        "motor_secciones": {esc_: {str(r.seccion): [round(r.pct_peronismo_de_los_positivos, 1), round(r.p_gana_peronismo, 3)]
                                   for r in g.itertuples()} for esc_, g in sec.groupby(sec.escenario.str[0])},
        "logos": {r.bloque: b64(PROC / r.logo) for r in logos.itertuples() if isinstance(r.logo, str)},
        "logos_fuente": {r.bloque: r.fuente for r in logos.itertuples()},
        "geo": {"municipios": gj_m, "secciones": gj_s, "circuitos": gj_c},
        "circuitos": {r.circuito: {k: (None if pd.isna(getattr(r, k)) else getattr(r, k)) for k in
                                   ["per_D2025", "der_D2025", "part_D2025", "per_G2023", "der_G2023", "part_G2023",
                                    "nbi", "univ", "bp", "pob"]} | {"cod": r.cod_indec} for r in circ.itertuples()},
        "escuelas": [[round(r.longitud, 4), round(r.latitud, 4), r.establecimiento_nombre, r.nivel, r.sector,
                      None if pd.isna(r.matricula) else int(r.matricula)] for r in esc.itertuples()],
        "salud": [[round(r.long, 4), round(r.lat, 4), r.nor, r.mod, r.Dep] for r in sal.itertuples()],
        "simulador": "https://claude.ai/artifact/3HHPCqam3Q8GVwhqM8xeRo",
        "repo": "https://github.com/licgermancardenas-crypto/PROVINCIA-DE-BUENOS-AIRES---GOBERNADOR",
    }
    def limpio(o):
        """NaN y tipos de numpy -> JSON válido."""
        if isinstance(o, dict):
            return {k: limpio(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [limpio(v) for v in o]
        if isinstance(o, (float, np.floating)):
            return None if np.isnan(o) else float(o)
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.bool_):
            return bool(o)
        return o
    datos = limpio(datos)
    f = WEB / "tablero_datos.json"
    f.write_text(json.dumps(datos, ensure_ascii=False, separators=(",", ":"), allow_nan=False, default=str), encoding="utf-8")
    print(f"web: {f.stat().st_size / 1e6:.1f} MB")

    # ------------------------------------------------------------- Power BI: tablas planas
    dim = m.rename(columns={"municipio": "municipio_nombre"}).drop(columns=["electo_foto"])
    dim["foto_url"] = dim.electo_foto_fuente
    dim.to_csv(PBI / "dim_municipio.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([{"eleccion": k, "rotulo": r, "anio": a, "tipo": t, "cargo": " + ".join(c), "fuente": fu}
                  for k, r, fu, a, t, c in ELECCIONES]).to_csv(PBI / "dim_eleccion.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([{"espacio": k, "espacio_nombre": v} for k, v in ESPACIOS.items()]).to_csv(
        PBI / "dim_espacio.csv", index=False, encoding="utf-8-sig")
    larga = e.melt(id_vars=["eleccion", "cod_indec", "votos_positivos", "electores", "participacion", "ganador", "margen"],
                   value_vars=[c for c in ESPACIOS if c in e.columns], var_name="espacio", value_name="pct").dropna(subset=["pct"])
    larga["votos"] = (larga.pct / 100 * larga.votos_positivos).round(0)
    larga[["eleccion", "cod_indec", "espacio", "pct", "votos"]].to_csv(PBI / "fact_votos.csv", index=False, encoding="utf-8-sig")
    e[["eleccion", "cod_indec", "votos_positivos", "electores", "participacion", "ganador", "margen"]].to_csv(
        PBI / "fact_participacion.csv", index=False, encoding="utf-8-sig")
    mot.rename(columns={"esc": "escenario_clave"}).to_csv(PBI / "fact_motor_2027.csv", index=False, encoding="utf-8-sig")
    circ.drop(columns="geometry").to_csv(PBI / "dim_circuito.csv", index=False, encoding="utf-8-sig")
    for nombre, gj in [("municipios", gj_m), ("secciones", gj_s), ("circuitos", gj_c)]:
        (PBI / f"{nombre}.geojson").write_text(json.dumps(gj, separators=(",", ":")), encoding="utf-8")
    print("power bi:", sorted(x.name for x in PBI.iterdir()))


if __name__ == "__main__":
    main()
