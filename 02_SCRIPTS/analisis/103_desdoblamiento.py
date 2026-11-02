"""
103 · El desdoblamiento: septiembre contra octubre de 2025.

LA PREGUNTA
-----------
El 7 de septiembre (provincial: legisladores y concejales) Fuerza Patria le ganó a LLA-PRO por
unos 13 puntos. El 26 de octubre (nacional: diputados) quedaron casi empatados. Mismo año, mismo
territorio, siete semanas. ¿Qué cambió: quién fue a votar, quién cambió de voto, o el padrón?

POR QUÉ SÓLO POR MUNICIPIO
--------------------------
Septiembre no está por mesa (el portal de la Provincia se dio de baja); se tiene el definitivo de
la Junta Electoral por municipio. Octubre se agrega por municipio desde las mesas. 135 unidades.

DOS PADRONES
------------
En septiembre votan los extranjeros (categorías provinciales) y en octubre no. Se estima la parte
extranjera de septiembre por municipio:
- electores extranjeros = padrón de septiembre − padrón de octubre (misma fecha de corte);
- votantes y reparto = los de las mesas de extranjeros de Gobernador 2023 en ese municipio.
Con eso se arma un septiembre «sólo nativos» comparable con octubre. Se publica también el bruto.

TRES PARTES
-----------
a. Resultados: % de los positivos, votos y participación, bruto y sólo nativos.
b. Matriz septiembre -> octubre (sólo nativos) con el estimador común, sus controles fuera de
   muestra y remuestreo de municipios. Con 135 unidades es más ruidosa que la del `102`.
c. Dónde ganó LLA-PRO: el cambio en su voto (en % del padrón) contra el cambio de participación,
   la zona, el intendente peronista y la composición. Spearman parcial descontando composición,
   Benjamini-Hochberg y fragilidad (regla de la casa).

Salidas (03_OUTPUTS/tablas/)
- desdoblamiento_municipio.csv   : municipio × elección × espacio, bruto y sólo nativos
- desdoblamiento_resumen.csv     : provincia y zonas
- desdoblamiento_matriz.csv      : matriz septiembre -> octubre, con intervalo 5-95
- desdoblamiento_control.csv     : reconstrucción y fuera de muestra
- desdoblamiento_correlatos.csv  : batería de la parte c
"""
from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.model_selection import GroupKFold, KFold
from statsmodels.stats.multitest import multipletests

RAIZ = Path(__file__).resolve().parents[2]
PROC = RAIZ / "01_DATOS" / "processed"
TABLAS = RAIZ / "03_OUTPUTS" / "tablas"
sys.path.insert(0, str(RAIZ / "02_SCRIPTS" / "etl"))
sys.path.insert(0, str(Path(__file__).parent))
from _inferencia import cotas, error_reconstruccion, estimar  # noqa: E402

censo_mod = import_module("06_censo2022_circuitos")
mapeo_mod = import_module("08_mapeo_espacios")
geo = import_module("02_geo_base")

CATS = {"PERONISMO": "Fuerza Patria", "LLA_PRO": "LLA-PRO", "TERCERA_VIA": "Provincias Unidas",
        "IZQUIERDA": "Izquierda", "OTROS": "Otros", "BLANCO_NULO": "Blanco y nulo", "NO_VOTO": "No votó"}
BLANCO = {"BLANCO", "NULO", "RECURRIDO", "IMPUGNADO", "COMANDO"}
VOTOS = ["PERONISMO", "LLA_PRO", "TERCERA_VIA", "IZQUIERDA", "OTROS", "BLANCO_NULO"]
# Equivalencia del voto extranjero 2023 (Gobernador) con los espacios 2025.
EXT_2023_A_2025 = {"PERONISMO": "PERONISMO", "PRO_JXC": "LLA_PRO", "LLA": "LLA_PRO", "IZQUIERDA": "IZQUIERDA"}


def cat(esp: pd.Series) -> pd.Series:
    validos = {"PERONISMO", "LLA_PRO", "TERCERA_VIA", "IZQUIERDA"}
    return esp.where(esp.isin(validos), np.where(esp.isin(BLANCO), "BLANCO_NULO", "OTROS"))


