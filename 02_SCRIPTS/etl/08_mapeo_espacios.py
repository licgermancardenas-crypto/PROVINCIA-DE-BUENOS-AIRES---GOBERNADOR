# -*- coding: utf-8 -*-
"""
ETL 08 · Mapeo agrupación -> espacio político, 2005-2025, todas las fuentes y categorías.

    python 02_SCRIPTS/etl/08_mapeo_espacios.py

Qué contesta: a qué espacio político pertenece cada lista que compitió en PBA, para poder
seguir una fuerza de una elección a la siguiente. Aplica `config/reglas_mapeo.yaml` sobre el
inventario de todas las agrupaciones y deja:
- `01_DATOS/processed/inventario_agrupaciones.csv`: fuente × año × tipo × cargo × agrupación,
  con votos, % y en cuántos municipios compitió
- `config/mapeo_espacios.csv`: lo mismo + espacio, regla, ambigüedad. La columna
  `espacio_override` se respeta en la corrida siguiente: sirve para corregir una fila puntual
  sin tocar la regla.
- `03_OUTPUTS/tablas/espacios_por_eleccion.csv`: % de cada espacio por elección y categoría
- `03_OUTPUTS/tablas/control_mapeo_gobernador.csv`: Gobernador por espacio, provisorio DINE
  contra definitivo del catálogo PBA

Fuentes del inventario:
- DINE por mesa 2011-2025 (`mesas_dine_pba_*.parquet`)
- Catálogo PBA, definitivo por municipio: generales provinciales 2005-2023 y PASO 2011-2021
  (es la única fuente de Gobernador 2007 y de las legislativas 2005)
- Junta Electoral, definitivo 2025 por municipio (`jep_2025_municipio.csv`)

Qué supone: que una lista con el mismo nombre en el mismo año es la misma fuerza en todas las
categorías (salvo las reglas con `cargos`, como UDESO 2011). Que una lista sin regla que compite
en una sola categoría municipal, o en dos municipios o menos, es vecinal.

Qué no puede afirmar: el espacio de las listas marcadas `ambiguo`. Son decisiones, no datos:
están en `00_DOCS/mapeo_espacios.md` con su peso, para que las valide el cliente.
"""
import re
import unicodedata
from pathlib import Path

import pandas as pd
import yaml

RAIZ = Path(__file__).resolve().parents[2]
OUT = RAIZ / "01_DATOS" / "processed"
RAW = RAIZ / "01_DATOS" / "raw" / "electoral"
TABLAS = RAIZ / "03_OUTPUTS" / "tablas"
CONFIG = RAIZ / "config"
REGLAS = yaml.safe_load((CONFIG / "reglas_mapeo.yaml").read_text(encoding="utf-8"))["reglas"]
NO_POS = {"EN BLANCO": "BLANCO", "BLANCO": "BLANCO", "NULO": "NULO", "RECURRIDO": "NULO",
          "IMPUGNADO": "NULO", "COMANDO": "NULO"}
MUNICIPAL = re.compile(r"INTENDENTE|CONCEJAL|CONSEJER")


def norm(s) -> str:
    """Las fuentes escriben la misma lista de cinco maneras: «ALIANZA JUNTOS» / «JUNTOS»,
    «NUEVO ENCUENTRO (NE)», «FTE DE IZQ. Y DE TRABAJADORES-UNIDAD». Se saca el prefijo ALIANZA,
    la sigla entre paréntesis al final y se expanden FTE e IZQ."""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().upper()
    s = re.sub(r"\s*\([^)]*\)\s*$", "", s.strip())
    s = re.sub(r"\bFTE\b", "FRENTE", s)
    s = re.sub(r"\bIZQ\b", "IZQUIERDA", s)
    s = re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9+ ]", " ", s)).strip()
    return re.sub(r"^ALIANZA ", "", s)


def norm_cargo(c: str) -> str:
    c = norm(str(c).upper().replace("/AS", "").replace("/A", ""))
    c = re.sub(r"\bY VICE\b", "", c).strip()
    c = {"DIPUTADO NACIONAL": "DIPUTADOS NACIONALES", "SENADOR NACIONAL": "SENADORES NACIONALES",
         "DIPUTADO PROVINCIAL": "DIPUTADOS PROVINCIALES", "SENADOR PROVINCIAL": "SENADORES PROVINCIALES",
         "CONCEJALES TITULARES": "CONCEJALES", "SENADOR PROV TIT": "SENADORES PROVINCIALES"}.get(c, c)
    return re.sub(r"\s+", " ", c)


