"""
p06 · Proyecto de Power BI Desktop (PBIP) del tablero electoral de la Provincia.

Genera, a partir de las tablas de `p04` (03_OUTPUTS/powerbi/datos/):

  03_OUTPUTS/powerbi/
    Atlas_PBA.pbip                    <- se abre con Power BI Desktop
    Atlas_PBA.SemanticModel/          <- modelo en TMDL: tablas (Power Query sobre los CSV),
                                         relaciones y medidas DAX
    Atlas_PBA.Report/                 <- reporte en PBIR: 4 páginas, tema Atlas Analytics
    datos/                            <- CSV enriquecidos + pba_municipios.topojson (mapa de formas)
    LEEME_POWERBI.md

Cada JSON del reporte se valida contra los esquemas públicos de Microsoft (definición PBIR). El
modelo TMDL no tiene validador público: se escribe con la sintaxis documentada y conviene abrirlo
una vez en Desktop para confirmarlo.

Uso: python p06_powerbi.py [--esquemas <carpeta con indice.json de esquemas PBIR>]
"""
from __future__ import annotations

import json
import shutil
import sys
import uuid
from pathlib import Path
from urllib.parse import unquote

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
PBI = RAIZ / "03_OUTPUTS" / "powerbi"
DATOS = PBI / "datos"
PROC = RAIZ / "01_DATOS" / "processed"
NOMBRE = "Atlas_PBA"
SIMULADOR = "https://claude.ai/artifact/3HHPCqam3Q8GVwhqM8xeRo"
TABLERO_WEB = "https://claude.ai/artifact/VJCzzRwMbPm95QyWSaX3c9"
REPO = "https://github.com/licgermancardenas-crypto/PROVINCIA-DE-BUENOS-AIRES---GOBERNADOR"
MAPA = "pba_municipios.json"  # TopoJSON incrustado en el reporte como recurso ShapeMap
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"

COLOR_ESPACIO = {"PERONISMO": "#29A3F0", "LLA": "#9B4DFF", "LLA_PRO": "#7E57FF", "PRO_JXC": "#F5C518",
                 "CENTRO_UCR": "#E94F4F", "TERCERA_VIA": "#FF6FB5", "IZQUIERDA": "#C2185B", "VECINAL": "#2FC4A6",
                 "OTROS": "#8D86A6"}
FUERZAS = [("Fuerza Patria", "#29A3F0"), ("Somos / Provincias Unidas", "#FF6FB5"), ("La Libertad Avanza", "#9B4DFF"),
           ("Vecinalismo", "#2FC4A6"), ("PRO", "#F5C518"), ("UCR", "#E94F4F"), ("Otros", "#8D86A6")]
RANGOS_P = [("Peronismo seguro (90 % o más)", "#29A3F0"), ("Peronismo probable (60-90 %)", "#2178B8"),
            ("En disputa (40-60 %)", "#C40BFF"), ("Derecha probable (10-40 %)", "#5B3FA8"),
            ("Derecha segura (menos de 10 %)", "#7E57FF")]


def fuerza(e: str) -> str:
    if not isinstance(e, str):
        return "Otros"
    return ("Fuerza Patria" if e.startswith("Fuerza Patria") else "Somos / Provincias Unidas" if e.startswith("Somos")
            else "La Libertad Avanza" if e.startswith("La Libertad") else "PRO" if e == "PRO" else "UCR" if e == "UCR"
            else "Vecinalismo" if e.startswith("Vecinal") else "Otros")


def filepath(url) -> str | None:
    """Página de Commons -> URL directa de la imagen (Special:FilePath), 300 px."""
    if not isinstance(url, str) or "/File:" not in url:
        return None
    return "https://commons.wikimedia.org/wiki/Special:FilePath/" + url.split("/File:", 1)[1] + "?width=300"


# =============================================================================== 1 · datos
def preparar_datos() -> dict[str, pd.DataFrame]:
    m = pd.read_csv(DATOS / "_base_municipio.csv", dtype={"cod_indec": str, "seccion_electoral": str})
    sec_nom = {"1": "1ª", "2": "2ª", "3": "3ª", "4": "4ª", "5": "5ª", "6": "6ª", "7": "7ª", "8": "8ª Capital"}
    logos = pd.read_csv(PROC / "logos_partidos.csv")
    logo = {r.bloque: filepath(r.fuente) for r in logos.itertuples()}
    logo_fz = {"Fuerza Patria": logo.get("PERONISMO"), "Somos / Provincias Unidas": logo.get("TERCERA"),
               "La Libertad Avanza": logo.get("LLA"), "PRO": logo.get("JXC")}
    d = pd.DataFrame({
        "cod_indec": m.cod_indec, "municipio": m.municipio_nombre,
        "seccion": m.seccion_electoral.map(sec_nom), "seccion_num": m.seccion_electoral.astype(int),
        "zona": m.conurbano.map({True: "Conurbano", False: "Interior"}), "region": m.region,
        "pob": m.pob, "pob26": m.pob26, "km2": m.km2, "dens": m.dens, "hogares": m.hogares,
        "agua": m.agua, "cloaca": m.cloaca, "gas": m.gas, "nbi": m.nbi, "pct_univ": m.pct_univ, "pct_65": m.pct_65,
        "pct_18_29": m.pct_18_29, "pct_extranjeros": m.pct_extranjeros, "pct_internet": m.pct_internet,
        "pct_sin_obra_social": m.pct_sin_obra_social, "pct_barrio_popular": m.pct_barrio_popular,
        "barrios_populares": m.barrios_populares, "escuelas": m.escuelas, "matricula": m.matricula,
        "centros_salud": m.salud, "caps": m.salud_sin_internacion,
        "transferencias_hab": m.trh, "gasto_hab": m.gph, "transparencia_asap": m.asap, "semaforo": m.tsem,
        "tasa_homicidios": m.tasa_homicidios_dolosos_prom3, "mortalidad_infantil": m.tasa_mortalidad_infantil_trienio,
        "intendente": m.intendente, "intendente_espacio": m.intendente_espacio,
        "fuerza_intendente": m.intendente_espacio.map(fuerza), "intendente_partido": m.intendente_partido,
        "intendente_situacion": m.intendente_situacion, "intendente_desde": m.intendente_desde,
        "electo_2023": m.electo_intendente, "electo_partido_2023": m.electo_partido, "electo_alianza_2023": m.electo_alianza,
        "reelecto_2023": m.electo_reelecto.fillna(False).astype(bool),
        "foto_url": m.electo_foto_fuente.map(filepath),
        "foto_credito": (m.electo_foto_autor.fillna("") + " · " + m.electo_foto_licencia.fillna("")).where(m.electo_foto_fuente.notna()),
        "wikipedia_url": m.electo_wikipedia.where(m.misma_persona),
        "ubicacion": "Partido de " + m.municipio_nombre + ", Buenos Aires, Argentina",
        "simulador_url": SIMULADOR,
    })
    d["color_fuerza"] = d.fuerza_intendente.map(dict(FUERZAS))
    d["logo_url"] = d.fuerza_intendente.map(logo_fz)
    d["orden_fuerza"] = d.fuerza_intendente.map({f: i for i, (f, _) in enumerate(FUERZAS)})

    esp = pd.read_csv(DATOS / "dim_espacio.csv")
    esp["color"] = esp.espacio.map(COLOR_ESPACIO)
    esp["logo_url"] = esp.espacio.map({"PERONISMO": logo.get("PERONISMO"), "LLA": logo.get("LLA"), "LLA_PRO": logo.get("LLA"),
                                       "PRO_JXC": logo.get("JXC"), "TERCERA_VIA": logo.get("TERCERA"), "IZQUIERDA": logo.get("IZQUIERDA")})
    esp["orden"] = range(len(esp))

    el = pd.read_csv(DATOS / "dim_eleccion.csv")
    el["grupo"] = el.eleccion.str[0].map({"D": "Diputados nacionales", "S": "Legislativa provincial", "G": "Gobernador",
                                          "I": "Intendente", "P": "Presidente", "B": "Presidente"})
    corto = {"D": "Dip.", "S": "Prov.", "G": "Gob.", "I": "Int.", "P": "Pres.", "B": "Bal."}
    el["etiqueta"] = el.eleccion.str[0].map(corto) + " " + el.anio.astype(str)
    sub = {"G": 1, "I": 2, "P": 3, "B": 4, "S": 5, "D": 6}
    el["orden"] = el.anio * 10 + el.eleccion.str[0].map(sub)

    fv = pd.read_csv(DATOS / "fact_votos.csv", dtype={"cod_indec": str})
    fp = pd.read_csv(DATOS / "fact_participacion.csv", dtype={"cod_indec": str})
    fp["ganador_nombre"] = fp.ganador.map(dict(zip(esp.espacio, esp.espacio_nombre)))
    fm = pd.read_csv(DATOS / "fact_motor_2027.csv", dtype={"cod_indec": str})
    fm = fm[["escenario", "escenario_clave", "cod_indec", "pct_peronismo", "p_gana_peronismo"]].copy()
    fm["escenario"] = fm.escenario.str.replace(r"^[A-Z]\s*·\s*", "", regex=True)
    cortes = [(0.9, 0), (0.6, 1), (0.4, 2), (0.1, 3), (-1, 4)]
    fm["rango_p"] = fm.p_gana_peronismo.map(lambda p: RANGOS_P[next(i for c, i in cortes if p >= c)][0])
    fz = pd.DataFrame([{"fuerza_intendente": f, "color": c, "orden": i} for i, (f, c) in enumerate(FUERZAS)])
    return {"dim_municipio": d, "dim_espacio": esp, "dim_eleccion": el, "fact_votos": fv, "fact_participacion": fp,
            "fact_motor_2027": fm, "dim_fuerza": fz}


