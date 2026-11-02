"""
105 · El motor 2027, paso 1: qué regla de traslado reproduce el mapa (backtest).

LA PREGUNTA
-----------
Gobernador se gana por simple pluralidad provincial: el nivel provincial de cada fuerza es un
**parámetro del escenario**, no algo que el motor adivine. Lo que el motor tiene que hacer bien es
**bajar ese nivel al territorio**: dado cuánto saca cada bloque en la provincia, cuánto saca en
cada sección, municipio y circuito. Eso se puede examinar contra el pasado.

LAS REGLAS QUE SE COMPARAN
--------------------------
Dado el resultado provincial real de la elección t1 (oráculo) y el mapa de t0:
- **sin cambio**: cada circuito repite t0;
- **uniforme**: cada circuito se mueve los mismos puntos que la provincia;
- **proporcional**: cada circuito se mueve en proporción a su nivel (cociente logarítmico:
  s1 ∝ s0 · exp(δ_bloque), con δ ajustado para que la provincia dé el resultado real). Es lo que
  sugirió el `104`.
Pares: todos los de Gobernador y Diputados Nacionales consecutivos, y los **análogos a 2027**: de
la legislativa de medio término a la de Gobernador siguiente (2013→2015, 2017→2019, 2021→2023),
como será 2025→2027.

BLOQUES
-------
Peronismo; derecha (PRO/JxC + LLA + LLA-PRO); tercera (tercera vía + centro/UCR); izquierda;
resto. Porcentaje de los positivos, por circuito estable.

LA REGLA ELEGIDA: MEZCLA
------------------------
La proporcional tiene menos error medio y acierta más ganadores; la uniforme reproduce mejor el
margen y anduvo mejor en 2023. La mezcla mitad y mitad queda cerca de la mejor en las dos medidas,
y es la que usa el motor.

DE AQUÍ SALE EL RUIDO DEL MOTOR
-------------------------------
Residuo por municipio de la regla mezcla, en cociente logarítmico peronismo / derecha. Tres cosas
que aparecieron al calibrarlo:
- depende del **tamaño**: un municipio chico se aparta mucho más (σ ∝ votos^b, b ≈ −0,29);
- depende del **régimen de oferta**: cuando entra una fuerza grande nueva (2013-2015) el ruido es
  2-3 veces mayor;
- con oferta estable tiene **colas pesadas** (t de 5 grados);
- tiene **un componente común por sección** (`110`: la autocorrelación espacial de los residuos
  se explica casi toda por la sección). El motor lo sortea aparte: shock de sección + ruido propio
  de cada municipio, con la varianza total del municipio sin cambiar.
Calibración: dejando un par afuera y reestimando todo sin él, ¿los intervalos cubren lo que dicen?

Salidas (03_OUTPUTS/tablas/)
- motor_backtest.csv          : par × regla × escala: error medio, acierto de ganador
- motor_ruido.csv             : desvío de los residuos por par
- motor_residuos_municipio.csv: los residuos, municipio por municipio
- motor_ruido_modelo.csv      : el modelo de ruido que usa el motor
- motor_calibracion.csv       : cobertura de los intervalos dejando un par afuera
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

RAIZ = Path(__file__).resolve().parents[2]
PROC = RAIZ / "01_DATOS" / "processed"
TABLAS = RAIZ / "03_OUTPUTS" / "tablas"
BLOQUES = ["PERONISMO", "DERECHA", "TERCERA", "IZQUIERDA", "RESTO"]
A_BLOQUE = {"PERONISMO": "PERONISMO", "PRO_JXC": "DERECHA", "LLA": "DERECHA", "LLA_PRO": "DERECHA",
            "TERCERA_VIA": "TERCERA", "CENTRO_UCR": "TERCERA", "IZQUIERDA": "IZQUIERDA"}
NO_POS = {"BLANCO", "NULO", "RECURRIDO", "IMPUGNADO", "COMANDO"}
G, D = "GOBERNADOR", "DIPUTADOS NACIONALES"
PARES = [
    (G, 2011, G, 2015, "gobernador"), (G, 2015, G, 2019, "gobernador"), (G, 2019, G, 2023, "gobernador"),
    (D, 2013, G, 2015, "análogo 2027"), (D, 2017, G, 2019, "análogo 2027"), (D, 2021, G, 2023, "análogo 2027"),
    (D, 2011, D, 2013, "diputados"), (D, 2013, D, 2015, "diputados"), (D, 2015, D, 2017, "diputados"),
    (D, 2017, D, 2019, "diputados"), (D, 2019, D, 2021, "diputados"), (D, 2021, D, 2023, "diputados"),
    (D, 2023, D, 2025, "diputados"),
]
# Pares en los que entra o se arma una fuerza grande nueva (el Frente Renovador de 2013-2015):
# el mapa se reacomoda mucho más y el ruido es otro.
PARES_OFERTA_NUEVA = {(2011, 2013), (2013, 2015), (2011, 2015)}
PESO_PROPORCIONAL = 0.5  # regla mezcla: mitad proporcional, mitad uniforme (ver bitácora)
DISTRIBUCION = {"oferta estable": 5, "oferta nueva": None}  # grados de libertad de la t; None = normal


def ventana(anio: int) -> str:
    return "2023_2025" if anio >= 2023 else "2019_2025" if anio >= 2019 else "2015_2025" if anio >= 2015 else "2011_2025"


def cargar():
    p = pd.read_parquet(PROC / "panel_circuito.parquet",
                        columns=["anio", "tipo", "cargo", "circuito", "espacio", "votos", "cod_indec", "seccion_electoral"])
    p = p[(p.tipo == "GENERALES") & p.cargo.isin([G, D]) & ~p.espacio.isin(NO_POS)].copy()
    p["bloque"] = p.espacio.map(A_BLOQUE).fillna("RESTO")
    eq = pd.read_csv(PROC / "circuitos_equivalencias.csv", dtype=str)
    return p, eq


def mapa(p, eq, cargo, anio, vent) -> pd.DataFrame:
    e = eq[eq.ventana == vent][["circuito", "ce_id"]]
    x = p[(p.cargo == cargo) & (p.anio == anio)].merge(e, on="circuito")
    v = x.pivot_table(index="ce_id", columns="bloque", values="votos", aggfunc="sum", fill_value=0)
    return v.reindex(columns=BLOQUES, fill_value=0).astype(float)


def proporcional(s0: np.ndarray, w: np.ndarray, S1: np.ndarray, iters: int = 200) -> np.ndarray:
    """s1 ∝ s0·exp(δ), con δ tal que el agregado ponderado dé S1. Un bloque ausente en t0 que
    aparece en t1 se siembra parejo (no hay de dónde sacar su mapa)."""
    s0 = s0.copy()
    nuevo = (s0 * w[:, None]).sum(axis=0) / w.sum() < 1e-4
    s0[:, nuevo] = 1e-3
    s0 = s0 / s0.sum(axis=1, keepdims=True)
    delta = np.zeros(s0.shape[1])
    for _ in range(iters):
        s1 = s0 * np.exp(delta)
        s1 /= s1.sum(axis=1, keepdims=True)
        agg = (s1 * w[:, None]).sum(axis=0) / w.sum()
        ok = (S1 > 0) & (agg > 0)
        delta[ok] += np.log(S1[ok] / agg[ok])
        delta[S1 == 0] = -50
    s1 = s0 * np.exp(delta)
    return s1 / s1.sum(axis=1, keepdims=True)


def uniforme(s0, w, S1):
    S0 = (s0 * w[:, None]).sum(axis=0) / w.sum()
    s1 = np.clip(s0 + (S1 - S0), 0, None)
    return s1 / np.where(s1.sum(axis=1, keepdims=True) > 0, s1.sum(axis=1, keepdims=True), 1)


def errores(pred: np.ndarray, real: np.ndarray, w: np.ndarray, grupos: pd.Series | None) -> dict:
    """Error medio absoluto (pp, ponderado) por bloque principal y acierto del ganador, a la escala dada."""
    if grupos is not None:
        P = pd.DataFrame(pred * w[:, None]).groupby(grupos.to_numpy()).sum()
        R = pd.DataFrame(real * w[:, None]).groupby(grupos.to_numpy()).sum()
        ww = R.sum(axis=1).to_numpy()
        pred, real, w = (P.to_numpy() / ww[:, None]), (R.to_numpy() / ww[:, None]), ww
    mae = np.average(np.abs(pred - real)[:, :2].mean(axis=1), weights=w) * 100
    margen_p, margen_r = pred[:, 0] - pred[:, 1], real[:, 0] - real[:, 1]
    return {"mae_pp": mae, "mae_margen_pp": np.average(np.abs(margen_p - margen_r), weights=w) * 100,
            "acierto_ganador": float(np.mean(pred.argmax(axis=1) == real.argmax(axis=1))), "unidades": len(w)}


def mezcla(s0, w, S1, peso_prop: float = PESO_PROPORCIONAL):
    return peso_prop * proporcional(s0, w, S1) + (1 - peso_prop) * uniforme(s0, w, S1)


def sigma_tamano(w: np.ndarray, coef: np.ndarray) -> np.ndarray:
    """Desvío esperado del residuo de un municipio según su tamaño: log|e| = a + b·log(votos)."""
    return np.exp(np.polyval(coef, np.log(w)))


def main() -> None:
    TABLAS.mkdir(parents=True, exist_ok=True)
    p, eq = cargar()
    seccion = p.drop_duplicates("cod_indec").set_index("cod_indec").seccion_electoral
    filas, ruido, resid = [], [], []
    for c0, a0, c1, a1, tipo in PARES:
        vent = ventana(a0)
        m0, m1 = mapa(p, eq, c0, a0, vent), mapa(p, eq, c1, a1, vent)
        ce = m0.index.intersection(m1.index)
        m0, m1 = m0.loc[ce], m1.loc[ce]
        ok = (m0.sum(axis=1) >= 30) & (m1.sum(axis=1) >= 30)
        m0, m1 = m0[ok], m1[ok]
        w = m0.sum(axis=1).to_numpy(float)
        s0 = (m0.T / m0.sum(axis=1)).T.to_numpy()
        s1 = (m1.T / m1.sum(axis=1)).T.to_numpy()
        S1 = (m1.sum() / m1.sum().sum()).to_numpy()
        muni = pd.Series(m0.index.str[:5], index=m0.index)
        secc = muni.map(seccion)
        preds = {"sin cambio": s0, "uniforme": uniforme(s0, w, S1), "proporcional": proporcional(s0, w, S1)}
        preds["mezcla"] = PESO_PROPORCIONAL * preds["proporcional"] + (1 - PESO_PROPORCIONAL) * preds["uniforme"]
        par = f"{c0[:3].title()} {a0} → {c1[:3].title()} {a1}"
        regimen = "oferta nueva" if (a0, a1) in PARES_OFERTA_NUEVA else "oferta estable"
        for regla, pr in preds.items():
            for escala, grp in [("circuito", None), ("municipio", muni), ("sección", secc)]:
                filas.append({"par": par, "tipo": tipo, "regimen": regimen, "regla": regla, "escala": escala,
                              **errores(pr, s1, w, grp)})
        # Residuo de la regla mezcla por municipio, en cociente logarítmico peronismo / derecha.
        pr = preds["mezcla"]
        Pm = pd.DataFrame(pr * w[:, None], columns=BLOQUES).groupby(muni.to_numpy()).sum()
        Rm = pd.DataFrame(s1 * w[:, None], columns=BLOQUES).groupby(muni.to_numpy()).sum()
        e = np.log((Rm.PERONISMO + 1) / (Rm.DERECHA + 1)) - np.log((Pm.PERONISMO + 1) / (Pm.DERECHA + 1))
        r = pd.DataFrame({"par": par, "tipo": tipo, "regimen": regimen, "w": Rm.sum(axis=1), "e": e})
        r["seccion"] = r.index.map(seccion)
        sec = r.groupby("seccion").apply(lambda g: np.average(g.e, weights=g.w), include_groups=False)
        ruido.append({"par": par, "tipo": tipo, "regimen": regimen,
                      "sd_municipio_ponderado": float(np.sqrt(np.average(r.e ** 2, weights=r.w))),
                      "sd_municipio_simple": float(np.sqrt(np.mean(r.e ** 2))),
                      "sd_seccion": float(np.sqrt(np.average(sec ** 2, weights=r.groupby("seccion").w.sum())))})
        resid.append(r)
        print(f"  {par:28s} listo ({len(w)} CE)")

    bt = pd.DataFrame(filas)
    bt.round(4).to_csv(TABLAS / "motor_backtest.csv", index=False, encoding="utf-8")
    rd = pd.DataFrame(ruido)
    rd.round(4).to_csv(TABLAS / "motor_ruido.csv", index=False, encoding="utf-8")
    rm = pd.concat(resid)
    rm.reset_index(names="cod_indec").round(5).to_csv(TABLAS / "motor_residuos_municipio.csv", index=False, encoding="utf-8")

    # Modelo de ruido por régimen: desvío según tamaño del municipio, escala de los residuos
    # estandarizados y distribución (t de 5 grados con oferta estable, normal con oferta nueva).
    modelo, cal = [], []
    for reg, df in DISTRIBUCION.items():
        r = rm[rm.regimen == reg]
        coef = np.polyfit(np.log(r.w), np.log(np.abs(r.e) + 1e-4), 1)
        esc = float(np.sqrt(np.mean((r.e / sigma_tamano(r.w.to_numpy(), coef)) ** 2)))
        # Shock común por sección: la media ponderada del residuo de cada sección, en cada par.
        sec = (r.assign(ew=r.e * r.w).groupby(["par", "seccion"])[["ew", "w"]].sum())
        sec = sec.ew / sec.w
        sd_sec = float(np.sqrt(np.mean(sec ** 2)))
        modelo.append({"regimen": reg, "a": coef[1], "b": coef[0], "escala": esc, "gl_t": df, "sd_seccion": sd_sec,
                       "sd_10mil_votos": float(esc * sigma_tamano(np.array([1e4]), coef)[0]),
                       "sd_500mil_votos": float(esc * sigma_tamano(np.array([5e5]), coef)[0])})
        # Calibración dejando un par afuera, con todo reestimado sin ese par.
        for par, x in r.groupby("par"):
            o = r[r.par != par]
            cf = np.polyfit(np.log(o.w), np.log(np.abs(o.e) + 1e-4), 1)
            sc = np.sqrt(np.mean((o.e / sigma_tamano(o.w.to_numpy(), cf)) ** 2))
            z = np.abs(x.e / sigma_tamano(x.w.to_numpy(), cf)) / sc
            for nivel in (0.5, 0.8, 0.9, 0.95):
                q = stats.norm.ppf(0.5 + nivel / 2) if df is None else stats.t.ppf(0.5 + nivel / 2, df) * np.sqrt((df - 2) / df)
                cal.append({"regimen": reg, "par": par, "nivel": nivel, "escala_cal": "municipio", "cobertura": float(np.mean(z <= q)),
                            "cobertura_ponderada": float(np.average(z <= q, weights=x.w))})
        # Calibración del shock de sección dejando un par afuera.
        for par in r.par.unique():
            sd_o = float(np.sqrt(np.mean(sec.drop(index=par, level=0) ** 2)))
            z = np.abs(sec.loc[par].to_numpy()) / sd_o
            for nivel in (0.5, 0.8, 0.9, 0.95):
                q = stats.norm.ppf(0.5 + nivel / 2) if df is None else stats.t.ppf(0.5 + nivel / 2, df) * np.sqrt((df - 2) / df)
                cal.append({"regimen": reg, "par": par, "nivel": nivel, "escala_cal": "sección",
                            "cobertura": float(np.mean(z <= q)), "cobertura_ponderada": np.nan})
    pd.DataFrame(modelo).round(5).to_csv(TABLAS / "motor_ruido_modelo.csv", index=False, encoding="utf-8")
    cal = pd.DataFrame(cal)
    cal.round(4).to_csv(TABLAS / "motor_calibracion.csv", index=False, encoding="utf-8")

    pd.set_option("display.width", 250)
    t = bt[bt.escala == "municipio"].pivot_table(index=["tipo", "par"], columns="regla", values="mae_pp").round(2)
    print("\nError medio por municipio (pp, peronismo y derecha)\n", t.to_string())
    print("\nResumen por regla\n", bt.groupby(["escala", "regla"])[["mae_pp", "mae_margen_pp", "acierto_ganador"]].mean().round(3).to_string())
    print("\nRuido por par\n", rd.round(3).to_string(index=False))
    print("\nModelo de ruido\n", pd.DataFrame(modelo).round(3).to_string(index=False))
    print("\nCalibración dejando un par afuera\n", cal.groupby(["escala_cal", "regimen", "nivel"])[["cobertura", "cobertura_ponderada"]].mean().round(3).to_string())


if __name__ == "__main__":
    main()
