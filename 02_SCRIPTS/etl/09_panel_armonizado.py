# -*- coding: utf-8 -*-
"""
ETL 09 · Panel armonizado: voto por espacio político, por circuito y por municipio, 2005-2025.

    python 02_SCRIPTS/etl/09_panel_armonizado.py

Qué contesta: cuántos votos sacó cada espacio en cada circuito (y municipio), en cada elección
y categoría, con su padrón y su participación, separando mesas de nativos y de extranjeros.
Es la columna vertebral de los análisis y del motor 2027. Deja:
- `01_DATOS/processed/panel_circuito.parquet`: anio × tipo × cargo × circuito × espacio (DINE,
  2011-2025, por mesa sumada a circuito), con `votos`, y por circuito `electores_nativos`,
  `electores_extranjeros`, `votantes_nativos`, `votantes_extranjeros`, `mesas`
- `01_DATOS/processed/panel_municipio.parquet`: lo mismo por municipio, todas las fuentes
  (DINE agregada + definitivo de la Provincia 2005-2023 + Junta 2025), con la columna `fuente`
- `03_OUTPUTS/tablas/control_panel.csv`: totales del panel contra los del ETL 01, por elección

Qué supone:
- El espacio de cada lista sale de `config/mapeo_espacios.csv` (columna `espacio_final`,
  validado el 01-11-2026). Una lista sin fila en el mapeo es un error y corta la corrida.
- Votantes de una mesa = suma de todos los tipos de voto de esa categoría (positivos, blanco,
  nulo, recurrido, impugnado). Electores = padrón de la mesa, contado una vez por categoría.
- El circuito se normaliza con `norm_circuito` (4 dígitos + letra) y el municipio se lleva a
  código INDEC con `municipios_claves.csv`.

Qué no puede afirmar: el panel por circuito es el **provisorio** (faltan mesas no transmitidas);
para totales oficiales, el panel por municipio trae el definitivo donde existe. Los circuitos
cambian entre años (934 con voto en 2011, 1.047 en 2023): seguir un circuito en el tiempo
pide la tabla de equivalencias (etapa 1.9), que todavía no está.
"""
import sys
from importlib import import_module
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
geo = import_module("02_geo_base")
mapeo_mod = import_module("08_mapeo_espacios")

OUT = RAIZ / "01_DATOS" / "processed"
RAW = RAIZ / "01_DATOS" / "raw" / "electoral"
TABLAS = RAIZ / "03_OUTPUTS" / "tablas"
NO_POS = mapeo_mod.NO_POS


def cargar_mapeo() -> pd.DataFrame:
    m = pd.read_csv(RAIZ / "config" / "mapeo_espacios.csv")
    return m[["fuente", "anio", "tipo", "cargo", "agrupacion", "votos_tipo", "espacio_final"]]


