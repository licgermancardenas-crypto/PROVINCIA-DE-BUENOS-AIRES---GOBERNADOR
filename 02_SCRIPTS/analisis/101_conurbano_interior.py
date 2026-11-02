"""
101 · Conurbano contra interior: ¿una sola elección o dos?

LA PREGUNTA, EN FORMA DE PRUEBA
-------------------------------
¿Un circuito del Conurbano vota como un circuito del interior con la misma composición social?
Si la composición explica la diferencia, es una sola provincia con barrios distintos: el motor
2027 puede modelar el voto por tipo de circuito sin importar dónde está. Si después de controlar
queda una brecha, son dos electorados y el motor necesita parámetros por zona.

UNIDAD Y DATOS
--------------
Circuito estable de la ventana 2019-2025 (`etl/10`): el mismo territorio en las cuatro
elecciones. Voto: Diputados Nacionales en las generales 2019, 2021, 2023 y 2025 (la única
categoría presente los cuatro años, sólo nativos) y Gobernador 2019 y 2023. Composición: censo
2022 sumado por CE desde los conteos (`etl/06`), así que cada indicador se recalcula, no se
promedia.

Dos juegos de controles:
- **composición**: quiénes viven ahí (educación, edad, NBI y privación, obra social, empleo,
  migración, inquilinos, cuentapropismo) y log(población / electores), regla de la casa.
- **+ urbanización**: densidad, viviendas rurales, cloaca y gas de red. Es en parte lo que
  *es* el Conurbano, así que la brecha que sobrevive a este modelo es la cota baja.

CUATRO MEDIDAS
--------------
a. La brecha bruta, ponderada por electores.
b. La brecha que queda: coeficiente de «Conurbano» en una regresión ponderada por electores, con
   error agrupado por municipio (24 grupos contra 111).
c. Fuera de muestra: validación agrupada por municipio (GroupKFold). ¿Saber la zona mejora la
   predicción del voto de municipios que el modelo no vio? Con modelo lineal y con árboles
   (HistGradientBoosting), por si la diferencia es una interacción y no un nivel.
d. Fragilidad: el coeficiente de zona sacando de a un municipio, y sacando los tres que más lo
   mueven.
Lo mismo para los **cambios** 2019→2023 (Gobernador) y 2021→2025 y 2023→2025 (Diputados).

Salidas (03_OUTPUTS/tablas/)
- conurbano_interior_base.csv   : CE × indicadores × voto
- conurbano_interior_brecha.csv : por elección y espacio: bruta, controlada (2 modelos), fragilidad
- conurbano_interior_oos.csv    : R² fuera de muestra con y sin zona
"""
from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import GroupKFold

RAIZ = Path(__file__).resolve().parents[2]
PROC = RAIZ / "01_DATOS" / "processed"
TABLAS = RAIZ / "03_OUTPUTS" / "tablas"
sys.path.insert(0, str(RAIZ / "02_SCRIPTS" / "etl"))
censo_mod = import_module("06_censo2022_circuitos")

VENTANA = "2019_2025"
ALBERS = "+proj=aea +lat_1=-34 +lat_2=-39 +lat_0=-36.5 +lon_0=-60"
COMPOSICION = ["pct_univ_completo", "pct_hasta_sec_incompleto", "pct_18_29", "pct_65_mas", "pct_hog_nbi",
               "pct_hog_privacion_convergente", "pct_sin_obra_social", "tasa_desocupacion", "pct_nac_otro_pais",
               "pct_nac_otra_prov", "pct_hog_inquilino", "pct_cuenta_propia", "log_pob_electores"]
URBANIZACION = ["log_densidad", "pct_viv_rural", "pct_hog_cloaca", "pct_hog_gas_red"]
ELECCIONES = [(2019, "DIPUTADOS NACIONALES"), (2021, "DIPUTADOS NACIONALES"), (2023, "DIPUTADOS NACIONALES"),
              (2025, "DIPUTADOS NACIONALES"), (2019, "GOBERNADOR"), (2023, "GOBERNADOR")]
CAMBIOS = [("GOBERNADOR", 2019, 2023), ("DIPUTADOS NACIONALES", 2021, 2025), ("DIPUTADOS NACIONALES", 2023, 2025)]
BLOQUES = {"peronismo": ["PERONISMO"], "derecha": ["PRO_JXC", "LLA", "LLA_PRO"]}
NO_ESPACIO = {"BLANCO", "NULO", "RECURRIDO", "IMPUGNADO", "COMANDO", "SIN_REGLA"}


