"""
110 · Autocorrelación espacial: ¿los hallazgos y el motor la tienen en cuenta?

LA PREGUNTA
-----------
Circuitos y municipios vecinos se parecen. Si los residuos de un análisis están correlacionados en
el espacio, los valores p que suponen observaciones independientes son demasiado optimistas, y un
motor que sortea ruido independiente por municipio subestima la incertidumbre de las secciones.

QUÉ SE HACE
-----------
1. **Motor.** Índice de Moran de los residuos del backtest (`105`) por municipio, en bruto y
   después de sacar el componente común de cada sección. Si la sección se lleva la
   autocorrelación, el ruido del motor se modela como shock de sección + ruido propio (hecho en
   el `106`).
2. **Hallazgos por circuito** (`101` Conurbano, `104` batería sobre los cambios). Para cada prueba:
   Moran de los residuos, y la misma prueba con dos correcciones espaciales: error agrupado por
   municipio y **modelo de error espacial** (SEM, máxima verosimilitud), sobre rangos como la
   batería original. Se cuenta qué sobrevive con Benjamini-Hochberg.
3. **Hallazgos por municipio** (`103` desdoblamiento): lo mismo con 135 municipios.

Vecindad: polígonos que se tocan con una tolerancia de 200 m (las capas tienen pequeñas grietas
entre partidos que dejaban 29 «islas» con la contigüidad estricta).

Salidas (03_OUTPUTS/tablas/)
- espacial_motor.csv     : Moran de los residuos del backtest, en bruto y sin sección
- espacial_hallazgos.csv : cada prueba con su Moran y sus valores p corregidos
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
from esda.moran import Moran
from libpysal.weights import fuzzy_contiguity
from scipy import stats
from spreg import ML_Error
from statsmodels.stats.multitest import multipletests

warnings.filterwarnings("ignore")
RAIZ = Path(__file__).resolve().parents[2]
PROC = RAIZ / "01_DATOS" / "processed"
TABLAS = RAIZ / "03_OUTPUTS" / "tablas"
sys.path.insert(0, str(Path(__file__).parent))
ALBERS = "+proj=aea +lat_1=-34 +lat_2=-39 +lat_0=-36.5 +lon_0=-60"


def pesos(gdf: gpd.GeoDataFrame, ids: list[str]):
    g = gdf.set_index(gdf.columns[0]).loc[ids].reset_index().to_crs(ALBERS)
    w = fuzzy_contiguity(g, buffering=True, buffer=200, ids=list(g.iloc[:, 0]))
    w.transform = "r"
    return w


def moran(v: np.ndarray, w) -> tuple[float, float]:
    m = Moran(v, w, permutations=499)
    return float(m.I), float(m.p_sim)


# ----------------------------------------------------------------------------- 1. motor
def motor(wm, ids) -> pd.DataFrame:
    r = pd.read_csv(TABLAS / "motor_residuos_municipio.csv", dtype={"cod_indec": str, "seccion": str})
    filas = []
    for par, x in r.groupby("par"):
        x = x.set_index("cod_indec").reindex(ids)
        e = x.e.fillna(x.e.mean()).to_numpy()
        sec = x.groupby("seccion").apply(lambda d: np.average(d.e, weights=d.w), include_groups=False)
        e2 = (x.e - x.seccion.map(sec)).fillna(0).to_numpy()
        i1, p1 = moran(e, wm)
        i2, p2 = moran(e2, wm)
        filas.append({"par": par, "regimen": x.regimen.dropna().iloc[0], "moran": i1, "p": p1,
                      "moran_sin_seccion": i2, "p_sin_seccion": p2})
    return pd.DataFrame(filas)


# ----------------------------------------------------------------------------- 2-3. hallazgos
def rangos(a):
    return stats.rankdata(a)


def prueba(y, x, Z, w, grupos) -> dict:
    """Spearman parcial como regresión en rangos: y ~ x + Z. Devuelve Moran de los residuos y el
    valor p de x con error agrupado y con modelo de error espacial."""
    Y = rangos(y)
    X = np.column_stack([rangos(x)] + [rangos(z) for z in Z.T])
    Xs = (X - X.mean(axis=0)) / X.std(axis=0)
    Ys = (Y - Y.mean()) / Y.std()
    ols = sm.OLS(Ys, sm.add_constant(Xs)).fit()
    clu = sm.OLS(Ys, sm.add_constant(Xs)).fit(cov_type="cluster", cov_kwds={"groups": grupos})
    i_res, p_res = moran(ols.resid, w)
    try:
        sem = ML_Error(Ys.reshape(-1, 1), Xs, w=w, method="LU")
        b_sem, p_sem, lam = float(sem.betas[1, 0]), float(sem.z_stat[1][1]), float(sem.lam)
    except Exception:
        b_sem, p_sem, lam = np.nan, np.nan, np.nan
    return {"beta": float(ols.params[1]), "p_ols": float(ols.pvalues[1]), "p_cluster_municipio": float(clu.pvalues[1]),
            "moran_residuos": i_res, "p_moran": p_res, "beta_sem": b_sem, "p_sem": p_sem, "lambda_sem": lam}


def hallazgos_104(gce) -> pd.DataFrame:
    t = import_module("104_territorio_predice")
    bat = pd.read_csv(TABLAS / "territorio_bateria.csv")
    filas = []
    for bloque, (base_fn, control, vent, niveles) in {
        "reciente": (t.base_reciente, t.CONTROL_22, "2019_2025",
                     {"Cambio peronismo · Gobernador 2019-2023": "peronismo_gob_2019",
                      "Cambio peronismo · Diputados 2023-2025": "peronismo_dip_2023",
                      "Captura de LLA-PRO · Diputados 2023-2025": "derecha_dip_2023",
                      "Cambio participación 2023-2025": "participacion_dip_2023"}),
        "largo": (t.base_larga, t.CONTROL_10, "2011_2025",
                  {"Cambio peronismo · Gobernador 2011-2023": "peronismo_gob_2011",
                   "Cambio peronismo · Diputados 2011-2023": "peronismo_dip_2011"})}.items():
        d, _ = base_fn()
        if bloque == "reciente":
            for b in ("peronismo", "derecha", "participacion"):
                d[f"cambio_{b}_dip_2023_2025"] = d[f"{b}_dip_2025"] - d[f"{b}_dip_2023"]
            d["cambio_peronismo_gob_2019_2023"] = d.peronismo_gob_2023 - d.peronismo_gob_2019
            ycol = {"Cambio peronismo · Gobernador 2019-2023": "cambio_peronismo_gob_2019_2023",
                    "Cambio peronismo · Diputados 2023-2025": "cambio_peronismo_dip_2023_2025",
                    "Captura de LLA-PRO · Diputados 2023-2025": "cambio_derecha_dip_2023_2025",
                    "Cambio participación 2023-2025": "cambio_participacion_dip_2023_2025"}
        else:
            d["cambio_peronismo_gob_2011_2023"] = d.peronismo_gob_2023 - d.peronismo_gob_2011
            d["cambio_peronismo_dip_2011_2023"] = d.peronismo_dip_2023 - d.peronismo_dip_2011
            ycol = {"Cambio peronismo · Gobernador 2011-2023": "cambio_peronismo_gob_2011_2023",
                    "Cambio peronismo · Diputados 2011-2023": "cambio_peronismo_dip_2011_2023"}
        capa = gce[vent]
        for obj, g in bat[(bat.bloque == bloque) & bat.pasa].groupby("objetivo"):
            Zc = list(control) + [niveles[obj]]
            for v in g.variable:
                x = d.dropna(subset=[ycol[obj], v] + Zc)
                x = x[x.index.isin(capa.ce_id)]
                w = pesos(capa[["ce_id", "geometry"]], list(x.index))
                r = prueba(x[ycol[obj]].to_numpy(float), x[v].to_numpy(float), x[Zc].to_numpy(float), w,
                           x.index.str[:5].astype("category").codes)
                filas.append({"analisis": "104", "objetivo": obj, "variable": v, "n": len(x), **r})
                print(f"  104 {obj[:40]:40s} {v:30s} Moran {r['moran_residuos']:+.2f} p_ols {r['p_ols']:.4f} "
                      f"p_clu {r['p_cluster_municipio']:.4f} p_sem {r['p_sem']:.4f}")
    return pd.DataFrame(filas)


def hallazgos_103(gpart) -> pd.DataFrame:
    """Rehace la base de correlatos del `103` y prueba lo que pasó."""
    dd = import_module("103_desdoblamiento")
    pm = pd.read_parquet(PROC / "panel_municipio.parquet")
    claves = pd.read_csv(PROC / "municipios_claves.csv", dtype=str).set_index("cod_indec")
    zona = claves.conurbano.map({"True": 1.0, "False": 0.0})
    sep = dd.votos_municipio(pm[(pm.fuente == "jep_definitivo") & (pm.cargo != "CONCEJALES")])
    octu = dd.votos_municipio(pm[(pm.fuente == "dine_mesa") & (pm.anio == 2025) & (pm.cargo == "DIPUTADOS NACIONALES")])
    octu["electores"] = pm[(pm.fuente == "dine_mesa") & (pm.anio == 2025)].drop_duplicates("cod_indec").set_index("cod_indec").electores_nativos
    sn = dd.septiembre_nativos(sep.loc[octu.index], octu, dd.extranjeros_2023())
    x, y = dd.proporciones(sn), dd.proporciones(octu)
    d = pd.DataFrame(index=x.index)
    d["cambio_lla_pro"] = 100 * (y.LLA_PRO - x.LLA_PRO)
    d["cambio_peronismo"] = 100 * (y.PERONISMO - x.PERONISMO)
    d["cambio_participacion"] = 100 * ((1 - y.NO_VOTO) - (1 - x.NO_VOTO))
    d["conurbano"] = zona.reindex(d.index)
    it = pm[(pm.fuente == "gba_definitivo") & (pm.anio == 2023) & (pm.cargo == "INTENDENTE") & ~pm.espacio.isin(dd.BLANCO)]
    gan = it.loc[it.groupby("cod_indec").votos.idxmax()].set_index("cod_indec").espacio
    d["intendente_peronista"] = (gan.reindex(d.index) == "PERONISMO").astype(float)
    con = pm[(pm.fuente == "jep_definitivo") & (pm.cargo == "CONCEJALES") & ~pm.espacio.isin(dd.BLANCO)]
    d["vecinal_septiembre"] = 100 * con[con.espacio == "VECINAL"].groupby("cod_indec").votos.sum().reindex(d.index).fillna(0) \
        / con.groupby("cod_indec").votos.sum().reindex(d.index)
    d["pct_extranjeros_padron"] = 100 * sn.extranjeros_electores_est / sep.electores
    per = dd.perfil_municipio()
    d = d.join(per[["pct_univ_completo", "pct_hog_nbi", "pct_65_mas", "pct_nac_otro_pais", "pob"]])
    d["log_pob_electores"] = np.log(d.pob / octu.electores.reindex(d.index))
    d = d.dropna()
    cor = pd.read_csv(TABLAS / "desdoblamiento_correlatos.csv")
    var = {"Cambio de participación (pp)": "cambio_participacion", "Conurbano": "conurbano",
           "Intendente peronista (2023)": "intendente_peronista",
           "Voto vecinal en concejales de septiembre (%)": "vecinal_septiembre",
           "Nacidos en otro país (%)": "pct_nac_otro_pais",
           "Extranjeros en el padrón de septiembre (%)": "pct_extranjeros_padron"}
    w = pesos(gpart[["cod_indec", "geometry"]], list(d.index))
    sec = claves.seccion_electoral.reindex(d.index).astype("category").cat.codes
    control = ["pct_univ_completo", "pct_hog_nbi", "pct_65_mas", "log_pob_electores"]
    filas = []
    for _, row in cor[cor.pasa].iterrows():
        yv = "cambio_lla_pro" if "LLA" in row.resultado else "cambio_peronismo"
        v = var.get(row.variable)
        if v is None:
            continue
        r = prueba(d[yv].to_numpy(float), d[v].to_numpy(float), d[control].to_numpy(float), w, sec)
        filas.append({"analisis": "103", "objetivo": row.resultado, "variable": row.variable, "n": len(d), **r})
        print(f"  103 {row.resultado[:40]:40s} {row.variable[:30]:30s} Moran {r['moran_residuos']:+.2f} "
              f"p_ols {r['p_ols']:.4f} p_sem {r['p_sem']:.4f}")
    return pd.DataFrame(filas)


def hallazgos_101(gce) -> pd.DataFrame:
    m = import_module("101_conurbano_interior")
    d = m.base()
    capa = gce["2019_2025"]
    filas = []
    for y in ["peronismo_dip_2025", "peronismo_gob_2023", "derecha_dip_2025"]:
        x = d.dropna(subset=[y] + m.COMPOSICION).set_index("ce_id")
        x = x[x.index.isin(capa.ce_id)]
        w = pesos(capa[["ce_id", "geometry"]], list(x.index))
        X = x[m.COMPOSICION + ["conurbano"]].to_numpy(float)
        Xs = (X - X.mean(axis=0)) / X.std(axis=0)
        ols = sm.OLS(x[y].to_numpy(float), sm.add_constant(X)).fit()
        i_res, p_res = moran(ols.resid, w)
        sem = ML_Error(x[y].to_numpy(float).reshape(-1, 1), X, w=w, method="LU")
        k = len(m.COMPOSICION) + 1
        filas.append({"analisis": "101", "objetivo": y, "variable": "Conurbano (pp, sin ponderar)", "n": len(x),
                      "beta": float(ols.params[k]), "p_ols": float(ols.pvalues[k]), "moran_residuos": i_res,
                      "p_moran": p_res, "beta_sem": float(sem.betas[k, 0]), "p_sem": float(sem.z_stat[k][1]),
                      "lambda_sem": float(sem.lam)})
        print(f"  101 {y:25s} Conurbano OLS {ols.params[k]:+.2f} (Moran resid {i_res:+.2f}) SEM {sem.betas[k, 0]:+.2f} p {sem.z_stat[k][1]:.4f} λ {float(sem.lam):.2f}")
        _ = Xs
    return pd.DataFrame(filas)


def main() -> None:
    TABLAS.mkdir(parents=True, exist_ok=True)
    gpart = gpd.read_file(PROC / "geo" / "partidos.gpkg")[["cod_indec", "geometry"]]
    ids = sorted(gpart.cod_indec)
    wm = pesos(gpart, ids)
    print(f"partidos sin vecinos con tolerancia de 200 m: {len(wm.islands)}")
    mo = motor(wm, ids)
    mo.round(4).to_csv(TABLAS / "espacial_motor.csv", index=False, encoding="utf-8")
    pd.set_option("display.width", 250)
    print(mo.round(3).to_string(index=False))

    gce = {v: gpd.read_file(PROC / "geo" / "circuitos_estables.gpkg", layer=f"ce_{v}")[["ce_id", "geometry"]]
           for v in ("2019_2025", "2011_2025")}
    h = pd.concat([hallazgos_101(gce), hallazgos_104(gce), hallazgos_103(gpart)], ignore_index=True)
    for col in ("p_ols", "p_cluster_municipio", "p_sem"):
        ok = h[col].notna()
        h.loc[ok, f"q_{col}"] = multipletests(h.loc[ok, col], method="fdr_bh")[1]
    h["sobrevive_sem"] = (h.q_p_sem < 0.05) & (np.sign(h.beta_sem) == np.sign(h.beta))
    h.round(5).to_csv(TABLAS / "espacial_hallazgos.csv", index=False, encoding="utf-8")
    print("\nresumen por análisis")
    print(h.groupby("analisis").agg(pruebas=("p_ols", "size"), moran_mediano=("moran_residuos", "median"),
                                    sobreviven_sem=("sobrevive_sem", "sum")).to_string())


if __name__ == "__main__":
    main()