def panel_dine(mapeo: pd.DataFrame, claves: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    mp = mapeo[mapeo.fuente == "dine_mesa"].drop(columns="fuente")
    partes, ctl = [], []
    for f in sorted(OUT.glob("mesas_dine_pba_*.parquet")):
        d = pd.read_parquet(f, columns=["anio", "eleccion_tipo", "cargo_nombre", "seccion_id", "circuito_id", "mesa_id",
                                        "mesa_tipo", "mesa_electores", "agrupacion_nombre", "votos_tipo", "votos_cantidad"])
        d["tipo"] = d.eleccion_tipo.str.upper().str.strip().replace({"GENERAL": "GENERALES"})
        d["cargo"] = d.cargo_nombre.map(mapeo_mod.norm_cargo)
        d["agrupacion"] = d.agrupacion_nombre.fillna("").str.strip()
        d.loc[d.votos_tipo != "POSITIVO", "agrupacion"] = d.votos_tipo
        d = d.merge(mp, on=["anio", "tipo", "cargo", "agrupacion", "votos_tipo"], how="left")
        sin = d[d.espacio_final.isna()]
        if len(sin):
            raise ValueError(f"{f.name}: {len(sin)} filas sin espacio en el mapeo, p. ej. "
                             f"{sin[['cargo', 'agrupacion']].drop_duplicates().head(3).values.tolist()}")
        d["circuito"] = d.circuito_id.map(geo.norm_circuito)
        # Marca o numeración 9000+: ver es_extranjera en 01_mesas_dine_pba.py
        d["extranjeros"] = (d.mesa_tipo.fillna("").str.upper().str.startswith("EXTRANJ")
                            | (pd.to_numeric(d.mesa_id, errors="coerce") >= 9000))

        clave_mesa = ["anio", "tipo", "cargo", "seccion_id", "circuito", "mesa_id", "extranjeros"]
        mesas = d.groupby(clave_mesa).agg(electores=("mesa_electores", "first"), votantes=("votos_cantidad", "sum")).reset_index()
        g = ["anio", "tipo", "cargo", "seccion_id", "circuito"]
        padron = mesas.pivot_table(index=g, columns="extranjeros", values=["electores", "votantes"], aggfunc="sum", fill_value=0)
        padron.columns = [f"{v}_{'extranjeros' if e else 'nativos'}" for v, e in padron.columns]
        padron = padron.reset_index()
        for c in ("electores_nativos", "electores_extranjeros", "votantes_nativos", "votantes_extranjeros"):
            if c not in padron:
                padron[c] = 0
        padron["mesas"] = mesas.groupby(g).size().values
        votos = d.groupby(g + ["espacio_final"]).votos_cantidad.sum().rename("votos").reset_index()
        p = votos.merge(padron, on=g).rename(columns={"espacio_final": "espacio"})
        partes.append(p)
        ctl.append(d.groupby(["anio", "tipo", "cargo"]).votos_cantidad.sum().rename("votos_etl01").reset_index())
    panel = pd.concat(partes, ignore_index=True)
    panel = panel.merge(claves[["seccion_id_dine", "cod_indec", "seccion_electoral", "conurbano"]],
                        left_on="seccion_id", right_on="seccion_id_dine", how="left").drop(columns="seccion_id_dine")
    assert panel.cod_indec.notna().all(), "seccion_id de la DINE sin código INDEC"
    return panel, ctl


def panel_catalogo(mapeo: pd.DataFrame, claves: pd.DataFrame) -> pd.DataFrame:
    mp = mapeo[mapeo.fuente == "gba_definitivo"].drop(columns="fuente")
    partes = []
    for archivo, tipo in (("generales_provinciales_2005_2023.csv", "GENERALES"), ("paso_provinciales_2011_2021.csv", "PASO")):
        d = pd.read_csv(RAW / "gba" / archivo, encoding="latin-1")
        d = d.rename(columns={"eleccion": "anio", "lista": "agrupacion"})
        # PASO 2011, Intendente: 3 filas sin nombre de lista (7.227 votos). Van como «SIN NOMBRE»
        # en las dos puntas (mapeo y panel) para que no se pierdan ni rompan el cruce.
        d["agrupacion"] = d.agrupacion.fillna("SIN NOMBRE").astype(str).str.strip()
        d["tipo"] = tipo
        d["cargo"] = d.cargo.map(mapeo_mod.norm_cargo)
        d["distrito_jep"] = d.distrito_id.astype(int)
        d = d.merge(mp.drop(columns="votos_tipo").drop_duplicates(["anio", "tipo", "cargo", "agrupacion"]),
                    on=["anio", "tipo", "cargo", "agrupacion"], how="left")
        assert d.espacio_final.notna().all(), d[d.espacio_final.isna()].agrupacion.unique()[:5]
        hab = "votantes_habilitados" if "votantes_habilitados" in d else "electores_habilitados"
        g = d.groupby(["anio", "tipo", "cargo", "distrito_jep", "espacio_final"]).votos.sum().rename("votos").reset_index()
        e = d.groupby(["anio", "tipo", "cargo", "distrito_jep"]).agg(electores=(hab, "first"), votantes=("votos", "sum")).reset_index()
        partes.append(g.merge(e, on=["anio", "tipo", "cargo", "distrito_jep"]).assign(fuente="gba_definitivo"))
    p = pd.concat(partes, ignore_index=True).rename(columns={"espacio_final": "espacio"})
    p = p.merge(claves[["seccion_id_dine", "cod_indec", "seccion_electoral", "conurbano"]],
                left_on="distrito_jep", right_on="seccion_id_dine", how="left").drop(columns=["seccion_id_dine", "distrito_jep"])
    return p


def panel_jep(mapeo: pd.DataFrame) -> pd.DataFrame:
    mp = mapeo[mapeo.fuente == "jep_definitivo"][["cargo", "agrupacion", "espacio_final"]]
    d = pd.read_csv(OUT / "jep_2025_municipio.csv")
    r = pd.read_csv(OUT / "jep_2025_municipio_resumen.csv", dtype={"cod_indec": str})
    d["cargo"] = d.categoria.map(mapeo_mod.norm_cargo)
    d = d.merge(mp, on=["cargo", "agrupacion"], how="left")
    assert d.espacio_final.notna().all()
    g = d.groupby(["distrito_jep", "cargo", "espacio_final"]).votos.sum().rename("votos").reset_index()
    # blancos: la Junta los da aparte del detalle por lista
    bl = []
    for _, x in r.iterrows():
        for cargo, col in ((mapeo_mod.norm_cargo(x.categoria_legislativa), "blanco_leg"), ("CONCEJALES", "blanco_concejales")):
            bl.append({"distrito_jep": x.distrito_jep, "cargo": cargo, "espacio_final": "BLANCO", "votos": x[col]})
    g = pd.concat([g, pd.DataFrame(bl)], ignore_index=True)
    tot = r.set_index("distrito_jep")
    g["electores"] = g.distrito_jep.map(tot.electores)
    g["votantes"] = np.where(g.cargo == "CONCEJALES", g.distrito_jep.map(tot.total_concejales), g.distrito_jep.map(tot.total_leg))
    g = g.merge(r[["distrito_jep", "cod_indec", "seccion_electoral"]], on="distrito_jep").drop(columns="distrito_jep")
    return g.rename(columns={"espacio_final": "espacio"}).assign(anio=2025, tipo="PROVINCIAL", fuente="jep_definitivo")


def main() -> None:
    claves = pd.read_csv(OUT / "municipios_claves.csv", dtype={"cod_indec": str})
    mapeo = cargar_mapeo()

    destino = OUT / "panel_circuito.parquet"
    insumos = [RAIZ / "config" / "mapeo_espacios.csv", *OUT.glob("mesas_dine_pba_*.parquet")]
    if destino.exists() and destino.stat().st_mtime > max(p.stat().st_mtime for p in insumos):
        pc = pd.read_parquet(destino)  # tarda ~6 minutos rehacerlo: se reutiliza si nada cambió
        print(f"  panel circuito: reutilizado ({len(pc):,} filas; los insumos no cambiaron)")
    else:
        pc, ctl = panel_dine(mapeo, claves)
        pc.to_parquet(destino, index=False, compression="zstd")
        # control: el panel suma exactamente lo que sale del ETL 01
        c = pd.concat(ctl).groupby(["anio", "tipo", "cargo"]).votos_etl01.sum().reset_index()
        s = pc.groupby(["anio", "tipo", "cargo"]).votos.sum().rename("votos_panel").reset_index()
        c = c.merge(s, on=["anio", "tipo", "cargo"])
        c["dif"] = c.votos_panel - c.votos_etl01
        c.to_csv(TABLAS / "control_panel.csv", index=False, encoding="utf-8")
        print(f"  panel circuito: {len(pc):,} filas · {pc.groupby(['anio', 'tipo', 'cargo']).ngroups} elecciones×categorías · "
              f"{pc.circuito.nunique()} circuitos · votos que no cierran con el ETL 01: {int(c.dif.abs().sum())}")

    # Circuitos chicos con el padrón mal cargado en el provisorio: participación > 100 % o < 30 %.
    # Son 0,02 % de los votantes (mediana 80 electores). Se marcan, no se borran.
    if "participacion_anomala" not in pc:
        part = (pc.votantes_nativos + pc.votantes_extranjeros) / (pc.electores_nativos + pc.electores_extranjeros)
        pc["participacion_anomala"] = (part > 1) | (part < 0.3)
        pc.to_parquet(destino, index=False, compression="zstd")
    print(f"  circuitos con participación anómala: {pc.drop_duplicates(['anio', 'tipo', 'cargo', 'seccion_id', 'circuito']).participacion_anomala.sum()} "
          f"(se marcan en `participacion_anomala`)")

    # por municipio: DINE agregada + definitivo de la Provincia + Junta 2025
    g = ["anio", "tipo", "cargo", "cod_indec", "seccion_electoral", "conurbano"]
    pad = pc.drop_duplicates(g[:4] + ["circuito"]).groupby(g)[["electores_nativos", "electores_extranjeros",
                                                              "votantes_nativos", "votantes_extranjeros"]].sum()
    pm_d = pc.groupby(g + ["espacio"]).votos.sum().reset_index().merge(pad.reset_index(), on=g)
    pm_d["electores"] = pm_d.electores_nativos + pm_d.electores_extranjeros
    pm_d["votantes"] = pm_d.votantes_nativos + pm_d.votantes_extranjeros
    pm = pd.concat([pm_d.assign(fuente="dine_mesa"), panel_catalogo(mapeo, claves), panel_jep(mapeo)], ignore_index=True)
    pm.to_parquet(OUT / "panel_municipio.parquet", index=False, compression="zstd")
    print(f"  panel municipio: {len(pm):,} filas · fuentes {pm.fuente.value_counts().to_dict()}")

    # vista: Gobernador por espacio, provincia, todas las elecciones
    gob = pm[(pm.cargo == "GOBERNADOR") & (pm.tipo == "GENERALES")]
    for fuente in ("gba_definitivo", "dine_mesa"):
        x = gob[gob.fuente == fuente]
        pos = x[~x.espacio.isin(["BLANCO", "NULO"])]
        t = pos.pivot_table(index="anio", columns="espacio", values="votos", aggfunc="sum", fill_value=0)
        t = (100 * t.div(t.sum(axis=1), axis=0)).round(1)
        part = x.groupby("anio").votos.sum() / x.drop_duplicates(["anio", "cod_indec"]).groupby("anio").electores.sum()
        t["participacion"] = (100 * part).round(1)
        print(f"\n  Gobernador · {fuente} · % de los positivos:")
        print(t.to_string())


if __name__ == "__main__":
    main()
