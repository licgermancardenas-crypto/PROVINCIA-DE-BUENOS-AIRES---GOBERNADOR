# -*- coding: utf-8 -*-
"""
ETL 03 · MunicipiosArgentinos.net -> indicadores fiscales, de servicios y de control por municipio.

    python 02_SCRIPTS/etl/03_municipios_argentinos.py           # usa la foto de raw/ si existe
    python 02_SCRIPTS/etl/03_municipios_argentinos.py --bajar   # saca una foto nueva del sitio

Qué contesta: para los 135 municipios de PBA, ~50 indicadores en una sola tabla con el código
INDEC del partido (`cod`, 5 dígitos): población 2022 y 2026, servicios del censo 2022 (agua,
cloaca, gas, NBI), transferencias de la Provincia 2025 (coparticipación, Fondo Educativo),
gasto devengado 2025 (personal, Concejo, bienes de uso, publicidad), deuda, resultado
financiero, fallos del Tribunal de Cuentas, transparencia (ASAP y relevamiento propio), delito
(SNIC, trienio), mortalidad infantil, y el intendente en ejercicio con su espacio político.

Qué supone:
- El sitio publica sus datos en archivos JS estáticos (`js/data-*.js`, `js/fuentes.js`,
  `js/intendentes.js`); su robots.txt permite todo salvo /admin/ y /api/, que no se tocan.
- Cada valor viene como [valor, período, id_fuente]. Se guarda el período al lado de cada
  valor: **no todos los municipios tienen el mismo año** (empleo municipal va de 2022 a 2026).

Qué no puede afirmar:
- Es una **fuente secundaria**: compila datos oficiales (RAFAM/Ministerio de Economía PBA,
  Tribunal de Cuentas, INDEC, SNIC, DEIS) pero la compilación es de un tercero. Antes de
  publicar un hallazgo que dependa de uno de estos indicadores, se contrasta contra la fuente
  primaria que cita (`municipios_ma_fuentes.csv` la trae con URL).
- El «índice» y el «semáforo» son construcciones del sitio, con sus pesos. Se guardan, pero no
  se usan como variable explicativa sin desarmarlos en sus componentes.
- El espacio político del intendente sale en buena parte de prensa local (fuente no oficial).
"""
import json
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
RAW = RAIZ / "01_DATOS" / "raw" / "social" / "municipiosargentinos"
OUT = RAIZ / "01_DATOS" / "processed"
BASE = "https://municipiosargentinos.net/"
ARCHIVOS = [f"js/data-{i}.js" for i in range(7)] + ["js/fuentes.js", "js/intendentes.js"]


def bajar() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    for a in ARCHIVOS:
        req = urllib.request.Request(BASE + a, headers={"User-Agent": "Mozilla/5.0 (Atlas PBA)"})
        with urllib.request.urlopen(req, timeout=120) as r:
            (RAW / Path(a).name).write_bytes(r.read())
    (RAW / "FOTO.txt").write_text(f"bajado {date.today().isoformat()} de {BASE}\n", encoding="utf-8")


def json_de_js(nombre: str):
    s = (RAW / nombre).read_text(encoding="utf-8")
    m = re.search(r'JSON\.parse\((".*")\)', s, re.S)
    return json.loads(json.loads(m.group(1)))


def main() -> None:
    if "--bajar" in sys.argv or not (RAW / "data-0.js").exists():
        bajar()

    cab = json_de_js("data-0.js")
    muni = list(cab["list"])
    for i in range(1, 7):
        muni += json_de_js(f"data-{i}.js")
    fuentes = json_de_js("fuentes.js")
    intend = json_de_js("intendentes.js")
    meta = cab["meta"]

    filas = []
    for m in muni:
        f = {"cod_indec": m["cod"], "slug": m["id"], "municipio": m["nombre"],
             "seccion_electoral": m.get("sec"), "region": m.get("region"), "grupo_ma": m.get("grupo")}
        for k, v in m.get("d", {}).items():
            f[k] = v[0]
            f[f"{k}__periodo"] = v[1]
            f[f"{k}__fuente"] = json.dumps(v[2]) if len(v) > 2 else None
        ix = m.get("ix") or {}
        for k in ("v", "T", "R", "C", "sem"):
            if k in ix:
                f[f"ma_indice_{k}"] = ix[k]
        for k, v in (ix.get("rv") or {}).items():  # valores crudos de servicios/seguridad
            f[k] = v[0]
            f[f"{k}__periodo"] = v[1]
        it = intend.get(m["id"], {})
        f.update({"intendente": it.get("nombre"), "intendente_espacio": it.get("espacio"),
                  "intendente_partido": it.get("partido"), "intendente_situacion": it.get("situacion"),
                  "intendente_desde": it.get("desde")})
        filas.append(f)

    df = pd.DataFrame(filas).sort_values("cod_indec")
    assert len(df) == 135, f"esperaba 135 municipios, hay {len(df)}"
    assert df["cod_indec"].str.match(r"^06\d{3}$").all()

    dicc = pd.DataFrame([{"variable": k, "nombre": v[0], "unidad": v[1], "formula": v[2]} for k, v in meta.items()])
    fu = pd.DataFrame(fuentes, columns=["organismo", "titulo", "url", "consultado", "oficial"])
    fu.insert(0, "id_fuente", range(len(fu)))

    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / "municipios_ma.csv", index=False, encoding="utf-8")
    dicc.to_csv(OUT / "municipios_ma_diccionario.csv", index=False, encoding="utf-8")
    fu.to_csv(OUT / "municipios_ma_fuentes.csv", index=False, encoding="utf-8")
    print(f"municipios_ma.csv: {df.shape[0]} municipios x {df.shape[1]} columnas "
          f"(datos actualizados {cab.get('actualizado')}) · {len(fu)} fuentes · "
          f"{(fu.oficial == 1).mean():.0%} oficiales")


if __name__ == "__main__":
    main()