def base() -> pd.DataFrame:
    eq = pd.read_csv(PROC / "circuitos_equivalencias.csv", dtype=str)
    eq = eq[eq.ventana == VENTANA][["circuito", "ce_id", "cod_indec"]]

    # Censo: conteos por circuito-polígono -> CE, e indicadores recalculados.
    c = pd.read_csv(PROC / "censo2022_circuito.csv", dtype={"circuito": str, "cod_indec": str})
    conteos = [k for k in c.columns if not k.startswith(("pct_", "tasa_")) and k not in
               ("circuito", "cod_indec", "electores_nativos_2025", "razon_padron_2025", "calidad_cruce")]
    c = c.merge(eq[["circuito", "ce_id"]], on="circuito")
    ce = c.groupby("ce_id")[conteos].sum().reset_index()
    ce = censo_mod.indicadores(ce)

    g = gpd.read_file(PROC / "geo" / "circuitos.gpkg").to_crs(ALBERS)
    g["km2"] = g.area / 1e6
    area = g.merge(eq[["circuito", "ce_id"]], on="circuito").groupby("ce_id").km2.sum()
    ce["log_densidad"] = np.log((ce.pob / ce.ce_id.map(area)).clip(lower=0.1))

    # Voto por CE.
    p = pd.read_parquet(PROC / "panel_circuito.parquet",
                        columns=["anio", "tipo", "cargo", "circuito", "espacio", "votos", "electores_nativos", "conurbano", "cod_indec"])
    p = p[(p.tipo == "GENERALES")].merge(eq[["circuito", "ce_id"]], on="circuito")
    zona = p.drop_duplicates("ce_id").set_index("ce_id")[["conurbano", "cod_indec"]]
    filas = []
    for anio, cargo in ELECCIONES:
        x = p[(p.anio == anio) & (p.cargo == cargo) & ~p.espacio.isin(NO_ESPACIO)]
        pos = x.groupby("ce_id").votos.sum()
        col = f"{cargo[:3].lower()}_{anio}"
        for b, esp in BLOQUES.items():
            filas.append((100 * x[x.espacio.isin(esp)].groupby("ce_id").votos.sum().reindex(pos.index, fill_value=0) / pos)
                         .rename(f"{b}_{col}"))
        el = x.drop_duplicates(["ce_id", "circuito"]).groupby("ce_id").electores_nativos.sum()
        filas.append(el.rename(f"electores_{col}"))
    votos = pd.concat(filas, axis=1)
    d = ce.set_index("ce_id").join(zona).join(votos, how="inner").reset_index()
    num = d.columns.difference(["ce_id", "cod_indec"])
    d[num] = d[num].astype(float)
    d["log_pob_electores"] = np.log(d.pob / d.electores_dip_2025)
    d["conurbano"] = d.conurbano.astype(int)
    return d.replace([np.inf, -np.inf], np.nan)


def wls_zona(d: pd.DataFrame, y: str, X: list[str], peso: str):
    x = d.dropna(subset=[y, peso] + X)
    A = sm.add_constant(x[X + ["conurbano"]].astype(float))
    return sm.WLS(x[y].astype(float), A, weights=x[peso].astype(float)).fit(cov_type="cluster", cov_kwds={"groups": x.cod_indec.astype("category").cat.codes}), x


def fragilidad(d: pd.DataFrame, y: str, X: list[str], peso: str, coef: float) -> dict:
    vals = {}
    for m in d.cod_indec.unique():
        r, _ = wls_zona(d[d.cod_indec != m], y, X, peso)
        vals[m] = r.params["conurbano"]
    s = pd.Series(vals)
    top3 = (s - coef).abs().nlargest(3).index
    r3, _ = wls_zona(d[~d.cod_indec.isin(top3)], y, X, peso)
    return {"sin_uno_min": s.min(), "sin_uno_max": s.max(), "sin_top3": r3.params["conurbano"],
            "top3": "|".join(top3)}


