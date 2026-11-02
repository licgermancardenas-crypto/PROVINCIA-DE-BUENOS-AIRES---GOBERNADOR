"""
106 · El motor 2027, paso 2: escenarios de Gobernador con Monte Carlo.

QUÉ ES Y QUÉ NO
---------------
No es un pronóstico. El nivel provincial de cada fuerza es un **parámetro del escenario**: lo que
dirán las encuestas o lo que se quiera explorar. El motor hace lo que el backtest (`105`) probó que
se puede hacer bien: **bajar ese nivel al territorio** y medir lo que sí es aritmética —el padrón
de 2027, la participación de cada zona, el voto extranjero— con una incertidumbre calibrada contra
las elecciones pasadas.

CÓMO FUNCIONA
-------------
1. **Base**: el voto por circuito estable (ventana 2023-2025) de una elección de referencia:
   - octubre 2025 (Diputados Nacionales, nativos);
   - septiembre 2025 (provincial, sólo por municipio; se baja a circuito con el patrón de octubre
     dentro de cada municipio y se le descuenta la parte extranjera, como en el `103`).
2. **Escenario**: el % provincial de cada bloque (peronismo, derecha, tercera, izquierda, resto)
   entre los votos positivos de los nativos. Se baja a cada circuito con la **regla mezcla**
   (mitad proporcional, mitad uniforme: la del `105`).
3. **Padrón 2027**: el de 2025 de cada circuito, crecido al ritmo de 2023-2025. Los extranjeros
   votan Gobernador: su padrón (estimado en el `103`) crece igual; votan con su participación y su
   reparto de las mesas de extranjeros de Gobernador 2023 en cada municipio.
4. **Participación**: la provincial es un parámetro; cada circuito conserva su distancia al
   promedio (se escala el odds), con el patrón de Gobernador 2023 (elección concurrente).
5. **Monte Carlo**: en cada simulación,
   - un shock provincial en el margen peronismo − derecha, t de 5 grados con desvío `sd_provincial`
     (parámetro: cuánto se confía en el nivel del escenario);
   - ruido municipal en el cociente peronismo / derecha, con el modelo calibrado del `105`
     (desvío según tamaño, t de 5 grados con oferta estable); luego se reajusta para que la
     provincia dé lo que dio el shock: el ruido redistribuye el territorio, no cambia el nivel.

LO QUE SE REPORTA
-----------------
Por escenario: % provincial final (con el padrón y la participación de 2027 y los extranjeros),
probabilidad de que el peronismo gane la Gobernación (simple pluralidad, sin balotaje), margen,
municipios y secciones que gana cada uno. Y el efecto de las palancas que no son preferencia:
participación y voto extranjero.

Salidas (03_OUTPUTS/tablas/)
- motor_2027_escenarios.csv : un renglón por escenario
- motor_2027_seccion.csv    : escenario × sección
- motor_2027_municipio.csv  : escenario × municipio (% medio, probabilidad de ganar)
- motor_2027_circuito.csv   : el escenario base, por circuito estable
- motor_2027_grilla.csv     : el margen provincial de −12 a +12: municipios y secciones
"""
from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

RAIZ = Path(__file__).resolve().parents[2]
PROC = RAIZ / "01_DATOS" / "processed"
TABLAS = RAIZ / "03_OUTPUTS" / "tablas"
sys.path.insert(0, str(Path(__file__).parent))
bt = import_module("105_motor_backtest")
tr = import_module("102_transferencias_2023_2025")
dd = import_module("103_desdoblamiento")

BLOQUES = ["PERONISMO", "DERECHA", "TERCERA", "IZQUIERDA", "RESTO"]
NOMBRE = {"PERONISMO": "Peronismo", "DERECHA": "Derecha (LLA-PRO)", "TERCERA": "Tercera vía",
          "IZQUIERDA": "Izquierda", "RESTO": "Resto"}
A_BLOQUE = {"PERONISMO": "PERONISMO", "LLA_PRO": "DERECHA", "PRO_JXC": "DERECHA", "TERCERA_VIA": "TERCERA",
            "CENTRO_UCR": "TERCERA", "IZQUIERDA": "IZQUIERDA"}
NO_POS = {"BLANCO", "NULO", "RECURRIDO", "IMPUGNADO", "COMANDO"}
N_SIM = 1000
GL = 5


