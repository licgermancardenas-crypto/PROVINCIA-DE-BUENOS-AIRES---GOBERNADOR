"""
102 · Retención y transferencia 2023 → 2025.

LA PREGUNTA
-----------
¿Adónde fueron los votantes de 2023? Cuántos de Kicillof se quedaron con Fuerza Patria, cuántos
de Santilli (JxC) se fueron a la alianza LLA-PRO o a Provincias Unidas, y cuántos no fueron a
votar.

QUÉ SE COMPARA
--------------
Gobernador 2023 (generales, octubre) contra Diputados Nacionales 2025 (generales, octubre), por
circuito estable (ventana 2023-2025, 1.033 unidades). Es el único par por circuito: la provincial
de septiembre 2025 sólo está por municipio. **Mismo padrón en las dos puntas**: Gobernador 2023
se arma sólo con las mesas de nativos (en 2025 los extranjeros no votan categorías nacionales).
Cada elección en proporción de su propio padrón, con «no votó» como una categoría más.

EL ESTIMADOR
------------
El de CABA (`_inferencia.py`): una sola regresión no negativa con la restricción de filas adentro.
Se estima para la provincia y por zona (Conurbano / interior), porque el `101` mostró que los
niveles difieren por zona.

TRES CONTROLES
--------------
1. Reconstrucción: cuánto del resultado 2025 no logra colocar la matriz (dentro de muestra).
2. **Fuera de muestra**: se estima la matriz con 4/5 de los municipios y se predice el resultado
   2025 de los municipios que quedaron afuera, por circuito y por municipio. Se compara con una
   predicción ingenua (cada circuito se mueve como la provincia). Si la matriz no le gana a la
   ingenua, no dice nada.
3. Cotas de Duncan-Davis para las celdas clave: lo único que se sabe sin supuestos.

Salidas (03_OUTPUTS/tablas/)
- transferencias_2023_2025_matriz.csv : origen × destino, % de la fila y votos, por ámbito; en la
  provincia, intervalo 5-95 por remuestreo de municipios (p05, p95)
- transferencias_2023_2025_cotas.csv  : cotas de Duncan-Davis
- transferencias_2023_2025_control.csv: reconstrucción y fuera de muestra
- transferencias_2023_2025_base.csv   : la base por CE
"""
from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

RAIZ = Path(__file__).resolve().parents[2]
PROC = RAIZ / "01_DATOS" / "processed"
TABLAS = RAIZ / "03_OUTPUTS" / "tablas"
sys.path.insert(0, str(RAIZ / "02_SCRIPTS" / "etl"))
sys.path.insert(0, str(Path(__file__).parent))
from _inferencia import cotas, error_reconstruccion, estimar  # noqa: E402

geo = import_module("02_geo_base")
mapeo_mod = import_module("08_mapeo_espacios")

ORIGEN = {"PERONISMO": "Kicillof (UxP)", "PRO_JXC": "Santilli (JxC)", "LLA": "Píparo (LLA)",
          "IZQUIERDA": "Izquierda", "OTROS": "Otros", "BLANCO_NULO": "Blanco y nulo", "NO_VOTO": "No votó"}
DESTINO = {"PERONISMO": "Fuerza Patria", "LLA_PRO": "LLA-PRO", "TERCERA_VIA": "Provincias Unidas",
           "IZQUIERDA": "Izquierda", "OTROS": "Otros", "BLANCO_NULO": "Blanco y nulo", "NO_VOTO": "No votó"}
BLANCO = {"BLANCO", "NULO", "RECURRIDO", "IMPUGNADO", "COMANDO"}


def agrupar(esp: pd.Series, validos: set[str]) -> pd.Series:
    return esp.where(esp.isin(validos), np.where(esp.isin(BLANCO), "BLANCO_NULO", "OTROS"))


def gobernador_2023_nativos() -> pd.DataFrame:
    d = pd.read_parquet(PROC / "mesas_dine_pba_2023_generales.parquet",
                        columns=["cargo_nombre", "circuito_id", "mesa_id", "mesa_tipo", "mesa_electores",
                                 "agrupacion_nombre", "votos_tipo", "votos_cantidad", "seccion_id"])
    d["cargo"] = d.cargo_nombre.map(mapeo_mod.norm_cargo)
    d = d[d.cargo == "GOBERNADOR"]
    ext = d.mesa_tipo.fillna("").str.upper().str.startswith("EXTRANJ") | (pd.to_numeric(d.mesa_id, errors="coerce") >= 9000)
    d = d[~ext].copy()
    m = pd.read_csv(RAIZ / "config" / "mapeo_espacios.csv")
    m = m[(m.fuente == "dine_mesa") & (m.anio == 2023) & (m.tipo == "GENERALES") & (m.cargo == "GOBERNADOR")]
    d["agrupacion"] = d.agrupacion_nombre.fillna("").str.strip()
    d.loc[d.votos_tipo != "POSITIVO", "agrupacion"] = d.votos_tipo
    d = d.merge(m[["agrupacion", "votos_tipo", "espacio_final"]], on=["agrupacion", "votos_tipo"], how="left")
    assert d.espacio_final.notna().all(), "Gobernador 2023 con listas sin mapeo"
    d["circuito"] = d.circuito_id.map(geo.norm_circuito)
    el = d.drop_duplicates(["seccion_id", "mesa_id"]).groupby("circuito").mesa_electores.sum()
    d["cat"] = agrupar(d.espacio_final, set(ORIGEN) - {"BLANCO_NULO", "NO_VOTO", "OTROS"})
    v = d.pivot_table(index="circuito", columns="cat", values="votos_cantidad", aggfunc="sum", fill_value=0)
    v["NO_VOTO"] = el - v.sum(axis=1)
    v["electores"] = el
    return v


