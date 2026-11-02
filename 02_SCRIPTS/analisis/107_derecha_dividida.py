"""
107 · El motor 2027 con la derecha dividida.

LA PREGUNTA
-----------
En 2025 LLA y el PRO fueron juntos. ¿Qué pasa en 2027 si van separados? Gobernador se gana por
simple pluralidad, sin balotaje: si la derecha se divide, el peronismo gana con menos votos. La
pregunta útil es **cuánto**: con qué reparto de la derecha y con qué margen sobre la derecha unida
el peronismo sigue primero, y cómo queda el mapa.

CÓMO
----
Sobre el motor del `106`. En cada simulación el bloque de la derecha de cada circuito se parte
entre LLA y el PRO con el patrón de Gobernador 2023 (Píparo contra Santilli, sólo nativos),
corrido para dar el reparto provincial del escenario, con ruido municipal calibrado con el único
par que tiene a las dos fuerzas (Diputados 2021 -> Gobernador 2023): error medio 5 pp por
municipio, correlación 0,72. Los extranjeros se reparten con el patrón de su municipio.

El reparto provincial es el parámetro: en 2023 el PRO (Santilli) fue el 52 % de la derecha; en
2025 la alianza la encabezó LLA. **No se modela el voto útil**: si la derecha va dividida, parte de
sus votantes puede concentrarse en el que mejor mide. Eso es equivalente a un reparto más
desparejo, y la grilla lo cubre.

Salidas (03_OUTPUTS/tablas/)
- motor_2027_dividida_escenarios.csv : reparto × base: % de cada uno, quién gana, municipios
- motor_2027_dividida_grilla.csv     : margen peronismo − derecha unida × reparto: P(gana el peronismo)
- motor_2027_dividida_municipio.csv  : escenario × municipio, probabilidad de que gane cada uno
"""
from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
TABLAS = RAIZ / "03_OUTPUTS" / "tablas"
sys.path.insert(0, str(Path(__file__).parent))
motor = import_module("106_motor_2027")
BLOQUES = motor.BLOQUES


def main() -> None:
    mo = motor.Motor()
    S_oct = mo.provincia(mo.s_oct) * 100
    S_sep = mo.provincia(mo.s_sep) * 100
    medio = dict(zip(BLOQUES, (S_oct + S_sep) / 2))
    pi23 = float(np.average(mo.pi23, weights=mo.s_oct[:, 1] * mo.w))
    print(f"parte del PRO en la derecha, patrón 2023 aplicado a octubre: {pi23:.3f}")

    filas, muni = [], []
    escenarios = "--solo-grilla" not in sys.argv
    for base_nom, base, metas in [("Octubre 2025", "octubre", None), ("Punto medio sept-oct", "octubre", medio),
                                  ("Septiembre 2025", "septiembre", None)]:
        for pi, rot in [(None, "unida"), (0.52, "dividida, PRO 52 % (como 2023)"), (0.35, "dividida, PRO 35 %"),
                        (0.25, "dividida, PRO 25 %"), (0.15, "dividida, PRO 15 %")]:
            if not escenarios:
                continue
            r = mo.simular(base, metas, pi_prov=pi, sd_pi_provincial=0.03 if pi else 0.0)
            nombres = r["nombres"]
            fila = {"base": base_nom, "derecha": rot, "parte_pro": pi}
            for k, nmb in enumerate(nombres):
                fila[f"pct_{nmb}"] = r["R"][:, k].mean()
                fila[f"p_primero_{nmb}"] = r["p_primero"][k]
                fila[f"municipios_{nmb}"] = np.median(r["munis_primero"][:, k])
                fila[f"secciones_{nmb}"] = r["sec_p_k"][:, k].sum()
            fila["margen_peronismo_sobre_segundo_p50"] = np.median(r["margen"])
            filas.append(fila)
            for j, m in enumerate(mo.munis):
                muni.append({"base": base_nom, "derecha": rot, "cod_indec": m, "municipio": mo.nombre_muni.get(m, m),
                             **{f"p_{nmb}": r["muni_p_k"][j, k] for k, nmb in enumerate(nombres)}})
            print(f"  {base_nom:22s} {rot:32s} " + "  ".join(f"{nmb[:4]} {r['R'][:, k].mean():4.1f}" for k, nmb in enumerate(nombres))
                  + f"   P(peronismo) {r['p_gana_peronismo']:.2f}  municipios " +
                  " ".join(f"{nmb[:3]} {np.median(r['munis_primero'][:, k]):.0f}" for k, nmb in enumerate(nombres) if k < 3))
    if escenarios:
        pd.DataFrame(filas).round(3).to_csv(TABLAS / "motor_2027_dividida_escenarios.csv", index=False, encoding="utf-8")
        pd.DataFrame(muni).round(3).to_csv(TABLAS / "motor_2027_dividida_municipio.csv", index=False, encoding="utf-8")

    # Grilla: margen del peronismo sobre la derecha unida (base octubre) × parte del PRO.
    grilla = []
    tot = S_oct[0] + S_oct[1]
    for mg in range(-24, 9, 2):
        metas = dict(zip(BLOQUES, S_oct))
        metas["PERONISMO"], metas["DERECHA"] = (tot + mg) / 2, (tot - mg) / 2
        for pi in (0.10, 0.20, 0.30, 0.40, 0.50):
            r = mo.simular("octubre", metas, n=80, pi_prov=pi, sd_pi_provincial=0.03, semilla=(mg + 30) * 100 + int(pi * 100))
            grilla.append({"margen_sobre_derecha_unida": mg, "parte_pro": pi, "p_gana_peronismo": r["p_gana_peronismo"],
                           "p_gana_lla": r["p_primero"][1], "p_gana_pro": r["p_primero"][2],
                           "pct_peronismo": r["R"][:, 0].mean(), "pct_lla": r["R"][:, 1].mean(), "pct_pro": r["R"][:, 2].mean()})
    g = pd.DataFrame(grilla)
    g.round(3).to_csv(TABLAS / "motor_2027_dividida_grilla.csv", index=False, encoding="utf-8")
    pd.set_option("display.width", 250)
    print("\nP(gana el peronismo): filas = margen sobre la derecha unida, columnas = parte del PRO en la derecha\n",
          g.pivot(index="margen_sobre_derecha_unida", columns="parte_pro", values="p_gana_peronismo").round(2).to_string())


if __name__ == "__main__":
    main()