# ----------------------------------------------------------------------------- insumos
def base_octubre() -> tuple[pd.DataFrame, pd.DataFrame]:
    eq = pd.read_csv(PROC / "circuitos_equivalencias.csv", dtype=str)
    eq = eq[eq.ventana == "2023_2025"][["circuito", "ce_id"]]
    p = pd.read_parquet(PROC / "panel_circuito.parquet",
                        columns=["anio", "tipo", "cargo", "circuito", "espacio", "votos", "electores_nativos"])
    x = p[(p.anio == 2025) & (p.tipo == "GENERALES") & (p.cargo == "DIPUTADOS NACIONALES")].merge(eq, on="circuito")
    pos = x[~x.espacio.isin(NO_POS)].assign(bloque=lambda d: d.espacio.map(A_BLOQUE).fillna("RESTO"))
    v = pos.pivot_table(index="ce_id", columns="bloque", values="votos", aggfunc="sum", fill_value=0)
    v = v.reindex(columns=BLOQUES, fill_value=0).astype(float)
    el = x.drop_duplicates("circuito").groupby("ce_id").electores_nativos.sum().astype(float)
    x23 = p[(p.anio == 2023) & (p.tipo == "GENERALES") & (p.cargo == "DIPUTADOS NACIONALES")].merge(eq, on="circuito")
    el23 = x23.drop_duplicates("circuito").groupby("ce_id").electores_nativos.sum().astype(float)
    info = pd.DataFrame({"electores_2025": el, "electores_2023": el23})
    info["cod_indec"] = info.index.str[:5]
    return v, info


def participacion_2023(ce_index) -> pd.Series:
    eq = pd.read_csv(PROC / "circuitos_equivalencias.csv", dtype=str)
    eq = eq[eq.ventana == "2023_2025"].set_index("circuito")
    g = tr.gobernador_2023_nativos().groupby(eq.ce_id).sum()
    return ((g.electores - g.NO_VOTO) / g.electores).reindex(ce_index)


def septiembre_municipio() -> pd.DataFrame:
    """Septiembre 2025 sólo nativos por municipio, en bloques (el `103`)."""
    pm = pd.read_parquet(PROC / "panel_municipio.parquet")
    sep = dd.votos_municipio(pm[(pm.fuente == "jep_definitivo") & (pm.cargo != "CONCEJALES")])
    octu = dd.votos_municipio(pm[(pm.fuente == "dine_mesa") & (pm.anio == 2025) & (pm.cargo == "DIPUTADOS NACIONALES")])
    octu["electores"] = pm[(pm.fuente == "dine_mesa") & (pm.anio == 2025)].drop_duplicates("cod_indec").set_index("cod_indec").electores_nativos
    ext = dd.extranjeros_2023()
    sn = dd.septiembre_nativos(sep.loc[octu.index], octu, ext)
    out = pd.DataFrame({"PERONISMO": sn.PERONISMO, "DERECHA": sn.LLA_PRO, "TERCERA": sn.TERCERA_VIA,
                        "IZQUIERDA": sn.IZQUIERDA, "RESTO": sn.OTROS})
    return out, sn.extranjeros_electores_est, ext


def bajar_a_circuito(muni_votos: pd.DataFrame, s_oct: np.ndarray, w: np.ndarray, muni: pd.Series) -> np.ndarray:
    """Dentro de cada municipio, el patrón de octubre llevado (proporcional) al total del municipio."""
    out = s_oct.copy()
    for m, idx in muni.groupby(muni.to_numpy()).indices.items():
        if m not in muni_votos.index:
            continue
        S = muni_votos.loc[m].to_numpy(float)
        S = S / S.sum()
        out[idx] = bt.proporcional(s_oct[idx], w[idx], S)
    return out


def escalar_participacion(p_base: np.ndarray, el: np.ndarray, meta: float) -> np.ndarray:
    """Lleva la participación provincial a `meta` escalando el odds de cada circuito (bisección)."""
    p = np.clip(p_base, 0.05, 0.97)
    odds = p / (1 - p)
    lo, hi = 0.05, 20.0
    for _ in range(60):
        k = (lo + hi) / 2
        q = k * odds / (1 + k * odds)
        if (q * el).sum() / el.sum() < meta:
            lo = k
        else:
            hi = k
    return k * odds / (1 + k * odds)