def votos_municipio(p: pd.DataFrame) -> pd.DataFrame:
    p = p.assign(cat=cat(p.espacio))
    v = p.pivot_table(index="cod_indec", columns="cat", values="votos", aggfunc="sum", fill_value=0)
    v = v.reindex(columns=VOTOS, fill_value=0)
    pad = p.drop_duplicates("cod_indec").set_index("cod_indec")
    v["electores"] = pad.electores
    v["votantes"] = v[VOTOS].sum(axis=1)
    return v


def extranjeros_2023() -> pd.DataFrame:
    """Por municipio: participación y reparto del voto en las mesas de extranjeros, Gobernador 2023."""
    d = pd.read_parquet(PROC / "mesas_dine_pba_2023_generales.parquet",
                        columns=["cargo_nombre", "seccion_id", "mesa_id", "mesa_tipo", "mesa_electores",
                                 "agrupacion_nombre", "votos_tipo", "votos_cantidad"])
    d = d[d.cargo_nombre.map(mapeo_mod.norm_cargo) == "GOBERNADOR"]
    ext = d.mesa_tipo.fillna("").str.upper().str.startswith("EXTRANJ") | (pd.to_numeric(d.mesa_id, errors="coerce") >= 9000)
    d = d[ext].copy()
    m = pd.read_csv(RAIZ / "config" / "mapeo_espacios.csv")
    m = m[(m.fuente == "dine_mesa") & (m.anio == 2023) & (m.tipo == "GENERALES") & (m.cargo == "GOBERNADOR")]
    d["agrupacion"] = d.agrupacion_nombre.fillna("").str.strip()
    d.loc[d.votos_tipo != "POSITIVO", "agrupacion"] = d.votos_tipo
    d = d.merge(m[["agrupacion", "votos_tipo", "espacio_final"]], on=["agrupacion", "votos_tipo"], how="left")
    d["cat"] = d.espacio_final.map(EXT_2023_A_2025).fillna(
        pd.Series(np.where(d.espacio_final.isin(BLANCO), "BLANCO_NULO", "OTROS"), index=d.index))
    claves = pd.read_csv(PROC / "municipios_claves.csv", dtype=str)
    d["cod_indec"] = d.seccion_id.astype(int).astype(str).str.zfill(3).map(
        claves.set_index(claves.seccion_id_dine.astype(int).astype(str).str.zfill(3)).cod_indec)
    el = d.drop_duplicates(["seccion_id", "mesa_id"]).groupby("cod_indec").mesa_electores.sum()
    v = d.pivot_table(index="cod_indec", columns="cat", values="votos_cantidad", aggfunc="sum", fill_value=0)
    v = v.reindex(columns=VOTOS, fill_value=0)
    out = v.div(v.sum(axis=1), axis=0).add_prefix("rep_")
    out["participacion_ext"] = v.sum(axis=1) / el
    return out


def septiembre_nativos(sep: pd.DataFrame, octu: pd.DataFrame, ext: pd.DataFrame) -> pd.DataFrame:
    s = sep.copy()
    e_el = (sep.electores - octu.electores).clip(lower=0)
    prov = ext.mean()  # municipio sin mesas de extranjeros en 2023: promedio provincial
    e = ext.reindex(s.index).fillna(prov)
    e_vot = e_el * e.participacion_ext
    for c in VOTOS:
        s[c] = (s[c] - e_vot * e[f"rep_{c}"]).clip(lower=0)
    s["electores"] = sep.electores - e_el
    s["votantes"] = s[VOTOS].sum(axis=1)
    s["extranjeros_electores_est"] = e_el
    s["extranjeros_votantes_est"] = e_vot
    return s


def resumen(tablas: dict[str, pd.DataFrame], zona: pd.Series) -> pd.DataFrame:
    filas = []
    for nombre, t in tablas.items():
        for z, idx in [("Provincia", t.index), ("Conurbano", t.index[zona.reindex(t.index)]),
                       ("Interior", t.index[~zona.reindex(t.index)])]:
            x = t.loc[idx]
            pos = x[[c for c in VOTOS if c != "BLANCO_NULO"]].sum().sum()
            fila = {"eleccion": nombre, "ambito": z, "electores": x.electores.sum(), "votantes": x.votantes.sum(),
                    "participacion": 100 * x.votantes.sum() / x.electores.sum()}
            for c in VOTOS:
                fila[f"votos_{c}"] = x[c].sum()
                if c != "BLANCO_NULO":
                    fila[f"pct_{c}"] = 100 * x[c].sum() / pos
            filas.append(fila)
    return pd.DataFrame(filas)


