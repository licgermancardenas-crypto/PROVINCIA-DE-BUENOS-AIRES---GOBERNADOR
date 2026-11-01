# -*- coding: utf-8 -*-
"""
ETL 06 · Censo 2022 por radio censal -> circuito electoral.

    python 02_SCRIPTS/etl/06_censo2022_circuitos.py

Qué contesta: cómo es cada circuito electoral de PBA según el Censo 2022 —edad, educación,
empleo, cobertura de salud, migración, NBI, privación material, servicios, hacinamiento,
conectividad, tenencia—, a partir de las 23.901 tablas por radio del INDEC. Deja:
- `01_DATOS/processed/censo2022_radio_conteos.parquet`: radio × variable × categoría
  (las variables elegidas, en conteos; insumo para cualquier indicador nuevo)
- `01_DATOS/processed/censo2022_radio.csv`: un radio por fila, conteos agregados + indicadores
- `01_DATOS/processed/radio_circuito_2022.csv`: el reparto radio -> circuito, con su peso
- `01_DATOS/processed/censo2022_circuito.csv`: un circuito por fila, conteos + indicadores
- `03_OUTPUTS/tablas/control_censo_circuitos.csv`: población por partido, censo contra INDEC

Qué supone:
- El `codigo` de 9 dígitos de las tablas (06 + departamento + fracción + radio) es el `LINK`
  de los polígonos del catálogo PBA. Se verifica: radios de tabla sin polígono y al revés.
- **Reparto por superposición de área.** Un radio que cae entero (≥ 95 % de su área) en un
  circuito va entero; uno partido entre circuitos se reparte por área. Eso es exacto en la
  ciudad, donde los radios son manzanas, y aproximado en el campo, donde un radio rural
  grande puede tener el pueblo de un lado. Cuánta población cae en radios partidos queda
  medido en el control y en `pob_en_radios_partidos` por circuito.
- Las tablas son univariadas (cada variable sola sobre su universo): no hay cruces del tipo
  «universitarios de 25 años y más». Los indicadores de educación se calculan sobre la
  población del universo de la pregunta y quedan confundidos con la edad del circuito: en los
  modelos, la edad entra como control.

- Las tablas por radio cubren sólo **viviendas particulares** (`VIVIENDA_TIPOVIVG` tiene una
  sola categoría). Quedan afuera cárceles, geriátricos, cuarteles y situación de calle: por eso
  la suma da 0,66 % menos que el total del INDEC, y −20 % en General Alvear o −15 % en
  Magdalena, que tienen unidades penales.
- Se valida contra el padrón: la población de 16+ de cada circuito tiene que parecerse a sus
  electores nativos. `calidad_cruce` marca `revisar` cuando la razón sale de 0,6-1,5.

Qué no puede afirmar: nada sobre personas (es ecológico) y nada sobre circuitos que no están
en la capa de polígonos (0,6 % del padrón en 2023, 0 % en 2025: ver bitácora). El censo es de
2022; los circuitos, de la capa de marzo de 2026.
"""
import zipfile
from pathlib import Path

import duckdb
import geopandas as gpd
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
RAW = RAIZ / "01_DATOS" / "raw"
INTERIM = RAIZ / "01_DATOS" / "interim" / "censo2022"
OUT = RAIZ / "01_DATOS" / "processed"
TABLAS = RAIZ / "03_OUTPUTS" / "tablas"
# Albers equivalente centrada en PBA: las áreas tienen que ser comparables entre el norte y el sur.
AEA = "+proj=aea +lat_1=-34 +lat_2=-39 +lat_0=-36.5 +lon_0=-60 +datum=WGS84 +units=m"
ENTERO = 0.95

VARIABLES = [
    # persona
    "PERSONA_P02", "PERSONA_EDAD", "PERSONA_MNI", "PERSONA_CONDACT", "PERSONA_P19", "PERSONA_P20",
    "PERSONA_P13", "PERSONA_P17", "PERSONA_DESCAPOR", "PERSONA_P30", "PERSONA_CONASI",
    # hogar
    "HOGAR_NBI_TOT", "HOGAR_NBI_HAC", "HOGAR_NBI_SAN", "HOGAR_NBI_VIV", "HOGAR_NBI_ESC", "HOGAR_NBI_SUB",
    "HOGAR_IPMH", "HOGAR_EDUHOG", "HOGAR_H14", "HOGAR_H18", "HOGAR_H19", "HOGAR_H20CP", "HOGAR_H22",
    "HOGAR_H24A", "HOGAR_H24C", "HOGAR_INMAT", "HOGAR_HOGMIG", "HOGAR_TIPHOGAR",
    # vivienda
    "VIVIENDA_URP", "VIVIENDA_V02", "VIVIENDA_TIPOVIVG",
]


