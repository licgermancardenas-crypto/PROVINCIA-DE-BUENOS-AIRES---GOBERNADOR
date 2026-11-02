"""
108 · La Legislatura 2027: bancas por sección con el sistema de cociente.

LA REGLA (Ley 5.109, texto ordenado, arts. 115 y 116)
------------------------------------------------------
En cada sección, sobre los votos positivos (sin blancos ni nulos):
a) cociente = votos / bancas en juego;
b) cada lista recibe tantas bancas como veces contiene el cociente; **las listas que no llegan al
   cociente quedan sin representación**;
c) las bancas que faltan van a las listas (con representación) de mayor residuo, y si aún faltan,
   a la más votada; a igual residuo, la más votada.
Si ninguna lista llega al cociente, el piso es la mitad.

QUÉ SE ELIGE EN 2027
--------------------
La Legislatura se renueva por mitades y cada sección alterna cámara. En 2027, como en 2023:
diputados en la 1ª (15), 4ª (14), 5ª (11) y 7ª (6): 46 de 92; senadores en la 2ª (5), 3ª (9), 6ª (6)
y 8ª (3): 23 de 46. Siguen hasta 2029 los electos en 2025.

PASOS
-----
1. Validación: la regla aplicada a los resultados reales por lista de 2023 y 2025.
2. 2027: en cada simulación del motor (`106`) se reparten las bancas de cada sección. Los bloques
   son listas; el «resto» se supone fragmentado en listas chicas que no llegan al cociente (cuenta
   para el total pero no recibe bancas). Composición 2027-2029 = electos 2025 + electos 2027.

Salidas (03_OUTPUTS/tablas/)
- legislatura_validacion.csv       : bancas por sección y lista en 2023 y 2025 según la regla
- legislatura_2027_escenarios.csv  : escenario × bloque: bancas 2027 y composición de cada cámara
"""
from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
PROC = RAIZ / "01_DATOS" / "processed"
RAW = RAIZ / "01_DATOS" / "raw" / "electoral"
TABLAS = RAIZ / "03_OUTPUTS" / "tablas"
sys.path.insert(0, str(Path(__file__).parent))

DIP = {"1": 15, "2": 11, "3": 18, "4": 14, "5": 11, "6": 11, "7": 6, "8": 6}
SEN = {"1": 8, "2": 5, "3": 9, "4": 7, "5": 5, "6": 6, "7": 3, "8": 3}
CAMARA_2027 = {"1": "DIP", "4": "DIP", "5": "DIP", "7": "DIP", "2": "SEN", "3": "SEN", "6": "SEN", "8": "SEN"}
SECCION_NUM = {"Primera": "1", "Segunda": "2", "Tercera": "3", "Cuarta": "4", "Quinta": "5", "Sexta": "6",
               "Séptima": "7", "Septima": "7", "Capital": "8", "Octava": "8"}