def proporciones(t: pd.DataFrame) -> pd.DataFrame:
    p = t[VOTOS].div(t.electores, axis=0)
    p["NO_VOTO"] = 1 - p.sum(axis=1)
    return p


def matriz(x, y, info):
    B = estimar(x.to_numpy(), y.to_numpy(), info.electores.to_numpy())
    filas = [{"origen": CATS[o], "destino": CATS[d], "pct_fila": 100 * B[i, j],
              "votos": B[i, j] * (x[o] * info.electores).sum()}
             for i, o in enumerate(x.columns) for j, d in enumerate(y.columns)]
    return B, pd.DataFrame(filas)


def controles(x, y, info, n_boot=300) -> tuple[pd.DataFrame, dict]:
    w = info.electores
    rng = np.random.default_rng(0)
    reps = []
    for _ in range(n_boot):
        idx = rng.choice(len(x), size=len(x), replace=True)
        reps.append(estimar(x.iloc[idx].to_numpy(), y.iloc[idx].to_numpy(), w.iloc[idx].to_numpy()))
    R = np.stack(reps) * 100
    ic = pd.DataFrame([{"origen": CATS[o], "destino": CATS[d], "p05": np.percentile(R[:, i, j], 5),
                        "p95": np.percentile(R[:, i, j], 95)}
                       for i, o in enumerate(x.columns) for j, d in enumerate(y.columns)])
    pred_m, pred_i = np.zeros(y.shape), np.zeros(y.shape)
    for tr, te in KFold(n_splits=5, shuffle=True, random_state=0).split(x):
        B = estimar(x.iloc[tr].to_numpy(), y.iloc[tr].to_numpy(), w.iloc[tr].to_numpy())
        pred_m[te] = x.iloc[te].to_numpy() @ B
        mov = np.average(y.iloc[tr], axis=0, weights=w.iloc[tr]) - np.average(x.iloc[tr], axis=0, weights=w.iloc[tr])
        pred_i[te] = np.clip(x.iloc[te].to_numpy() + mov, 0, 1)
    real = y.to_numpy()
    ctl = {"error_reconstruccion_pct": error_reconstruccion(x, estimar(x.to_numpy(), real, w.to_numpy()), y, w)}
    for nom, pr in [("matriz", pred_m), ("ingenua", pred_i)]:
        ctl[f"fuera_muestra_pp_{nom}"] = float(np.average(np.abs(pr - real).mean(axis=1), weights=w) * 100)
        ctl[f"fuera_muestra_votos_mal_ubicados_pct_{nom}"] = float(
            (np.abs(pr - real) * w.to_numpy()[:, None]).sum() / (real * w.to_numpy()[:, None]).sum() * 100)
    return ic, ctl


def perfil_municipio() -> pd.DataFrame:
    c = pd.read_csv(PROC / "censo2022_circuito.csv", dtype={"circuito": str, "cod_indec": str})
    conteos = [k for k in c.columns if not k.startswith(("pct_", "tasa_")) and k not in
               ("circuito", "cod_indec", "electores_nativos_2025", "razon_padron_2025", "calidad_cruce")]
    m = censo_mod.indicadores(c.groupby("cod_indec")[conteos].sum().reset_index()).set_index("cod_indec")
    return m


def spearman_parcial(a, b, Z) -> tuple[float, float]:
    """Spearman parcial: correlación de los residuos de los rangos."""
    ra, rb = stats.rankdata(a), stats.rankdata(b)
    RZ = np.column_stack([np.ones(len(a))] + [stats.rankdata(z) for z in Z.T])
    ea = ra - RZ @ np.linalg.lstsq(RZ, ra, rcond=None)[0]
    eb = rb - RZ @ np.linalg.lstsq(RZ, rb, rcond=None)[0]
    r = np.corrcoef(ea, eb)[0, 1]
    n, k = len(a), Z.shape[1]
    t = r * np.sqrt((n - 2 - k) / (1 - r ** 2))
    return r, 2 * stats.t.sf(abs(t), n - 2 - k)


