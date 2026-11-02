"""
109 · Movilización diferencial: quién va a votar, no sólo cuántos.

LA PREGUNTA
-----------
El motor (`106`) subía o bajaba la participación pareja: cada circuito votaba como siempre, sólo
más o menos gente. Así, la participación casi no movía el resultado (±0,1 pp). Pero la gente que
se suma cuando la participación sube —el **votante marginal**— no tiene por qué votar como el
promedio de su circuito. Entre octubre 2025 (67 % de los nativos) y una elección general de
Gobernador (~76 %) se suman más de un millón de votantes: lo que voten es una palanca.

QUÉ DICEN LOS DATOS
-------------------
1. **El votante marginal, medido por circuito.** Entre dos elecciones, dentro de cada municipio:
   cuánto cambia el voto de cada bloque (sobre el padrón) por cada punto que cambia la
   participación. Diputados Nacionales, nativos, circuitos estables. La pendiente es la
   composición de los que entran o salen **si** el cambio de preferencias no va con el cambio de
   participación; cuando sí va (2019 -> 2021 da pendientes imposibles, más de 100 %), no se puede
   separar movilización de conversión.
2. **La abstención 2023 -> 2025 por la matriz de transferencias** (`102`): quiénes, de los que
   votaron en 2023, no fueron en octubre 2025.
Las dos fuentes no coinciden y los pares no se parecen entre sí: quién se moviliza depende de la
elección. Por eso entra al motor como **perfil del escenario**, con los perfiles observados como
rango.

EL MOTOR
--------
Votos de la elección base con su participación por circuito; los que se suman hasta la
participación de 2027 votan según el perfil. Perfiles: parejo (como el promedio provincial), retorno 2023
(vuelven los que se abstuvieron en 2025, con su voto), y las composiciones marginales observadas.

Salidas (03_OUTPUTS/tablas/)
- movilizacion_marginal.csv : composición del votante marginal por par de elecciones
- movilizacion_perfiles.csv : los perfiles que usa el motor
- movilizacion_2027.csv     : escenario × perfil: resultado, P(gana), bancas
"""
from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

RAIZ = Path(__file__).resolve().parents[2]
PROC = RAIZ / "01_DATOS" / "processed"
TABLAS = RAIZ / "03_OUTPUTS" / "tablas"
sys.path.insert(0, str(Path(__file__).parent))
B = {"PERONISMO": "PERONISMO", "PRO_JXC": "DERECHA", "LLA": "DERECHA", "LLA_PRO": "DERECHA",
     "BLANCO": "BLANCO", "NULO": "BLANCO", "RECURRIDO": "BLANCO", "IMPUGNADO": "BLANCO", "COMANDO": "BLANCO"}
PARES = [(2017, 2019, "2015_2025"), (2019, 2021, "2019_2025"), (2021, 2023, "2019_2025"), (2023, 2025, "2023_2025")]


def votante_marginal() -> pd.DataFrame:
    p = pd.read_parquet(PROC / "panel_circuito.parquet",
                        columns=["anio", "tipo", "cargo", "circuito", "espacio", "votos", "electores_nativos", "votantes_nativos"])
    p = p[(p.tipo == "GENERALES") & (p.cargo == "DIPUTADOS NACIONALES")]
    eq = pd.read_csv(PROC / "circuitos_equivalencias.csv", dtype=str)

    def ce(anio, vent):
        e = eq[eq.ventana == vent][["circuito", "ce_id"]]
        x = p[p.anio == anio].merge(e, on="circuito")
        x["b"] = x.espacio.map(B).fillna("OTROS")
        v = x.pivot_table(index="ce_id", columns="b", values="votos", aggfunc="sum", fill_value=0).astype(float)
        pad = x.drop_duplicates("circuito").groupby("ce_id")[["electores_nativos", "votantes_nativos"]].sum().astype(float)
        return v.join(pad)

    filas = []
    for a0, a1, vent in PARES:
        x0, x1 = ce(a0, vent), ce(a1, vent)
        i = x0.index.intersection(x1.index)
        x0, x1 = x0.loc[i], x1.loc[i]
        ok = (x0.electores_nativos > 200) & (x1.electores_nativos > 200)
        x0, x1 = x0[ok], x1[ok]
        dT = x1.votantes_nativos / x1.electores_nativos - x0.votantes_nativos / x0.electores_nativos
        muni = pd.Series(x0.index.str[:5], index=x0.index)
        w = x1.electores_nativos
        grupos = muni.astype("category").cat.codes

        def dm(s):  # dentro de cada municipio (ponderado)
            return s - (s * w).groupby(muni).transform("sum") / w.groupby(muni).transform("sum")

        fila = {"par": f"{a0}-{a1}", "cambio_participacion_pp": 100 * np.average(dT, weights=w)}
        for b in ("PERONISMO", "DERECHA", "OTROS", "BLANCO"):
            dv = x1.get(b, 0) / x1.electores_nativos - x0.get(b, 0) / x0.electores_nativos
            r = sm.WLS(dm(dv), sm.add_constant(dm(dT)), weights=w).fit(cov_type="cluster", cov_kwds={"groups": grupos})
            fila[f"marginal_{b}"] = r.params.iloc[1]
            fila[f"ee_{b}"] = r.bse.iloc[1]
            fila[f"promedio_{b}"] = float((x0.get(b, 0)).sum() / x0.votantes_nativos.sum())
        # Separable: peronismo y derecha entre 0 y 1 y nada por debajo de −0,2 (negativos chicos = ruido).
        fila["separable"] = (all(0 <= fila[f"marginal_{b}"] <= 1 for b in ("PERONISMO", "DERECHA"))
                             and min(fila[f"marginal_{b}"] for b in ("OTROS", "BLANCO")) > -0.2)
        filas.append(fila)
    return pd.DataFrame(filas)