def topojson(dim: pd.DataFrame) -> None:
    """GeoJSON de municipios -> TopoJSON sin arcos compartidos (válido para el mapa de formas)."""
    gj = json.loads((DATOS / "municipios.geojson").read_text(encoding="utf-8"))
    m = dim.rename(columns={"municipio": "municipio_nombre"}).set_index("cod_indec")
    arcs, geoms = [], []
    for f in gj["features"]:
        g, cod = f["geometry"], f["properties"]["name"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        out = []
        for p in polys:
            rings = []
            for ring in p:
                arcs.append(ring)
                rings.append([len(arcs) - 1])
            out.append(rings)
        geoms.append({"type": "MultiPolygon", "id": cod, "arcs": out,
                      "properties": {"cod_indec": cod, "municipio": m.municipio_nombre.get(cod, cod)}})
    topo = {"type": "Topology", "objects": {"municipios": {"type": "GeometryCollection", "geometries": geoms}}, "arcs": arcs}
    (DATOS / "pba_municipios.topojson").write_text(json.dumps(topo, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


# =============================================================================== 2 · modelo TMDL
_tags: list = []


def tag() -> str:
    """lineageTag determinístico: el mismo objeto conserva su etiqueta entre corridas."""
    _tags.append(1)
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"atlas-pba/{len(_tags)}"))
TIPO = {"int64": ("int64", "Int64.Type"), "float64": ("double", "type number"), "bool": ("boolean", "type logical"),
        "object": ("string", "type text"), "str": ("string", "type text"), "string": ("string", "type text")}
CATEGORIA = {"foto_url": "ImageUrl", "logo_url": "ImageUrl", "wikipedia_url": "WebUrl", "simulador_url": "WebUrl",
             "ubicacion": "Place"}
SUMA = {"pob", "pob26", "km2", "hogares", "barrios_populares", "escuelas", "matricula", "centros_salud", "caps",
        "votos", "votos_positivos", "electores"}
FORMATO = {"double": "#,0.0", "int64": "#,0"}


def q(nombre: str) -> str:
    return f"'{nombre}'" if any(c in nombre for c in " .=:'%()-/·") else nombre


def tabla_tmdl(nombre: str, df: pd.DataFrame, ocultas: set[str] = frozenset(), orden: dict[str, str] | None = None) -> str:
    orden = orden or {}
    cols, tipos = [], []
    for c in df.columns:
        dt, mt = TIPO[str(df[c].dtype)] if str(df[c].dtype) in TIPO else ("string", "type text")
        tipos.append(f'{{"{c}", {mt}}}')
        lin = [f"\tcolumn {q(c)}", f"\t\tdataType: {dt}"]
        if dt in FORMATO and c not in ("seccion_num", "orden", "anio", "orden_fuerza"):
            lin.append(f"\t\tformatString: {FORMATO[dt]}")
        if c in CATEGORIA:
            lin.append(f"\t\tdataCategory: {CATEGORIA[c]}")
        if c in ocultas:
            lin.append("\t\tisHidden")
        lin.append(f"\t\tlineageTag: {tag()}")
        lin.append(f"\t\tsummarizeBy: {'sum' if c in SUMA else 'none'}")
        lin.append(f"\t\tsourceColumn: {c}")
        if c in orden:
            lin.append(f"\t\tsortByColumn: {orden[c]}")
        lin.append("")
        lin.append("\t\tannotation SummarizationSetBy = Automatic")
        cols.append("\n".join(lin))
    m = (f'\tpartition {q(nombre)} = m\n\t\tmode: import\n\t\tsource =\n'
         f'\t\t\t\tlet\n'
         f'\t\t\t\t    Origen = Csv.Document(File.Contents(CarpetaDatos & "{nombre}.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),\n'
         f'\t\t\t\t    Encabezados = Table.PromoteHeaders(Origen, [PromoteAllScalars=true]),\n'
         f'\t\t\t\t    Tipos = Table.TransformColumnTypes(Encabezados, {{{", ".join(tipos)}}}, "en-US")\n'
         f'\t\t\t\tin\n\t\t\t\t    Tipos\n')
    return f"table {q(nombre)}\n\tlineageTag: {tag()}\n\n" + "\n\n".join(cols) + "\n\n" + m + "\n\tannotation PBI_ResultType = Table\n"


MEDIDAS = [
    # (nombre, expresión DAX, formato, carpeta, categoría)
    ("Elección activa", 'SELECTEDVALUE ( dim_eleccion[eleccion], "D2025" )', None, "Elección", None),
    ("Elección seleccionada", 'SELECTEDVALUE ( dim_eleccion[rotulo], "Diputados nacionales 2025" )', None, "Elección", None),
    ("Votos", 'IF ( HASONEVALUE ( dim_eleccion[eleccion] ), SUM ( fact_votos[votos] ), CALCULATE ( SUM ( fact_votos[votos] ), dim_eleccion[eleccion] = "D2025" ) )', "#,0", "Votación", None),
    ("% Voto", "DIVIDE ( [Votos], CALCULATE ( [Votos], REMOVEFILTERS ( dim_espacio ) ) )", "0.0%", "Votación", None),
    ("% Peronismo", 'CALCULATE ( [% Voto], dim_espacio[espacio] = "PERONISMO" )', "0.0%", "Votación", None),
    ("% Derecha", 'CALCULATE ( [% Voto], dim_espacio[espacio] IN { "LLA", "LLA_PRO", "PRO_JXC" } )', "0.0%", "Votación", None),
    ("Ganador", 'VAR t = ADDCOLUMNS ( VALUES ( dim_espacio[espacio_nombre] ), "@v", [Votos] )\nRETURN MAXX ( TOPN ( 1, t, [@v], DESC ), dim_espacio[espacio_nombre] )', None, "Votación", None),
    ("% Ganador", 'MAXX ( VALUES ( dim_espacio[espacio] ), [% Voto] )', "0.0%", "Votación", None),
    ("Margen (pts)", 'VAR t = ADDCOLUMNS ( VALUES ( dim_espacio[espacio] ), "@p", [% Voto] )\nVAR p1 = MAXX ( t, [@p] )\nVAR p2 = MAXX ( FILTER ( t, [@p] < p1 ), [@p] )\nRETURN ( p1 - p2 ) * 100', "0.0", "Votación", None),
    ("Electores", 'IF ( HASONEVALUE ( dim_eleccion[eleccion] ), SUM ( fact_participacion[electores] ), CALCULATE ( SUM ( fact_participacion[electores] ), dim_eleccion[eleccion] = "D2025" ) )', "#,0", "Participación", None),
    ("Votantes", 'VAR v = SUMX ( fact_participacion, fact_participacion[electores] * fact_participacion[participacion] / 100 )\nRETURN IF ( HASONEVALUE ( dim_eleccion[eleccion] ), v, CALCULATE ( SUMX ( fact_participacion, fact_participacion[electores] * fact_participacion[participacion] / 100 ), dim_eleccion[eleccion] = "D2025" ) )', "#,0", "Participación", None),
    ("Participación", "DIVIDE ( [Votantes], [Electores] )", "0.0%", "Participación", None),
    ("Municipios", "DISTINCTCOUNT ( dim_municipio[cod_indec] )", "#,0", "Territorio", None),
    ("Población", "SUM ( dim_municipio[pob] )", "#,0", "Territorio", None),
    ("% de la Provincia", "DIVIDE ( [Población], CALCULATE ( [Población], REMOVEFILTERS ( dim_municipio ) ) )", "0.0%", "Territorio", None),
    ("Hogares con NBI %", "DIVIDE ( SUMX ( dim_municipio, dim_municipio[hogares] * dim_municipio[nbi] / 100 ), SUM ( dim_municipio[hogares] ) )", "0.0%", "Censo", None),
    ("Hogares en barrios populares %", "DIVIDE ( SUMX ( dim_municipio, dim_municipio[hogares] * dim_municipio[pct_barrio_popular] / 100 ), SUM ( dim_municipio[hogares] ) )", "0.0%", "Censo", None),
    ("Universitarios %", "DIVIDE ( SUMX ( dim_municipio, dim_municipio[pob] * dim_municipio[pct_univ] / 100 ), [Población] )", "0.0%", "Censo", None),
    ("Escuelas", "SUM ( dim_municipio[escuelas] )", "#,0", "Censo", None),
    ("Transferencias por habitante", "DIVIDE ( SUMX ( dim_municipio, dim_municipio[transferencias_hab] * dim_municipio[pob] ), [Población] )", "$ #,0", "Gestión", None),
    ("Intendente", 'SELECTEDVALUE ( dim_municipio[intendente], "Elegí un municipio" )', None, "Ficha", None),
    ("Municipio", 'SELECTEDVALUE ( dim_municipio[municipio], "Provincia de Buenos Aires" )', None, "Ficha", None),
    ("Foto intendente", "SELECTEDVALUE ( dim_municipio[foto_url] )", None, "Ficha", "ImageUrl"),
    ("Título ficha", '[Municipio] & IF ( HASONEVALUE ( dim_municipio[cod_indec] ), " · " & SELECTEDVALUE ( dim_municipio[fuerza_intendente] ), "" )', None, "Ficha", None),
    ("Título elección", '"Resultado · " & [Elección seleccionada]', None, "Elección", None),
    ("P(peronismo) 2027", "AVERAGE ( fact_motor_2027[p_gana_peronismo] )", "0%", "2027", None),
    ("Municipios peronistas esperados", "SUM ( fact_motor_2027[p_gana_peronismo] )", "#,0.0", "2027", None),
    ("Municipios en disputa", "COUNTROWS ( FILTER ( fact_motor_2027, fact_motor_2027[p_gana_peronismo] >= 0.2 && fact_motor_2027[p_gana_peronismo] <= 0.8 ) )", "#,0", "2027", None),
    ("Color fuerza", "SELECTEDVALUE ( dim_municipio[color_fuerza] )", None, "Formato", None),
    ("Color espacio", "SELECTEDVALUE ( dim_espacio[color] )", None, "Formato", None),
]


def medidas_tmdl() -> str:
    out = [f"table Medidas\n\tlineageTag: {tag()}\n"]
    for n, expr, fmt, carpeta, cat in MEDIDAS:
        if "\n" in expr:
            cuerpo = "\n".join("\t\t\t" + x for x in expr.split("\n"))
            s = f"\tmeasure {q(n)} =\n{cuerpo}\n"
        else:
            s = f"\tmeasure {q(n)} = {expr}\n"
        if fmt:
            s += f"\t\tformatString: {fmt}\n"
        if cat:
            s += f"\t\tdataCategory: {cat}\n"
        s += f"\t\tdisplayFolder: {carpeta}\n\t\tlineageTag: {tag()}\n"
        out.append(s)
    out.append(f"\tcolumn x\n\t\tdataType: string\n\t\tisHidden\n\t\tlineageTag: {tag()}\n\t\tsummarizeBy: none\n\t\tsourceColumn: x\n")
    out.append('\tpartition Medidas = m\n\t\tmode: import\n\t\tsource = #table(type table [x = text], {})\n')
    out.append("\tannotation PBI_ResultType = Table\n")
    return "\n".join(out)


RELACIONES = [("fact_votos", "cod_indec", "dim_municipio", "cod_indec"), ("fact_votos", "eleccion", "dim_eleccion", "eleccion"),
              ("fact_votos", "espacio", "dim_espacio", "espacio"), ("fact_participacion", "cod_indec", "dim_municipio", "cod_indec"),
              ("fact_participacion", "eleccion", "dim_eleccion", "eleccion"), ("fact_motor_2027", "cod_indec", "dim_municipio", "cod_indec"),
              ("dim_municipio", "fuerza_intendente", "dim_fuerza", "fuerza_intendente")]


def escribir_modelo(t: dict[str, pd.DataFrame]) -> None:
    sm = PBI / f"{NOMBRE}.SemanticModel"
    if sm.exists():
        shutil.rmtree(sm / "definition", ignore_errors=True)
    (sm / "definition" / "tables").mkdir(parents=True, exist_ok=True)
    (sm / "definition.pbism").write_text(json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
        "version": "4.0", "settings": {}}, indent=2), encoding="utf-8")
    d = sm / "definition"
    (d / "database.tmdl").write_text("database\n\tcompatibilityLevel: 1567\n", encoding="utf-8")
    nombres = list(t) + ["Medidas"]
    (d / "model.tmdl").write_text(
        "model Model\n\tculture: es-AR\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n\tsourceQueryCulture: es-AR\n"
        "\tdataAccessOptions\n\t\tlegacyRedirects\n\t\treturnErrorValuesAsNull\n\n"
        f"annotation PBI_QueryOrder = {json.dumps(['CarpetaDatos'] + nombres)}\n\n"
        "annotation __PBI_TimeIntelligenceEnabled = 0\n\n" + "\n".join(f"ref table {q(n)}" for n in nombres) + "\n",
        encoding="utf-8")
    carpeta = str(DATOS).rstrip("\\") + "\\"
    (d / "expressions.tmdl").write_text(
        f'expression CarpetaDatos = "{carpeta}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]\n'
        f"\tlineageTag: {tag()}\n\n\tannotation PBI_ResultType = Text\n", encoding="utf-8")
    ocultas = {"dim_municipio": {"orden_fuerza", "color_fuerza", "ubicacion", "simulador_url"},
               "dim_eleccion": {"orden"}, "dim_espacio": {"orden", "color"}, "dim_fuerza": {"orden", "color"},
               "fact_votos": {"cod_indec", "eleccion", "espacio"}, "fact_participacion": {"cod_indec", "eleccion"},
               "fact_motor_2027": {"cod_indec"}}
    orden = {"dim_eleccion": {"etiqueta": "orden", "rotulo": "orden"}, "dim_espacio": {"espacio_nombre": "orden"},
             "dim_fuerza": {"fuerza_intendente": "orden"}, "dim_municipio": {"seccion": "seccion_num", "fuerza_intendente": "orden_fuerza"}}
    for n, df in t.items():
        (d / "tables" / f"{n}.tmdl").write_text(tabla_tmdl(n, df, ocultas.get(n, set()), orden.get(n)), encoding="utf-8")
    (d / "tables" / "Medidas.tmdl").write_text(medidas_tmdl(), encoding="utf-8")
    rel = []
    for a, ca, b, cb in RELACIONES:
        rel.append(f"relationship {uuid.uuid5(uuid.NAMESPACE_URL, a + ca + b)}\n\tfromColumn: {a}.{ca}\n\ttoColumn: {b}.{cb}\n")
    (d / "relationships.tmdl").write_text("\n".join(rel), encoding="utf-8")