def diputados_2025() -> pd.DataFrame:
    p = pd.read_parquet(PROC / "panel_circuito.parquet",
                        columns=["anio", "tipo", "cargo", "circuito", "espacio", "votos", "electores_nativos",
                                 "electores_extranjeros"])
    p = p[(p.anio == 2025) & (p.tipo == "GENERALES") & (p.cargo == "DIPUTADOS NACIONALES")].copy()
    p["cat"] = agrupar(p.espacio, set(DESTINO) - {"BLANCO_NULO", "NO_VOTO", "OTROS"})
    v = p.pivot_table(index="circuito", columns="cat", values="votos", aggfunc="sum", fill_value=0)
    el = p.drop_duplicates("circuito").set_index("circuito")
    v["electores"] = el.electores_nativos + el.electores_extranjeros
    v["NO_VOTO"] = v.electores - v.drop(columns="electores").sum(axis=1)
    return v


def base() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    eq = pd.read_csv(PROC / "circuitos_equivalencias.csv", dtype=str)
    eq = eq[eq.ventana == "2023_2025"].set_index("circuito")
    claves = pd.read_csv(PROC / "municipios_claves.csv", dtype=str).set_index("cod_indec")
    a = gobernador_2023_nativos().groupby(eq.ce_id).sum()
    b = diputados_2025().groupby(eq.ce_id).sum()
    ce = a.index.intersection(b.index)
    a, b = a.loc[ce], b.loc[ce]
    x = a[[o for o in ORIGEN if o in a.columns and a[o].sum() > 0]].div(a.electores, axis=0)  # Gobernador 2023 no tuvo «otros»
    y = b.reindex(columns=list(DESTINO), fill_value=0).div(b.electores, axis=0)
    info = pd.DataFrame({"electores_2023": a.electores, "electores_2025": b.electores}, index=ce)
    info["cod_indec"] = info.index.str[:5]
    info["zona"] = info.cod_indec.map(claves.conurbano).map({"True": "Conurbano", "False": "Interior"})
    ok = (x.min(axis=1) >= 0) & (y.min(axis=1) >= 0) & (info.electores_2023 >= 50)
    return x[ok], y[ok], info[ok]


def matriz(x, y, w) -> np.ndarray:
    return estimar(x.to_numpy(), y.to_numpy(), w.to_numpy())


def fuera_de_muestra(x, y, info) -> dict:
    w = info.electores_2023
    pred_ei = np.zeros(y.shape)
    pred_ing = np.zeros(y.shape)
    for tr, te in GroupKFold(n_splits=5).split(x, groups=info.cod_indec):
        B = matriz(x.iloc[tr], y.iloc[tr], w.iloc[tr])
        pred_ei[te] = x.iloc[te].to_numpy() @ B
        # Ingenua: el circuito conserva su 2023 y se le suma el movimiento provincial (swing uniforme)
        # en los destinos que existen en las dos (peronismo, izquierda, blanco, no votó); el resto,
        # la proporción provincial de entrenamiento.
        tot_tr = np.average(y.iloc[tr].to_numpy(), axis=0, weights=w.iloc[tr])
        pred_ing[te] = tot_tr
        for j, col in enumerate(y.columns):
            if col in x.columns:
                mov = tot_tr[j] - np.average(x.iloc[tr][col], weights=w.iloc[tr])
                pred_ing[te, j] = np.clip(x.iloc[te][col].to_numpy() + mov, 0, 1)
    real = y.to_numpy()
    out = {}
    for nombre, pred in [("matriz", pred_ei), ("ingenua", pred_ing)]:
        # Error por circuito: puntos porcentuales medios por categoría, ponderado por padrón.
        out[f"error_circuito_pp_{nombre}"] = float(np.average(np.abs(pred - real).mean(axis=1), weights=w) * 100)
        votos_p = pd.DataFrame(pred * w.to_numpy()[:, None], index=x.index).groupby(info.cod_indec).sum()
        votos_r = pd.DataFrame(real * w.to_numpy()[:, None], index=x.index).groupby(info.cod_indec).sum()
        out[f"error_municipio_pct_{nombre}"] = float((votos_p - votos_r).abs().to_numpy().sum() / votos_r.to_numpy().sum() * 100)
        out[f"error_peronismo_municipio_pp_{nombre}"] = float(
            (100 * (votos_p[0] / votos_r.sum(axis=1) - votos_r[0] / votos_r.sum(axis=1))).abs().median())
    return out