# --- inventario ----------------------------------------------------------------------------------
def inventario() -> pd.DataFrame:
    partes = []
    for f in sorted(OUT.glob("mesas_dine_pba_*.parquet")):
        d = pd.read_parquet(f, columns=["anio", "eleccion_tipo", "cargo_nombre", "seccion_id", "agrupacion_nombre",
                                        "votos_tipo", "votos_cantidad"])
        d["agrupacion"] = d.agrupacion_nombre.fillna("").str.strip()
        d.loc[d.votos_tipo != "POSITIVO", "agrupacion"] = d.votos_tipo
        g = d.groupby(["anio", "eleccion_tipo", "cargo_nombre", "agrupacion", "votos_tipo"]).agg(
            votos=("votos_cantidad", "sum"),
            n_municipios=("seccion_id", lambda s: s[d.loc[s.index, "votos_cantidad"] > 0].nunique())).reset_index()
        partes.append(g.assign(fuente="dine_mesa"))

    for archivo, tipo in (("generales_provinciales_2005_2023.csv", "GENERALES"), ("paso_provinciales_2011_2021.csv", "PASO")):
        p = RAW / "gba" / archivo
        if not p.exists():
            continue
        d = pd.read_csv(p, encoding="latin-1")
        anio_col = "eleccion" if "eleccion" in d else d.columns[0]
        d = d.rename(columns={anio_col: "anio", "cargo": "cargo_nombre", "lista": "agrupacion"})
        if "municipio_id" not in d:  # el de PASO trae el número de distrito de la Junta
            d["municipio_id"] = d["distrito_id"]
        d["agrupacion"] = d.agrupacion.fillna("SIN NOMBRE").astype(str).str.strip()  # 3 filas en PASO 2011
        # Por nombre completo, no por palabra suelta: «PARTIDO UNION CELESTE Y BLANCO» es una lista.
        d["votos_tipo"] = d.agrupacion.map(lambda x: "EN BLANCO" if re.fullmatch(r"VOTOS? EN BLANCO", norm(x))
                                           else ("NULO" if re.fullmatch(r"VOTOS? NULOS?", norm(x)) else "POSITIVO"))
        g = d.groupby(["anio", "cargo_nombre", "agrupacion", "votos_tipo"]).agg(
            votos=("votos", "sum"), n_municipios=("municipio_id", lambda s: s[d.loc[s.index, "votos"] > 0].nunique())).reset_index()
        partes.append(g.assign(fuente="gba_definitivo", eleccion_tipo=tipo))

    j = OUT / "jep_2025_municipio.csv"
    if j.exists():
        d = pd.read_csv(j)
        g = d.groupby(["categoria", "agrupacion"]).agg(votos=("votos", "sum"),
                                                       n_municipios=("distrito_jep", "nunique")).reset_index()
        partes.append(g.rename(columns={"categoria": "cargo_nombre"}).assign(
            fuente="jep_definitivo", anio=2025, eleccion_tipo="PROVINCIAL", votos_tipo="POSITIVO"))

    inv = pd.concat(partes, ignore_index=True)
    inv["cargo"] = inv.cargo_nombre.map(norm_cargo)
    inv["tipo"] = inv.eleccion_tipo.str.upper().str.strip().replace({"GENERAL": "GENERALES"})
    inv["agrupacion_norm"] = inv.agrupacion.map(norm)
    pos = inv[inv.votos_tipo == "POSITIVO"]
    tot = pos.groupby(["fuente", "anio", "tipo", "cargo"]).votos.transform("sum")
    inv.loc[pos.index, "pct"] = (100 * pos.votos / tot).round(3)
    return inv[["fuente", "anio", "tipo", "cargo", "agrupacion", "agrupacion_norm", "votos_tipo", "votos", "pct", "n_municipios"]]


# --- reglas --------------------------------------------------------------------------------------
def aplicar(f) -> dict:
    if f.votos_tipo != "POSITIVO":
        return {"espacio": NO_POS.get(f.votos_tipo, "NULO"), "regla": "no_positivo", "ambiguo": False, "alternativas": "", "motivo": ""}
    for i, r in enumerate(REGLAS):
        a0, a1 = r.get("anios", [0, 9999])
        if not (a0 <= f.anio <= a1):
            continue
        if "cargos" in r and not re.search(r["cargos"], f.cargo):
            continue
        if re.search(r["patron"], f.agrupacion_norm):
            return {"espacio": r["espacio"], "regla": f"r{i:03d}", "ambiguo": bool(r.get("ambiguo", False)),
                    "alternativas": ",".join(r.get("alternativas", [])), "motivo": r.get("motivo", "")}
    if MUNICIPAL.search(f.cargo) or f.n_municipios <= 2:
        return {"espacio": "VECINAL", "regla": "datos_local", "ambiguo": False, "alternativas": "",
                "motivo": "sin regla y local (categoría municipal o <= 2 municipios)"}
    return {"espacio": "SIN_REGLA", "regla": "", "ambiguo": False, "alternativas": "", "motivo": ""}