# --- 1 · tablas del censo -> conteos por radio --------------------------------------------------
def conteos_por_radio() -> pd.DataFrame:
    destino = OUT / "censo2022_radio_conteos.parquet"
    INTERIM.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(RAW / "censo" / "c2022_pba.zip") as z:
        for n in z.namelist():
            if not (INTERIM / n).exists():
                z.extract(n, INTERIM)
    lista = ", ".join(f"'{v}'" for v in VARIABLES)
    archivos = [str(p).replace("\\", "/") for p in sorted(INTERIM.glob("*.csv"))]
    con = duckdb.connect()
    con.execute("SET memory_limit='1500MB'")
    con.execute(f"""
        COPY (
            SELECT codigo, cod_variable, CAST(cod_categoria AS VARCHAR) AS cod_categoria,
                   SUM(cantidad)::BIGINT AS cantidad
            FROM read_csv({archivos}, header=true, union_by_name=true,
                          types={{'codigo':'VARCHAR','cod_categoria':'VARCHAR','cantidad':'BIGINT'}})
            WHERE cod_variable IN ({lista})
            GROUP BY ALL
        ) TO '{str(destino).replace(chr(92), "/")}' (FORMAT parquet, COMPRESSION zstd)
    """)
    c = pd.read_parquet(destino)
    faltan = set(VARIABLES) - set(c.cod_variable)
    assert not faltan, f"variables que no aparecen en las tablas: {faltan}"
    print(f"  conteos: {len(c):,} filas · {c.codigo.nunique():,} radios · {c.cod_variable.nunique()} variables")
    return c


def suma(w: pd.DataFrame, var: str, cats=None) -> pd.Series:
    cols = [c for c in w.columns if c.startswith(var + "__")]
    if cats is not None:
        cols = [c for c in cols if c.split("__")[1] in {str(x) for x in cats}]
    return w[cols].sum(axis=1) if cols else pd.Series(0, index=w.index)