# =============================================================================== 3 · reporte PBIR
def lit(v) -> dict:
    if isinstance(v, bool):
        return {"expr": {"Literal": {"Value": "true" if v else "false"}}}
    if isinstance(v, (int, float)):
        return {"expr": {"Literal": {"Value": f"{v}D"}}}
    return {"expr": {"Literal": {"Value": "'" + str(v).replace("'", "''") + "'"}}}


def color(hexa: str) -> dict:
    return {"solid": {"color": lit(hexa)}}


def col(tabla: str, c: str) -> dict:
    return {"Column": {"Expression": {"SourceRef": {"Entity": tabla}}, "Property": c}}


def med(n: str) -> dict:
    return {"Measure": {"Expression": {"SourceRef": {"Entity": "Medidas"}}, "Property": n}}


def proj(campo: dict, nombre: str | None = None) -> dict:
    k = "Column" if "Column" in campo else "Measure"
    ent, prop = campo[k]["Expression"]["SourceRef"]["Entity"], campo[k]["Property"]
    p = {"field": campo, "queryRef": f"{ent}.{prop}", "nativeQueryRef": prop}
    if nombre:
        p["displayName"] = nombre
    return p


def titulo(texto: str | None, tam: int = 12) -> dict:
    o = {"title": [{"properties": {"show": lit(bool(texto))} | ({"text": lit(texto), "fontSize": lit(tam)} if texto else {})}]}
    return o