def reparto(votos: dict[str, float], bancas: int, elegibles: set[str] | None = None) -> dict[str, int]:
    """Arts. 115-116 de la Ley 5.109. `elegibles`: listas que pueden recibir bancas (el resto cuenta
    en el total pero no es una lista: p. ej. «resto», que son muchas listas chicas)."""
    total = sum(votos.values())
    if total <= 0:
        return {}
    cand = {k: v for k, v in votos.items() if elegibles is None or k in elegibles}
    q = total / bancas
    piso = q if any(v >= q for v in cand.values()) else q / 2
    pasan = {k: v for k, v in cand.items() if v >= piso}
    asign = {k: int(v // q) for k, v in pasan.items()}
    faltan = bancas - sum(asign.values())
    orden = sorted(pasan, key=lambda k: (-(pasan[k] / q - int(pasan[k] // q)), -pasan[k]))
    for k in orden[:max(faltan, 0)]:
        asign[k] += 1
    faltan = bancas - sum(asign.values())
    if faltan > 0 and pasan:
        asign[max(pasan, key=pasan.get)] += faltan
    return {k: v for k, v in asign.items() if v > 0}


def validacion() -> tuple[pd.DataFrame, dict[str, dict[str, int]]]:
    filas = []
    # 2025, Junta Electoral, por lista.
    j = pd.read_csv(PROC / "jep_2025_municipio.csv")
    r = pd.read_csv(PROC / "jep_2025_municipio_resumen.csv", dtype=str)
    j = j.merge(r[["distrito_jep", "seccion_electoral"]].astype({"distrito_jep": int}), on="distrito_jep")
    j = j[j.categoria != "CONCEJALES"]
    for (sec, cat), g in j.groupby(["seccion_electoral", "categoria"]):
        b = (DIP if cat.startswith("DIP") else SEN)[str(sec)]
        v = g.groupby("agrupacion").votos.sum().to_dict()
        for lista, n in reparto(v, b).items():
            filas.append({"anio": 2025, "seccion": str(sec), "camara": cat[:3], "bancas": b, "lista": lista,
                          "votos": v[lista], "pct": 100 * v[lista] / sum(v.values()), "bancas_lista": n})
    # 2023, definitivo de la Provincia, por lista.
    g = pd.read_csv(RAW / "gba" / "generales_provinciales_2005_2023.csv", encoding="latin-1", dtype=str)
    g = g[(g.eleccion == "2023") & g.cargo.str.upper().str.contains("DIPUTADOS PROV|SENADORES PROV")]
    g["votos"] = pd.to_numeric(g.votos, errors="coerce").fillna(0)
    g = g[~g.lista.str.upper().str.contains("BLANCO|NULO|RECURRIDO|IMPUGNADO", na=False)]
    g["sec"] = g.seccion_electoral.map(SECCION_NUM)
    for (sec, cargo), x in g.groupby(["sec", "cargo"]):
        b = (DIP if "DIP" in cargo.upper() else SEN)[sec]
        v = x.groupby("lista").votos.sum().to_dict()
        for lista, n in reparto(v, b).items():
            filas.append({"anio": 2023, "seccion": sec, "camara": cargo.upper()[:3], "bancas": b, "lista": lista,
                          "votos": v[lista], "pct": 100 * v[lista] / sum(v.values()), "bancas_lista": n})
    val = pd.DataFrame(filas)
    # Electos 2025 que siguen hasta 2029, en bloques del motor.
    bloque = {"ALIANZA FUERZA PATRIA": "PERONISMO", "ALIANZA LA LIBERTAD AVANZA": "DERECHA",
              "ALIANZA SOMOS BUENOS AIRES": "TERCERA", "FTE. DE IZQUIERDA Y DE TRABAJADORES - UNIDAD": "IZQUIERDA"}
    v25 = val[val.anio == 2025].assign(bloque=lambda d: d.lista.map(bloque).fillna("OTROS"))
    sigue = {c: v25[v25.camara == c].groupby("bloque").bancas_lista.sum().to_dict() for c in ("DIP", "SEN")}
    return val, sigue


def bancas_2027(sec_votos: np.ndarray, sec_ids: list, nombres: list[str]) -> tuple[np.ndarray, np.ndarray]:
    """Por simulación: bancas de diputados y de senadores 2027 por bloque."""
    elegibles = {n for n in nombres if n != "RESTO"}
    n_sim = sec_votos.shape[0]
    dip, sen = np.zeros((n_sim, len(nombres))), np.zeros((n_sim, len(nombres)))
    for i in range(n_sim):
        for k, s in enumerate(sec_ids):
            s = str(s)
            cam = CAMARA_2027[s]
            b = DIP[s] if cam == "DIP" else SEN[s]
            asign = reparto(dict(zip(nombres, sec_votos[i, k])), b, elegibles)
            dest = dip if cam == "DIP" else sen
            for nmb, nb in asign.items():
                dest[i, nombres.index(nmb)] += nb
    return dip, sen


def main() -> None:
    TABLAS.mkdir(parents=True, exist_ok=True)
    val, sigue = validacion()
    val.round(2).to_csv(TABLAS / "legislatura_validacion.csv", index=False, encoding="utf-8")
    pd.set_option("display.width", 250)
    for anio in (2023, 2025):
        t = val[val.anio == anio].groupby(["camara", "lista"]).bancas_lista.sum().reset_index().sort_values(["camara", "bancas_lista"], ascending=[True, False])
        print(f"\n{anio}: bancas según la regla\n", t.to_string(index=False))
    print("\nsiguen hasta 2029 (electos 2025):", sigue)

    motor = import_module("106_motor_2027")
    mo = motor.Motor()
    S_oct, S_sep = mo.provincia(mo.s_oct) * 100, mo.provincia(mo.s_sep) * 100
    medio = dict(zip(motor.BLOQUES, (S_oct + S_sep) / 2))
    ESC = [("A · Octubre 2025, derecha unida", "octubre", None, None),
           ("B · Septiembre 2025, derecha unida", "septiembre", None, None),
           ("C · Punto medio, derecha unida", "octubre", medio, None),
           ("A · Octubre 2025, derecha dividida (PRO 25 %)", "octubre", None, 0.25),
           ("A · Octubre 2025, derecha dividida (PRO 52 %)", "octubre", None, 0.52)]
    filas = []
    for nombre, base, metas, pi in ESC:
        r = mo.simular(base, metas, n=500, pi_prov=pi, sd_pi_provincial=0.03 if pi else 0.0)
        nombres = r["nombres"]
        dip, sen = bancas_2027(r["sec_votos"], r["sec_ids"], nombres)
        for k, nmb in enumerate(nombres):
            clave = "DERECHA" if nmb in ("LLA", "PRO", "DERECHA") else nmb
            sd = sigue["DIP"].get(clave, 0) if nmb in ("PERONISMO", "DERECHA", "TERCERA", "IZQUIERDA") else 0
            ss = sigue["SEN"].get(clave, 0) if nmb in ("PERONISMO", "DERECHA", "TERCERA", "IZQUIERDA") else 0
            filas.append({"escenario": nombre, "bloque": nmb,
                          "diputados_2027_p50": np.median(dip[:, k]), "diputados_2027_p10": np.percentile(dip[:, k], 10),
                          "diputados_2027_p90": np.percentile(dip[:, k], 90),
                          "senadores_2027_p50": np.median(sen[:, k]), "senadores_2027_p10": np.percentile(sen[:, k], 10),
                          "senadores_2027_p90": np.percentile(sen[:, k], 90),
                          "diputados_siguen_2025": sd, "senadores_siguen_2025": ss})
        per = nombres.index("PERONISMO")
        dip_tot = dip[:, per] + sigue["DIP"].get("PERONISMO", 0)
        sen_tot = sen[:, per] + sigue["SEN"].get("PERONISMO", 0)
        filas.append({"escenario": nombre, "bloque": "PERONISMO · cámara completa",
                      "diputados_2027_p50": np.median(dip_tot), "diputados_2027_p10": np.percentile(dip_tot, 10),
                      "diputados_2027_p90": np.percentile(dip_tot, 90), "senadores_2027_p50": np.median(sen_tot),
                      "senadores_2027_p10": np.percentile(sen_tot, 10), "senadores_2027_p90": np.percentile(sen_tot, 90),
                      "p_mayoria_diputados": float(np.mean(dip_tot >= 47)), "p_mayoria_senado": float(np.mean(sen_tot >= 24))})
        print(f"  {nombre:48s} 2027 dip " + " ".join(f"{n[:4]} {np.median(dip[:, k]):.0f}" for k, n in enumerate(nombres)) +
              " | sen " + " ".join(f"{n[:4]} {np.median(sen[:, k]):.0f}" for k, n in enumerate(nombres)) +
              f" | peronismo cámara: dip {np.median(dip_tot):.0f}/92 (P≥47 {np.mean(dip_tot >= 47):.2f}), "
              f"sen {np.median(sen_tot):.0f}/46 (P≥24 {np.mean(sen_tot >= 24):.2f})")
    pd.DataFrame(filas).round(3).to_csv(TABLAS / "legislatura_2027_escenarios.csv", index=False, encoding="utf-8")


if __name__ == "__main__":
    main()
