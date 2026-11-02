"""
10 · Circuitos estables en el tiempo (tabla de equivalencias 2011-2025).

Los circuitos electorales cambian entre elecciones: se subdividen (0022 -> 0022A/B/C), los rurales
chicos se absorben en un vecino y a veces se pasan barrios enteros de un código a otro (Almirante
Brown 2025). La capa de polígonos es una sola partición de una fecha intermedia y no guarda esa
historia, así que las equivalencias se deducen del padrón.

Regla. Entre dos elecciones consecutivas, dentro de cada municipio, se calcula para cada circuito
el exceso de electores respecto de lo esperado si creciera como su municipio. Un circuito que
desaparece pierde todo; uno que aparece gana todo. Cada circuito con pérdida significativa se une
con los circuitos con ganancia significativa que son sus vecinos en el mapa o de su misma familia
de código (mismo número, distinta letra). Si no tiene ninguno, se une con el vecino que más ganó.
Las uniones se acumulan sobre todas las transiciones de la ventana (union-find) y cada grupo es un
«circuito estable» (CE): un territorio cuyo padrón se puede comparar entre años.

Se calcula para varias ventanas: cuanto más corta, menos fusiones. Para comparar 2023 con 2025
alcanza la ventana 2023-2025; para series largas, 2011-2025.

Padrón: electores nativos, máximo entre categorías de las generales (en nativos todas las
categorías comparten mesas). Fuente: panel_circuito.parquet (ETL 09).

Salidas
- 01_DATOS/processed/circuitos_equivalencias.csv : ventana, cod_indec, circuito, ce_id, ce_codigos
- 01_DATOS/processed/circuitos_estables_serie.csv : ventana, ce_id, anio, electores, n_codigos
- 01_DATOS/processed/geo/circuitos_estables.gpkg  : una capa por ventana (polígonos disueltos)
- 03_OUTPUTS/tablas/control_circuitos_estables.csv : por ventana, cuántos CE y qué tan estables
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
PROC = RAIZ / "01_DATOS" / "processed"
TABLAS = RAIZ / "03_OUTPUTS" / "tablas"
ALBERS = "+proj=aea +lat_1=-34 +lat_2=-39 +lat_0=-36.5 +lon_0=-60"

VENTANAS = {"2011_2025": 2011, "2015_2025": 2015, "2019_2025": 2019, "2023_2025": 2023}
# Un cambio es significativo si supera ambos umbrales (absoluto y relativo al circuito).
MIN_ABS = 150
MIN_REL = 0.15


class Grupos:
    """Union-find sobre códigos de circuito."""

    def __init__(self, elementos):
        self.padre = {e: e for e in elementos}

    def raiz(self, x):
        while self.padre[x] != x:
            self.padre[x] = self.padre[self.padre[x]]
            x = self.padre[x]
        return x

    def unir(self, a, b):
        ra, rb = self.raiz(a), self.raiz(b)
        if ra != rb:
            self.padre[max(ra, rb)] = min(ra, rb)


def padron_circuitos() -> pd.DataFrame:
    p = pd.read_parquet(PROC / "panel_circuito.parquet",
                        columns=["anio", "tipo", "cod_indec", "circuito", "electores_nativos"])
    p = p[p.tipo == "GENERALES"]
    el = p.groupby(["anio", "cod_indec", "circuito"]).electores_nativos.max().rename("electores").reset_index()
    return el[el.electores > 0]


def vecinos() -> tuple[dict[str, set[str]], gpd.GeoDataFrame]:
    g = gpd.read_file(PROC / "geo" / "circuitos.gpkg").to_crs(ALBERS)
    b = g[["circuito", "cod_indec", "geometry"]].copy()
    b["geometry"] = b.buffer(5)
    j = gpd.sjoin(b, b, predicate="intersects")
    j = j[(j.circuito_left != j.circuito_right) & (j.cod_indec_left == j.cod_indec_right)]
    v: dict[str, set[str]] = {}
    for a, c in j[["circuito_left", "circuito_right"]].values:
        v.setdefault(a, set()).add(c)
    return v, g


def familia(c: str) -> str:
    return c[:4]


def vecinos_de(c: str, vec: dict[str, set[str]]) -> set[str]:
    """Vecinos en el mapa. Un código sin polígono (de otra fecha que la capa) toma los vecinos y los
    polígonos de los de su familia."""
    if c in vec:
        return vec[c]
    fam = [x for x in vec if familia(x) == familia(c)]
    return set().union(*(vec[x] | {x} for x in fam)) - {c} if fam else set()


def uniones_transicion(a: pd.DataFrame, b: pd.DataFrame, vec: dict[str, set[str]],
                       transitorios: set[str]) -> list[tuple[str, str, str]]:
    """Pares a unir entre dos elecciones de un municipio, con el motivo. `transitorios` son los
    circuitos cuyo cambio se revierte en la elección siguiente (mesas que faltan en el provisorio):
    no cuentan como pérdida ni como ganancia."""
    m = a.merge(b, on="circuito", how="outer", suffixes=("_t0", "_t1")).fillna({"electores_t0": 0, "electores_t1": 0})
    crec = m.electores_t1.sum() / max(m.electores_t0.sum(), 1)
    m["exceso"] = m.electores_t1 - m.electores_t0 * crec
    base = np.maximum(m.electores_t0 * crec, m.electores_t1)
    signif = (m.exceso.abs() >= MIN_ABS) & (m.exceso.abs() >= MIN_REL * base) & ~m.circuito.isin(transitorios)
    m["pierde"] = (m.exceso < 0) & (signif | (m.electores_t1 == 0))
    m["gana"] = (m.exceso > 0) & (signif | (m.electores_t0 == 0))
    ganan = set(m.circuito[m.gana])
    exceso = m.set_index("circuito").exceso
    desaparece = set(m.circuito[m.electores_t1 == 0])
    pares = []
    for c in m.circuito[m.pierde]:
        cerca = vecinos_de(c, vec)
        cand = {x for x in ganan if x in cerca or familia(x) == familia(c)}
        # Si gana uno de una familia, ganan todos los de esa familia que crecen (subdivisión).
        cand |= {x for x in ganan if any(familia(x) == familia(y) for y in cand)}
        if cand:
            pares += [(c, x, "vecino o familia que gana") for x in cand]
            continue
        if c not in desaparece:
            continue
        presentes = [x for x in cerca if x in exceso.index and x != c]
        if presentes:
            pares.append((c, max(presentes, key=lambda y: exceso[y]), "desaparece: vecino que más ganó"))
        elif len(exceso) > 1:
            x = exceso.drop(c).idxmax()
            pares.append((c, x, "desaparece sin polígono ni familia: el que más ganó en el municipio"))
    unidos = {x for p in pares for x in p[:2]}
    for c in m.circuito[m.gana & (m.electores_t0 == 0)]:
        # Un código nuevo que nadie reclamó: se une con su familia o con el vecino que más perdió.
        if c in unidos:
            continue
        fam = [x for x in exceso.index if familia(x) == familia(c) and x != c]
        cerca = [x for x in vecinos_de(c, vec) if x in exceso.index]
        if fam:
            pares.append((c, min(fam, key=lambda y: exceso[y]), "aparece: misma familia"))
        elif cerca:
            pares.append((c, min(cerca, key=lambda y: exceso[y]), "aparece: vecino que más perdió"))
    return pares


def transitorios(w: pd.DataFrame, t0: int, t1: int, t2: int | None) -> set[str]:
    """Circuitos cuyo padrón cambia en t1 y vuelve en t2 a lo que tenía en t0."""
    if t2 is None:
        return set()
    x0, x1, x2 = w[t0], w[t1], w[t2]
    baja = (x1 < x0 * (1 - MIN_REL)) & (x2 >= x0 * 0.9)
    sube = (x1 > x0 * (1 + MIN_REL)) & (x2 <= x0 * 1.1)
    return set(w.index[(baja | sube) & x1.gt(0)])


def estables(el: pd.DataFrame, desde: int, vec) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    d = el[el.anio >= desde]
    anios = sorted(d.anio.unique())
    muni = d.drop_duplicates("circuito").set_index("circuito").cod_indec
    grp = Grupos(muni.index)
    motivos = []
    w = d.pivot(index="circuito", columns="anio", values="electores")
    for k, (t0, t1) in enumerate(zip(anios, anios[1:])):
        trans = transitorios(w, t0, t1, anios[k + 2] if k + 2 < len(anios) else None)
        for cod, dm in d[d.anio.isin([t0, t1])].groupby("cod_indec"):
            a = dm[dm.anio == t0][["circuito", "electores"]]
            b = dm[dm.anio == t1][["circuito", "electores"]]
            for x, y, mot in uniones_transicion(a, b, vec, trans):
                grp.unir(x, y)
                motivos.append((t0, t1, cod, x, y, mot))
    eq = pd.DataFrame({"circuito": muni.index, "cod_indec": muni.values})
    eq["ce_raiz"] = eq.circuito.map(grp.raiz)
    cods = eq.groupby("ce_raiz").circuito.apply(lambda s: "|".join(sorted(s)))
    eq["ce_codigos"] = eq.ce_raiz.map(cods)
    eq["ce_id"] = eq.cod_indec + "-" + eq.ce_raiz
    eq["n_codigos"] = eq.ce_raiz.map(eq.ce_raiz.value_counts())
    serie = (d.merge(eq[["circuito", "ce_id"]], on="circuito")
             .groupby(["ce_id", "anio"]).agg(electores=("electores", "sum"), n_codigos=("circuito", "nunique"))
             .reset_index())
    # Bajón o pico de un solo año que se revierte: faltan mesas en el provisorio. Se marca.
    ws = serie.pivot(index="ce_id", columns="anio", values="electores")
    marca = []
    for k in range(1, len(anios) - 1):
        for ce in transitorios(ws, anios[k - 1], anios[k], anios[k + 1]):
            marca.append((ce, anios[k]))
    serie["padron_incompleto"] = pd.MultiIndex.from_frame(serie[["ce_id", "anio"]]).isin(marca)
    mot = pd.DataFrame(motivos, columns=["anio_desde", "anio_hasta", "cod_indec", "circuito_a", "circuito_b", "motivo"])
    return eq.drop(columns="ce_raiz"), serie, mot


def control(serie: pd.DataFrame, eq: pd.DataFrame, ventana: str) -> dict:
    """Qué tan estable queda cada CE. Un salto es un cambio de más de 30 % en su peso dentro del
    municipio entre dos elecciones (en CE de 1.000 electores o más). Los saltos transitorios (se
    revierten) son mesas faltantes; los que se sostienen son crecimiento o despoblamiento real, o
    una equivalencia mal resuelta, y se revisan a mano en circuitos_estables_serie.csv."""
    w = serie.pivot(index="ce_id", columns="anio", values="electores")
    inc = serie.pivot(index="ce_id", columns="anio", values="padron_incompleto").fillna(False).astype(bool)
    anios = sorted(w.columns)
    completos = w.notna().all(axis=1)
    limpio = w.mask(inc).ffill(axis=1)
    rel = limpio.div(limpio.groupby(limpio.index.str[:5]).transform("sum"))
    salto = (rel.diff(axis=1).abs() / rel.shift(axis=1)).iloc[:, 1:]
    grande = ((salto > 0.30) & (limpio.shift(axis=1).iloc[:, 1:] >= 1000)).any(axis=1)
    el_ult = w[anios[-1]].sum()
    return {
        "ventana": ventana,
        "codigos": len(eq),
        "circuitos_estables": len(w),
        "ce_un_solo_codigo": int((eq.n_codigos == 1).sum()),
        "ce_con_fusion": int((eq.drop_duplicates("ce_id").n_codigos > 1).sum()),
        "max_codigos_en_un_ce": int(eq.n_codigos.max()),
        "ce_presentes_todos_los_anios": int(completos.sum()),
        "pct_padron_ultimo_anio_en_ce_completos": round(float(100 * w.loc[completos, anios[-1]].sum() / el_ult), 2),
        "ce_anio_padron_incompleto": int(inc.values.sum()),
        "ce_con_salto_sostenido_30pct": int(grande.sum()),
        "pct_padron_en_ce_con_salto": round(float(100 * w.loc[grande, anios[-1]].sum() / el_ult), 2),
    }


def main() -> None:
    el = padron_circuitos()
    vec, g = vecinos()
    sin_poligono = sorted(set(el.circuito) - set(g.circuito))
    print(f"códigos con voto: {el.circuito.nunique()}; sin polígono: {len(sin_poligono)} {sin_poligono}")

    eqs, series, mots, ctl, capas = [], [], [], [], {}
    for ventana, desde in VENTANAS.items():
        eq, serie, mot = estables(el, desde, vec)
        eq.insert(0, "ventana", ventana)
        serie.insert(0, "ventana", ventana)
        mot.insert(0, "ventana", ventana)
        eqs.append(eq); series.append(serie); mots.append(mot)
        ctl.append(control(serie.drop(columns="ventana"), eq, ventana))
        # Polígonos disueltos por CE (los códigos sin polígono quedan afuera de la capa).
        gg = g.merge(eq[["circuito", "ce_id", "ce_codigos", "n_codigos"]], on="circuito", how="inner")
        capas[ventana] = gg.dissolve(by="ce_id", aggfunc={"cod_indec": "first", "ce_codigos": "first",
                                                           "n_codigos": "first", "seccion_electoral": "first",
                                                           "conurbano": "first"}).reset_index()
        print(f"{ventana}: {ctl[-1]}")

    pd.concat(eqs).to_csv(PROC / "circuitos_equivalencias.csv", index=False, encoding="utf-8")
    pd.concat(series).to_csv(PROC / "circuitos_estables_serie.csv", index=False, encoding="utf-8")
    pd.concat(mots).to_csv(TABLAS / "circuitos_uniones_motivos.csv", index=False, encoding="utf-8")
    pd.DataFrame(ctl).to_csv(TABLAS / "control_circuitos_estables.csv", index=False, encoding="utf-8")
    destino = PROC / "geo" / "circuitos_estables.gpkg"
    destino.unlink(missing_ok=True)
    for ventana, capa in capas.items():
        capa.to_crs(4326).to_file(destino, layer=f"ce_{ventana}", driver="GPKG")
    print("listo")


if __name__ == "__main__":
    main()
