# -*- coding: utf-8 -*-
"""
ETL 04 · Inventario completo de los catálogos de datos abiertos (CKAN) que tocan a PBA.

    python 02_SCRIPTS/etl/04_inventario_catalogos.py

Qué contesta: «¿qué hay publicado que no tengamos?». Recorre cada catálogo entero y deja
`01_DATOS/inventario_catalogos.csv`, una fila por recurso (archivo), con el catálogo, el
dataset, el organismo, el formato, la URL y tres marcas para priorizar:
- `escala_municipal`: el título o la descripción habla de municipio / partido / departamento
- `censal`: censo, NBI, radio censal, hogares, viviendas
- `geo`: formato geográfico (shp, geojson, kml, gpkg, wfs)
Y `01_DATOS/inventario_catalogos_resumen.csv` con el conteo por catálogo y marca.

Catálogos:
- `catalogo.datos.gba.gob.ar` · Gobierno de la Provincia (todos los datasets)
- `datos.estadistica.ec.gba.gov.ar` · Dirección Provincial de Estadística (todos)
- `datos.gob.ar` · Nación, **filtrado** a lo que menciona Buenos Aires, municipio,
  departamento, radio censal, censo o elecciones (el catálogo entero son miles de datasets)

Qué supone: la API CKAN v3 (`package_search`) responde sin clave. Se pagina de a 100.

Qué no puede afirmar: que un dataset sirva. Las marcas son por palabra clave: separan el
grano de la paja, no reemplazan abrirlo. Lo que no está en un CKAN (portales ArcGIS, REDATAM
del INDEC, IGN) se relevó a mano en `01_DATOS/RELEVAMIENTO.md`.
"""
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
OUT = RAIZ / "01_DATOS"

CATALOGOS = {
    "gba": ("https://catalogo.datos.gba.gob.ar", "*:*"),
    "estadistica_pba": ("https://datos.estadistica.ec.gba.gov.ar", "*:*"),
    # En Nación se buscan varias consultas y se deduplica por dataset.
    "nacion": ("https://datos.gob.ar", [
        "buenos aires", "municipio", "municipios", "departamento", "departamentos", "radio censal",
        "censo", "elecciones", "electoral", "localidades", "establecimientos", "transferencias",
    ]),
}
RE_MUNI = re.compile(r"municip|partido|departament|\bpor localidad", re.I)
RE_CENSO = re.compile(r"censo|censal|\bnbi\b|necesidades b[aá]sicas|hogares|viviendas", re.I)
GEO = {"SHP", "SHAPEFILE", "GEOJSON", "KML", "KMZ", "GPKG", "WFS", "WMS", "ZIP-SHP"}


def ckan(base: str, accion: str, **params):
    url = f"{base}/api/3/action/{accion}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Atlas PBA)"})
    for intento in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)["result"]
        except Exception:  # noqa: BLE001 — reintento simple ante cortes del portal
            if intento == 2:
                raise
            time.sleep(3)


def buscar(base: str, q: str):
    inicio, filas = 0, 100
    while True:
        res = ckan(base, "package_search", q=q, rows=filas, start=inicio)
        yield from res["results"]
        inicio += filas
        if inicio >= res["count"]:
            break


def main() -> None:
    registros, vistos = [], set()
    for nombre, (base, consultas) in CATALOGOS.items():
        consultas = [consultas] if isinstance(consultas, str) else consultas
        n0 = len(registros)
        for q in consultas:
            for p in buscar(base, q):
                if (nombre, p["name"]) in vistos:
                    continue
                vistos.add((nombre, p["name"]))
                texto = " ".join([p.get("title") or "", p.get("notes") or "",
                                  " ".join(t["name"] for t in p.get("tags", []))])
                if nombre == "nacion" and not re.search(r"buenos aires|municip|departament|censo|censal|electoral|eleccion|localidad|radio", texto, re.I):
                    continue
                org = (p.get("organization") or {}).get("title")
                for r in p.get("resources", []) or [{}]:
                    fmt = (r.get("format") or "").upper().strip()
                    registros.append({
                        "catalogo": nombre, "dataset": p["name"], "titulo": p.get("title"),
                        "organismo": org, "modificado": (p.get("metadata_modified") or "")[:10],
                        "recurso": r.get("name"), "formato": fmt, "url": r.get("url"),
                        "escala_municipal": bool(RE_MUNI.search(texto + " " + (r.get("name") or ""))),
                        "censal": bool(RE_CENSO.search(texto)),
                        "geo": fmt in GEO or bool(re.search(r"\.(shp|geojson|kml|gpkg)\b", r.get("url") or "", re.I)),
                        "descripcion": (p.get("notes") or "")[:300].replace("\n", " "),
                    })
        print(f"  {nombre}: {len({d for c, d in vistos if c == nombre})} datasets, {len(registros) - n0} recursos")

    df = pd.DataFrame(registros)
    df.to_csv(OUT / "inventario_catalogos.csv", index=False, encoding="utf-8")
    ds = df.drop_duplicates(["catalogo", "dataset"])
    res = ds.groupby("catalogo").agg(datasets=("dataset", "size"), escala_municipal=("escala_municipal", "sum"),
                                     censal=("censal", "sum"), geo=("geo", "sum"))
    res.to_csv(OUT / "inventario_catalogos_resumen.csv", encoding="utf-8")
    print(res.to_string())


if __name__ == "__main__":
    main()
