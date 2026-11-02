"""
104 · Lo que el territorio predice y lo que no: nivel contra cambio.

LA PREGUNTA
-----------
¿Cuánto del voto de un circuito se adivina sabiendo quién vive ahí? En CABA la respuesta fue
asimétrica: el censo predice muy bien el **nivel** de voto de cada fuerza y nada el **cambio**
entre elecciones (la retención del PRO dio R² validado negativo). Antes de construir el motor
2027 hay que saber si en PBA pasa lo mismo, porque decide qué se modela con el territorio y qué
con un movimiento común.

DOS PREGUNTAS MÁS QUE EN CABA
-----------------------------
1. **¿El censo le gana a la inercia?** El motor parte del último resultado de cada circuito. Si
   el censo no agrega nada sobre «votará como la vez pasada», sobra en el nivel.
2. **El largo plazo:** ¿los circuitos que más cambiaron socialmente entre 2010 y 2022 son los que
   más cambiaron de voto entre 2011 y 2023?

MÉTODO
------
- Unidades: circuitos estables 2019-2025 (997) para lo reciente, 2011-2025 (919) para lo largo.
- Voto en **porcentajes** (cuotas), nunca razones entre cantidades (trampa del denominador,
  documentada en CABA). Diputados Nacionales: sólo nativos, presente todos los años.
- Predicción fuera de muestra: GroupKFold por municipio (5 grupos), ponderado por electores.
  Modelos: media, inercia (el mismo resultado en la elección anterior), censo (elastic net y
  árboles) y censo + inercia.
- Batería sobre los **cambios**: Spearman parcial de cada indicador descontando NBI,
  universitarios, los dos tramos de edad, log(población / electores) y **el nivel de partida**
  (si no, lo que aparece es el cambio proporcional al nivel); Benjamini-Hochberg sobre
  toda la batería; fragilidad por distancia de Cook (sin el circuito más influyente y sin los
  tres). Pasa si q < 0,05 y mantiene signo y |ρ| ≥ 0,1 en las dos pruebas de fragilidad.

Salidas (03_OUTPUTS/tablas/)
- territorio_prediccion.csv : R² fuera de muestra por objetivo y modelo
- territorio_bateria.csv    : batería sobre los cambios, con los tres filtros
"""
from __future__ import annotations

import sys
import warnings
from importlib import import_module
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import ElasticNetCV, LinearRegression
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from statsmodels.stats.multitest import multipletests

warnings.filterwarnings("ignore")
RAIZ = Path(__file__).resolve().parents[2]
PROC = RAIZ / "01_DATOS" / "processed"
TABLAS = RAIZ / "03_OUTPUTS" / "tablas"
sys.path.insert(0, str(RAIZ / "02_SCRIPTS" / "etl"))
censo22 = import_module("06_censo2022_circuitos")
censo_hist = import_module("07_censos_historicos_circuitos")
ALBERS = "+proj=aea +lat_1=-34 +lat_2=-39 +lat_0=-36.5 +lon_0=-60"
NO_ESPACIO = {"BLANCO", "NULO", "RECURRIDO", "IMPUGNADO", "COMANDO", "SIN_REGLA"}
DERECHA = {"PRO_JXC", "LLA", "LLA_PRO"}
CONTROL_22 = ["pct_hog_nbi", "pct_univ_completo", "pct_18_29", "pct_65_mas", "log_pob_electores"]
CONTROL_10 = ["pct_hog_nbi_2010", "pct_llego_universidad_2010", "pct_15_29_2010", "pct_65_mas_2010", "log_pob_electores"]