def bootstrap(x, y, info, n: int = 200, semilla: int = 0) -> pd.DataFrame:
    """Incertidumbre por remuestreo de municipios (con reemplazo): percentiles 5 y 95 de cada celda."""
    rng = np.random.default_rng(semilla)
    munis = info.cod_indec.unique()
    pos = {m: np.flatnonzero(info.cod_indec.to_numpy() == m) for m in munis}
    reps = []
    for _ in range(n):
        idx = np.concatenate([pos[m] for m in rng.choice(munis, size=len(munis), replace=True)])
        reps.append(matriz(x.iloc[idx], y.iloc[idx], info.electores_2023.iloc[idx]))
    R = np.stack(reps) * 100
    filas = []
    for i, o in enumerate(x.columns):
        for j, dd in enumerate(y.columns):
            filas.append({"origen": ORIGEN[o], "destino": DESTINO[dd],
                          "p05": np.percentile(R[:, i, j], 5), "p95": np.percentile(R[:, i, j], 95)})
    return pd.DataFrame(filas)


def main() -> None:
    TABLAS.mkdir(parents=True, exist_ok=True)
    x, y, info = base()
    pd.concat([x.add_prefix("o23_"), y.add_prefix("d25_"), info], axis=1).round(5).to_csv(
        TABLAS / "transferencias_2023_2025_base.csv", encoding="utf-8")
    print(f"CE: {len(x)}  electores 2023: {info.electores_2023.sum():,.0f}  2025: {info.electores_2025.sum():,.0f}")

    filas, ctl, cot = [], [], []
    for ambito, msk in [("Provincia", info.index == info.index), ("Conurbano", info.zona == "Conurbano"),
                        ("Interior", info.zona == "Interior")]:
        xs, ys, ws = x[msk], y[msk], info.electores_2023[msk]
        B = matriz(xs, ys, ws)
        tot_o = xs.mul(ws, axis=0).sum()
        for i, o in enumerate(x.columns):
            for j, dd in enumerate(y.columns):
                filas.append({"ambito": ambito, "origen": ORIGEN[o], "destino": DESTINO[dd],
                              "pct_fila": 100 * B[i, j], "votos": B[i, j] * tot_o[o]})
        ctl.append({"ambito": ambito, "circuitos": int(msk.sum()),
                    "error_reconstruccion_pct": error_reconstruccion(xs, B, ys, ws)})
        if ambito == "Provincia":
            for o, dd in [("PERONISMO", "PERONISMO"), ("PERONISMO", "NO_VOTO"), ("PRO_JXC", "LLA_PRO"),
                          ("PRO_JXC", "TERCERA_VIA"), ("LLA", "LLA_PRO"), ("NO_VOTO", "NO_VOTO"),
                          ("NO_VOTO", "PERONISMO"), ("NO_VOTO", "LLA_PRO")]:
                lo, hi = cotas(xs, ys, ws, o, dd)
                cot.append({"origen": ORIGEN[o], "destino": DESTINO[dd], "estimado": 100 * B[x.columns.get_loc(o), y.columns.get_loc(dd)],
                            "cota_inf": lo, "cota_sup": hi})
    ctl[0].update(fuera_de_muestra(x, y, info))
    M = pd.DataFrame(filas)
    M = M.merge(bootstrap(x, y, info).assign(ambito="Provincia"), on=["ambito", "origen", "destino"], how="left")
    M.round(2).to_csv(TABLAS / "transferencias_2023_2025_matriz.csv", index=False, encoding="utf-8")
    pd.DataFrame(cot).round(1).to_csv(TABLAS / "transferencias_2023_2025_cotas.csv", index=False, encoding="utf-8")
    pd.DataFrame(ctl).round(3).to_csv(TABLAS / "transferencias_2023_2025_control.csv", index=False, encoding="utf-8")

    pd.set_option("display.width", 250)
    for amb in ["Provincia", "Conurbano", "Interior"]:
        t = M[M.ambito == amb].pivot(index="origen", columns="destino", values="pct_fila")
        t = t.loc[[ORIGEN[o] for o in x.columns], [DESTINO[d] for d in y.columns]]
        print(f"\n{amb} · % de cada origen 2023 que fue a cada destino 2025\n", t.round(1).to_string())
        if amb == "Provincia":
            r = M[M.ambito == amb]
            r = r.assign(ic=r.p05.round(0).astype(int).astype(str) + "-" + r.p95.round(0).astype(int).astype(str))
            print("  intervalo 5-95 (remuestreo de municipios)\n",
                  r.pivot(index="origen", columns="destino", values="ic").loc[t.index, t.columns].to_string())
    print("\nCotas\n", pd.DataFrame(cot).round(1).to_string(index=False))
    print("\nControl\n", pd.DataFrame(ctl).round(2).T.to_string())


if __name__ == "__main__":
    main()
