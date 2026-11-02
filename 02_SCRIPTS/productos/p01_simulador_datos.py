"""
p01 · Datos del simulador 2027 (la página `03_OUTPUTS/simulador/simulador_2027.html`).

El simulador corre el motor del `106` en el navegador: la misma regla mezcla, el mismo ruido por
sección y municipio calibrado en el `105`, la derecha dividida del `107` y el reparto de bancas del
`108`. Este script exporta lo que el motor necesita, ya calculado:

- por circuito estable (ventana 2023-2025): municipio, votos positivos de referencia, reparto en
  bloques de octubre y de septiembre 2025 (nativos), padrón 2027, participación de Gobernador 2023 y
  de octubre 2025, reparto PRO / LLA de 2023;
- por municipio: nombre, sección, padrón extranjero 2027, su participación y su reparto, y el
  contorno simplificado (proyección de áreas iguales del proyecto, en km) para el mapa;
- el modelo de ruido, las bancas por sección y los electos de 2025 que siguen hasta 2029;
- resultados de referencia del motor en Python, para validar la versión del navegador.

Salidas (03_OUTPUTS/simulador/)
- datos_simulador.json
- referencia_python.json
"""
from __future__ import annotations

import json
import sys
from importlib import import_module
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
PROC = RAIZ / "01_DATOS" / "processed"
SALIDA = RAIZ / "03_OUTPUTS" / "simulador"
sys.path.insert(0, str(RAIZ / "02_SCRIPTS" / "analisis"))
motor = import_module("106_motor_2027")
leg = import_module("108_legislatura_2027")
ALBERS = "+proj=aea +lat_1=-34 +lat_2=-39 +lat_0=-36.5 +lon_0=-60"


def ruta_svg(geom, x0: float, y1: float) -> str:
    """Polígono -> path SVG en km (y hacia abajo), un decimal."""
    partes = [g for g in getattr(geom, "geoms", [geom]) if g.geom_type == "Polygon"] +         [h for g in getattr(geom, "geoms", []) if g.geom_type == "MultiPolygon" for h in g.geoms]
    out = []
    for p in partes:
        for anillo in [p.exterior, *p.interiors]:
            xy = np.asarray(anillo.coords)
            pts = [f"{(x - x0) / 1000:.1f} {(y1 - y) / 1000:.1f}" for x, y in xy[:-1]]
            out.append("M" + "L".join(pts) + "Z")
    return "".join(out)


def geometria() -> tuple[dict, dict, list]:
    part = gpd.read_file(PROC / "geo" / "partidos.gpkg").to_crs(ALBERS)
    secc = gpd.read_file(PROC / "geo" / "secciones.gpkg").to_crs(ALBERS)
    x0, _, _, y1 = part.total_bounds
    # Tolerancia 300 m: alcanza para la provincia entera y deja reconocibles los partidos del Conurbano.
    part["geometry"] = part.geometry.simplify(300, preserve_topology=True)
    secc["geometry"] = secc.geometry.simplify(600, preserve_topology=True)
    p = {r.cod_indec: ruta_svg(r.geometry, x0, y1) for r in part.itertuples()}
    s = {str(r.seccion_electoral): ruta_svg(r.geometry, x0, y1) for r in secc.itertuples()}
    b = part.total_bounds
    conu = part[part.conurbano.astype(str) == "True"].total_bounds
    caja = [round((conu[0] - x0) / 1000, 1), round((y1 - conu[3]) / 1000, 1),
            round((conu[2] - conu[0]) / 1000, 1), round((conu[3] - conu[1]) / 1000, 1)]
    return p, s, {"ancho": round((b[2] - b[0]) / 1000, 1), "alto": round((b[3] - b[1]) / 1000, 1), "conurbano": caja}