# ----------------------------------------------------------------------------- datos
def voto_ce(ventana: str, elecciones: list[tuple[int, str]]) -> pd.DataFrame:
    eq = pd.read_csv(PROC / "circuitos_equivalencias.csv", dtype=str)
    eq = eq[eq.ventana == ventana][["circuito", "ce_id"]]
    p = pd.read_parquet(PROC / "panel_circuito.parquet",
                        columns=["anio", "tipo", "cargo", "circuito", "espacio", "votos", "electores_nativos",
                                 "votantes_nativos", "cod_indec", "conurbano"])
    p = p[p.tipo == "GENERALES"].merge(eq, on="circuito")
    cols = {}
    for anio, cargo in elecciones:
        x = p[(p.anio == anio) & (p.cargo == cargo)]
        k = f"{cargo[:3].lower()}_{anio}"
        pos = x[~x.espacio.isin(NO_ESPACIO)].groupby("ce_id").votos.sum()
        cols[f"peronismo_{k}"] = 100 * x[x.espacio == "PERONISMO"].groupby("ce_id").votos.sum().reindex(pos.index, fill_value=0) / pos
        cols[f"derecha_{k}"] = 100 * x[x.espacio.isin(DERECHA)].groupby("ce_id").votos.sum().reindex(pos.index, fill_value=0) / pos
        pad = x.drop_duplicates("circuito").groupby("ce_id")[["electores_nativos", "votantes_nativos"]].sum()
        cols[f"participacion_{k}"] = 100 * pad.votantes_nativos / pad.electores_nativos
        cols[f"electores_{k}"] = pad.electores_nativos
    d = pd.DataFrame(cols)
    info = p.drop_duplicates("ce_id").set_index("ce_id")[["cod_indec", "conurbano"]]
    return d.join(info)


def area_ce(ventana: str) -> pd.Series:
    eq = pd.read_csv(PROC / "circuitos_equivalencias.csv", dtype=str)
    eq = eq[eq.ventana == ventana][["circuito", "ce_id"]]
    g = gpd.read_file(PROC / "geo" / "circuitos.gpkg").to_crs(ALBERS)
    g["km2"] = g.area / 1e6
    return g.merge(eq, on="circuito").groupby("ce_id").km2.sum()


def base_reciente() -> tuple[pd.DataFrame, list[str]]:
    v = voto_ce("2019_2025", [(2019, "DIPUTADOS NACIONALES"), (2021, "DIPUTADOS NACIONALES"),
                              (2023, "DIPUTADOS NACIONALES"), (2025, "DIPUTADOS NACIONALES"),
                              (2019, "GOBERNADOR"), (2023, "GOBERNADOR")])
    eq = pd.read_csv(PROC / "circuitos_equivalencias.csv", dtype=str)
    eq = eq[eq.ventana == "2019_2025"][["circuito", "ce_id"]]
    c = pd.read_csv(PROC / "censo2022_circuito.csv", dtype={"circuito": str, "cod_indec": str})
    conteos = [k for k in c.columns if not k.startswith(("pct_", "tasa_")) and k not in
               ("circuito", "cod_indec", "electores_nativos_2025", "razon_padron_2025", "calidad_cruce")]
    ce = censo22.indicadores(c.merge(eq, on="circuito").groupby("ce_id")[conteos].sum().reset_index()).set_index("ce_id")
    rasgos = [k for k in ce.columns if k.startswith(("pct_", "tasa_"))]
    ce["log_densidad"] = np.log((ce.pob / area_ce("2019_2025")).clip(lower=0.1))
    d = v.join(ce[rasgos + ["pob", "log_densidad"]], how="inner")
    d["log_pob_electores"] = np.log(d.pob / d.electores_dip_2025)
    d = d.replace([np.inf, -np.inf], np.nan)
    return d, rasgos + ["log_densidad", "log_pob_electores"]


def base_larga() -> tuple[pd.DataFrame, list[str]]:
    v = voto_ce("2011_2025", [(2011, "DIPUTADOS NACIONALES"), (2023, "DIPUTADOS NACIONALES"),
                              (2011, "GOBERNADOR"), (2023, "GOBERNADOR")])
    eq = pd.read_csv(PROC / "circuitos_equivalencias.csv", dtype=str)
    eq = eq[eq.ventana == "2011_2025"][["circuito", "ce_id"]]
    s = pd.read_csv(PROC / "censos_circuito_serie.csv", dtype={"circuito": str, "cod_indec": str})
    s = s[s.censo.isin([2010, 2022])].merge(eq, on="circuito")
    out = []
    for anio, x in s.groupby("censo"):
        agg = censo_hist.indicadores(x.groupby("ce_id")[censo_hist.CONTEOS].sum(min_count=1).reset_index()).set_index("ce_id")
        ind = agg[list(censo_hist.COMUNES)].add_suffix(f"_{anio}")
        ind[f"pob_{anio}"] = agg.pob
        out.append(ind)
    ce = pd.concat(out, axis=1)
    cambios = []
    for k in censo_hist.COMUNES:
        if ce[f"{k}_2010"].notna().sum() > 100 and ce[f"{k}_2022"].notna().sum() > 100:
            ce[f"d_{k}"] = ce[f"{k}_2022"] - ce[f"{k}_2010"]
            cambios.append(f"d_{k}")
    ce["crec_pob_10_22"] = 100 * (ce.pob_2022 / ce.pob_2010 - 1)
    ce.loc[ce.pob_2010 < 200, "crec_pob_10_22"] = np.nan
    d = v.join(ce, how="inner")
    d["log_pob_electores"] = np.log(d.pob_2022 / d.electores_dip_2023)
    d = d.replace([np.inf, -np.inf], np.nan)
    niveles = [f"{k}_2010" for k in censo_hist.COMUNES if f"d_{k}" in cambios]
    return d, niveles + cambios + ["crec_pob_10_22", "log_pob_electores"]


