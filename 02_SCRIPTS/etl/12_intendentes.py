"""
12 · Intendentes electos en 2023 (mandato 2023-2027), con foto cuando hay una de licencia libre.

FUENTES
-------
- Lista: la tabla «Intendente electo» de «Elecciones provinciales de Buenos Aires de 2023» en
  Wikipedia en español (municipio, intendente, partido, alianza, reelecto). Se descarga el
  wikitexto con la API de MediaWiki.
- Fotos: la imagen principal del artículo de cada intendente que tiene artículo (API `pageimages`),
  con su licencia y autor (`imageinfo` / `extmetadata`). Sólo se guardan imágenes de Wikimedia
  Commons (licencias libres); las de uso legítimo de Wikipedia se descartan. Sin foto: iniciales.

LIMITACIÓN
----------
Es quién **ganó** en 2023. Si un intendente pidió licencia o renunció durante el mandato, la tabla
no lo refleja: hay que revisarlo a mano antes de un uso público.

Salidas
- 01_DATOS/processed/intendentes_2023.csv
- 01_DATOS/processed/fotos_intendentes/<cod_indec>.jpg  (200 px)
- 01_DATOS/raw/intendentes/elecciones_2023.json        (wikitexto descargado)
"""
from __future__ import annotations

import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
RAW = RAIZ / "01_DATOS" / "raw" / "intendentes"
PROC = RAIZ / "01_DATOS" / "processed"
FOTOS = PROC / "fotos_intendentes"
API = "https://es.wikipedia.org/w/api.php"
UA = {"User-Agent": "AtlasPBA/1.0 (investigacion electoral; github.com/licgermancardenas-crypto)"}
PAGINA = "Elecciones_provinciales_de_Buenos_Aires_de_2023"


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def api(**kw) -> dict:
    kw.update(format="json", formatversion=2)
    return json.loads(get(API + "?" + urllib.parse.urlencode(kw)))


def norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().upper()
    return re.sub(r"[^A-Z ]", " ", t).split() and " ".join(re.sub(r"[^A-Z ]", " ", t).split())