def referencia(mo) -> list[dict]:
    """Escenarios del motor en Python, con las mismas perillas que expone la página."""
    S_oct = mo.provincia(mo.s_oct) * 100
    casos = [
        ("Octubre se repite", dict(base="octubre", metas=None)),
        ("Septiembre se repite", dict(base="septiembre", metas=None)),
        ("Octubre, participación 64 %", dict(base="octubre", metas=None, part=0.64)),
        ("Octubre, derecha dividida (PRO 25 %)", dict(base="octubre", metas=None, pi_prov=0.25, sd_pi_provincial=0.03)),
        ("Empate 40-40 desde octubre", dict(base="octubre", metas=dict(zip(motor.BLOQUES, [40, 40, *S_oct[2:]])))),
    ]
    out = []
    for nombre, kw in casos:
        r = mo.simular(n=1000, semilla=1, **kw)
        dip, sen = leg.bancas_2027(r["sec_votos"], r["sec_ids"], r["nombres"])
        per = r["nombres"].index("PERONISMO")
        out.append({"caso": nombre, "parametros": {k: (v if not isinstance(v, dict) else {a: float(b) for a, b in v.items()})
                                                   for k, v in kw.items()},
                    "pct": dict(zip(r["nombres"], np.round(r["R"].mean(axis=0), 2).tolist())),
                    "margen_p10_p50_p90": np.round(np.percentile(r["margen"], [10, 50, 90]), 2).tolist(),
                    "p_gana_peronismo": round(r["p_gana_peronismo"], 3),
                    "municipios_peronismo_p50": float(np.median(r["munis_per"])),
                    "secciones_p_peronismo": dict(zip(map(str, r["sec_ids"]), np.round(r["sec_p"], 3).tolist())),
                    "diputados_2027_peronismo_p50": float(np.median(dip[:, per])),
                    "senadores_2027_peronismo_p50": float(np.median(sen[:, per]))})
        print(f"  {nombre:40s} P {r['p_gana_peronismo']:.3f} margen {np.median(r['margen']):+.2f} "
              f"munis {np.median(r['munis_per']):.0f} dip {np.median(dip[:, per]):.0f} sen {np.median(sen[:, per]):.0f}")
    return out


def main() -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    mo = motor.Motor()
    munis = mo.munis
    idx = {m: k for k, m in enumerate(munis)}
    _, sigue = leg.validacion()
    paths, secs, caja = geometria()
    claves = pd.read_csv(PROC / "municipios_claves.csv", dtype=str).set_index("cod_indec")
    r4 = lambda a: np.round(np.asarray(a, float), 5).tolist()
    datos = {
        "bloques": motor.BLOQUES,
        "circuitos": {
            "id": list(mo.ce), "muni": [idx[m] for m in mo.muni], "w": r4(mo.w),
            "s_oct": r4(mo.s_oct), "s_sep": r4(mo.s_sep), "el27": r4(mo.el27),
            "p23": r4(mo.p23), "p25": r4(mo.p25), "pi23": r4(mo.pi23)},
        "municipios": [{
            "cod": m, "nombre": mo.nombre_muni.get(m, m), "seccion": str(claves.seccion_electoral[m]),
            "conurbano": claves.conurbano[m] == "True",
            "ext_el": float(round(mo.ext_el.get(m, 0.0), 1)),
            "ext_part": float(round(mo.ext_part.get(m, np.nan), 4)) if m in mo.ext_part.index else None,
            "ext_rep": r4(mo.ext_rep.loc[m]) if m in mo.ext_rep.index else None,
            "path": paths.get(m, "")} for m in munis],
        "secciones_path": secs, "caja": caja,
        "ruido": {k: {c: (None if pd.isna(v) else float(v)) for c, v in fila.items()}
                  for k, fila in mo.ruido[["a", "b", "escala", "gl_t", "sd_seccion"]].iterrows()},
        "ruido_pi": motor.RUIDO_PI, "gl": motor.GL,
        "legislatura": {"dip": leg.DIP, "sen": leg.SEN, "camara_2027": leg.CAMARA_2027,
                        "siguen_2025": sigue},
        "base_pct": {"octubre": r4(mo.provincia(mo.s_oct) * 100), "septiembre": r4(mo.provincia(mo.s_sep) * 100)},
    }
    (SALIDA / "datos_simulador.json").write_text(json.dumps(datos, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"datos: {len(mo.ce)} circuitos, {len(munis)} municipios, "
          f"{(SALIDA / 'datos_simulador.json').stat().st_size / 1e6:.2f} MB")
    ref = referencia(mo)
    (SALIDA / "referencia_python.json").write_text(json.dumps(ref, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