# ----------------------------------------------------------------------------- predicción
def r2w(y, p, w):
    return 1 - np.sum(w * (y - p) ** 2) / np.sum(w * (y - np.average(y, weights=w)) ** 2)


def predecir(d: pd.DataFrame, y: str, peso: str, rasgos: list[str], inercia: str | None, nivel: str | None = None) -> dict:
    """`nivel`: para un cambio, el nivel de partida. Si el cambio es proporcional al nivel (cada circuito
    pierde la misma fracción de su voto), el censo «predice» el cambio sólo porque predice el nivel."""
    x = d.dropna(subset=[y, peso] + ([inercia] if inercia else []) + ([nivel] if nivel else [])).reset_index()
    X = x[rasgos].fillna(x[rasgos].median())
    w = x[peso].to_numpy()
    preds = {k: np.zeros(len(x)) for k in ["media", "inercia", "censo_lineal", "censo_arboles", "censo_mas_inercia",
                                           "nivel_inicial", "censo_mas_nivel"]}
    for tr, te in GroupKFold(n_splits=5).split(x, groups=x.cod_indec):
        yt, wt = x.loc[tr, y], w[tr]
        preds["media"][te] = np.average(yt, weights=wt)
        if inercia:
            m = LinearRegression().fit(x.loc[tr, [inercia]], yt, sample_weight=wt)
            preds["inercia"][te] = m.predict(x.loc[te, [inercia]])
        en = make_pipeline(StandardScaler(), ElasticNetCV(l1_ratio=[0.2, 0.5, 0.9], cv=4, n_alphas=30, max_iter=5000))
        en.fit(X.loc[tr], yt, elasticnetcv__sample_weight=wt)
        preds["censo_lineal"][te] = en.predict(X.loc[te])
        hgb = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, min_samples_leaf=20, random_state=0)
        hgb.fit(X.loc[tr], yt, sample_weight=wt)
        preds["censo_arboles"][te] = hgb.predict(X.loc[te])
        if inercia:
            Xi = pd.concat([X, x[[inercia]]], axis=1)
            en2 = make_pipeline(StandardScaler(), ElasticNetCV(l1_ratio=[0.2, 0.5, 0.9], cv=4, n_alphas=30, max_iter=5000))
            en2.fit(Xi.loc[tr], yt, elasticnetcv__sample_weight=wt)
            preds["censo_mas_inercia"][te] = en2.predict(Xi.loc[te])
        if nivel:
            m = LinearRegression().fit(x.loc[tr, [nivel]], yt, sample_weight=wt)
            preds["nivel_inicial"][te] = m.predict(x.loc[te, [nivel]])
            Xn = pd.concat([X, x[[nivel]]], axis=1)
            en3 = make_pipeline(StandardScaler(), ElasticNetCV(l1_ratio=[0.2, 0.5, 0.9], cv=4, n_alphas=30, max_iter=5000))
            en3.fit(Xn.loc[tr], yt, elasticnetcv__sample_weight=wt)
            preds["censo_mas_nivel"][te] = en3.predict(Xn.loc[te])
    out = {"n": len(x)}
    for k, p in preds.items():
        if (k in ("inercia", "censo_mas_inercia") and not inercia) or (k in ("nivel_inicial", "censo_mas_nivel") and not nivel):
            out[f"r2_{k}"] = np.nan
            continue
        out[f"r2_{k}"] = r2w(x[y].to_numpy(), p, w)
        out[f"rmse_{k}"] = float(np.sqrt(np.average((x[y].to_numpy() - p) ** 2, weights=w)))
    return out


# ----------------------------------------------------------------------------- batería
def rangos_resid(v, RZ):
    return v - RZ @ np.linalg.lstsq(RZ, v, rcond=None)[0]