def correlatos(d: pd.DataFrame) -> pd.DataFrame:
    control = ["pct_univ_completo", "pct_hog_nbi", "pct_65_mas", "log_pob_electores"]
    bateria = {"cambio_participacion": "Cambio de participación (pp)",
               "conurbano": "Conurbano",
               "intendente_peronista": "Intendente peronista (2023)",
               "vecinal_septiembre": "Voto vecinal en concejales de septiembre (%)",
               "pct_univ_completo": "Universitarios (%)", "pct_hog_nbi": "Hogares con NBI (%)",
               "pct_65_mas": "Mayores de 65 (%)", "pct_nac_otro_pais": "Nacidos en otro país (%)",
               "pct_extranjeros_padron": "Extranjeros en el padrón de septiembre (%)"}
    filas = []
    for y, ry in [("cambio_lla_pro", "LLA-PRO"), ("cambio_peronismo", "Fuerza Patria")]:
        for v, rot in bateria.items():
            Z = [c for c in control if c != v]
            x = d.dropna(subset=[y, v] + Z)
            r_simple = stats.spearmanr(x[v], x[y])[0]
            r, p = spearman_parcial(x[v].to_numpy(float), x[y].to_numpy(float), x[Z].to_numpy(float))
            # Fragilidad: sacar el municipio más influyente y los tres más influyentes.
            infl = {}
            for m in x.index:
                rr, _ = spearman_parcial(x.drop(m)[v].to_numpy(float), x.drop(m)[y].to_numpy(float), x.drop(m)[Z].to_numpy(float))
                infl[m] = abs(rr - r)
            top = pd.Series(infl).nlargest(3).index
            r1, _ = spearman_parcial(*(x.drop(top[:1])[c].to_numpy(float) for c in (v, y)), x.drop(top[:1])[Z].to_numpy(float))
            r3, _ = spearman_parcial(*(x.drop(top)[c].to_numpy(float) for c in (v, y)), x.drop(top)[Z].to_numpy(float))
            filas.append({"resultado": f"Cambio {ry} sep -> oct (pp del padrón)", "variable": rot, "n": len(x),
                          "spearman": r_simple, "spearman_parcial": r, "p": p, "sin_1": r1, "sin_3": r3})
    t = pd.DataFrame(filas)
    t["q_bh"] = multipletests(t.p, method="fdr_bh")[1]
    t["pasa"] = (t.q_bh < 0.05) & (np.sign(t.sin_1) == np.sign(t.spearman_parcial)) & \
                (np.sign(t.sin_3) == np.sign(t.spearman_parcial)) & (t.sin_3.abs() >= 0.1)
    return t