def limpiar(celda: str) -> tuple[str, str | None]:
    """'[[Mariano Cascallares]] <span>R</span>' -> ('Mariano Cascallares', 'Mariano Cascallares')."""
    link = None
    m = re.search(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", celda)
    if m:
        link = m.group(1).strip()
    txt = re.sub(r"<[^>]+>R?</span>|<[^>]+>", "", celda)
    txt = re.sub(r"\[\[(?:[^\]|]+\|)?([^\]]+)\]\]", r"\1", txt)
    txt = re.sub(r"\{\{[^}]*\}\}|'''?", "", txt)
    return re.sub(r"\s+", " ", txt).strip(), link


def tabla() -> pd.DataFrame:
    RAW.mkdir(parents=True, exist_ok=True)
    f = RAW / "elecciones_2023.json"
    if not f.exists():
        f.write_bytes(get(API + "?" + urllib.parse.urlencode(
            {"action": "parse", "page": PAGINA, "prop": "wikitext", "format": "json", "formatversion": 2})))
    t = json.loads(f.read_text(encoding="utf-8"))["parse"]["wikitext"]
    ini = t.index("! Intendente electo")
    fin = t.index("|}", ini)
    filas = []
    for bloque in t[ini:fin].split("\n|-")[1:]:
        celdas = [c[1:] if c.startswith("|") else c for c in bloque.strip().split("\n") if c.startswith("|")]
        if len(celdas) < 6:
            continue
        muni, _ = limpiar(celdas[0])
        nombre, link = limpiar(celdas[1])
        partido, _ = limpiar(celdas[3])
        alianza, _ = limpiar(celdas[5])
        filas.append({"municipio_wiki": muni, "intendente": nombre, "articulo": link,
                      "reelecto": "color:#008000\">R" in celdas[1] or ">R</span>" in celdas[1],
                      "partido": partido, "alianza": alianza})
    return pd.DataFrame(filas)


ALIANZA = {"UP": "Unión por la Patria", "JxC": "Juntos por el Cambio"}
BLOQUE = {"Unión por la Patria": "PERONISMO", "Juntos por el Cambio": "JXC"}
# Nombres de Wikipedia que no coinciden con los del proyecto después de normalizar.
ALIAS = {"CORONEL DE MARINA L ROSALES": "CORONEL ROSALES", "GENERAL JUAN MADARIAGA": "GENERAL MADARIAGA",
         "LEANDRO N ALEM": "LEANDRO N ALEM", "JOSE C PAZ": "JOSE C PAZ"}


def fotos(df: pd.DataFrame) -> pd.DataFrame:
    FOTOS.mkdir(parents=True, exist_ok=True)
    titulos = [a for a in df.articulo.dropna().unique()]
    img = {}
    for i in range(0, len(titulos), 40):
        r = api(action="query", prop="pageimages", piprop="name|thumbnail", pithumbsize=240,
                titles="|".join(titulos[i:i + 40]), redirects=1)
        red = {x["from"]: x["to"] for x in r["query"].get("redirects", [])}
        norm_t = {x["from"]: x["to"] for x in r["query"].get("normalized", [])}
        por = {p["title"]: p for p in r["query"]["pages"]}
        for tt in titulos[i:i + 40]:
            k = red.get(norm_t.get(tt, tt), norm_t.get(tt, tt))
            p = por.get(k, {})
            if "pageimage" in p and "thumbnail" in p:
                img[tt] = (p["pageimage"], p["thumbnail"]["source"])
        time.sleep(0.5)
    # Licencia: sólo Commons (las de uso legítimo viven en es.wikipedia y no tienen licencia libre).
    info = {}
    nombres = list({v[0] for v in img.values()})
    for i in range(0, len(nombres), 40):
        r = api(action="query", prop="imageinfo", iiprop="extmetadata|url",
                titles="|".join("File:" + n for n in nombres[i:i + 40]))
        for p in r["query"]["pages"]:
            ii = (p.get("imageinfo") or [{}])[0]
            md = ii.get("extmetadata", {})
            info[p["title"].split(":", 1)[1].replace(" ", "_")] = {
                "repo": p.get("imagerepository"),
                "licencia": md.get("LicenseShortName", {}).get("value"),
                "autor": re.sub("<[^>]+>", "", md.get("Artist", {}).get("value", "")).strip(),
                "pagina_foto": ii.get("descriptionurl")}
        time.sleep(0.5)
    out = []
    for _, r in df.iterrows():
        d = {"foto": None, "foto_licencia": None, "foto_autor": None, "foto_fuente": None}
        if r.articulo in img:
            nombre, url = img[r.articulo]
            meta = info.get(nombre.replace(" ", "_"), {})
            if meta.get("repo") == "shared" and meta.get("licencia"):
                destino = FOTOS / f"{r.cod_indec}.jpg"
                if not destino.exists():
                    destino.write_bytes(get(url))
                    time.sleep(0.3)
                d = {"foto": f"fotos_intendentes/{r.cod_indec}.jpg", "foto_licencia": meta["licencia"],
                     "foto_autor": meta["autor"][:120], "foto_fuente": meta["pagina_foto"]}
        out.append(d)
    return pd.concat([df.reset_index(drop=True), pd.DataFrame(out)], axis=1)


def main() -> None:
    df = tabla()
    claves = pd.read_csv(PROC / "municipios_claves.csv", dtype=str)
    claves["k"] = claves.municipio_nombre.map(norm)
    df["municipio_wiki"] = df.municipio_wiki.str.replace(r"\s*\(ver detalle\)", "", regex=True)         .str.replace(r"^Partido de ", "", regex=True)
    df["k"] = df.municipio_wiki.map(norm).replace(ALIAS)
    df = df.merge(claves[["k", "cod_indec", "municipio_nombre", "seccion_electoral"]], on="k", how="left")
    sin = df[df.cod_indec.isna()]
    if len(sin):
        print("sin cruce:", sin.municipio_wiki.tolist())
    df = df.dropna(subset=["cod_indec"])
    df["alianza"] = df.alianza.replace(ALIANZA)
    df["bloque"] = df.alianza.map(BLOQUE).fillna("VECINAL")
    df["wikipedia"] = df.articulo.map(lambda a: None if pd.isna(a) else
                                      "https://es.wikipedia.org/wiki/" + urllib.parse.quote(a.replace(" ", "_")))
    df = fotos(df)
    cols = ["cod_indec", "municipio_nombre", "seccion_electoral", "intendente", "reelecto", "partido", "alianza",
            "bloque", "wikipedia", "foto", "foto_licencia", "foto_autor", "foto_fuente"]
    df[cols].sort_values("cod_indec").to_csv(PROC / "intendentes_2023.csv", index=False, encoding="utf-8")
    print(f"{len(df)} intendentes · {df.cod_indec.nunique()} municipios · con foto libre: {df.foto.notna().sum()}")
    print(df.alianza.value_counts().to_string())


if __name__ == "__main__":
    main()


# ----------------------------------------------------------------------------- logos de partidos
# Archivos de los cuadros de resultados de las elecciones 2023 y 2025 en Wikipedia. Se guardan sólo
# los de Wikimedia Commons (licencia libre o por debajo del umbral de originalidad), para
# identificar a cada fuerza en tableros: no se usan como marca propia.
LOGOS = {"PERONISMO": "Logo de \"Fuerza Patria\".jpg", "PERONISMO_2023": "Unión por la Patria logo completo.png",
         "LLA": "Logo La Libertad Avanza (sin águila).svg", "JXC": "Juntos-Por-El-Cambio-Logo.svg",
         "IZQUIERDA": "Logo Frente de Izquierda y de Trabajadores-Unidad.svg",
         "TERCERA": "Logo Somos Buenos Aires.jpg"}


def logos() -> pd.DataFrame:
    dest = PROC / "logos_partidos"
    dest.mkdir(parents=True, exist_ok=True)
    r = api(action="query", prop="imageinfo", iiprop="extmetadata|url", iiurlwidth=200,
            titles="|".join("File:" + v for v in LOGOS.values()))
    por = {p["title"].split(":", 1)[1]: p for p in r["query"]["pages"]}
    filas = []
    for k, v in LOGOS.items():
        p = por.get(v.replace("_", " "), {})
        ii = (p.get("imageinfo") or [{}])[0]
        md = ii.get("extmetadata", {})
        fila = {"bloque": k, "archivo": v, "repo": p.get("imagerepository"),
                "licencia": md.get("LicenseShortName", {}).get("value"), "fuente": ii.get("descriptionurl"), "logo": None}
        if fila["repo"] == "shared" and ii.get("thumburl"):
            f = dest / f"{k}.png"
            if not f.exists():
                f.write_bytes(get(ii["thumburl"]))
            fila["logo"] = f"logos_partidos/{k}.png"
        filas.append(fila)
    t = pd.DataFrame(filas)
    t.to_csv(PROC / "logos_partidos.csv", index=False, encoding="utf-8")
    print(t[["bloque", "repo", "licencia", "logo"]].to_string(index=False))
    return t


if __name__ == "__main__" and "--logos" in __import__("sys").argv:
    logos()