def main() -> None:
    TABLAS.mkdir(parents=True, exist_ok=True)
    inv = inventario()
    inv.to_csv(OUT / "inventario_agrupaciones.csv", index=False, encoding="utf-8")
    m = pd.concat([inv, inv.apply(aplicar, axis=1, result_type="expand")], axis=1)

    destino = CONFIG / "mapeo_espacios.csv"
    clave = ["fuente", "anio", "tipo", "cargo", "agrupacion"]
    if destino.exists():
        prev = pd.read_csv(destino, dtype=str)
        if "espacio_override" in prev and prev.espacio_override.notna().any():
            ov = prev.dropna(subset=["espacio_override"])[clave + ["espacio_override"]]
            ov["anio"] = ov.anio.astype(int)
            m = m.merge(ov, on=clave, how="left")
    if "espacio_override" not in m:
        m["espacio_override"] = pd.NA
    m["espacio_final"] = m.espacio_override.fillna(m.espacio)
    m.to_csv(destino, index=False, encoding="utf-8")

    pos = m[m.votos_tipo == "POSITIVO"]
    print(f"  inventario: {len(inv):,} filas · {inv.agrupacion_norm.nunique()} nombres distintos · "
          f"{inv.groupby(['fuente', 'anio', 'tipo', 'cargo']).ngroups} elecciones×categorías")

    # cobertura
    sr = pos[pos.espacio_final == "SIN_REGLA"]
    print(f"  sin regla: {sr.votos.sum() / pos.votos.sum():.3%} de los votos positivos · "
          f"{len(sr)} filas · máximo {sr.pct.max() if len(sr) else 0:.2f} % en una categoría")
    if len(sr):
        print(sr.sort_values("pct", ascending=False).head(15)[["fuente", "anio", "cargo", "agrupacion", "pct", "n_municipios"]].to_string(index=False))
    vec = pos[pos.regla == "datos_local"]
    print(f"  vecinal por regla de datos: {len(vec)} filas, {vec.votos.sum() / pos.votos.sum():.2%} de los votos positivos "
          f"(de los cuales en categorías no municipales: {vec[~vec.cargo.str.contains('INTENDENTE|CONCEJAL|CONSEJER')].votos.sum() / pos.votos.sum():.3%})")

    # ambiguos con peso
    amb = pos[pos.ambiguo].groupby(["motivo", "espacio", "alternativas"]).agg(
        pct_max=("pct", "max"), votos=("votos", "sum"), anios=("anio", lambda s: ",".join(map(str, sorted(set(s)))))).reset_index()
    amb.sort_values("pct_max", ascending=False).to_csv(TABLAS / "mapeo_ambiguos.csv", index=False, encoding="utf-8")
    print(f"\n  decisiones abiertas (ambiguos): {len(amb)}")
    print(amb.sort_values("pct_max", ascending=False).head(12)[["pct_max", "espacio", "alternativas", "anios", "motivo"]].to_string(index=False))

    # % por espacio, por elección y categoría
    e = pos.groupby(["fuente", "anio", "tipo", "cargo", "espacio_final"]).votos.sum().reset_index()
    e["pct"] = (100 * e.votos / e.groupby(["fuente", "anio", "tipo", "cargo"]).votos.transform("sum")).round(2)
    e.to_csv(TABLAS / "espacios_por_eleccion.csv", index=False, encoding="utf-8")
    vista = e[e.cargo.isin(["GOBERNADOR", "DIPUTADOS NACIONALES", "DIPUTADOS PROVINCIALES"]) & (e.tipo.isin(["GENERALES", "PROVINCIAL"]))]
    vista = vista[(vista.fuente == "gba_definitivo") | ((vista.fuente != "gba_definitivo") & (vista.cargo == "DIPUTADOS NACIONALES")) | (vista.fuente == "jep_definitivo")]
    piv = vista.pivot_table(index=["anio", "cargo", "fuente"], columns="espacio_final", values="pct", fill_value=0).round(1)
    orden = [c for c in ["PERONISMO", "TERCERA_VIA", "PRO_JXC", "LLA", "LLA_PRO", "CENTRO_UCR", "IZQUIERDA", "VECINAL", "OTROS", "SIN_REGLA"] if c in piv]
    print("\n  % de los positivos por espacio:")
    print(piv[orden].to_string())

    # control: categorías provinciales, provisorio DINE contra definitivo del catálogo PBA.
    # El mismo mapeo sobre dos fuentes independientes: si una categoría no cierra, el problema
    # está en una de las fuentes, no en las reglas.
    g = e[e.cargo.isin(["GOBERNADOR", "DIPUTADOS PROVINCIALES", "SENADORES PROVINCIALES"]) & (e.tipo == "GENERALES")]
    c = g.pivot_table(index=["anio", "cargo", "espacio_final"], columns="fuente", values="pct", fill_value=0).reset_index()
    if {"dine_mesa", "gba_definitivo"} <= set(c.columns):
        k = c.groupby(["anio", "cargo"])
        c = c[(k.dine_mesa.transform("sum") > 0) & (k.gba_definitivo.transform("sum") > 0)].copy()
        c["dif_pp"] = (c.dine_mesa - c.gba_definitivo).round(2)
        c.to_csv(TABLAS / "control_mapeo_provinciales.csv", index=False, encoding="utf-8")
        r = c.assign(a=c.dif_pp.abs()).groupby(["anio", "cargo"]).a.max().rename("max_dif_pp").reset_index()
        print("\n  categorías provinciales: máxima diferencia por espacio, provisorio DINE contra definitivo PBA (pp):")
        print(r.pivot_table(index="anio", columns="cargo", values="max_dif_pp").round(2).to_string())


if __name__ == "__main__":
    main()