def conteos_agregados(c: pd.DataFrame) -> pd.DataFrame:
    """Lleva radio × variable × categoría a las columnas de conteo que usan los indicadores.
    Todo queda en conteos (numerador y denominador) para poder sumar por circuito."""
    w = c.assign(col=c.cod_variable + "__" + c.cod_categoria).pivot_table(
        index="codigo", columns="col", values="cantidad", aggfunc="sum", fill_value=0)
    edad = {int(k.split("__")[1]): w[k] for k in w.columns if k.startswith("PERSONA_EDAD__")}
    rango = lambda a, b: sum(edad[i] for i in edad if a <= i <= b)  # noqa: E731
    mni_validos = suma(w, "PERSONA_MNI") - suma(w, "PERSONA_MNI", [99])
    d = pd.DataFrame({
        "pob": suma(w, "PERSONA_P02"),
        "mujeres": suma(w, "PERSONA_P02", [1]),
        "e16_17": rango(16, 17), "e18_29": rango(18, 29), "e30_44": rango(30, 44),
        "e45_64": rango(45, 64), "e65_mas": rango(65, 200),
        "mni_validos": mni_validos,
        "mni_hasta_sec_incompleto": suma(w, "PERSONA_MNI", [1, 2, 3, 4]),
        "mni_superior_completo": suma(w, "PERSONA_MNI", [7, 9, 10, 11]),
        "mni_univ_completo": suma(w, "PERSONA_MNI", [9, 10, 11]),
        "act_ocupados": suma(w, "PERSONA_CONDACT", [1]),
        "act_desocupados": suma(w, "PERSONA_CONDACT", [2]),
        "act_total": suma(w, "PERSONA_CONDACT"),
        "salud_total": suma(w, "PERSONA_P19"),
        "salud_sin_obra_social": suma(w, "PERSONA_P19", [2, 3]),
        "jubilados": suma(w, "PERSONA_P20", [1]),
        "jub_total": suma(w, "PERSONA_P20"),
        "nac_total": suma(w, "PERSONA_P13"),
        "nac_otra_prov": suma(w, "PERSONA_P13", [2]),
        "nac_otro_pais": suma(w, "PERSONA_P13", [3]),
        "res5_total": suma(w, "PERSONA_P17", [1, 2, 3, 4]),
        "res5_otro_lugar": suma(w, "PERSONA_P17", [2, 3, 4]),
        "aporte_total": suma(w, "PERSONA_DESCAPOR", [1, 2, 3]),
        "aporte_no": suma(w, "PERSONA_DESCAPOR", [3]),
        "cat_total": suma(w, "PERSONA_P30", [1, 2, 3, 4, 5]),
        "cat_cuenta_propia": suma(w, "PERSONA_P30", [3]),
        "cat_domestico": suma(w, "PERSONA_P30", [1]),
        "cat_patron": suma(w, "PERSONA_P30", [4]),
        "hogares": suma(w, "HOGAR_NBI_TOT"),
        "hog_nbi": suma(w, "HOGAR_NBI_TOT", [1]),
        "hog_nbi_hac": suma(w, "HOGAR_NBI_HAC", [1]),
        "hog_nbi_san": suma(w, "HOGAR_NBI_SAN", [1]),
        "hog_nbi_viv": suma(w, "HOGAR_NBI_VIV", [1]),
        "hog_nbi_esc": suma(w, "HOGAR_NBI_ESC", [1]),
        "hog_nbi_sub": suma(w, "HOGAR_NBI_SUB", [1]),
        "hog_ipmh_total": suma(w, "HOGAR_IPMH"),
        "hog_ipmh_alguna": suma(w, "HOGAR_IPMH", [2, 3, 4]),
        "hog_ipmh_convergente": suma(w, "HOGAR_IPMH", [4]),
        "hog_edu_validos": suma(w, "HOGAR_EDUHOG", [1, 2, 3, 4, 5]),
        "hog_edu_bajo": suma(w, "HOGAR_EDUHOG", [1, 2]),
        "hog_edu_alto": suma(w, "HOGAR_EDUHOG", [4, 5]),
        "hog_agua_total": suma(w, "HOGAR_H14"),
        "hog_agua_red": suma(w, "HOGAR_H14", [1]),
        "hog_desague_total": suma(w, "HOGAR_H18"),
        "hog_cloaca": suma(w, "HOGAR_H18", [1]),
        "hog_comb_total": suma(w, "HOGAR_H19"),
        "hog_gas_red": suma(w, "HOGAR_H19", [2]),
        "hog_garrafa_lena": suma(w, "HOGAR_H19", [4, 5]),
        "hog_hacin_total": suma(w, "HOGAR_H20CP"),
        "hog_hacin_mas2": suma(w, "HOGAR_H20CP", [5, 6]),     # más de 2 personas por cuarto
        "hog_hacin_critico": suma(w, "HOGAR_H20CP", [6]),     # más de 3: definición INDEC de crítico
        "hog_ten_total": suma(w, "HOGAR_H22"),
        "hog_propia": suma(w, "HOGAR_H22", [1]),
        "hog_alquila": suma(w, "HOGAR_H22", [2]),
        "hog_inet_total": suma(w, "HOGAR_H24A"),
        "hog_internet": suma(w, "HOGAR_H24A", [1]),
        "hog_compu_total": suma(w, "HOGAR_H24C"),
        "hog_computadora": suma(w, "HOGAR_H24C", [1]),
        "hog_mat_validos": suma(w, "HOGAR_INMAT", [1, 2, 3, 4]),
        "hog_mat_malos": suma(w, "HOGAR_INMAT", [3, 4]),
        "hog_migrante": suma(w, "HOGAR_HOGMIG", [1]),
        "hog_mig_total": suma(w, "HOGAR_HOGMIG"),
        "viv_total": suma(w, "VIVIENDA_URP"),
        "viv_rural": suma(w, "VIVIENDA_URP", [2, 3]),
        "viv_v02_total": suma(w, "VIVIENDA_V02"),
        "viv_desocupadas": suma(w, "VIVIENDA_V02", [2]),
    })
    return d.reset_index()