def colores_por(campo_col: dict, pares: list[tuple[str, str]]) -> list:
    return [{"properties": {"fill": color(c)},
             "selector": {"data": [{"scopeId": {"Comparison": {"ComparisonKind": 0, "Left": campo_col,
                                                                "Right": {"Literal": {"Value": "'" + v + "'"}}}}}]}}
            for v, c in pares]


class Pagina:
    def __init__(self, nombre: str, visible: str):
        self.nombre, self.visible, self.visuales, self.z, self.interacciones = nombre, visible, [], 1000, []

    def add(self, nombre, tipo, x, y, w, h, roles=None, objetos=None, contenedor=None, orden=None, extra=None):
        self.z += 10
        v = {"visualType": tipo}
        if roles:
            v["query"] = {"queryState": {r: {"projections": [proj(c, n) if isinstance(c, dict) else proj(*c) for c in (cs if isinstance(cs, list) else [cs]) for n in [None]]}
                                         for r, cs in roles.items()}}
            if orden:
                v["query"]["sortDefinition"] = {"sort": [{"field": orden[0], "direction": orden[1]}], "isDefaultSort": False}
        if objetos:
            v["objects"] = objetos
        v["visualContainerObjects"] = contenedor or {}
        if extra:
            v.update(extra)
        self.visuales.append({"$schema": f"{SCHEMA}/visualContainer/1.3.0/schema.json", "name": nombre,
                              "position": {"x": x, "y": y, "z": self.z, "width": w, "height": h, "tabOrder": self.z}, "visual": v})
        return nombre


def texto(p: Pagina, nombre, x, y, w, h, runs: list[tuple[str, dict]]):
    parrafos = [{"textRuns": [{"value": t, "textStyle": est} for t, est in fila]} for fila in runs]
    p.add(nombre, "textbox", x, y, w, h, objetos={"general": [{"properties": {"paragraphs": parrafos}}]},
          contenedor={"background": [{"properties": {"show": lit(False)}}], "border": [{"properties": {"show": lit(False)}}]})


def boton(p: Pagina, nombre, x, y, w, h, etiqueta, destino=None, url=None, activo=False):
    link = {"show": lit(True)}
    if destino:
        link |= {"type": lit("PageNavigation"), "navigationSection": lit(destino)}
    else:
        link |= {"type": lit("WebUrl"), "webUrl": lit(url)}
    fondo = "#C40BFF" if activo or url == SIMULADOR else "#1B0A3D"
    tinta = "#12042E" if activo or url == SIMULADOR else "#F2EBFA"
    p.add(nombre, "actionButton", x, y, w, h,
          objetos={"icon": [{"properties": {"show": lit(False)}}],
                   "text": [{"properties": {"show": lit(True), "text": lit(etiqueta), "fontColor": color(tinta), "fontSize": lit(11),
                                            "bold": lit(True)}, "selector": {"id": "default"}}],
                   "fill": [{"properties": {"show": lit(True), "fillColor": color(fondo), "transparency": lit(0)}, "selector": {"id": "default"}}],
                   "outline": [{"properties": {"show": lit(True), "lineColor": color("#3D2A63"), "roundEdge": lit(8)}, "selector": {"id": "default"}}]},
          contenedor={"visualLink": [{"properties": link}]})