def parcial(a, b, Z):
    ra, rb = stats.rankdata(a), stats.rankdata(b)
    RZ = np.column_stack([np.ones(len(a))] + [stats.rankdata(z) for z in Z.T])
    ea, eb = rangos_resid(ra, RZ), rangos_resid(rb, RZ)
    r = np.corrcoef(ea, eb)[0, 1]
    df = len(a) - 2 - Z.shape[1]
    return r, 2 * stats.t.sf(abs(r * np.sqrt(df / (1 - r ** 2))), df)


def bateria(d: pd.DataFrame, objetivos: dict[str, tuple[str, str]], rasgos: list[str], control: list[str]) -> pd.DataFrame:
    """objetivos: cambio -> (rótulo, nivel de partida). El nivel de partida entra en los controles: lo que
    queda es lo que el territorio dice del cambio más allá del cambio proporcional."""
    filas = []
    for y, (rot, nivel) in objetivos.items():
        for v in rasgos:
            if v in control:
                continue
            Zc = list(control) + [nivel]
            x = d.dropna(subset=[y, v] + Zc)
            if len(x) < 50 or x[v].nunique() < 10:
                continue
            a, b, Z = x[v].to_numpy(float), x[y].to_numpy(float), x[Zc].to_numpy(float)
            r, p = parcial(a, b, Z)
            # Cook sobre la regresión en rangos y ~ x + controles.
            A = sm.add_constant(np.column_stack([stats.rankdata(a)] + [stats.rankdata(z) for z in Z.T]))
            cook = sm.OLS(stats.rankdata(b), A).fit().get_influence().cooks_distance[0]
            orden = np.argsort(-cook)
            keep1, keep3 = np.ones(len(a), bool), np.ones(len(a), bool)
            keep1[orden[:1]] = False
            keep3[orden[:3]] = False
            r1, _ = parcial(a[keep1], b[keep1], Z[keep1])
            r3, _ = parcial(a[keep3], b[keep3], Z[keep3])
            filas.append({"objetivo": rot, "variable": v, "n": len(x), "spearman": stats.spearmanr(a, b)[0],
                          "spearman_parcial": r, "p": p, "sin_1": r1, "sin_3": r3})
    t = pd.DataFrame(filas)
    t["q_bh"] = multipletests(t.p, method="fdr_bh")[1]
    t["pasa"] = (t.q_bh < 0.05) & (np.sign(t.sin_1) == np.sign(t.spearman_parcial)) & \
                (np.sign(t.sin_3) == np.sign(t.spearman_parcial)) & (t.sin_3.abs() >= 0.1)
    return t