def main() -> None:
    TABLAS.mkdir(parents=True, exist_ok=True)
    pm = pd.read_parquet(PROC / "panel_municipio.parquet")
    claves = pd.read_csv(PROC / "municipios_claves.csv", dtype=str).set_index("cod_indec")
    zona = claves.conurbano.map({"True": True, "False": False})

    jep = pm[(pm.fuente == "jep_definitivo") & (pm.cargo != "CONCEJALES")]
    sep = votos_municipio(jep)
    octu = votos_municipio(pm[(pm.fuente == "dine_mesa") & (pm.anio == 2025) & (pm.cargo == "DIPUTADOS NACIONALES")])
    octu["electores"] = pm[(pm.fuente == "dine_mesa") & (pm.anio == 2025)].drop_duplicates("cod_indec").set_index("cod_indec").electores_nativos
    sep, octu = sep.loc[octu.index.intersection(sep.index)], octu.loc[octu.index.intersection(sep.index)]
    ext = extranjeros_2023()
    sepn = septiembre_nativos(sep, octu, ext)

    tablas = {"Septiembre (bruto)": sep, "Septiembre (sólo nativos)": sepn, "Octubre": octu}
    res = resumen(tablas, zona)
    res.round(2).to_csv(TABLAS / "desdoblamiento_resumen.csv", index=False, encoding="utf-8")
    largo = pd.concat([t[VOTOS + ["electores", "votantes"]].assign(eleccion=n) for n, t in tablas.items()])
    largo.reset_index().round(1).to_csv(TABLAS / "desdoblamiento_municipio.csv", index=False, encoding="utf-8")
    pd.set_option("display.width", 250)
    cols = ["eleccion", "ambito", "electores", "votantes", "participacion", "pct_PERONISMO", "pct_LLA_PRO",
            "pct_TERCERA_VIA", "pct_IZQUIERDA", "pct_OTROS", "votos_PERONISMO", "votos_LLA_PRO"]
    print(res[cols].round(1).to_string(index=False))
    print(f"\nextranjeros estimados en septiembre: {sepn.extranjeros_electores_est.sum():,.0f} electores, "
          f"{sepn.extranjeros_votantes_est.sum():,.0f} votantes")

    # b. Matriz septiembre (nativos) -> octubre.
    x, y = proporciones(sepn), proporciones(octu)
    info = pd.DataFrame({"electores": sepn.electores})
    ok = (x.min(axis=1) >= 0) & (y.min(axis=1) >= 0)
    x, y, info = x[ok], y[ok], info[ok]
    B, M = matriz(x, y, info)
    ic, ctl = controles(x, y, info)
    M = M.merge(ic, on=["origen", "destino"])
    M.round(2).to_csv(TABLAS / "desdoblamiento_matriz.csv", index=False, encoding="utf-8")
    cot = []
    for o, d_ in [("PERONISMO", "PERONISMO"), ("LLA_PRO", "LLA_PRO"), ("NO_VOTO", "LLA_PRO"),
                  ("NO_VOTO", "PERONISMO"), ("NO_VOTO", "NO_VOTO"), ("TERCERA_VIA", "LLA_PRO")]:
        lo, hi = cotas(x, y, info.electores, o, d_)
        cot.append({"origen": CATS[o], "destino": CATS[d_], "cota_inf": lo, "cota_sup": hi})
    ctl["municipios"] = int(ok.sum())
    pd.DataFrame([ctl]).round(3).to_csv(TABLAS / "desdoblamiento_control.csv", index=False, encoding="utf-8")
    t = M.pivot(index="origen", columns="destino", values="pct_fila").loc[[CATS[c] for c in x.columns], [CATS[c] for c in y.columns]]
    print("\nMatriz septiembre (nativos) -> octubre, % de cada origen\n", t.round(1).to_string())
    M["ic"] = M.p05.round(0).astype(int).astype(str) + "-" + M.p95.round(0).astype(int).astype(str)
    print(M.pivot(index="origen", columns="destino", values="ic").loc[t.index, t.columns].to_string())
    print("\ncotas\n", pd.DataFrame(cot).round(1).to_string(index=False))
    print("\ncontrol\n", pd.Series(ctl).round(3).to_string())

    # c. Dónde ganó LLA-PRO.
    perfil = perfil_municipio()
    d = pd.DataFrame(index=x.index)
    d["cambio_lla_pro"] = 100 * (y.LLA_PRO - x.LLA_PRO)
    d["cambio_peronismo"] = 100 * (y.PERONISMO - x.PERONISMO)
    d["cambio_participacion"] = 100 * ((1 - y.NO_VOTO) - (1 - x.NO_VOTO))
    d["conurbano"] = zona.reindex(d.index).astype(float)
    it = pm[(pm.fuente == "gba_definitivo") & (pm.anio == 2023) & (pm.cargo == "INTENDENTE") & ~pm.espacio.isin(BLANCO)]
    gan = it.loc[it.groupby("cod_indec").votos.idxmax()].set_index("cod_indec").espacio
    d["intendente_peronista"] = (gan.reindex(d.index) == "PERONISMO").astype(float)
    con = pm[(pm.fuente == "jep_definitivo") & (pm.cargo == "CONCEJALES") & ~pm.espacio.isin(BLANCO)]
    d["vecinal_septiembre"] = 100 * con[con.espacio == "VECINAL"].groupby("cod_indec").votos.sum().reindex(d.index).fillna(0) \
        / con.groupby("cod_indec").votos.sum().reindex(d.index)
    d["pct_extranjeros_padron"] = 100 * sepn.extranjeros_electores_est / sep.electores
    d = d.join(perfil[["pct_univ_completo", "pct_hog_nbi", "pct_65_mas", "pct_nac_otro_pais", "pob"]])
    d["log_pob_electores"] = np.log(d.pob / octu.electores.reindex(d.index))
    c = correlatos(d)
    c.round(3).to_csv(TABLAS / "desdoblamiento_correlatos.csv", index=False, encoding="utf-8")
    print("\ncorrelatos del cambio\n", c.drop(columns="resultado").round(2).to_string(index=False))
    print("\ncambio medio ponderado (pp del padrón): LLA-PRO",
          round(np.average(d.cambio_lla_pro, weights=info.electores), 2), " FP",
          round(np.average(d.cambio_peronismo, weights=info.electores), 2), " participación",
          round(np.average(d.cambio_participacion, weights=info.electores), 2))


if __name__ == "__main__":
    main()