def perfil_retorno_2023() -> dict:
    """Los que votaron en 2023 y no fueron en octubre 2025 (matriz del `102`), con su voto de 2023."""
    m = pd.read_csv(TABLAS / "transferencias_2023_2025_matriz.csv")
    m = m[(m.ambito == "Provincia") & (m.destino == "No votó") & (m.origen != "No votó")].set_index("origen").votos
    a = {"Kicillof (UxP)": "PERONISMO", "Santilli (JxC)": "DERECHA", "Píparo (LLA)": "DERECHA",
         "Izquierda": "IZQUIERDA", "Blanco y nulo": "BLANCO"}
    tot = m.sum()
    perfil = {}
    for o, v in m.items():
        perfil[a.get(o, "RESTO")] = perfil.get(a.get(o, "RESTO"), 0) + v / tot
    return perfil


def main() -> None:
    TABLAS.mkdir(parents=True, exist_ok=True)
    mg = votante_marginal()
    mg.round(4).to_csv(TABLAS / "movilizacion_marginal.csv", index=False, encoding="utf-8")
    pd.set_option("display.width", 250)
    print(mg[["par", "cambio_participacion_pp", "marginal_PERONISMO", "marginal_DERECHA", "marginal_OTROS",
              "marginal_BLANCO", "promedio_PERONISMO", "promedio_DERECHA", "separable"]].round(2).to_string(index=False))

    perfiles = {"Retorno 2023 (vuelven los que se abstuvieron en 2025)": perfil_retorno_2023()}
    for _, r in mg[mg.separable].iterrows():
        v = {"PERONISMO": r.marginal_PERONISMO, "DERECHA": r.marginal_DERECHA, "RESTO": r.marginal_OTROS,
             "BLANCO": r.marginal_BLANCO}
        v = {k: max(x, 0.0) for k, x in v.items()}
        perfiles[f"Como {r.par}"] = {k: x / sum(v.values()) for k, x in v.items()}
    print("\nperfiles:")
    for k, v in perfiles.items():
        print(f"  {k}: " + ", ".join(f"{b} {x:.2f}" for b, x in v.items()))
    pd.DataFrame([{"perfil": k, **v} for k, v in perfiles.items()]).round(4).to_csv(
        TABLAS / "movilizacion_perfiles.csv", index=False, encoding="utf-8")

    motor = import_module("106_motor_2027")
    leg = import_module("108_legislatura_2027")
    _, sigue = leg.validacion()
    mo = motor.Motor()
    t_oct = float((mo.p25 * mo.el27).sum() / mo.el27.sum())
    print(f"\nparticipación base octubre 2025 (nativos, padrón 2027): {t_oct:.3f}")
    filas = []
    for base, part_base in [("octubre", t_oct), ("septiembre", 0.635)]:
        S = mo.provincia(mo.s_oct if base == "octubre" else mo.s_sep)
        parejo = dict(zip(motor.BLOQUES, S * 0.95))
        todos = {"Parejo (como el promedio provincial)": parejo, **perfiles}
        for nombre, perfil in todos.items():
            for pi in (None, 0.25):
                r = mo.simular(base, None, part=0.76, n=400, perfil_marginal=perfil, part_base=part_base,
                               pi_prov=pi, sd_pi_provincial=0.03 if pi else 0.0)
                nombres = r["nombres"]
                dip, sen = leg.bancas_2027(r["sec_votos"], r["sec_ids"], nombres)
                k = nombres.index("PERONISMO")
                d_tot = dip[:, k] + sigue["DIP"].get("PERONISMO", 0)
                s_tot = sen[:, k] + sigue["SEN"].get("PERONISMO", 0)
                fila = {"base": base, "derecha": "unida" if pi is None else "dividida (PRO 25 %)", "perfil": nombre,
                        "participacion_base": part_base, "participacion_2027": 0.76,
                        "pct_peronismo": r["R"][:, 0].mean(),
                        "pct_rival_principal": r["R"][:, 1].mean(),
                        "margen_p50": np.median(r["margen"]), "margen_p10": np.percentile(r["margen"], 10),
                        "margen_p90": np.percentile(r["margen"], 90), "p_gana_peronismo": r["p_gana_peronismo"],
                        "municipios_peronismo": np.median(r["munis_per"]),
                        "diputados_peronismo": np.median(d_tot), "senadores_peronismo": np.median(s_tot),
                        "p_mayoria_senado": float(np.mean(s_tot >= 24))}
                filas.append(fila)
                print(f"  {base:10s} {fila['derecha']:20s} {nombre:55s} per {fila['pct_peronismo']:4.1f} rival {fila['pct_rival_principal']:4.1f} "
                      f"margen {fila['margen_p50']:+5.1f} P {fila['p_gana_peronismo']:.2f} dip {fila['diputados_peronismo']:.0f} sen {fila['senadores_peronismo']:.0f}")
    pd.DataFrame(filas).round(3).to_csv(TABLAS / "movilizacion_2027.csv", index=False, encoding="utf-8")


if __name__ == "__main__":
    main()