PAGINAS = [("politico", "Territorio político"), ("elecciones", "Elecciones"), ("censo", "Censo y gestión"), ("escenarios", "Escenarios 2027")]


def encabezado(p: Pagina):
    texto(p, f"{p.nombre}_marca", 16, 8, 520, 50, [[("ATLAS ANALYTICS", {"fontSize": "9pt", "fontWeight": "bold", "color": "#C40BFF"})],
                                                   [("Provincia de Buenos Aires · " + p.visible, {"fontSize": "16pt", "fontWeight": "bold", "color": "#F2EBFA"})]])
    x = 560
    for clave, vis in PAGINAS:
        boton(p, f"{p.nombre}_nav_{clave}", x, 14, 130, 34, vis, destino=clave, activo=clave == p.nombre)
        x += 136
    boton(p, f"{p.nombre}_web_sim", 1110, 14, 154, 34, "Simulador 2027 ↗", url=SIMULADOR)


def slicer(p: Pagina, nombre, x, y, w, h, campo, tit, modo="Dropdown", unico=False):
    obj = {"data": [{"properties": {"mode": lit(modo)}}],
           "selection": [{"properties": {"strictSingleSelect": lit(unico), "selectAllCheckboxEnabled": lit(not unico)}}],
           "header": [{"properties": {"show": lit(True), "text": lit(tit), "fontColor": color("#A08FC2"), "textSize": lit(9)}}]}
    p.add(nombre, "slicer", x, y, w, h, roles={"Values": [campo]}, objetos=obj)


def filtros_comunes(p: Pagina, y0=70):
    slicer(p, f"{p.nombre}_s_muni", 12, y0, 220, 58, col("dim_municipio", "municipio"), "Municipio")
    slicer(p, f"{p.nombre}_s_sec", 12, y0 + 64, 220, 58, col("dim_municipio", "seccion"), "Sección electoral")
    slicer(p, f"{p.nombre}_s_zona", 12, y0 + 128, 220, 58, col("dim_municipio", "zona"), "Zona")
    slicer(p, f"{p.nombre}_s_fz", 12, y0 + 192, 220, 58, col("dim_fuerza", "fuerza_intendente"), "Fuerza del intendente")


def tarjeta(p: Pagina, nombre, x, y, w, h, medida, etiqueta, fmt_color="#F2EBFA"):
    p.add(nombre, "card", x, y, w, h, roles={"Values": [med(medida)]},
          objetos={"labels": [{"properties": {"color": color(fmt_color), "fontSize": lit(22)}}],
                   "categoryLabels": [{"properties": {"show": lit(True), "color": color("#A08FC2"), "fontSize": lit(9)}}]},
          contenedor=titulo(None) | {"background": [{"properties": {"show": lit(True), "color": color("#1B0A3D")}}]})
    p.visuales[-1]["visual"]["query"]["queryState"]["Values"]["projections"][0]["displayName"] = etiqueta


def mapa(p: Pagina, nombre, x, y, w, h, leyenda: dict, pares: list[tuple[str, str]], tit: str):
    p.add(nombre, "shapeMap", x, y, w, h,
          roles={"Category": [col("dim_municipio", "cod_indec")], "Series": [leyenda],
                 "Tooltips": [col("dim_municipio", "municipio"), col("dim_municipio", "intendente")]},
          objetos={"shape": [{"properties": {
                       "map": {"geoJson": {"type": lit("packaged"), "name": lit(MAPA),
                                           "content": {"expr": {"ResourcePackageItem": {"PackageName": "RegisteredResources",
                                                                                         "PackageType": 1, "ItemName": MAPA}}}}},
                       "projectionEnum": lit("mercator")}}],
                   "zoom": [{"properties": {"autoZoom": lit(True), "selectionZoom": lit(True), "manualZoom": lit(True)}}],
                   "dataPoint": colores_por(leyenda, pares),
                   "legend": [{"properties": {"show": lit(True), "position": lit("Bottom"), "labelColor": color("#DCD2EA")}}],
                   "defaultColors": [{"properties": {"defaultShow": lit(True), "defaultColor": color("#2A1D4A"),
                                                     "borderColor": color("#0E0324"), "borderThickness": lit(1)}}]},
          contenedor=titulo(tit))


def tabla_ficha(p: Pagina, nombre, x, y, w, h):
    p.add(nombre, "tableEx", x, y, w, h,
          roles={"Values": [col("dim_municipio", "foto_url"), col("dim_municipio", "municipio"), col("dim_municipio", "intendente"),
                            col("dim_municipio", "fuerza_intendente"), col("dim_municipio", "intendente_situacion"),
                            col("dim_municipio", "logo_url"), col("dim_municipio", "wikipedia_url")]},
          objetos={"values": [{"properties": {"fontColorPrimary": color("#F2EBFA"), "backColorPrimary": color("#1B0A3D"),
                                              "backColorSecondary": color("#220E4A"), "fontSize": lit(10)}}],
                   "columnHeaders": [{"properties": {"fontColor": color("#A08FC2"), "backColor": color("#12042E")}}],
                   "grid": [{"properties": {"imageHeight": lit(56), "rowPadding": lit(4), "gridHorizontalColor": color("#2E1A57")}}]},
          contenedor=titulo("Intendentes en ejercicio · clic en un municipio para filtrar"),
          orden=(col("dim_municipio", "pob"), "Descending"))
    for pr, n in zip(p.visuales[-1]["visual"]["query"]["queryState"]["Values"]["projections"],
                     ["Foto", "Municipio", "Intendente", "Fuerza", "Situación", "Fuerza (logo)", "Wikipedia"]):
        pr["displayName"] = n