def main() -> None:
    TABLAS.mkdir(parents=True, exist_ok=True)
    d, rasgos = base_reciente()
    for b in ("peronismo", "derecha", "participacion"):
        d[f"cambio_{b}_dip_2023_2025"] = d[f"{b}_dip_2025"] - d[f"{b}_dip_2023"]
        d[f"cambio_{b}_dip_2021_2023"] = d[f"{b}_dip_2023"] - d[f"{b}_dip_2021"]
        d[f"cambio_{b}_dip_2021_2025"] = d[f"{b}_dip_2025"] - d[f"{b}_dip_2021"]
    d["cambio_peronismo_gob_2019_2023"] = d.peronismo_gob_2023 - d.peronismo_gob_2019
    d["cambio_peronismo_dip_2019_2021"] = d.peronismo_dip_2021 - d.peronismo_dip_2019
    print(f"reciente: {len(d)} CE")

    # (objetivo, peso, inercia, rótulo, tipo)
    objetivos = [
        ("peronismo_dip_2025", "electores_dip_2025", "peronismo_dip_2023", "Peronismo · Diputados 2025", "nivel"),
        ("derecha_dip_2025", "electores_dip_2025", "derecha_dip_2023", "LLA-PRO · Diputados 2025", "nivel"),
        ("participacion_dip_2025", "electores_dip_2025", "participacion_dip_2023", "Participación 2025", "nivel"),
        ("peronismo_gob_2023", "electores_gob_2023", "peronismo_gob_2019", "Peronismo · Gobernador 2023", "nivel"),
        ("cambio_peronismo_gob_2019_2023", "electores_gob_2023", "cambio_peronismo_dip_2019_2021", "Cambio peronismo · Gobernador 2019-2023", "cambio"),
        ("cambio_peronismo_dip_2023_2025", "electores_dip_2025", "cambio_peronismo_dip_2021_2023", "Cambio peronismo · Diputados 2023-2025", "cambio"),
        ("cambio_derecha_dip_2023_2025", "electores_dip_2025", "cambio_derecha_dip_2021_2023", "Captura de LLA-PRO · Diputados 2023-2025", "cambio"),
        ("cambio_participacion_dip_2023_2025", "electores_dip_2025", "cambio_participacion_dip_2021_2023", "Cambio participación 2023-2025", "cambio"),
    ]
    filas = []
    for y, peso, ine, rot, tipo in objetivos:
        nivel = {"cambio_peronismo_gob_2019_2023": "peronismo_gob_2019", "cambio_peronismo_dip_2023_2025": "peronismo_dip_2023",
                 "cambio_derecha_dip_2023_2025": "derecha_dip_2023",
                 "cambio_participacion_dip_2023_2025": "participacion_dip_2023"}.get(y)
        r = predecir(d, y, peso, rasgos, ine, nivel)
        filas.append({"objetivo": rot, "tipo": tipo, "inercia_usada": ine, **r})
        print(f"  {rot:45s} media {r['r2_media']:+.2f} inercia {r['r2_inercia']:+.2f} censo {r['r2_censo_lineal']:+.2f}/"
              f"{r['r2_censo_arboles']:+.2f} censo+inercia {r['r2_censo_mas_inercia']:+.2f} nivel {r['r2_nivel_inicial']:+.2f} censo+nivel {r['r2_censo_mas_nivel']:+.2f}")

    dl, rasgos_l = base_larga()
    dl["cambio_peronismo_gob_2011_2023"] = dl.peronismo_gob_2023 - dl.peronismo_gob_2011
    dl["cambio_peronismo_dip_2011_2023"] = dl.peronismo_dip_2023 - dl.peronismo_dip_2011
    print(f"largo: {len(dl)} CE")
    for y, peso, rot in [("cambio_peronismo_gob_2011_2023", "electores_gob_2023", "Cambio peronismo · Gobernador 2011-2023"),
                         ("cambio_peronismo_dip_2011_2023", "electores_dip_2023", "Cambio peronismo · Diputados 2011-2023")]:
        r = predecir(dl, y, peso, rasgos_l, None, y.replace("cambio_", "").replace("_2011_2023", "_2011"))
        filas.append({"objetivo": rot, "tipo": "cambio largo", "inercia_usada": None, **r})
        print(f"  {rot:45s} censo {r['r2_censo_lineal']:+.2f}/{r['r2_censo_arboles']:+.2f} nivel {r['r2_nivel_inicial']:+.2f} censo+nivel {r['r2_censo_mas_nivel']:+.2f}")
    pr = pd.DataFrame(filas)
    pr.round(3).to_csv(TABLAS / "territorio_prediccion.csv", index=False, encoding="utf-8")

    niveles = {"cambio_peronismo_gob_2019_2023": "peronismo_gob_2019", "cambio_peronismo_dip_2023_2025": "peronismo_dip_2023",
               "cambio_derecha_dip_2023_2025": "derecha_dip_2023", "cambio_participacion_dip_2023_2025": "participacion_dip_2023"}
    b1 = bateria(d, {o[0]: (o[3], niveles[o[0]]) for o in objetivos if o[4] == "cambio"}, rasgos, CONTROL_22)
    b2 = bateria(dl, {"cambio_peronismo_gob_2011_2023": ("Cambio peronismo · Gobernador 2011-2023", "peronismo_gob_2011"),
                      "cambio_peronismo_dip_2011_2023": ("Cambio peronismo · Diputados 2011-2023", "peronismo_dip_2011")},
                 [r for r in rasgos_l if r.startswith(("d_", "crec"))], CONTROL_10)
    b = pd.concat([b1.assign(bloque="reciente"), b2.assign(bloque="largo")])
    b.round(4).to_csv(TABLAS / "territorio_bateria.csv", index=False, encoding="utf-8")
    pd.set_option("display.width", 250)
    print(f"\nbatería: {len(b)} pruebas, pasan {int(b.pasa.sum())}")
    print(b[b.pasa].sort_values(["objetivo", "spearman_parcial"])[["objetivo", "variable", "spearman", "spearman_parcial",
                                                                     "q_bh", "sin_1", "sin_3"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