# Indicador = numerador / denominador, ambos conteos. Se recalculan en cada escala.
INDICADORES = {
    "pct_mujeres": ("mujeres", "pob"),
    "pct_16_17": ("e16_17", "pob"), "pct_18_29": ("e18_29", "pob"), "pct_30_44": ("e30_44", "pob"),
    "pct_45_64": ("e45_64", "pob"), "pct_65_mas": ("e65_mas", "pob"),
    "pct_hasta_sec_incompleto": ("mni_hasta_sec_incompleto", "mni_validos"),
    "pct_superior_completo": ("mni_superior_completo", "mni_validos"),
    "pct_univ_completo": ("mni_univ_completo", "mni_validos"),
    "tasa_desocupacion": ("act_desocupados", ("act_ocupados", "act_desocupados")),
    "tasa_empleo": ("act_ocupados", "act_total"),
    "pct_sin_obra_social": ("salud_sin_obra_social", "salud_total"),
    "pct_jubilados": ("jubilados", "jub_total"),
    "pct_nac_otra_prov": ("nac_otra_prov", "nac_total"),
    "pct_nac_otro_pais": ("nac_otro_pais", "nac_total"),
    "pct_migrante_reciente": ("res5_otro_lugar", "res5_total"),
    "pct_sin_aporte": ("aporte_no", "aporte_total"),
    "pct_cuenta_propia": ("cat_cuenta_propia", "cat_total"),
    "pct_domestico": ("cat_domestico", "cat_total"),
    "pct_patron": ("cat_patron", "cat_total"),
    "pct_hog_nbi": ("hog_nbi", "hogares"),
    "pct_hog_nbi_hac": ("hog_nbi_hac", "hogares"), "pct_hog_nbi_san": ("hog_nbi_san", "hogares"),
    "pct_hog_nbi_viv": ("hog_nbi_viv", "hogares"), "pct_hog_nbi_esc": ("hog_nbi_esc", "hogares"),
    "pct_hog_nbi_sub": ("hog_nbi_sub", "hogares"),
    "pct_hog_privacion": ("hog_ipmh_alguna", "hog_ipmh_total"),
    "pct_hog_privacion_convergente": ("hog_ipmh_convergente", "hog_ipmh_total"),
    "pct_hog_clima_edu_bajo": ("hog_edu_bajo", "hog_edu_validos"),
    "pct_hog_clima_edu_alto": ("hog_edu_alto", "hog_edu_validos"),
    "pct_hog_agua_red": ("hog_agua_red", "hog_agua_total"),
    # sobre el total de hogares, como la cifra oficial (H18 sólo pregunta a hogares con inodoro)
    "pct_hog_cloaca": ("hog_cloaca", "hogares"),
    "pct_hog_gas_red": ("hog_gas_red", "hog_comb_total"),
    "pct_hog_garrafa_lena": ("hog_garrafa_lena", "hog_comb_total"),
    "pct_hog_hacinamiento": ("hog_hacin_mas2", "hog_hacin_total"),
    "pct_hog_hacinamiento_critico": ("hog_hacin_critico", "hog_hacin_total"),
    "pct_hog_propietario": ("hog_propia", "hog_ten_total"),
    "pct_hog_inquilino": ("hog_alquila", "hog_ten_total"),
    "pct_hog_internet": ("hog_internet", "hog_inet_total"),
    "pct_hog_computadora": ("hog_computadora", "hog_compu_total"),
    "pct_hog_materiales_malos": ("hog_mat_malos", "hog_mat_validos"),
    "pct_hog_migrante": ("hog_migrante", "hog_mig_total"),
    "pct_viv_rural": ("viv_rural", "viv_total"),
    "pct_viv_desocupadas": ("viv_desocupadas", "viv_v02_total"),
}


def indicadores(d: pd.DataFrame) -> pd.DataFrame:
    nuevos = {}
    for k, (num, den) in INDICADORES.items():
        den_v = d[list(den)].sum(axis=1) if isinstance(den, tuple) else d[den]
        nuevos[k] = (100 * d[num] / den_v.where(den_v > 0)).round(2)
    return pd.concat([d.reset_index(drop=True), pd.DataFrame(nuevos).reset_index(drop=True)], axis=1)