def construir_reporte(esquemas: Path | None) -> None:
    rep = PBI / f"{NOMBRE}.Report"
    shutil.rmtree(rep, ignore_errors=True)
    (rep / "definition" / "pages").mkdir(parents=True)
    (rep / "StaticResources" / "RegisteredResources").mkdir(parents=True)
    tema = {"name": "Atlas Analytics", "dataColors": ["#29A3F0", "#9B4DFF", "#FF6FB5", "#2FC4A6", "#F5C518", "#E94F4F", "#C40BFF",
                                                      "#7E57FF", "#C2185B", "#8D86A6", "#FFB547", "#4DD0E1"],
            "background": "#12042E", "foreground": "#F2EBFA", "tableAccent": "#C40BFF", "good": "#3DDC97", "bad": "#E94F4F",
            "neutral": "#A08FC2", "maximum": "#C40BFF", "center": "#3A2A66", "minimum": "#1B0A3D",
            "textClasses": {"title": {"fontFace": "Segoe UI Semibold", "color": "#F2EBFA", "fontSize": 12},
                            "label": {"fontFace": "Segoe UI", "color": "#DCD2EA", "fontSize": 10},
                            "callout": {"fontFace": "Segoe UI Semibold", "color": "#F2EBFA", "fontSize": 24},
                            "header": {"fontFace": "Segoe UI Semibold", "color": "#F2EBFA", "fontSize": 12}},
            "visualStyles": {
                "page": {"*": {"background": [{"color": {"solid": {"color": "#12042E"}}, "transparency": 0}],
                               "outspace": [{"color": {"solid": {"color": "#0E0324"}}, "transparency": 0}]}},
                "*": {"*": {"background": [{"show": True, "color": {"solid": {"color": "#1B0A3D"}}, "transparency": 0}],
                            "border": [{"show": True, "color": {"solid": {"color": "#2E1A57"}}, "radius": 10}],
                            "title": [{"fontColor": {"solid": {"color": "#F2EBFA"}}, "fontSize": 11}],
                            "visualHeader": [{"background": {"solid": {"color": "#1B0A3D"}}, "foreground": {"solid": {"color": "#A08FC2"}}}],
                            "categoryAxis": [{"labelColor": {"solid": {"color": "#A08FC2"}}, "gridlineColor": {"solid": {"color": "#2E1A57"}}}],
                            "valueAxis": [{"labelColor": {"solid": {"color": "#A08FC2"}}, "gridlineColor": {"solid": {"color": "#2E1A57"}}}],
                            "legend": [{"labelColor": {"solid": {"color": "#DCD2EA"}}}],
                            "labels": [{"color": {"solid": {"color": "#F2EBFA"}}}]}},
                "slicer": {"*": {"items": [{"fontColor": {"solid": {"color": "#F2EBFA"}}, "background": {"solid": {"color": "#220E4A"}}}]}}}}
    (rep / "StaticResources" / "RegisteredResources" / "AtlasAnalytics.json").write_text(json.dumps(tema, indent=2, ensure_ascii=False), encoding="utf-8")
    shutil.copy2(DATOS / "pba_municipios.topojson", rep / "StaticResources" / "RegisteredResources" / MAPA)

    pags = []
    fz_col = col("dim_fuerza", "fuerza_intendente")
    # ---------------------------------------------------------------- 1 · Territorio político
    p = Pagina("politico", "Territorio político")
    encabezado(p)
    filtros_comunes(p)
    tarjeta(p, "politico_k1", 244, 70, 180, 80, "Municipios", "Municipios")
    tarjeta(p, "politico_k2", 432, 70, 180, 80, "Población", "Población 2022")
    tarjeta(p, "politico_k3", 620, 70, 180, 80, "Electores", "Electores 2025")
    tarjeta(p, "politico_k4", 808, 70, 180, 80, "Participación", "Participación 2025")
    tarjeta(p, "politico_k5", 996, 70, 272, 80, "Título ficha", "Selección", "#E9B6FF")
    mapa(p, "politico_mapa", 244, 158, 520, 554, fz_col, FUERZAS, "Fuerza del intendente en ejercicio")
    tabla_ficha(p, "politico_ficha", 772, 158, 496, 290)
    p.add("politico_dona", "donutChart", 772, 456, 244, 256, roles={"Category": [fz_col], "Y": [med("Población")]},
          objetos={"dataPoint": colores_por(fz_col, FUERZAS), "legend": [{"properties": {"show": lit(False)}}],
                   "labels": [{"properties": {"show": lit(True), "labelStyle": lit("Percent of total")}}]},
          contenedor=titulo("Población gobernada por fuerza"))
    p.add("politico_secciones", "columnChart", 1024, 456, 244, 256,
          roles={"Category": [col("dim_municipio", "seccion")], "Series": [fz_col], "Y": [med("Municipios")]},
          objetos={"dataPoint": colores_por(fz_col, FUERZAS), "legend": [{"properties": {"show": lit(False)}}]},
          contenedor=titulo("Intendentes por sección"), orden=(col("dim_municipio", "seccion"), "Ascending"))
    texto(p, "politico_nota", 12, 330, 220, 380, [
        [("Cómo usar", {"fontSize": "10pt", "fontWeight": "bold", "color": "#E9B6FF"})],
        [("Elegí municipio, sección, zona o fuerza: todo se filtra junto. Clic en el mapa, en la tabla o en un gráfico para cruzar. "
          "Fotos de Wikimedia Commons (licencia libre) sólo cuando el intendente en ejercicio es el electo en 2023.", {"fontSize": "9pt", "color": "#A08FC2"})],
        [("Intendentes a octubre de 2026. Fuentes: DINE, Junta Electoral PBA, INDEC, RENABAP, Municipios Argentinos.", {"fontSize": "8pt", "color": "#6b5a8c"})]])
    pags.append(p)

    # ---------------------------------------------------------------- 2 · Elecciones
    p = Pagina("elecciones", "Elecciones")
    encabezado(p)
    slicer(p, "elecciones_s_el", 12, 70, 220, 58, col("dim_eleccion", "rotulo"), "Elección (una)", unico=True)
    slicer(p, "elecciones_s_sec", 12, 134, 220, 58, col("dim_municipio", "seccion"), "Sección electoral")
    slicer(p, "elecciones_s_zona", 12, 198, 220, 58, col("dim_municipio", "zona"), "Zona")
    slicer(p, "elecciones_s_muni", 12, 262, 220, 58, col("dim_municipio", "municipio"), "Municipio")
    slicer(p, "elecciones_s_esp", 12, 326, 220, 200, col("dim_espacio", "espacio_nombre"), "Fuerzas", modo="Basic")
    tarjeta(p, "elecciones_k1", 244, 70, 250, 80, "Ganador", "Ganador", "#E9B6FF")
    tarjeta(p, "elecciones_k2", 502, 70, 180, 80, "% Ganador", "% del ganador")
    tarjeta(p, "elecciones_k3", 690, 70, 180, 80, "Margen (pts)", "Margen (puntos)")
    tarjeta(p, "elecciones_k4", 878, 70, 180, 80, "Participación", "Participación")
    tarjeta(p, "elecciones_k5", 1066, 70, 202, 80, "Electores", "Electores")
    gan = col("fact_participacion", "ganador_nombre")
    pares_esp = [(n, COLOR_ESPACIO[k]) for k, n in pd.read_csv(DATOS / "dim_espacio.csv").set_index("espacio").espacio_nombre.items()]
    mapa(p, "elecciones_mapa", 244, 158, 400, 554, gan, pares_esp, "Ganador por municipio")
    esp_col = col("dim_espacio", "espacio_nombre")
    p.add("elecciones_barras", "clusteredBarChart", 652, 158, 300, 270, roles={"Category": [esp_col], "Y": [med("% Voto")]},
          objetos={"dataPoint": colores_por(esp_col, pares_esp), "labels": [{"properties": {"show": lit(True)}}]},
          contenedor=titulo("% sobre votos positivos"), orden=(med("% Voto"), "Descending"))
    p.add("elecciones_linea", "lineChart", 960, 158, 308, 270,
          roles={"Category": [col("dim_eleccion", "etiqueta")], "Series": [esp_col], "Y": [med("% Voto")]},
          objetos={"dataPoint": colores_por(esp_col, pares_esp), "legend": [{"properties": {"show": lit(False)}}]},
          contenedor=titulo("Evolución 2007-2025 (todas las elecciones)"), orden=(col("dim_eleccion", "etiqueta"), "Ascending"))
    p.add("elecciones_tabla", "tableEx", 652, 436, 616, 276,
          roles={"Values": [col("dim_municipio", "municipio"), col("dim_municipio", "seccion"), med("Ganador"), med("% Ganador"),
                            med("Margen (pts)"), med("Participación"), med("% Peronismo"), med("% Derecha")]},
          objetos={"values": [{"properties": {"fontColorPrimary": color("#F2EBFA"), "backColorPrimary": color("#1B0A3D"),
                                              "backColorSecondary": color("#220E4A")}}],
                   "columnHeaders": [{"properties": {"fontColor": color("#A08FC2"), "backColor": color("#12042E")}}]},
          contenedor=titulo("Municipios"), orden=(med("Margen (pts)"), "Ascending"))
    p.interacciones = [{"source": "elecciones_s_el", "target": "elecciones_linea", "type": "NoFilter"}]
    pags.append(p)

    # ---------------------------------------------------------------- 3 · Censo y gestión
    p = Pagina("censo", "Censo y gestión")
    encabezado(p)
    filtros_comunes(p)
    slicer(p, "censo_s_el", 12, 326, 220, 58, col("dim_eleccion", "rotulo"), "Elección del eje vertical", unico=True)
    tarjeta(p, "censo_k1", 244, 70, 200, 80, "Hogares con NBI %", "Hogares con NBI")
    tarjeta(p, "censo_k2", 452, 70, 200, 80, "Hogares en barrios populares %", "En barrios populares")
    tarjeta(p, "censo_k3", 660, 70, 200, 80, "Universitarios %", "Universitarios")
    tarjeta(p, "censo_k4", 868, 70, 190, 80, "Escuelas", "Escuelas")
    tarjeta(p, "censo_k5", 1066, 70, 202, 80, "Transferencias por habitante", "Transferencias / hab.")
    p.add("censo_dispersion", "scatterChart", 244, 158, 560, 554,
          roles={"Category": [col("dim_municipio", "municipio")], "Series": [fz_col], "X": [med("Hogares con NBI %")],
                 "Y": [med("% Peronismo")], "Size": [med("Población")]},
          objetos={"dataPoint": colores_por(fz_col, FUERZAS), "legend": [{"properties": {"show": lit(True), "position": lit("Top")}}]},
          contenedor=titulo("NBI y voto peronista por municipio (tamaño: población; color: fuerza del intendente)"))
    p.add("censo_tabla", "tableEx", 812, 158, 456, 554,
          roles={"Values": [col("dim_municipio", "municipio"), col("dim_municipio", "nbi"), col("dim_municipio", "pct_barrio_popular"),
                            col("dim_municipio", "pct_univ"), col("dim_municipio", "cloaca"), col("dim_municipio", "transferencias_hab"),
                            col("dim_municipio", "transparencia_asap"), col("dim_municipio", "tasa_homicidios")]},
          objetos={"values": [{"properties": {"fontColorPrimary": color("#F2EBFA"), "backColorPrimary": color("#1B0A3D"),
                                              "backColorSecondary": color("#220E4A")}}],
                   "columnHeaders": [{"properties": {"fontColor": color("#A08FC2"), "backColor": color("#12042E")}}]},
          contenedor=titulo("Ranking de municipios (clic en el encabezado para ordenar)"), orden=(col("dim_municipio", "nbi"), "Descending"))
    for pr, n in zip(p.visuales[-1]["visual"]["query"]["queryState"]["Values"]["projections"],
                     ["Municipio", "NBI %", "Barrios pop. %", "Univ. %", "Cloaca %", "Transf. / hab.", "ASAP", "Homicidios"]):
        pr["displayName"] = n
    pags.append(p)

    # ---------------------------------------------------------------- 4 · Escenarios 2027
    p = Pagina("escenarios", "Escenarios 2027")
    encabezado(p)
    slicer(p, "escenarios_s_esc", 12, 70, 220, 120, col("fact_motor_2027", "escenario"), "Escenario", modo="Basic", unico=True)
    slicer(p, "escenarios_s_sec", 12, 196, 220, 58, col("dim_municipio", "seccion"), "Sección electoral")
    slicer(p, "escenarios_s_fz", 12, 260, 220, 58, col("dim_fuerza", "fuerza_intendente"), "Fuerza del intendente")
    boton(p, "escenarios_b_sim", 12, 330, 220, 44, "Abrir el simulador 2027 ↗", url=SIMULADOR)
    boton(p, "escenarios_b_web", 12, 382, 220, 40, "Tablero web ↗", url=TABLERO_WEB)
    boton(p, "escenarios_b_repo", 12, 430, 220, 40, "Metodología ↗", url=REPO)
    tarjeta(p, "escenarios_k1", 244, 70, 330, 80, "Municipios peronistas esperados", "Municipios peronistas esperados")
    tarjeta(p, "escenarios_k2", 582, 70, 330, 80, "Municipios en disputa", "En disputa (20-80 %)", "#C40BFF")
    tarjeta(p, "escenarios_k3", 920, 70, 348, 80, "P(peronismo) 2027", "P(gana el peronismo), promedio municipal")
    rango = col("fact_motor_2027", "rango_p")
    mapa(p, "escenarios_mapa", 244, 158, 520, 554, rango, RANGOS_P, "Quién gana cada municipio · motor 2027 (1.000 simulaciones)")
    p.add("escenarios_tabla", "tableEx", 772, 158, 496, 554,
          roles={"Values": [col("dim_municipio", "municipio"), col("dim_municipio", "seccion"), col("fact_motor_2027", "p_gana_peronismo"),
                            col("fact_motor_2027", "pct_peronismo"), col("fact_motor_2027", "rango_p"), col("dim_municipio", "fuerza_intendente")]},
          objetos={"values": [{"properties": {"fontColorPrimary": color("#F2EBFA"), "backColorPrimary": color("#1B0A3D"),
                                              "backColorSecondary": color("#220E4A")}}],
                   "columnHeaders": [{"properties": {"fontColor": color("#A08FC2"), "backColor": color("#12042E")}}]},
          contenedor=titulo("Municipios: probabilidad de que gane el peronismo"), orden=(col("fact_motor_2027", "p_gana_peronismo"), "Descending"))
    for pr, n in zip(p.visuales[-1]["visual"]["query"]["queryState"]["Values"]["projections"],
                     ["Municipio", "Sección", "P(peronismo)", "% peronismo", "Categoría", "Intendente"]):
        pr["displayName"] = n
    pags.append(p)

    # ---------------------------------------------------------------- escribir
    d = rep / "definition"
    for p in pags:
        pd_ = d / "pages" / p.nombre
        (pd_ / "visuals").mkdir(parents=True)
        page = {"$schema": f"{SCHEMA}/page/2.0.0/schema.json", "name": p.nombre, "displayName": p.visible,
                "displayOption": "FitToPage", "height": 720, "width": 1280}
        if p.interacciones:
            page["visualInteractions"] = p.interacciones
        (pd_ / "page.json").write_text(json.dumps(page, indent=2, ensure_ascii=False), encoding="utf-8")
        for v in p.visuales:
            (pd_ / "visuals" / v["name"]).mkdir()
            (pd_ / "visuals" / v["name"] / "visual.json").write_text(json.dumps(v, indent=2, ensure_ascii=False), encoding="utf-8")
    (d / "pages" / "pages.json").write_text(json.dumps({"$schema": f"{SCHEMA}/pagesMetadata/1.0.0/schema.json",
                                                         "pageOrder": [p.nombre for p in pags], "activePageName": "politico"}, indent=2), encoding="utf-8")
    (d / "version.json").write_text(json.dumps({"$schema": f"{SCHEMA}/versionMetadata/1.0.0/schema.json", "version": "2.0.0"}, indent=2), encoding="utf-8")
    (d / "report.json").write_text(json.dumps({
        "$schema": f"{SCHEMA}/report/1.2.0/schema.json",
        "themeCollection": {"customTheme": {"name": "AtlasAnalytics.json", "reportVersionAtImport": "5.55", "type": "RegisteredResources"}},
        "layoutOptimization": "None",
        "resourcePackages": [{"name": "RegisteredResources", "type": "RegisteredResources",
                              "items": [{"name": "AtlasAnalytics.json", "path": "AtlasAnalytics.json", "type": "CustomTheme"},
                                        {"name": MAPA, "path": MAPA, "type": "ShapeMap"}]}],
        "settings": {"useStylableVisualContainerHeader": True, "defaultDrillFilterOtherVisuals": True, "allowChangeFilterTypes": True,
                     "useEnhancedTooltips": True}}, indent=2), encoding="utf-8")
    (rep / "definition.pbir").write_text(json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
        "version": "4.0", "datasetReference": {"byPath": {"path": f"../{NOMBRE}.SemanticModel"}}}, indent=2), encoding="utf-8")
    (PBI / f"{NOMBRE}.pbip").write_text(json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
        "version": "1.0", "artifacts": [{"report": {"path": f"{NOMBRE}.Report"}}], "settings": {"enableAutoRecovery": True}}, indent=2), encoding="utf-8")
    (PBI / ".gitignore").write_text("**/.pbi/localSettings.json\n**/.pbi/cache.abf\n", encoding="utf-8")
    print(f"reporte: {len(pags)} páginas, {sum(len(p.visuales) for p in pags)} visuales")
    if esquemas:
        validar(rep, esquemas)