# ----------------------------------------------------------------------------- motor
class Motor:
    def __init__(self):
        v, info = base_octubre()
        p23 = participacion_2023(v.index)
        ok = (v.sum(axis=1) >= 30) & info.electores_2025.notna() & p23.notna()
        self.v, self.info = v[ok], info[ok]
        self.ce = self.v.index
        self.muni = pd.Series(self.ce.str[:5], index=self.ce)
        self.w = self.v.sum(axis=1).to_numpy()
        self.s_oct = (self.v.T / self.v.sum(axis=1)).T.to_numpy()
        crec = (self.info.electores_2025 / self.info.electores_2023).clip(0.8, 1.3).fillna(1.0)
        self.el27 = (self.info.electores_2025 * crec).to_numpy()
        self.p23 = p23[ok].to_numpy()
        claves = pd.read_csv(PROC / "municipios_claves.csv", dtype=str).set_index("cod_indec")
        self.seccion = self.muni.map(claves.seccion_electoral).to_numpy()
        self.nombre_muni = claves.municipio_nombre
        sep_m, ext_el, ext = septiembre_municipio()
        self.s_sep = bajar_a_circuito(sep_m, self.s_oct, self.w, self.muni)
        # Extranjeros por municipio: padrón 2027, participación y reparto (en bloques).
        crec_m = (self.info.groupby("cod_indec").electores_2025.sum() / self.info.groupby("cod_indec").electores_2023.sum()).clip(0.8, 1.3)
        self.ext_el = (ext_el * crec_m.reindex(ext_el.index).fillna(1.0)).fillna(0)
        e = ext.reindex(self.ext_el.index).fillna(ext.mean())
        rep = pd.DataFrame({"PERONISMO": e.rep_PERONISMO, "DERECHA": e.rep_LLA_PRO, "TERCERA": e.rep_TERCERA_VIA,
                            "IZQUIERDA": e.rep_IZQUIERDA, "RESTO": e.rep_OTROS})
        self.ext_rep = rep.div(rep.sum(axis=1), axis=0)
        self.ext_part = e.participacion_ext
        mod = pd.read_csv(TABLAS / "motor_ruido_modelo.csv").set_index("regimen")
        self.ruido = mod
        m_idx = self.muni.groupby(self.muni.to_numpy()).indices
        self.m_idx = m_idx
        self.munis = list(m_idx)

    def provincia(self, s: np.ndarray, w: np.ndarray | None = None) -> np.ndarray:
        w = self.w if w is None else w
        return (s * w[:, None]).sum(axis=0) / w.sum()

    def escenario(self, base: str, metas: dict[str, float] | None) -> np.ndarray:
        s0 = self.s_oct if base == "octubre" else self.s_sep
        if not metas:
            return s0
        S1 = np.array([metas[b] for b in BLOQUES], float)
        S1 = S1 / S1.sum()
        return bt.mezcla(s0, self.w, S1)

    def simular(self, base: str, metas: dict | None, part: float = 0.76, part_ext: float | None = None,
                sd_provincial: float = 0.02, regimen: str = "oferta estable", n: int = N_SIM, semilla: int = 0) -> dict:
        rng = np.random.default_rng(semilla)
        s_esc = self.escenario(base, metas)
        S_esc = self.provincia(s_esc)
        r = self.ruido.loc[regimen]
        gl = None if pd.isna(r.gl_t) else int(r.gl_t)
        # Lo que no depende de la simulación: participación por circuito y voto extranjero.
        q = escalar_participacion(self.p23, self.el27, part)
        votantes = self.el27 * q * 0.95  # ~5 % de blanco y nulo
        pe = self.ext_part if part_ext is None else pd.Series(part_ext, index=self.ext_el.index)
        ext = self.ext_rep.mul(self.ext_el * pe * 0.95, axis=0).reindex(self.munis).fillna(0).to_numpy(float)
        codigo = {m: k for k, m in enumerate(self.munis)}
        cm = np.array([codigo[m] for m in self.muni.to_numpy()])
        sec_ids = sorted(set(self.seccion))
        sec_de_muni = np.array([sec_ids.index(self.seccion[self.m_idx[m][0]]) for m in self.munis])
        w_m = np.bincount(cm, weights=self.w)
        sig_m = r.escala * np.exp(r.a + r.b * np.log(w_m))
        res, muni_gana, muni_sh, sec_gana, sec_sh = [], [], [], [], []
        for _ in range(n):
            # Shock provincial: se mueve el margen peronismo − derecha.
            d = rng.standard_t(GL) * np.sqrt((GL - 2) / GL) * sd_provincial
            S = S_esc.copy()
            S[0] += d / 2
            S[1] -= d / 2
            S = np.clip(S, 1e-4, None)
            S /= S.sum()
            s = bt.mezcla(s_esc, self.w, S) if sd_provincial > 0 else s_esc.copy()
            # Ruido municipal en el cociente peronismo / derecha.
            e = (rng.standard_t(GL, len(self.munis)) * np.sqrt((GL - 2) / GL) if gl else rng.standard_normal(len(self.munis))) * sig_m
            fac = e[cm]
            s[:, 0] *= np.exp(fac / 2)
            s[:, 1] *= np.exp(-fac / 2)
            s /= s.sum(axis=1, keepdims=True)
            s = bt.proporcional(s, self.w, S, iters=40)  # el ruido no cambia el nivel provincial
            nat = s * votantes[:, None]
            vm = np.stack([np.bincount(cm, weights=nat[:, b], minlength=len(self.munis)) for b in range(len(BLOQUES))], axis=1) + ext
            tot = vm.sum(axis=0)
            res.append(tot / tot.sum())
            muni_gana.append(vm[:, 0] > vm[:, 1])
            muni_sh.append(vm[:, 0] / vm.sum(axis=1))
            vs = np.stack([np.bincount(sec_de_muni, weights=vm[:, b], minlength=len(sec_ids)) for b in range(len(BLOQUES))], axis=1)
            sec_gana.append(vs[:, 0] > vs[:, 1])
            sec_sh.append(vs[:, 0] / vs.sum(axis=1))
        R = np.array(res) * 100
        margen = R[:, 0] - R[:, 1]
        gana_per = (R[:, 0] == R.max(axis=1))
        MG = np.array(muni_gana)
        return {"R": R, "margen": margen, "p_gana_peronismo": gana_per.mean(), "munis_per": MG.sum(axis=1),
                "muni_p": MG.mean(axis=0), "muni_sh": np.array(muni_sh).mean(axis=0) * 100,
                "sec_p": np.array(sec_gana).mean(axis=0), "sec_sh": np.array(sec_sh).mean(axis=0) * 100,
                "sec_ids": sec_ids, "S_esc": S_esc * 100, "s_esc": s_esc}