def oos(d: pd.DataFrame, y: str, X: list[str], peso: str) -> dict:
    x = d.dropna(subset=[y, peso] + X).reset_index(drop=True)
    w = x[peso].to_numpy()
    out = {}
    for nombre, modelo in [("lineal", LinearRegression), ("arboles", lambda: HistGradientBoostingRegressor(
            max_iter=300, learning_rate=0.05, min_samples_leaf=20, random_state=0))]:
        for con_zona in (False, True):
            cols = X + (["conurbano"] if con_zona else [])
            pred = np.zeros(len(x))
            for tr, te in GroupKFold(n_splits=5).split(x, groups=x.cod_indec):
                m = modelo()
                m.fit(x.loc[tr, cols], x.loc[tr, y], sample_weight=w[tr])
                pred[te] = m.predict(x.loc[te, cols])
            res = x[y] - pred
            r2 = 1 - np.sum(w * res ** 2) / np.sum(w * (x[y] - np.average(x[y], weights=w)) ** 2)
            conu = x.conurbano == 1
            out[f"r2_{nombre}{'_zona' if con_zona else ''}"] = r2
            # Residuo medio del Conurbano sin decirle al modelo la zona: la brecha que no explica.
            if not con_zona:
                out[f"residuo_conurbano_{nombre}"] = np.average(res[conu], weights=w[conu])
    return out


def main() -> None:
    TABLAS.mkdir(parents=True, exist_ok=True)
    d = base()
    resultados = [(f"{b}_{c[:3].lower()}_{a}", f"electores_{c[:3].lower()}_{a}", f"{c.title()} {a}", b)
                  for a, c in ELECCIONES for b in BLOQUES]
    for cargo, t0, t1 in CAMBIOS:
        for b in BLOQUES:
            k = f"{b}_{cargo[:3].lower()}"
            d[f"cambio_{k}_{t0}_{t1}"] = d[f"{k}_{t1}"] - d[f"{k}_{t0}"]
            resultados.append((f"cambio_{k}_{t0}_{t1}", f"electores_{cargo[:3].lower()}_{t1}",
                               f"Cambio {cargo.title()} {t0}-{t1}", b))
    d.round(4).to_csv(TABLAS / "conurbano_interior_base.csv", index=False, encoding="utf-8")
    print(f"CE: {len(d)} (Conurbano {d.conurbano.sum()}, interior {(1 - d.conurbano).sum()})")

    filas, oosf = [], []
    for y, peso, rotulo, bloque in resultados:
        x = d.dropna(subset=[y, peso])
        w = x[peso]
        cu, it = x.conurbano == 1, x.conurbano == 0
        bruta = np.average(x.loc[cu, y], weights=w[cu]) - np.average(x.loc[it, y], weights=w[it])
        fila = {"resultado": rotulo, "bloque": bloque, "media_conurbano": np.average(x.loc[cu, y], weights=w[cu]),
                "media_interior": np.average(x.loc[it, y], weights=w[it]), "brecha_bruta": bruta}
        for nombre, X in [("composicion", COMPOSICION), ("urbanizacion", COMPOSICION + URBANIZACION)]:
            r, _ = wls_zona(d, y, X, peso)
            fila[f"brecha_{nombre}"] = r.params["conurbano"]
            fila[f"ic_inf_{nombre}"] = r.conf_int().loc["conurbano", 0]
            fila[f"ic_sup_{nombre}"] = r.conf_int().loc["conurbano", 1]
            fila[f"p_{nombre}"] = r.pvalues["conurbano"]
            fila[f"r2_{nombre}"] = r.rsquared
        fila.update(fragilidad(d, y, COMPOSICION, peso, fila["brecha_composicion"]))
        filas.append(fila)
        oosf.append({"resultado": rotulo, "bloque": bloque, **oos(d, y, COMPOSICION + URBANIZACION, peso)})
        print(f"  {rotulo:38s} {bloque:9s} bruta {bruta:+6.1f}  comp {fila['brecha_composicion']:+6.1f}  "
              f"urb {fila['brecha_urbanizacion']:+6.1f}")
    br = pd.DataFrame(filas)
    from statsmodels.stats.multitest import multipletests
    for nombre in ("composicion", "urbanizacion"):
        br[f"q_{nombre}"] = multipletests(br[f"p_{nombre}"], method="fdr_bh")[1]
    br.round(4).to_csv(TABLAS / "conurbano_interior_brecha.csv", index=False, encoding="utf-8")
    o = pd.DataFrame(oosf)
    o.round(4).to_csv(TABLAS / "conurbano_interior_oos.csv", index=False, encoding="utf-8")
    pd.set_option("display.width", 250)
    print(br[["resultado", "bloque", "brecha_bruta", "brecha_composicion", "q_composicion", "brecha_urbanizacion",
              "q_urbanizacion", "sin_uno_min", "sin_uno_max", "sin_top3"]].round(2).to_string(index=False))
    print(o.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