def validar(rep: Path, carpeta: Path) -> None:
    from jsonschema import Draft7Validator
    from referencing import Registry, Resource
    idx = json.loads((carpeta / "indice.json").read_text(encoding="utf-8"))
    reg = Registry().with_resources([(u, Resource.from_contents(s)) for u, s in idx.items()])
    errores = 0
    archivos = list(rep.rglob("*.json")) + [rep / "definition.pbir"]
    for f in archivos:
        if "StaticResources" in f.parts:
            continue
        doc = json.loads(f.read_text(encoding="utf-8"))
        url = doc.get("$schema")
        if url not in idx:
            print("  sin esquema local:", f.relative_to(rep), url)
            continue
        val = Draft7Validator(idx[url], registry=reg)
        for e in val.iter_errors(doc):
            errores += 1
            print("  ERROR", f.relative_to(rep), "/".join(map(str, e.path)), e.message[:200])
    print(f"validación PBIR: {len(archivos)} archivos, {errores} errores")
    if errores:
        sys.exit(1)


def leeme() -> None:
    (PBI / "LEEME_POWERBI.md").write_text(f"""# Atlas PBA · proyecto de Power BI

Tablero electoral de la Provincia de Buenos Aires para **Power BI Desktop** (formato de proyecto
PBIP: modelo en TMDL y reporte en PBIR, todo texto y versionable).

## Abrir

1. Power BI Desktop (2024 o posterior). Si es anterior a 2025, activar en *Archivo > Opciones >
   Características en versión preliminar* «Formato de proyecto de Power BI (.pbip)» y «Almacenar
   informes con el formato de metadatos mejorado (PBIR)».
2. Abrir `Atlas_PBA.pbip`.
3. Si los datos no están en `{DATOS}`, cambiar el parámetro **CarpetaDatos** (*Transformar datos >
   Administrar parámetros*) a la carpeta `03_OUTPUTS/powerbi/datos/` con la barra final.
4. **Actualizar** (Inicio > Actualizar). Los CSV se regeneran con `python 02_SCRIPTS/productos/p04_tablero_datos.py`
   y `p06_powerbi.py`.

## El mapa

Los tres mapas (Territorio político, Elecciones y Escenarios 2027) usan el visual **Mapa de formas**
(Shape map), porque los mapas de Bing fueron retirados. El contorno de los 135 municipios ya viene
**incrustado en el reporte** (`StaticResources/RegisteredResources/pba_municipios.json`, TopoJSON) y
cada mapa lo usa con la clave `cod_indec`: no hay que cargar nada.

- Si el visual aparece en blanco con un aviso, activar *Archivo > Opciones > Características en
  versión preliminar > Objeto visual de mapa de formas* y reabrir.
- Si algún mapa no muestra los municipios, cargarlo a mano una vez: *Formato > Forma del mapa >
  + Agregar mapa* → `datos/pba_municipios.topojson`.

## Qué tiene

| Página | Contenido |
|---|---|
| Territorio político | Filtros (municipio, sección, zona, fuerza), tarjetas (municipios, población, electores, participación), mapa por fuerza del intendente, tabla con foto, logo y enlace a Wikipedia, dona de población gobernada, columnas por sección |
| Elecciones | 17 elecciones 2007-2025: ganador, % del ganador, margen, participación; mapa del ganador por municipio; % por fuerza; evolución histórica (no se filtra por la elección elegida); tabla de municipios |
| Censo y gestión | NBI, barrios populares, universitarios, escuelas, transferencias; dispersión NBI × voto peronista; ranking con indicadores de servicios, gestión fiscal y seguridad |
| Escenarios 2027 | Motor de Atlas PBA: municipios peronistas esperados, municipios en disputa, mapa por categoría de probabilidad, tabla; botones al simulador y a la metodología |

Navegación con botones en el encabezado de cada página. Las fotos son de Wikimedia Commons (licencia
libre) y se cargan desde internet; sólo están cuando el intendente en ejercicio es el electo en 2023.

## Medidas principales (tabla Medidas)

`Votos`, `% Voto`, `% Peronismo`, `% Derecha`, `Ganador`, `% Ganador`, `Margen (pts)`, `Electores`,
`Participación`, `Municipios`, `Población`, `Hogares con NBI %`, `Hogares en barrios populares %`,
`Universitarios %`, `Transferencias por habitante`, `P(peronismo) 2027`, `Municipios peronistas
esperados`, `Municipios en disputa`. Si no hay una elección elegida, las de votación usan
Diputados nacionales 2025.

## Verificación

El reporte se validó contra los esquemas públicos de PBIR de Microsoft. El modelo TMDL no tiene
validador público: si Desktop marca un error al abrir, el mensaje indica archivo y línea en
`Atlas_PBA.SemanticModel/definition/`.
""", encoding="utf-8")


def main() -> None:
    esq = None
    if "--esquemas" in sys.argv:
        esq = Path(sys.argv[sys.argv.index("--esquemas") + 1])
    t = preparar_datos()
    for n, df in t.items():
        df.to_csv(DATOS / f"{n}.csv", index=False, encoding="utf-8")
    topojson(t["dim_municipio"])
    escribir_modelo(t)
    construir_reporte(esq)
    leeme()
    print("modelo:", sorted(x.name for x in (PBI / f"{NOMBRE}.SemanticModel" / "definition" / "tables").iterdir()))


if __name__ == "__main__":
    main()
