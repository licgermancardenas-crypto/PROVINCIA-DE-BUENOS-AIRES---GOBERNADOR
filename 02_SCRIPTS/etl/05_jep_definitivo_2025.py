# -*- coding: utf-8 -*-
"""
ETL 05 · Escrutinio definitivo de la provincial desdoblada del 7-09-2025, por municipio.

    python 02_SCRIPTS/etl/05_jep_definitivo_2025.py           # usa las páginas de raw/ si están
    python 02_SCRIPTS/etl/05_jep_definitivo_2025.py --bajar   # las vuelve a bajar

Qué contesta: votos por lista y municipio en la categoría legislativa provincial (Diputados o
Senadores, según la sección: se renueva una cámara por sección) y Concejales, con electores,
mesas y blancos. Deja `01_DATOS/processed/jep_2025_municipio.csv` (largo: municipio × categoría
× lista) y `jep_2025_municipio_resumen.csv` (una fila por municipio).

Qué supone: las páginas `distrito_NNN.html` de juntaelectoral.gba.gov.ar tienen una sola tabla
con columnas lista | partido | categoría legislativa | % | Concejales | %. El número de distrito
de la Junta (001-135) es el mismo `seccion_id` que usa la DINE (Adolfo Alsina = 1,
Gonzales Chaves = 56): se verifica contra `municipios_claves.csv`.

Qué no puede afirmar: nada por debajo del municipio. El portal con el provisorio mesa a mesa
(resultados.eleccionesbonaerenses.gba.gob.ar) se dio de baja después de la elección. Y el padrón
de esta elección **incluye extranjeros**: la participación no se compara con la de octubre.
"""
import html
import re
import sys
import urllib.request
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
RAW = RAIZ / "01_DATOS" / "raw" / "electoral" / "jep2025"
OUT = RAIZ / "01_DATOS" / "processed"
BASE = "https://www.juntaelectoral.gba.gov.ar/escrutinio-definitivo-2025/"


def num(s: str):
    s = s.strip()
    return None if s in ("-", "") else int(s.replace(".", ""))


def texto(s: str) -> list[str]:
    s = re.sub(r"<script.*?</script>|<style.*?</style>", "", s, flags=re.S)
    celdas = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", s, flags=re.S)
    return [html.unescape(re.sub(r"<[^>]+>", " ", c)).strip() for c in celdas]


def leer(n: int) -> tuple[dict, list[dict]]:
    p = RAW / f"distrito_{n:03d}.html"
    s = p.read_bytes().decode("utf-8", errors="replace")
    plano = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " | ", s)))
    def campo(etq):
        m = re.search(etq + r"\s*\|[\s|]*([\d.]+)", plano)
        return num(m.group(1)) if m else None
    nombre = re.search(r"Distrito\s*\|[\s|]*(\d{3}) - ([^|]+)", plano)
    cats = re.findall(r"(Diputados Prov\. Tit\.|Senadores Prov\. Tit\.)", plano)
    cat_leg = "SENADORES PROVINCIALES" if cats and cats[0].startswith("Senad") else "DIPUTADOS PROVINCIALES"
    cab = {"distrito_jep": n, "nombre_jep": nombre.group(2).strip() if nombre else None,
           "electores": campo("Electores habilitados"), "mesas": campo("Total de mesas"),
           "mesas_escrutadas": campo("Mesas escrutadas"), "categoria_legislativa": cat_leg}
    filas = []
    c = texto(s)
    for i in range(len(c) - 5):
        # número de lista: 2200 las alianzas, pero hay partidos locales de dos cifras (91 en San Nicolás)
        if re.fullmatch(r"\d{1,4}", c[i]) and re.search(r"[A-Z]{3}", c[i + 1]):
            for cat, v in ((cat_leg, c[i + 2]), ("CONCEJALES", c[i + 4])):
                if num(v) is not None:
                    filas.append({"distrito_jep": n, "categoria": cat, "lista": c[i], "agrupacion": c[i + 1],
                                  "votos": num(v)})
    # Filas de totales: «ETIQUETA | votos | % | votos | %». Concejales puede faltar (no en todos
    # los distritos hay, p. ej. si no se renueva el Concejo... en 2025 sí en los 135).
    # Un conteo se escribe con punto de miles («7.931»); un porcentaje, con dos decimales
    # («93.64», a veces con el «%» en otra celda): la forma los separa.
    conteo = re.compile(r"\d{1,3}(\.\d{3})*")
    for etq, tipo in (("VOTOS POSITIVOS", "positivos"), ("VOTO EN BLANCO", "blanco"), ("Total de votos", "total")):
        vals = []
        if etq in c:
            for x in c[c.index(etq) + 1:c.index(etq) + 8]:
                if conteo.fullmatch(x):
                    vals.append(num(x))
        cab[f"{tipo}_leg"] = vals[0] if vals else None
        cab[f"{tipo}_concejales"] = vals[1] if len(vals) > 1 else None
    return cab, filas


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    for n in range(1, 136):
        p = RAW / f"distrito_{n:03d}.html"
        if "--bajar" in sys.argv or not p.exists():
            req = urllib.request.Request(f"{BASE}distrito_{n:03d}.html", headers={"User-Agent": "Mozilla/5.0 (Atlas PBA)"})
            with urllib.request.urlopen(req, timeout=120) as r:
                p.write_bytes(r.read())
    cabs, filas = zip(*(leer(n) for n in range(1, 136)))
    res = pd.DataFrame(cabs)
    largo = pd.DataFrame([f for fs in filas for f in fs])

    claves = OUT / "municipios_claves.csv"
    if claves.exists():
        k = pd.read_csv(claves, dtype={"cod_indec": str})
        res = res.merge(k[["cod_indec", "municipio_nombre", "seccion_electoral", "seccion_id_dine"]],
                        left_on="distrito_jep", right_on="seccion_id_dine", how="left")
        print(f"  {res.cod_indec.notna().sum()} de 135 distritos con código INDEC vía seccion_id DINE")

    # control: la suma de listas tiene que dar los positivos de la página
    leg = largo[largo.categoria != "CONCEJALES"].groupby("distrito_jep").votos.sum()
    con = largo[largo.categoria == "CONCEJALES"].groupby("distrito_jep").votos.sum()
    r = res.set_index("distrito_jep")
    ok_leg = (leg - r["positivos_leg"]).abs().eq(0).sum()
    ok_con = (con - r["positivos_concejales"]).abs().eq(0).sum()
    print(f"  control: positivos legislativos cierran al voto en {ok_leg} de 135; concejales en {ok_con} de {len(con)}")

    largo.to_csv(OUT / "jep_2025_municipio.csv", index=False, encoding="utf-8")
    res.to_csv(OUT / "jep_2025_municipio_resumen.csv", index=False, encoding="utf-8")
    tot = largo[largo.categoria != "CONCEJALES"].groupby("agrupacion").votos.sum().sort_values(ascending=False)
    print(f"  electores {res.electores.sum():,} · mesas {res.mesas.sum():,} · "
          f"votos legislativos {res.total_leg.sum():,} ({res.total_leg.sum() / res.electores.sum():.2%})")
    print((tot / tot.sum() * 100).round(2).head(6).to_string())


if __name__ == "__main__":
    main()