def main() -> None:
    TABLAS.mkdir(parents=True, exist_ok=True)
    mo = Motor()
    S_oct = mo.provincia(mo.s_oct) * 100
    S_sep = mo.provincia(mo.s_sep) * 100
    print("octubre 2025 (base, % positivos nativos):", dict(zip(BLOQUES, S_oct.round(1))))
    print("septiembre 2025 (nativos, bajado a circuito):", dict(zip(BLOQUES, S_sep.round(1))))
    print(f"padrón 2027 nativos: {mo.el27.sum():,.0f}  extranjeros: {mo.ext_el.sum():,.0f}")

    def metas_desde(S, cambios):
        m = dict(zip(BLOQUES, S))
        for k, v in cambios.items():
            m[k] = v
        return m

    medio = (S_oct + S_sep) / 2
    tercera = metas_desde(S_oct, {"TERCERA": 12.0})
    falta = 12.0 - S_oct[2]
    tercera["DERECHA"] = S_oct[1] - falta * 2 / 3
    tercera["PERONISMO"] = S_oct[0] - falta / 3
    ESC = [
        ("A · Octubre 2025 se repite", "octubre", None, 0.76, None),
        ("B · Septiembre 2025 se repite", "septiembre", None, 0.76, None),
        ("C · Punto medio entre septiembre y octubre", "octubre", dict(zip(BLOQUES, medio)), 0.76, None),
        ("D · Tercera vía fuerte (12 %, 2/3 de la derecha)", "octubre", tercera, 0.76, None),
        ("A1 · Octubre, participación baja (64 %, como septiembre)", "octubre", None, 0.64, None),
        ("A2 · Octubre, participación alta (80 %)", "octubre", None, 0.80, None),
        ("A3 · Octubre, extranjeros votan al 45 %", "octubre", None, 0.76, 0.45),
        ("B1 · Septiembre, participación baja (64 %)", "septiembre", None, 0.64, None),
    ]
    filas, secc, muni = [], [], []
    for nombre, base, metas, part, pext in ESC:
        r = mo.simular(base, metas, part=part, part_ext=pext)
        R = r["R"]
        fila = {"escenario": nombre, "base": base, "participacion_nativos": part,
                "participacion_extranjeros": "2023" if pext is None else pext}
        for i, b in enumerate(BLOQUES):
            fila[f"meta_{b}"] = r["S_esc"][i]
            fila[f"pct_{b}"] = R[:, i].mean()
        fila.update({"margen_p10": np.percentile(r["margen"], 10), "margen_p50": np.percentile(r["margen"], 50),
                     "margen_p90": np.percentile(r["margen"], 90), "p_gana_peronismo": r["p_gana_peronismo"],
                     "municipios_peronismo_p10": np.percentile(r["munis_per"], 10),
                     "municipios_peronismo_p50": np.percentile(r["munis_per"], 50),
                     "municipios_peronismo_p90": np.percentile(r["munis_per"], 90),
                     "secciones_peronismo_media": r["sec_p"].sum()})
        filas.append(fila)
        for k, s in enumerate(r["sec_ids"]):
            secc.append({"escenario": nombre, "seccion": s, "pct_peronismo_de_los_positivos": r["sec_sh"][k],
                         "p_gana_peronismo": r["sec_p"][k]})
        for k, m in enumerate(mo.munis):
            muni.append({"escenario": nombre, "cod_indec": m, "municipio": mo.nombre_muni.get(m, m),
                         "pct_peronismo": r["muni_sh"][k], "p_gana_peronismo": r["muni_p"][k]})
        print(f"  {nombre:58s} peronismo {fila['pct_PERONISMO']:5.1f} derecha {fila['pct_DERECHA']:5.1f} "
              f"margen {fila['margen_p50']:+5.1f} [{fila['margen_p10']:+5.1f}, {fila['margen_p90']:+5.1f}] "
              f"P {fila['p_gana_peronismo']:.2f}  municipios {fila['municipios_peronismo_p50']:.0f}")
        if nombre.startswith("A ·"):
            c = pd.DataFrame(r["s_esc"] * 100, index=mo.ce, columns=[f"pct_{b}" for b in BLOQUES])
            c["electores_2027"] = mo.el27
            c.round(3).to_csv(TABLAS / "motor_2027_circuito.csv", encoding="utf-8")
    pd.DataFrame(filas).round(3).to_csv(TABLAS / "motor_2027_escenarios.csv", index=False, encoding="utf-8")
    pd.DataFrame(secc).round(3).to_csv(TABLAS / "motor_2027_seccion.csv", index=False, encoding="utf-8")
    pd.DataFrame(muni).round(3).to_csv(TABLAS / "motor_2027_municipio.csv", index=False, encoding="utf-8")

    # Grilla: margen provincial de −12 a +12 desde la base de octubre, el resto fijo.
    grilla = []
    for mg in range(-12, 13, 2):
        tot = S_oct[0] + S_oct[1]
        metas = dict(zip(BLOQUES, S_oct))
        metas["PERONISMO"], metas["DERECHA"] = (tot + mg) / 2, (tot - mg) / 2
        r = mo.simular("octubre", metas, n=400, sd_provincial=0.0)
        grilla.append({"margen_escenario": mg, "margen_final_p50": np.percentile(r["margen"], 50),
                       "municipios_peronismo_p10": np.percentile(r["munis_per"], 10),
                       "municipios_peronismo_p50": np.percentile(r["munis_per"], 50),
                       "municipios_peronismo_p90": np.percentile(r["munis_per"], 90),
                       **{f"seccion_{s}_p_peronismo": r["sec_p"][k] for k, s in enumerate(r["sec_ids"])}})
    g = pd.DataFrame(grilla)
    g.round(3).to_csv(TABLAS / "motor_2027_grilla.csv", index=False, encoding="utf-8")
    pd.set_option("display.width", 250)
    print("\ngrilla\n", g.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