def control_padron(circ: pd.DataFrame) -> pd.DataFrame:
    """Padrón nativo por circuito (DINE, Diputados Nacionales) contra la población de 16+ del
    censo. Una razón lejos de 1 dice que el polígono no es el circuito donde vota esa gente
    (límite corrido entre vecinos, o el voto rural anotado en el pueblo)."""
    from importlib import import_module
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    norm = import_module("02_geo_base").norm_circuito
    p16 = circ[["e16_17", "e18_29", "e30_44", "e45_64", "e65_mas"]].sum(axis=1)
    out = pd.DataFrame({"circuito": circ.circuito, "cod_indec": circ.cod_indec, "pob_16_mas": p16.round()})
    for anio in (2023, 2025):
        d = pd.read_parquet(OUT / f"mesas_dine_pba_{anio}_generales.parquet",
                            columns=["circuito_id", "mesa_id", "seccion_id", "mesa_electores", "cargo_nombre"])
        d = d[d.cargo_nombre.str.startswith("DIPUTADO") & d.cargo_nombre.str.contains("NACIONAL")]
        d = d.drop_duplicates(["seccion_id", "mesa_id"])
        e = d.groupby(d.circuito_id.map(norm)).mesa_electores.sum()
        out[f"electores_nativos_{anio}"] = out.circuito.map(e)
        out[f"razon_padron_{anio}"] = (out[f"electores_nativos_{anio}"] / out.pob_16_mas.where(out.pob_16_mas > 0)).round(3)
    r = out.razon_padron_2025.astype(float)
    out["calidad_cruce"] = np.select([r.isna().to_numpy(), r.between(0.6, 1.5).to_numpy()],
                                     ["sin_padron", "ok"], "revisar")
    return out


# --- 2 · radio -> circuito ---------------------------------------------------------------------
def reparto_radios() -> tuple[pd.DataFrame, gpd.GeoDataFrame]:
    r = gpd.read_file(f"zip://{RAW / 'geo' / 'radios_2022_pba.zip'}!radios-censales.geojson")
    r = r.rename(columns={"LINK": "codigo"})[["codigo", "geometry"]].to_crs(AEA)
    r["geometry"] = r.geometry.make_valid()
    r = r.dissolve(by="codigo").reset_index()
    r["area_radio"] = r.area
    c = gpd.read_file(OUTG := OUT / "geo" / "circuitos.gpkg")[["circuito", "cod_indec", "geometry"]].to_crs(AEA)
    ov = gpd.overlay(r, c, how="intersection", keep_geom_type=True)
    ov["peso"] = ov.area / ov.area_radio
    ov = ov[ov.peso > 1e-4]
    # Radios sin circuito (bordes de costa o de río): al circuito más cercano.
    sin = r[~r.codigo.isin(ov.codigo)]
    if len(sin):
        cerca = gpd.sjoin_nearest(sin[["codigo", "geometry"]], c, how="left")[["codigo", "circuito", "cod_indec"]]
        cerca["peso"] = 1.0
        ov = pd.concat([ov[["codigo", "circuito", "cod_indec", "peso"]], cerca.drop_duplicates("codigo")])
    rep = ov[["codigo", "circuito", "cod_indec", "peso"]].copy()
    # Radios casi enteros en un circuito: van enteros (la parte chica es ruido de borde).
    mx = rep.groupby("codigo").peso.transform("max")
    entero = mx >= ENTERO
    rep = pd.concat([rep[entero & (rep.peso == mx)].assign(peso=1.0), rep[~entero]])
    rep["peso"] = rep.peso / rep.groupby("codigo").peso.transform("sum")
    rep["partido_entre_circuitos"] = rep.groupby("codigo").circuito.transform("nunique") > 1
    print(f"  reparto: {rep.codigo.nunique():,} radios · {rep[rep.partido_entre_circuitos].codigo.nunique():,} "
          f"partidos entre circuitos · {len(sin)} sin circuito (al más cercano)")
    return rep, r


