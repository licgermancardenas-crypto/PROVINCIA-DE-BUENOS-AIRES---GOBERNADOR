"""
100 · El arrastre del intendente y el corte de boleta.

LA PREGUNTA
-----------
¿Cuánto mueve un intendente el voto a Gobernador? En PBA Intendente y Gobernador se votan el
mismo día (2007, 2011, 2015, 2019, 2023) con **boleta partidaria de papel**: para votar distinto
hay que cortar la boleta con la mano. La diferencia entre las dos categorías es entonces una
decisión con costo, y lo que se mide es un piso.

TRES MEDIDAS
------------
A. **La brecha** (municipio, definitivo de la Provincia, 2007-2023): cuánto saca cada espacio
   para Intendente menos lo que saca para Gobernador, en % de los votos positivos.
B. **El corte de boleta** (circuito, provisorio por mesa, 2011-2023): la divergencia entre las
   dos estructuras de voto del mismo día, 0,5 · Σ |%int − %gob|. Se publica en bruto y **pareado**:
   sólo los espacios que compiten en las dos categorías de ese municipio, renormalizados. La
   diferencia es oferta desigual (sobre todo vecinalismos sin candidato a gobernador), no corte.
C. **El efecto de tener la intendencia** (regresión discontinua): se comparan municipios donde un
   espacio ganó la intendencia por poco con aquellos donde la perdió por poco, y se mira su voto a
   Gobernador en la elección siguiente, como desvío respecto de su resultado provincial. Cerca del
   umbral, ganar o perder es casi azar, así que la diferencia es el efecto de gobernar el
   municipio. Prueba de validez: el mismo ejercicio sobre el voto a Gobernador de la elección
   anterior (placebo) no tiene que mostrar salto.

LO QUE NO PUEDE DECIR
---------------------
- A y B son agregados: cortes en direcciones opuestas se cancelan. Todo es un piso.
- C mide el efecto de que **el espacio** gobierne el municipio, no el de un intendente con nombre
  propio (no hay base de quién fue candidato a reelección). Y es local: vale para municipios
  competitivos, no para los feudos de 70 %.

Salidas (03_OUTPUTS/tablas/)
- arrastre_brecha_municipio.csv : municipio × año × espacio, % int, % gob, brecha
- arrastre_brecha_resumen.csv   : brecha del espacio ganador y del resto, por año y zona
- arrastre_brecha_espacio.csv   : brecha media de cada espacio, por año y zona
- corte_boleta_circuito.csv     : índice bruto y pareado por circuito y año
- corte_boleta_resumen.csv      : medianas por año y zona
- arrastre_rd.csv               : efecto de ganar la intendencia, por ancho de banda, con placebo
- arrastre_rd_datos.csv         : la base de la regresión discontinua
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

RAIZ = Path(__file__).resolve().parents[2]
PROC = RAIZ / "01_DATOS" / "processed"
TABLAS = RAIZ / "03_OUTPUTS" / "tablas"
ANIOS = [2007, 2011, 2015, 2019, 2023]
NO_ESPACIO = {"BLANCO", "NULO", "RECURRIDO", "IMPUGNADO", "COMANDO", "SIN_REGLA"}
ESPACIOS_RD = ["PERONISMO", "PRO_JXC"]
BANDAS = [5, 7.5, 10, 15, 20]


def porcentajes(df: pd.DataFrame, claves: list[str]) -> pd.DataFrame:
    """% de cada espacio sobre los positivos de su categoría."""
    d = df[~df.espacio.isin(NO_ESPACIO)].groupby(claves + ["cargo", "espacio"]).votos.sum().reset_index()
    d = d[d.votos > 0]  # el definitivo lista ofertas con 0 votos: no compiten
    d["pct"] = 100 * d.votos / d.groupby(claves + ["cargo"]).votos.transform("sum")
    return d


def brecha_municipal(pm: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    d = pm[(pm.fuente == "gba_definitivo") & (pm.tipo == "GENERALES") & pm.cargo.isin(["INTENDENTE", "GOBERNADOR"])]
    zona = d.drop_duplicates("cod_indec").set_index("cod_indec").conurbano
    p = porcentajes(d, ["anio", "cod_indec"])
    w = p.pivot_table(index=["anio", "cod_indec", "espacio"], columns="cargo", values="pct").reset_index()
    w = w.rename(columns={"INTENDENTE": "pct_int", "GOBERNADOR": "pct_gob"})
    w["compite_en"] = np.select([w.pct_int.notna() & w.pct_gob.notna(), w.pct_int.notna()],
                                ["ambas", "solo_intendente"], "solo_gobernador")
    w["brecha"] = w.pct_int.fillna(0) - w.pct_gob.fillna(0)
    ganador = w.loc[w.groupby(["anio", "cod_indec"]).pct_int.idxmax(), ["anio", "cod_indec", "espacio"]]
    w = w.merge(ganador.rename(columns={"espacio": "gana_intendencia"}), on=["anio", "cod_indec"])
    w["es_ganador"] = w.espacio == w.gana_intendencia
    gob_gana = w.loc[w.groupby(["anio", "cod_indec"]).pct_gob.idxmax(), ["anio", "cod_indec", "espacio"]]
    w = w.merge(gob_gana.rename(columns={"espacio": "gana_gobernador"}), on=["anio", "cod_indec"])
    w["zona"] = w.cod_indec.map(zona).map({True: "Conurbano", False: "Interior"})

    g = w[w.es_ganador]
    filas = []
    for (anio, zona_), x in list(g.groupby(["anio", "zona"])) + [((a, "Provincia"), x) for a, x in g.groupby("anio")]:
        amb = x[x.compite_en == "ambas"]
        filas.append({
            "anio": anio, "zona": zona_, "municipios": len(x),
            "ganador_vecinal_sin_gobernador": int((x.compite_en == "solo_intendente").sum()),
            "brecha_mediana_ganador": round(amb.brecha.median(), 1),
            "brecha_media_ganador": round(amb.brecha.mean(), 1),
            "pct_ganador_saca_mas_que_su_gobernador": round(100 * (amb.brecha > 0).mean(), 1),
            "corte_que_cambia_ganador": int((x.gana_intendencia != x.gana_gobernador).sum()),
        })
    res = pd.DataFrame(filas).sort_values(["anio", "zona"])
    return w, res


def corte_circuito(pc: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    d = pc[(pc.tipo == "GENERALES") & pc.cargo.isin(["INTENDENTE", "GOBERNADOR"])]
    p = porcentajes(d, ["anio", "cod_indec", "circuito"])
    w = p.pivot_table(index=["anio", "cod_indec", "circuito", "espacio"], columns="cargo", values="pct", fill_value=0).reset_index()
    bruto = w.groupby(["anio", "cod_indec", "circuito"]).apply(
        lambda x: 0.5 * (x.INTENDENTE - x.GOBERNADOR).abs().sum(), include_groups=False).rename("corte_bruto")
    # Pareado: sólo espacios con lista en las dos categorías en el municipio, renormalizados.
    ofertas = p.groupby(["anio", "cod_indec", "espacio"]).cargo.nunique()
    ambos = ofertas[ofertas == 2].reset_index()[["anio", "cod_indec", "espacio"]]
    wp = w.merge(ambos, on=["anio", "cod_indec", "espacio"])
    for c in ("INTENDENTE", "GOBERNADOR"):
        wp[c] = 100 * wp[c] / wp.groupby(["anio", "cod_indec", "circuito"])[c].transform("sum")
    par = wp.groupby(["anio", "cod_indec", "circuito"]).apply(
        lambda x: 0.5 * (x.INTENDENTE - x.GOBERNADOR).abs().sum(), include_groups=False).rename("corte_pareado")
    el = d.groupby(["anio", "cod_indec", "circuito"]).agg(electores=("electores_nativos", "max"),
                                                           conurbano=("conurbano", "first"))
    c = pd.concat([bruto, par], axis=1).join(el).reset_index()
    c["zona"] = c.conurbano.map({True: "Conurbano", False: "Interior"})
    res = []
    for (anio, z), x in list(c.groupby(["anio", "zona"])) + [((a, "Provincia"), x) for a, x in c.groupby("anio")]:
        pes = x.electores / x.electores.sum()
        res.append({"anio": anio, "zona": z, "circuitos": len(x),
                    "corte_bruto_mediana": round(x.corte_bruto.median(), 2),
                    "corte_pareado_mediana": round(x.corte_pareado.median(), 2),
                    "corte_pareado_ponderado": round((x.corte_pareado * pes).sum(), 2),
                    "corte_pareado_p90": round(x.corte_pareado.quantile(0.9), 2)})
    return c, pd.DataFrame(res).sort_values(["anio", "zona"])


def base_rd(w: pd.DataFrame) -> pd.DataFrame:
    """Una fila por municipio × espacio × transición (t-4 -> t)."""
    prov = w.groupby(["anio", "espacio"]).apply(lambda x: x.pct_gob.median(), include_groups=False)
    filas = []
    for t0, t1 in zip(ANIOS, ANIOS[1:]):
        a = w[w.anio == t0].set_index(["cod_indec", "espacio"])
        b = w[w.anio == t1].set_index(["cod_indec", "espacio"])
        for esp in ESPACIOS_RD:
            if (t1, esp) not in prov.index or (t0, esp) not in prov.index:
                continue
            for cod in a.index.get_level_values(0).unique():
                if (cod, esp) not in a.index or (cod, esp) not in b.index:
                    continue
                x0, x1 = a.loc[(cod, esp)], b.loc[(cod, esp)]
                if pd.isna(x0.pct_int) or pd.isna(x1.pct_gob) or pd.isna(x0.pct_gob):
                    continue
                rivales = a.loc[cod].drop(index=esp).pct_int.dropna()
                if rivales.empty:
                    continue
                filas.append({
                    "transicion": f"{t0}-{t1}", "espacio": esp, "cod_indec": cod, "zona": x0.zona,
                    "margen_int_t0": x0.pct_int - rivales.max(),
                    "gob_t1_desvio": x1.pct_gob - prov[(t1, esp)],
                    "gob_t0_desvio": x0.pct_gob - prov[(t0, esp)],
                    "int_t1": x1.pct_int if pd.notna(x1.pct_int) else np.nan,
                })
    d = pd.DataFrame(filas)
    d["gana"] = (d.margen_int_t0 > 0).astype(int)
    d["cambio_gob"] = d.gob_t1_desvio - d.gob_t0_desvio
    return d


def rd(d: pd.DataFrame, y: str, h: float) -> dict:
    x = d[d.margen_int_t0.abs() <= h].dropna(subset=[y])
    if x.gana.nunique() < 2 or len(x) < 15:
        return {"n": len(x)}
    m = x.margen_int_t0
    peso = 1 - m.abs() / h
    X = pd.DataFrame({"gana": x.gana, "m": m, "m_gana": m * x.gana})
    # Efectos fijos de espacio × transición: cada uno con su propio nivel.
    fe = pd.get_dummies(x.espacio + "_" + x.transicion, drop_first=True, dtype=float)
    X = sm.add_constant(pd.concat([X, fe], axis=1))
    r = sm.WLS(x[y], X, weights=peso).fit(cov_type="cluster", cov_kwds={"groups": x.cod_indec.astype("category").cat.codes})
    return {"n": len(x), "n_gana": int(x.gana.sum()), "efecto": r.params["gana"], "ee": r.bse["gana"],
            "p": r.pvalues["gana"], "ic_inf": r.params["gana"] - 1.96 * r.bse["gana"],
            "ic_sup": r.params["gana"] + 1.96 * r.bse["gana"]}


def main() -> None:
    TABLAS.mkdir(parents=True, exist_ok=True)
    pm = pd.read_parquet(PROC / "panel_municipio.parquet")
    pc = pd.read_parquet(PROC / "panel_circuito.parquet")

    w, res = brecha_municipal(pm)
    w.round(3).to_csv(TABLAS / "arrastre_brecha_municipio.csv", index=False, encoding="utf-8")
    res.to_csv(TABLAS / "arrastre_brecha_resumen.csv", index=False, encoding="utf-8")
    print("A · brecha del espacio que gana la intendencia (pp, int - gob)\n", res.to_string(index=False))

    c, cres = corte_circuito(pc)
    c.round(3).to_csv(TABLAS / "corte_boleta_circuito.csv", index=False, encoding="utf-8")
    cres.to_csv(TABLAS / "corte_boleta_resumen.csv", index=False, encoding="utf-8")
    print("\nB · corte de boleta por circuito\n", cres.to_string(index=False))

    d = base_rd(w)
    d.round(3).to_csv(TABLAS / "arrastre_rd_datos.csv", index=False, encoding="utf-8")
    filas = []
    for esp in ["TODOS"] + ESPACIOS_RD:
        dd = d if esp == "TODOS" else d[d.espacio == esp]
        for y, rotulo in [("gob_t1_desvio", "Gobernador t (efecto)"), ("gob_t0_desvio", "Gobernador t-4 (placebo)"),
                          ("cambio_gob", "Cambio t-4 -> t"), ("int_t1", "Intendente t (referencia)")]:
            for h in BANDAS:
                filas.append({"espacio": esp, "resultado": rotulo, "banda_pp": h, **rd(dd, y, h)})
    r = pd.DataFrame(filas)
    # Benjamini-Hochberg sobre toda la batería (todas las filas con p).
    from statsmodels.stats.multitest import multipletests
    ok = r.p.notna()
    r.loc[ok, "q_bh"] = multipletests(r.loc[ok, "p"], method="fdr_bh")[1]
    # Brecha por espacio, sólo donde compite en las dos categorías.
    pe = (w[w.compite_en == "ambas"].groupby(["anio", "zona", "espacio"])
          .agg(municipios=("brecha", "size"), brecha_media=("brecha", "mean")).round(2).reset_index())
    pe.to_csv(TABLAS / "arrastre_brecha_espacio.csv", index=False, encoding="utf-8")
    r.round(4).to_csv(TABLAS / "arrastre_rd.csv", index=False, encoding="utf-8")
    print("\nC · efecto de ganar la intendencia sobre el voto a Gobernador siguiente (pp)")
    print(r[r.banda_pp.isin([7.5, 10, 15])].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
