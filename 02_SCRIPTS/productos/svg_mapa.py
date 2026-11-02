"""
Contornos de municipios como paths SVG compactos, para dibujar el mapa con una medida DAX en
Power BI (imagen SVG que se recalcula con cada filtro; no depende de visuales en versión preliminar).

- Provincia: simplificada a ~900 m, coordenadas enteras y movimientos relativos (`m`/`l`), lienzo
  de 600 px de ancho.
- Recuadro del Conurbano y Gran La Plata: más detalle (~90 m), su propio lienzo de 600 px.
Todo en la proyección de áreas iguales del proyecto.
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
from shapely.geometry import box

RAIZ = Path(__file__).resolve().parents[2]
ALBERS = "+proj=aea +lat_1=-34 +lat_2=-39 +lat_0=-36.5 +lon_0=-60"
ANCHO = 600
RECUADRO_EXTRA = {"06441", "06098", "06245"}  # La Plata, Berisso, Ensenada


def _path(geom, x0, y1, k) -> str:
    partes = getattr(geom, "geoms", [geom])
    out = []
    for p in partes:
        if p.geom_type != "Polygon":
            continue
        for ring in [p.exterior]:  # sin huecos: no hay municipios dentro de otros que importen a esta escala
            pts = [(round((x - x0) * k), round((y1 - y) * k)) for x, y in ring.coords[:-1]]
            ded = [pts[0]] + [b for a, b in zip(pts, pts[1:]) if a != b]
            if len(ded) < 3:
                continue
            s = f"M{ded[0][0]} {ded[0][1]}l" + " ".join(f"{b[0] - a[0]} {b[1] - a[1]}" for a, b in zip(ded, ded[1:])) + "z"
            out.append(s.replace(" -", "-"))
    return "".join(out)


def paths() -> tuple[dict, dict, dict]:
    g = gpd.read_file(RAIZ / "01_DATOS" / "processed" / "geo" / "partidos.gpkg").to_crs(ALBERS)
    x0, y0, x1, y1 = g.total_bounds
    k = ANCHO / (x1 - x0)
    prov = {r.cod_indec: _path(r.geometry.simplify(900), x0, y1, k) for r in g.itertuples()}
    meta = {"prov_w": ANCHO, "prov_h": round((y1 - y0) * k)}
    sub = g[(g.conurbano.astype(str) == "True") | g.cod_indec.isin(RECUADRO_EXTRA)]
    bx0, by0, bx1, by1 = sub.total_bounds
    pad = 3000
    bx0, by0, bx1, by1 = bx0 - pad, by0 - pad, bx1 + pad, by1 + pad
    kc = ANCHO / (bx1 - bx0)
    caja = box(bx0, by0, bx1, by1)
    conu = {}
    for r in g.itertuples():
        if r.geometry.intersects(caja):
            conu[r.cod_indec] = _path(r.geometry.intersection(caja).simplify(90), bx0, by1, kc)
    meta |= {"conu_w": ANCHO, "conu_h": round((by1 - by0) * kc)}
    return prov, conu, meta


if __name__ == "__main__":
    prov, conu, meta = paths()
    print(meta, "provincia:", sum(len(v) for v in prov.values()), "caracteres;", "recuadro:",
          sum(len(v) for v in conu.values()), "caracteres en", len(conu), "municipios")