def main() -> None:
    TABLAS.mkdir(parents=True, exist_ok=True)
    c = conteos_por_radio()
    radio = conteos_agregados(c)
    rep, poligonos = reparto_radios()

    sin_poligono = set(radio.codigo) - set(poligonos.codigo)
    sin_tabla = set(poligonos.codigo) - set(radio.codigo)
    print(f"  radios con tabla y sin polígono: {len(sin_poligono)} "
          f"({radio[radio.codigo.isin(sin_poligono)].pob.sum():,} personas) · con polígono y sin tabla: {len(sin_tabla)}")

    radio["depto_indec"] = "06" + radio.codigo.str[2:5]
    indicadores(radio).to_csv(OUT / "censo2022_radio.csv", index=False, encoding="utf-8")

    # ¿El departamento del radio coincide con el partido de su circuito?
    m = rep.merge(radio[["codigo", "depto_indec", "pob"]], on="codigo")
    m["pob_asignada"] = m.pob * m.peso
    otro = m[m.depto_indec != m.cod_indec]
    print(f"  población asignada a un circuito de otro partido: {otro.pob_asignada.sum():,.0f} "
          f"({otro.pob_asignada.sum() / m.pob_asignada.sum():.3%})")

    conteos = [k for k in radio.columns if k not in ("codigo", "depto_indec")]
    x = rep.merge(radio[["codigo"] + conteos], on="codigo")
    x[conteos] = x[conteos].mul(x.peso, axis=0)
    x["pob_en_radios_partidos"] = np.where(x.partido_entre_circuitos, x.pob, 0)
    circ = x.groupby(["circuito", "cod_indec"])[conteos + ["pob_en_radios_partidos"]].sum().reset_index()
    circ["n_radios"] = rep.groupby("circuito").codigo.nunique().reindex(circ.circuito).values
    circ = indicadores(circ)
    pad = control_padron(circ)
    circ = circ.merge(pad[["circuito", "electores_nativos_2025", "razon_padron_2025", "calidad_cruce"]], on="circuito")
    circ.to_csv(OUT / "censo2022_circuito.csv", index=False, encoding="utf-8")
    pad.to_csv(TABLAS / "control_padron_censo_circuito.csv", index=False, encoding="utf-8")
    for anio in (2023, 2025):
        v = pad.dropna(subset=[f"electores_nativos_{anio}"])
        ok = v[f"razon_padron_{anio}"].between(0.6, 1.5)
        print(f"  padrón {anio}: {len(v)} circuitos · padrón/pob16+ = {v[f'electores_nativos_{anio}'].sum() / v.pob_16_mas.sum():.3f} · "
              f"correlación log {np.corrcoef(np.log(v[f'electores_nativos_{anio}']), np.log(v.pob_16_mas.clip(lower=1)))[0, 1]:.3f} · "
              f"padrón en circuitos con razón 0,6-1,5: {v[ok][f'electores_nativos_{anio}'].sum() / v[f'electores_nativos_{anio}'].sum():.1%}")
    print("  calidad del cruce (2025): " + ", ".join(f"{k} {n}" for k, n in circ.calidad_cruce.value_counts().items()))
    rep.to_csv(OUT / "radio_circuito_2022.csv", index=False, encoding="utf-8")

    # control: población por partido, censo por radio contra la cifra oficial del INDEC
    ma = pd.read_csv(OUT / "municipios_ma.csv", dtype={"cod_indec": str})[["cod_indec", "municipio", "pob"]]
    porp = circ.groupby("cod_indec").agg(pob_circuitos=("pob", "sum"),
                                         pob_radios_partidos=("pob_en_radios_partidos", "sum")).reset_index()
    porr = radio.groupby("depto_indec").pob.sum().rename("pob_radios").reset_index().rename(columns={"depto_indec": "cod_indec"})
    ctl = ma.rename(columns={"pob": "pob_indec"}).merge(porr, on="cod_indec", how="left").merge(porp, on="cod_indec", how="left")
    ctl["dif_radios_pct"] = (100 * (ctl.pob_radios / ctl.pob_indec - 1)).round(2)
    ctl["dif_circuitos_pct"] = (100 * (ctl.pob_circuitos / ctl.pob_indec - 1)).round(2)
    ctl.to_csv(TABLAS / "control_censo_circuitos.csv", index=False, encoding="utf-8")

    tot = ctl[["pob_indec", "pob_radios", "pob_circuitos"]].sum()
    print(f"\n  población PBA · INDEC {tot.pob_indec:,.0f} · suma de radios {tot.pob_radios:,.0f} "
          f"({tot.pob_radios / tot.pob_indec - 1:+.2%}) · suma de circuitos {tot.pob_circuitos:,.0f}")
    print(f"  partidos con |dif| > 1 % (radios): {(ctl.dif_radios_pct.abs() > 1).sum()} · "
          f"(circuitos): {(ctl.dif_circuitos_pct.abs() > 1).sum()}")
    print(f"  población en radios partidos entre circuitos: {circ.pob_en_radios_partidos.sum() / circ.pob.sum():.2%}")
    print(f"  circuitos: {len(circ)} · mediana {circ.pob.median():,.0f} hab · "
          f"mín {circ.pob.min():,.0f} · máx {circ.pob.max():,.0f}")
    print(ctl.reindex(ctl.dif_circuitos_pct.abs().sort_values(ascending=False).index).head(8)
          [["municipio", "pob_indec", "pob_radios", "pob_circuitos", "dif_radios_pct", "dif_circuitos_pct"]].to_string(index=False))


if __name__ == "__main__":
    main()
