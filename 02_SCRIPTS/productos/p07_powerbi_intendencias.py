"""
p07 · Power BI «Intendencias PBA 2027»: el Super Excel de Atlas Analytics llevado a Power BI, más el
análisis electoral de Atlas PBA (elecciones 2007-2025, censo, motor 2027).

Reemplaza el reporte de `p06` (usa sus tablas y utilidades) en el mismo proyecto:
  03_OUTPUTS/powerbi/Atlas_PBA.pbip

QUÉ TIENE
---------
Páginas: Inicio (menú y resumen) · Dashboard (filtros en botones, tarjetas, gráficos, tabla con
formato condicional) · Mapa (mapa de la Provincia y del Conurbano dibujado con una medida DAX en SVG,
con 9 capas a elección) · Ficha (página de obtención de detalles: datos, foto, prospectos, noticias,
evolución del voto) · Prospectos (CRM) · Noticias · Elecciones (dispersión animada 2007-2025 con eje
de reproducción) · Análisis 2027 (motor de escenarios) · Información emergente (tooltip con foto).

EL MAPA
-------
Una medida DAX arma una imagen SVG con los 135 municipios (contornos de `svg_mapa.py`) y los pinta
según la capa elegida; lo que queda fuera de los filtros se apaga y el municipio elegido se resalta.
Funciona en cualquier Power BI, sin visuales en versión preliminar.

PRIVACIDAD
----------
El CRM (prospectos, oportunidad) sale de `etl/13` a `datos_privados/` (fuera del repo). El modelo lo
lee de ahí con el parámetro `CarpetaPrivada`.

Uso: python p07_powerbi_intendencias.py [--esquemas <carpeta con indice.json de esquemas PBIR>]
"""
from __future__ import annotations

import json
import shutil
import sys
import uuid
from pathlib import Path
from urllib.parse import quote

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import p06_powerbi as b  # noqa: E402
import svg_mapa  # noqa: E402

PBI, DATOS, NOMBRE, SCHEMA = b.PBI, b.DATOS, b.NOMBRE, b.SCHEMA
PRIV = PBI / "datos_privados"
TABLAS = b.RAIZ / "03_OUTPUTS" / "tablas"
lit, color, col, med, titulo, colores_por, Pagina, q, tag = b.lit, b.color, b.col, b.med, b.titulo, b.colores_por, b.Pagina, b.q, b.tag

# ------------------------------------------------------------------ paletas
C_ESPACIO26 = [("Peronismo", "#29A3F0"), ("UCR", "#E94F4F"), ("PRO", "#F5C518"), ("Vecinal", "#2FC4A6"), ("LLA", "#9B4DFF"),
               ("PRO / LLA", "#B98CFF"), ("Hechos", "#FF8A3D")]
C_ESCENARIO = [("Sucesión abierta", "#FF8A3D"), ("Reelección posible", "#3DDC97"), ("Zona gris (judicial)", "#FFD54F")]
C_CONCEJALES = [("Fuerza Patria", "#29A3F0"), ("La Libertad Avanza", "#9B4DFF"), ("Somos Buenos Aires", "#FF6FB5"),
                ("Esp. Abierto Para El Des. Y La Int.", "#FF8A3D"), ("Primero San Miguel", "#2FC4A6"), ("Potencia", "#2FC4A6"),
                ("Nuevos Aires", "#2FC4A6"), ("Movimiento Para La Victoria", "#2FC4A6"), ("Accion Por Villarino", "#2FC4A6")]
C_OPORT = [("Muy alta", "#C40BFF"), ("Alta", "#9B4DFF"), ("Media", "#5B3FA8"), ("Baja", "#3A2A66")]
C_TAMANO = [("Grande (+200 mil)", "#C40BFF"), ("Mediano (50–200 mil)", "#7E57FF"), ("Chico (-50 mil)", "#3A6FB8")]
C_FAMILIA = [("Peronismo", "#29A3F0"), ("LLA", "#9B4DFF"), ("UCR / Somos", "#FF6FB5"), ("PRO", "#F5C518"), ("Vecinal / otros", "#2FC4A6"),
             ("Hechos", "#FF8A3D")]
RAMPA_AMBAR = ["#3A2A1E", "#6B4A1E", "#A0661C", "#D98A1A", "#FFB547"]
RAMPA_P = [("Peronismo seguro (≥ 90 %)", "#29A3F0"), ("Peronismo probable (60-90 %)", "#2178B8"), ("En disputa (40-60 %)", "#C40BFF"),
           ("Derecha probable (10-40 %)", "#5B3FA8"), ("Derecha segura (< 10 %)", "#7E57FF")]
RAMPA_PER = [("55 % o más", "#0B6FB8"), ("45-55 %", "#29A3F0"), ("35-45 %", "#7CC4F2"), ("25-35 %", "#3A4E78"), ("menos de 25 %", "#2A2350")]
GRIS, APAGADO = "#3A3350", "#241448"

CAPAS = [  # (capa, descripción, leyenda)
    ("Espacio 2026", "Espacio político que gobierna cada municipio (2026)", C_ESPACIO26),
    ("Escenario 2027", "¿El intendente puede reelegir en 2027?", C_ESCENARIO),
    ("Concejales 2025", "Fuerza que ganó concejales el 7/9/2025", C_CONCEJALES[:4] + [("Vecinales", "#2FC4A6")]),
    ("Fuerza del intendente", "Fuerza del intendente en ejercicio (oct. 2026)", b.FUERZAS),
    ("Oportunidad", "Nivel de oportunidad (Atlas Analytics)", C_OPORT),
    ("Ganador de la elección", "Ganador por municipio en la elección elegida", [(n, c) for k, c in b.COLOR_ESPACIO.items() for n in [k]]),
    ("% Peronismo", "% del peronismo en la elección elegida", RAMPA_PER),
    ("P(peronismo) 2027", "Motor 2027: probabilidad de que gane el peronismo", RAMPA_P),
    ("Hogares con NBI", "Hogares con necesidades básicas insatisfechas (quintiles)", None),
    ("Barrios populares", "% de hogares en barrios populares RENABAP (quintiles)", None),
]


def leyenda_svg(items: list[tuple[str, str]]) -> str:
    h = 22 * len(items) + 8
    s = [f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 300 {h}'>"]
    for i, (t, c) in enumerate(items):
        y = 6 + 22 * i
        t = t.replace("&", "y").replace("<", "&lt;").replace("'", "’")
        s.append(f"<rect x='4' y='{y}' width='16' height='16' rx='3' fill='{c}'/>"
                 f"<text x='28' y='{y + 13}' font-family='Segoe UI' font-size='13' fill='#DCD2EA'>{t}</text>")
    s.append("</svg>")
    return "data:image/svg+xml;utf8," + quote("".join(s), safe="/:=' ;,.()-<>")


def cortes(s: pd.Series, n=5) -> list[float]:
    return list(np.nanquantile(s.astype(float), [i / n for i in range(1, n)]))


# ================================================================== datos
def datos() -> dict:
    t = b.preparar_datos()
    m = t["dim_municipio"]
    prov, conu, meta = svg_mapa.paths()
    m["svg_prov"] = m.cod_indec.map(prov).fillna("")
    m["svg_conu"] = m.cod_indec.map(conu).fillna("")
    cn, cb = cortes(m.nbi), cortes(m.pct_barrio_popular.fillna(0))
    m["color_nbi"] = [RAMPA_AMBAR[int(np.searchsorted(cn, v, side="right"))] if pd.notna(v) else GRIS for v in m.nbi]
    m["color_bp"] = [RAMPA_AMBAR[int(np.searchsorted(cb, v, side="right"))] for v in m.pct_barrio_popular.fillna(0)]
    capas = []
    for i, (c, d, ley) in enumerate(CAPAS):
        if c == "Hogares con NBI":
            ley = list(zip([f"menos de {cn[0]:.1f} %"] + [f"{a:.1f} a {z:.1f} %" for a, z in zip(cn, cn[1:])] + [f"{cn[-1]:.1f} % o más"], RAMPA_AMBAR))
        if c == "Barrios populares":
            ley = list(zip([f"menos de {cb[0]:.1f} %"] + [f"{a:.1f} a {z:.1f} %" for a, z in zip(cb, cb[1:])] + [f"{cb[-1]:.1f} % o más"], RAMPA_AMBAR))
        if c == "Ganador de la elección":
            esp = t["dim_espacio"]
            ley = [(r.espacio_nombre, r.color) for r in esp.itertuples() if r.espacio in ("PERONISMO", "LLA_PRO", "LLA", "PRO_JXC", "CENTRO_UCR", "TERCERA_VIA", "VECINAL")]
        capas.append({"capa": c, "orden": i, "descripcion": d, "leyenda_svg": leyenda_svg(ley + [("Fuera del filtro", APAGADO)])})
    t["capa_mapa"] = pd.DataFrame(capas)
    t["meta_svg"] = meta

    e = pd.read_csv(TABLAS / "motor_2027_escenarios.csv")
    mv = pd.read_csv(TABLAS / "movilizacion_2027.csv")
    fil = []
    nombres = {"A": "Se repite octubre 2025", "B": "Se repite septiembre 2025", "C": "Punto medio sept.-oct.", "D": "Tercera vía fuerte (12 %)",
               "A1": "Octubre, participación 64 %", "A2": "Octubre, participación 80 %", "A3": "Octubre, extranjeros al 45 %",
               "B1": "Septiembre, participación 64 %"}
    for r in e.itertuples():
        k = r.escenario.split(" ")[0]
        fil.append({"escenario": nombres.get(k, r.escenario), "grupo": "Nivel provincial", "margen_p10": r.margen_p10, "margen": r.margen_p50,
                    "margen_p90": r.margen_p90, "p_gana_peronismo": r.p_gana_peronismo, "municipios_peronistas": r.municipios_peronismo_p50})
    for r in mv[mv.base == "octubre"].itertuples():
        fil.append({"escenario": f"Octubre, {r.derecha}: {r.perfil}", "grupo": "Movilización" if r.derecha == "unida" else "Derecha dividida",
                    "margen_p10": r.margen_p10, "margen": r.margen_p50, "margen_p90": r.margen_p90, "p_gana_peronismo": r.p_gana_peronismo,
                    "municipios_peronistas": r.municipios_peronismo})
    t["escenarios_2027"] = pd.DataFrame(fil).round(3)
    return t


def datos_privados() -> dict:
    i = pd.read_csv(PRIV / "intendencias.csv", dtype={"cod_indec": str})
    i = i.drop(columns=[c for c in ("electo_2023",) if c in i.columns])  # ya está en dim_municipio (Wikipedia)
    i["color_espacio_2026"] = i.espacio_2026.map(dict(C_ESPACIO26)).fillna(GRIS)
    i["color_escenario"] = i.escenario_2027.map(dict(C_ESCENARIO)).fillna(GRIS)
    i["color_concejales"] = i.gano_concejales_2025.map(dict(C_CONCEJALES)).fillna("#2FC4A6")
    i["color_oportunidad"] = i.nivel_oportunidad.map(dict(C_OPORT)).fillna(GRIS)
    i["orden_tamano"] = i.tamano.map({"Grande (+200 mil)": 1, "Mediano (50–200 mil)": 2, "Chico (-50 mil)": 3})
    i["orden_oportunidad"] = i.nivel_oportunidad.map({"Muy alta": 1, "Alta": 2, "Media": 3, "Baja": 4})
    p = pd.read_csv(PRIV / "prospectos.csv", dtype={"cod_indec": str})
    p["clave"] = range(1, len(p) + 1)
    n = pd.read_csv(PRIV / "noticias.csv", dtype={"cod_indec": str})
    n["mes"] = n.fecha.str[:7]
    n["clave"] = range(1, len(n) + 1)
    return {"intendencias": i, "prospectos": p, "noticias": n}


# ================================================================== modelo
def m_tipo(df: pd.DataFrame, c: str) -> tuple[str, str]:
    return b.TIPO.get(str(df[c].dtype), ("string", "type text"))


def columna(c: str, dt: str, oculta=False, orden=None, categoria=None, suma=False) -> str:
    lin = [f"\tcolumn {q(c)}", f"\t\tdataType: {dt}"]
    if dt == "double":
        lin.append("\t\tformatString: #,0.0")
    elif dt == "int64" and not c.startswith(("orden", "seccion_num", "clave", "anio")):
        lin.append("\t\tformatString: #,0")
    if categoria:
        lin.append(f"\t\tdataCategory: {categoria}")
    if oculta:
        lin.append("\t\tisHidden")
    lin += [f"\t\tlineageTag: {tag()}", f"\t\tsummarizeBy: {'sum' if suma else 'none'}", f"\t\tsourceColumn: {c}"]
    if orden:
        lin.append(f"\t\tsortByColumn: {orden}")
    lin += ["", "\t\tannotation SummarizationSetBy = Automatic"]
    return "\n".join(lin)


def csv_m(carpeta: str, archivo: str, df: pd.DataFrame, paso="Tipos") -> list[str]:
    tipos = ", ".join(f'{{"{c}", {m_tipo(df, c)[1]}}}' for c in df.columns)
    return [f'Origen_{archivo} = Csv.Document(File.Contents({carpeta} & "{archivo}.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv])',
            f'Enc_{archivo} = Table.PromoteHeaders(Origen_{archivo}, [PromoteAllScalars=true])',
            f'{paso} = Table.TransformColumnTypes(Enc_{archivo}, {{{tipos}}}, "en-US")']


def tabla(nombre: str, columnas: list[str], pasos: list[str], final: str) -> str:
    cuerpo = ",\n".join("\t\t\t\t    " + p for p in pasos)
    part = (f"\tpartition {q(nombre)} = m\n\t\tmode: import\n\t\tsource =\n\t\t\t\tlet\n{cuerpo}\n\t\t\t\tin\n\t\t\t\t    {final}\n")
    return f"table {q(nombre)}\n\tlineageTag: {tag()}\n\n" + "\n\n".join(columnas) + "\n\n" + part + "\n\tannotation PBI_ResultType = Table\n"


OCULTAS = {"svg_prov", "svg_conu", "color_fuerza", "color_nbi", "color_bp", "color_espacio_2026", "color_escenario", "color_concejales",
           "color_oportunidad", "orden_fuerza", "orden_tamano", "orden_oportunidad", "ubicacion", "simulador_url", "seccion_num", "leyenda_svg",
           "orden", "color", "clave", "orden_prioridad", "municipio_excel"}
CATEG = {"foto_url": "ImageUrl", "logo_url": "ImageUrl", "wikipedia_url": "WebUrl", "simulador_url": "WebUrl", "google_maps_url": "WebUrl",
         "noticias_url": "WebUrl", "perfil_pdf_url": "WebUrl", "url": "WebUrl", "leyenda_svg": "ImageUrl"}
SUMA = b.SUMA


def tmdl_simple(nombre, df, carpeta="CarpetaDatos", orden=None, ocultas=frozenset()):
    orden = orden or {}
    cols = [columna(c, m_tipo(df, c)[0], c in OCULTAS or c in ocultas, orden.get(c), CATEG.get(c), c in SUMA) for c in df.columns]
    return tabla(nombre, cols, csv_m(carpeta, nombre, df), "Tipos")


def tmdl_municipio(m: pd.DataFrame, i: pd.DataFrame) -> str:
    priv = [c for c in i.columns if c != "cod_indec"]
    orden = {"seccion": "seccion_num", "fuerza_intendente": "orden_fuerza", "tamano": "orden_tamano", "nivel_oportunidad": "orden_oportunidad"}
    cols = [columna(c, m_tipo(m, c)[0], c in OCULTAS, orden.get(c), CATEG.get(c), c in SUMA) for c in m.columns]
    cols += [columna(c, m_tipo(i, c)[0], c in OCULTAS, orden.get(c), CATEG.get(c), False) for c in priv]
    pasos = csv_m("CarpetaDatos", "dim_municipio", m, "Base") + csv_m("CarpetaPrivada", "intendencias", i, "Priv")
    lista = ", ".join(f'"{c}"' for c in priv)
    pasos += ['Unidos = Table.NestedJoin(Base, {"cod_indec"}, Priv, {"cod_indec"}, "p", JoinKind.LeftOuter)',
              f"Final = Table.ExpandTableColumn(Unidos, \"p\", {{{lista}}})"]
    return tabla("dim_municipio", cols, pasos, "Final")


def dax_mapa(columna_svg: str, w: int, h: int) -> str:
    def esc(pares, var):
        return " ".join(f'{var} >= {v}, "{c}",' for v, c in pares)
    return f'''VAR capa = SELECTEDVALUE ( capa_mapa[capa], "Espacio 2026" )
VAR el = [Elección activa]
VAR vis = VALUES ( dim_municipio[cod_indec] )
VAR n = COUNTROWS ( vis )
VAR total = COUNTROWS ( ALL ( dim_municipio ) )
VAR cuerpo =
    CONCATENATEX (
        FILTER ( ALL ( dim_municipio ), dim_municipio[{columna_svg}] <> "" ),
        VAR c = dim_municipio[cod_indec]
        VAR p = CALCULATE ( [P(peronismo) 2027] )
        VAR v = CALCULATE ( [% Peronismo] )
        VAR g = CALCULATE ( MAX ( fact_participacion[ganador] ), dim_eleccion[eleccion] = el )
        VAR relleno =
            SWITCH (
                capa,
                "Espacio 2026", dim_municipio[color_espacio_2026],
                "Escenario 2027", dim_municipio[color_escenario],
                "Concejales 2025", dim_municipio[color_concejales],
                "Fuerza del intendente", dim_municipio[color_fuerza],
                "Oportunidad", dim_municipio[color_oportunidad],
                "Hogares con NBI", dim_municipio[color_nbi],
                "Barrios populares", dim_municipio[color_bp],
                "Ganador de la elección", COALESCE ( LOOKUPVALUE ( dim_espacio[color], dim_espacio[espacio], g ), "{GRIS}" ),
                "P(peronismo) 2027", SWITCH ( TRUE (), ISBLANK ( p ), "{GRIS}", {esc([(0.9, "#29A3F0"), (0.6, "#2178B8"), (0.4, "#C40BFF"), (0.1, "#5B3FA8")], "p")} "#7E57FF" ),
                "% Peronismo", SWITCH ( TRUE (), ISBLANK ( v ), "{GRIS}", {esc([(0.55, "#0B6FB8"), (0.45, "#29A3F0"), (0.35, "#7CC4F2"), (0.25, "#3A4E78")], "v")} "#2A2350" ),
                "{GRIS}"
            )
        RETURN "<path fill='" & IF ( c IN vis, relleno, "{APAGADO}" ) & "' d='" & dim_municipio[{columna_svg}] & "'/>",
        ""
    )
VAR resalte =
    IF (
        n = 1 && n < total,
        "<path fill='none' stroke='#FFFFFF' stroke-width='3' stroke-linejoin='round' d='" & CALCULATE ( MAX ( dim_municipio[{columna_svg}] ) ) & "'/>"
    )
VAR svg = "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {w} {h}'><g stroke='#12042E' stroke-width='0.7' stroke-linejoin='round'>" & cuerpo & "</g>" & resalte & "</svg>"
RETURN "data:image/svg+xml;utf8," & SUBSTITUTE ( svg, "#", "%23" )'''


def medidas(meta) -> list:
    nuevas = [
        ("Sucesión abierta", 'CALCULATE ( [Municipios], dim_municipio[escenario_2027] = "Sucesión abierta" )', "#,0", "Intendencias", None),
        ("Reelección posible", 'CALCULATE ( [Municipios], dim_municipio[escenario_2027] = "Reelección posible" )', "#,0", "Intendencias", None),
        ("Zona gris", 'CALCULATE ( [Municipios], dim_municipio[escenario_2027] = "Zona gris (judicial)" )', "#,0", "Intendencias", None),
        ("% sucesión abierta", "DIVIDE ( [Sucesión abierta], [Municipios] )", "0%", "Intendencias", None),
        ("Prospectos", "COUNTROWS ( prospectos )", "#,0", "CRM", None),
        ("Rivales", 'CALCULATE ( [Prospectos], prospectos[rol] = "Oposición / rival" )', "#,0", "CRM", None),
        ("Prioridad alta", 'CALCULATE ( [Prospectos], prospectos[prioridad] = "Alta" )', "#,0", "CRM", None),
        ("Contactados", 'CALCULATE ( [Prospectos], prospectos[estado] <> "Pendiente" )', "#,0", "CRM", None),
        ("% contactados", "DIVIDE ( [Contactados], [Prospectos] )", "0%", "CRM", None),
        ("Noticias", "COUNTROWS ( noticias )", "#,0", "Noticias", None),
        ("Última noticia", "MAX ( noticias[fecha] )", "dd/mm/yyyy", "Noticias", None),
        ("Mapa Provincia", dax_mapa("svg_prov", meta["prov_w"], meta["prov_h"]), None, "Mapa", "ImageUrl"),
        ("Mapa Conurbano", dax_mapa("svg_conu", meta["conu_w"], meta["conu_h"]), None, "Mapa", "ImageUrl"),
        ("Leyenda mapa", 'VAR c = SELECTEDVALUE ( capa_mapa[capa], "Espacio 2026" )\nRETURN LOOKUPVALUE ( capa_mapa[leyenda_svg], capa_mapa[capa], c )', None, "Mapa", "ImageUrl"),
        ("Título mapa", 'VAR c = SELECTEDVALUE ( capa_mapa[capa], "Espacio 2026" )\nVAR d = LOOKUPVALUE ( capa_mapa[descripcion], capa_mapa[capa], c )\nRETURN d & IF ( c IN { "Ganador de la elección", "% Peronismo" }, " · " & [Elección seleccionada], "" ) & IF ( c = "P(peronismo) 2027", " · " & SELECTEDVALUE ( fact_motor_2027[escenario], "Se repite octubre 2025" ), "" )', None, "Mapa", None),
        ("Color espacio 2026", "SELECTEDVALUE ( dim_municipio[color_espacio_2026] )", None, "Formato", None),
        ("Color escenario", "SELECTEDVALUE ( dim_municipio[color_escenario] )", None, "Formato", None),
        ("Color oportunidad", "SELECTEDVALUE ( dim_municipio[color_oportunidad] )", None, "Formato", None),
        ("Color prioridad", 'SWITCH ( SELECTEDVALUE ( prospectos[prioridad] ), "Alta", "#C40BFF", "Media", "#5B3FA8", "Baja", "#3A2A66" )', None, "Formato", None),
        ("Título ficha", 'IF ( HASONEVALUE ( dim_municipio[cod_indec] ), SELECTEDVALUE ( dim_municipio[municipio] ) & " · " & SELECTEDVALUE ( dim_municipio[seccion] ) & " sección · " & SELECTEDVALUE ( dim_municipio[escenario_2027] ), "Elegí un municipio (o hacé clic derecho > Obtener detalles en cualquier página)" )', None, "Ficha", None),
        ("Título dashboard", '"Intendencias PBA 2027 · " & FORMAT ( [Municipios], "#,0" ) & " municipios · " & FORMAT ( [Población], "#,0" ) & " habitantes"', None, "Ficha", None),
        ("P(peronismo) 2027 en ficha", 'CALCULATE ( [P(peronismo) 2027], fact_motor_2027[escenario_clave] = "A" )', "0%", "2027", None),
    ]
    propias = {x[0] for x in nuevas} | {"Color fuerza", "Color espacio"}
    return [x for x in b.MEDIDAS if x[0] not in propias] + nuevas


def escribir_modelo(t: dict, priv: dict) -> None:
    sm = PBI / f"{NOMBRE}.SemanticModel"
    shutil.rmtree(sm / "definition", ignore_errors=True)
    d = sm / "definition"
    (d / "tables").mkdir(parents=True)
    (sm / "definition.pbism").write_text(json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
        "version": "4.0", "settings": {}}, indent=2), encoding="utf-8")
    (d / "database.tmdl").write_text("database\n\tcompatibilityLevel: 1567\n", encoding="utf-8")
    nombres = ["dim_municipio", "dim_espacio", "dim_eleccion", "dim_fuerza", "fact_votos", "fact_participacion", "fact_motor_2027",
               "capa_mapa", "escenarios_2027", "prospectos", "noticias", "Medidas"]
    (d / "model.tmdl").write_text(
        "model Model\n\tculture: es-AR\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n\tsourceQueryCulture: es-AR\n"
        "\tdataAccessOptions\n\t\tlegacyRedirects\n\t\treturnErrorValuesAsNull\n\n"
        f"annotation PBI_QueryOrder = {json.dumps(['CarpetaDatos', 'CarpetaPrivada'] + nombres)}\n\n"
        "annotation __PBI_TimeIntelligenceEnabled = 0\n\n" + "\n".join(f"ref table {q(n)}" for n in nombres) + "\n", encoding="utf-8")
    (d / "expressions.tmdl").write_text(
        f'expression CarpetaDatos = "{str(DATOS)}\\" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]\n'
        f"\tlineageTag: {tag()}\n\n\tannotation PBI_ResultType = Text\n\n"
        f'expression CarpetaPrivada = "{str(PRIV)}\\" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]\n'
        f"\tlineageTag: {tag()}\n\n\tannotation PBI_ResultType = Text\n", encoding="utf-8")
    T = d / "tables"
    (T / "dim_municipio.tmdl").write_text(tmdl_municipio(t["dim_municipio"], priv["intendencias"]), encoding="utf-8")
    orden = {"dim_eleccion": {"etiqueta": "orden", "rotulo": "orden"}, "dim_espacio": {"espacio_nombre": "orden"},
             "dim_fuerza": {"fuerza_intendente": "orden"}, "capa_mapa": {"capa": "orden"}, "prospectos": {"prioridad": "orden_prioridad"}}
    for n in ["dim_espacio", "dim_eleccion", "dim_fuerza", "fact_votos", "fact_participacion", "fact_motor_2027", "capa_mapa", "escenarios_2027"]:
        (T / f"{n}.tmdl").write_text(tmdl_simple(n, t[n], orden=orden.get(n), ocultas={"cod_indec", "eleccion", "espacio"} if n.startswith("fact") else set()), encoding="utf-8")
    for n in ["prospectos", "noticias"]:
        (T / f"{n}.tmdl").write_text(tmdl_simple(n, priv[n], "CarpetaPrivada", orden.get(n), {"cod_indec"}), encoding="utf-8")
    out = [f"table Medidas\n\tlineageTag: {tag()}\n"]
    for n, expr, fmt, carpeta, cat in medidas(t["meta_svg"]):
        if "\n" in expr:
            s = f"\tmeasure {q(n)} =\n" + "\n".join("\t\t\t" + x for x in expr.split("\n")) + "\n"
        else:
            s = f"\tmeasure {q(n)} = {expr}\n"
        if fmt:
            s += f"\t\tformatString: {fmt}\n"
        if cat:
            s += f"\t\tdataCategory: {cat}\n"
        s += f"\t\tdisplayFolder: {carpeta}\n\t\tlineageTag: {tag()}\n"
        out.append(s)
    out.append(f"\tcolumn x\n\t\tdataType: string\n\t\tisHidden\n\t\tlineageTag: {tag()}\n\t\tsummarizeBy: none\n\t\tsourceColumn: x\n")
    out.append("\tpartition Medidas = m\n\t\tmode: import\n\t\tsource = #table(type table [x = text], {})\n\n\tannotation PBI_ResultType = Table\n")
    (T / "Medidas.tmdl").write_text("\n".join(out), encoding="utf-8")
    rel = b.RELACIONES + [("prospectos", "cod_indec", "dim_municipio", "cod_indec"), ("noticias", "cod_indec", "dim_municipio", "cod_indec")]
    (d / "relationships.tmdl").write_text("\n".join(
        f"relationship {uuid.uuid5(uuid.NAMESPACE_URL, a + ca + bb)}\n\tfromColumn: {a}.{ca}\n\ttoColumn: {bb}.{cb}\n" for a, ca, bb, cb in rel),
        encoding="utf-8")


# ================================================================== reporte
PAGS = [("inicio", "Inicio"), ("dashboard", "Dashboard"), ("mapa", "Mapa"), ("ficha", "Ficha"), ("prospectos", "Prospectos"),
        ("noticias", "Noticias"), ("elecciones", "Elecciones"), ("analisis", "Análisis 2027")]
TT = "tooltip_municipio"
MC = lambda t, c: col(t, c)  # noqa: E731
DM = lambda c: col("dim_municipio", c)  # noqa: E731


def fondo(sin=False):
    return {"background": [{"properties": {"show": lit(not sin)}}], "border": [{"properties": {"show": lit(not sin)}}]}


def tooltip_pagina():
    return {"visualTooltip": [{"properties": {"show": lit(True), "type": lit("ReportPage"), "section": lit(TT)}}]}


def titulo_medida(nombre: str, tam=12) -> dict:
    return {"title": [{"properties": {"show": lit(True), "text": {"expr": {"Measure": med(nombre)["Measure"]}}, "fontSize": lit(tam)}}]}


def boton(p, nombre, x, y, w, h, texto, destino=None, url=None, atras=False, relleno="#1B0A3D", tinta="#F2EBFA", tam=10):
    link = {"show": lit(True)}
    if atras:
        link["type"] = lit("Back")
    elif destino:
        link |= {"type": lit("PageNavigation"), "navigationSection": lit(destino)}
    else:
        link |= {"type": lit("WebUrl"), "webUrl": lit(url)}
    # El rótulo y el color van en un cuadro de texto (se dibuja siempre); encima, un botón transparente
    # hace la navegación. Así no dependemos de cómo cada versión de Power BI lee el texto de los botones.
    lineas = [[(texto, {"fontSize": f"{tam}pt", "fontWeight": "bold", "color": tinta})]]
    b.texto(p, f"{nombre}_rotulo", x, y, w, h, lineas)
    v = p.visuales[-1]["visual"]
    for par in v["objects"]["general"][0]["properties"]["paragraphs"]:
        par["horizontalTextAlignment"] = "center"
    v["visualContainerObjects"] = {
        "background": [{"properties": {"show": lit(True), "color": color(relleno), "transparency": lit(0)}}],
        "border": [{"properties": {"show": lit(True), "color": color("#3D2A63"), "radius": lit(10)}}],
        "padding": [{"properties": {"top": lit(int(max(2, (h - tam * 1.9) // 2))), "bottom": lit(0), "left": lit(4), "right": lit(4)}}]}
    p.add(nombre, "actionButton", x, y, w, h,
          objetos={"icon": [{"properties": {"shapeType": lit("blank")}, "selector": {"id": "default"}}],
                   "text": [{"properties": {"show": lit(False)}, "selector": {"id": "default"}}],
                   "fill": [{"properties": {"show": lit(True), "fillColor": color("#FFFFFF"), "transparency": lit(100)}, "selector": {"id": "default"}},
                            {"properties": {"show": lit(True), "fillColor": color("#FFFFFF"), "transparency": lit(75)}, "selector": {"id": "hover"}}],
                   "outline": [{"properties": {"show": lit(False)}, "selector": {"id": "default"}}]},
          contenedor={"visualLink": [{"properties": link}], "background": [{"properties": {"show": lit(False)}}],
                      "border": [{"properties": {"show": lit(False)}}], "dropShadow": [{"properties": {"show": lit(False)}}]})


def encabezado(p, activa):
    b.texto(p, f"{p.nombre}_marca", 10, 4, 220, 50, [[("ATLAS ANALYTICS", {"fontSize": "8pt", "fontWeight": "bold", "color": "#C40BFF"})],
                                                     [("Intendencias PBA 2027", {"fontSize": "15pt", "fontWeight": "bold", "color": "#F2EBFA"})]])
    x = 236
    for clave, vis in PAGS:
        on = clave == activa
        boton(p, f"{p.nombre}_nav_{clave}", x, 12, 126, 32, vis.upper(), destino=clave, relleno="#F2A65A" if on else "#1F3A6E", tinta="#12042E" if on else "#F2EBFA", tam=9)
        x += 130


def slicer(p, nombre, x, y, w, h, campo, tit, modo="Basic", unico=False, horizontal=False, buscar=False):
    obj = {"data": [{"properties": {"mode": lit(modo)}}],
           "selection": [{"properties": {"strictSingleSelect": lit(unico), "selectAllCheckboxEnabled": lit(False), "singleSelect": lit(unico)}}],
           "header": [{"properties": {"show": lit(True), "text": lit(tit), "fontColor": color("#E9B6FF"), "textSize": lit(9)}}],
           "items": [{"properties": {"fontColor": color("#F2EBFA"), "background": color("#2B3F7A"), "textSize": lit(9)}}]}
    if horizontal:
        obj["general"] = [{"properties": {"orientation": lit(1)}}]
    p.add(nombre, "slicer", x, y, w, h, roles={"Values": [campo]}, objetos=obj)


def tarjeta(p, nombre, x, y, w, h, medida, etiqueta, tinta="#F2EBFA", tam=20, tt=False):
    cont = titulo(None) | {"background": [{"properties": {"show": lit(True), "color": color("#1B0A3D")}}]}
    if tt:
        cont |= tooltip_pagina()
    p.add(nombre, "card", x, y, w, h, roles={"Values": [med(medida)]},
          objetos={"labels": [{"properties": {"color": color(tinta), "fontSize": lit(tam)}}],
                   "categoryLabels": [{"properties": {"show": lit(True), "color": color("#A08FC2"), "fontSize": lit(9)}}]}, contenedor=cont)
    p.visuales[-1]["visual"]["query"]["queryState"]["Values"]["projections"][0]["displayName"] = etiqueta


def tabla_v(p, nombre, x, y, w, h, campos, tit=None, orden=None, nombres=None, formato_col=None, imagen=None, tt=True, tam=9, tit_medida=None):
    obj = {"values": [{"properties": {"fontColorPrimary": color("#F2EBFA"), "backColorPrimary": color("#1B0A3D"),
                                      "backColorSecondary": color("#220E4A"), "fontSize": lit(tam)}}],
           "columnHeaders": [{"properties": {"fontColor": color("#E9B6FF"), "backColor": color("#12042E"), "fontSize": lit(tam)}}],
           "grid": [{"properties": {"gridHorizontalColor": color("#2E1A57"), "rowPadding": lit(3)} | ({"imageHeight": lit(imagen)} if imagen else {})}],
           "total": [{"properties": {"totals": lit(False)}}]}
    for meta, medida in (formato_col or []):
        obj["values"].append({"properties": {"backColor": {"solid": {"color": {"expr": {"Measure": med(medida)["Measure"]}}}}, "fontColor": color("#12042E")},
                              "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}], "metadata": meta}})
    cont = titulo(tit) if not tit_medida else titulo_medida(tit_medida)
    if tt:
        cont |= tooltip_pagina()
    p.add(nombre, "tableEx", x, y, w, h, roles={"Values": campos}, objetos=obj, contenedor=cont, orden=orden)
    if nombres:
        for pr, n in zip(p.visuales[-1]["visual"]["query"]["queryState"]["Values"]["projections"], nombres):
            if n:
                pr["displayName"] = n


def imagen_svg(p, nombre, x, y, w, h, medida, alto):
    """Tabla de una celda que muestra la imagen SVG de una medida (dataCategory ImageUrl)."""
    p.add(nombre, "tableEx", x, y, w, h, roles={"Values": [med(medida)]},
          objetos={"values": [{"properties": {"backColorPrimary": color("#1B0A3D"), "backColorSecondary": color("#1B0A3D")}}],
                   "columnHeaders": [{"properties": {"fontColor": color("#1B0A3D"), "backColor": color("#1B0A3D"), "fontSize": lit(1)}}],
                   "grid": [{"properties": {"imageHeight": lit(alto), "gridHorizontal": lit(False), "gridVertical": lit(False),
                                            "outlineColor": color("#1B0A3D"), "rowPadding": lit(0)}}],
                   "total": [{"properties": {"totals": lit(False)}}]},
          contenedor=titulo(None))
    p.visuales[-1]["visual"]["query"]["queryState"]["Values"]["projections"][0]["displayName"] = " "


def barras(p, nombre, x, y, w, h, categoria, medida, pares, tit, tipo="clusteredBarChart", serie=None, orden=None, tt=True):
    roles = {"Category": [categoria], "Y": [med(medida) if isinstance(medida, str) else medida]}
    if serie:
        roles["Series"] = [serie]
    obj = {"labels": [{"properties": {"show": lit(True), "color": color("#F2EBFA")}}],
           "legend": [{"properties": {"show": lit(bool(serie)), "position": lit("Top"), "labelColor": color("#DCD2EA")}}]}
    if pares:
        obj["dataPoint"] = colores_por(serie or categoria, pares)
    cont = titulo(tit)
    if tt:
        cont |= tooltip_pagina()
    p.add(nombre, tipo, x, y, w, h, roles=roles, objetos=obj, contenedor=cont, orden=orden)


def construir(t: dict, esquemas: Path | None) -> None:
    rep = PBI / f"{NOMBRE}.Report"
    shutil.rmtree(rep, ignore_errors=True)
    (rep / "definition" / "pages").mkdir(parents=True)
    (rep / "StaticResources" / "RegisteredResources").mkdir(parents=True)
    tema = json.loads(json.dumps({  # tema Atlas Analytics
        "name": "Atlas Analytics Intendencias", "dataColors": ["#29A3F0", "#9B4DFF", "#FF6FB5", "#2FC4A6", "#F5C518", "#E94F4F", "#C40BFF",
                                                                "#FF8A3D", "#7E57FF", "#3DDC97", "#FFB547", "#4DD0E1"],
        "background": "#12042E", "foreground": "#F2EBFA", "tableAccent": "#C40BFF",
        "textClasses": {"title": {"fontFace": "Segoe UI Semibold", "color": "#F2EBFA", "fontSize": 11},
                        "label": {"fontFace": "Segoe UI", "color": "#DCD2EA", "fontSize": 9},
                        "callout": {"fontFace": "Segoe UI Semibold", "color": "#F2EBFA", "fontSize": 22}},
        "visualStyles": {
            "page": {"*": {"background": [{"color": {"solid": {"color": "#12042E"}}, "transparency": 0}],
                           "outspace": [{"color": {"solid": {"color": "#0B0220"}}, "transparency": 0}]}},
            "*": {"*": {"background": [{"show": True, "color": {"solid": {"color": "#1B0A3D"}}, "transparency": 0}],
                        "border": [{"show": True, "color": {"solid": {"color": "#2E1A57"}}, "radius": 12}],
                        "dropShadow": [{"show": True, "color": {"solid": {"color": "#000000"}}, "transparency": 70, "position": "Outer"}],
                        "title": [{"fontColor": {"solid": {"color": "#F2EBFA"}}, "fontSize": 11}],
                        "visualHeader": [{"background": {"solid": {"color": "#1B0A3D"}}, "foreground": {"solid": {"color": "#A08FC2"}}}],
                        "categoryAxis": [{"labelColor": {"solid": {"color": "#A08FC2"}}, "gridlineColor": {"solid": {"color": "#2E1A57"}}}],
                        "valueAxis": [{"labelColor": {"solid": {"color": "#A08FC2"}}, "gridlineColor": {"solid": {"color": "#2E1A57"}}}],
                        "legend": [{"labelColor": {"solid": {"color": "#DCD2EA"}}}]}},
            "multiRowCard": {"*": {"dataLabels": [{"color": {"solid": {"color": "#F2EBFA"}}, "fontSize": 11}],
                                   "categoryLabels": [{"color": {"solid": {"color": "#A08FC2"}}, "fontSize": 8}],
                                   "card": [{"barShow": True, "barColor": {"solid": {"color": "#C40BFF"}}}]}}}}))
    (rep / "StaticResources" / "RegisteredResources" / "AtlasAnalytics.json").write_text(json.dumps(tema, indent=2, ensure_ascii=False), encoding="utf-8")
    shutil.copy2(DATOS / "pba_municipios.topojson", rep / "StaticResources" / "RegisteredResources" / b.MAPA)

    P = []
    fz = col("dim_fuerza", "fuerza_intendente")
    esp26, esc27, conc, tam = DM("espacio_2026"), DM("escenario_2027"), DM("gano_concejales_2025"), DM("tamano")

    # ------------------------------------------------------------ Inicio
    p = Pagina("inicio", "Inicio")
    encabezado(p, "inicio")
    b.texto(p, "inicio_hero", 24, 64, 1232, 92, [[("INTENDENCIAS PBA 2027", {"fontSize": "30pt", "fontWeight": "bold", "color": "#F2EBFA"})],
                                                [("135 municipios · intendentes · sucesores · rivales · noticias · y el análisis electoral 2007-2025 con el motor de escenarios 2027",
                                                  {"fontSize": "12pt", "color": "#E9B6FF"})]])
    ks = [("Municipios", "Municipios"), ("Población", "Población 2022"), ("Sucesión abierta", "Sucesión abierta"), ("Reelección posible", "Reelección posible"),
          ("Zona gris", "Zona gris (judicial)"), ("Prospectos", "Prospectos"), ("Rivales", "Rivales"), ("Prioridad alta", "Prioridad alta")]
    for i, (mm, et) in enumerate(ks):
        tarjeta(p, f"inicio_k{i}", 24 + i * 154, 166, 148, 82, mm, et, ["#F2EBFA", "#F2EBFA", "#FF8A3D", "#3DDC97", "#FFD54F", "#F2EBFA", "#E94F4F", "#C40BFF"][i])
    menu = [("dashboard", "DASHBOARD · tablero con filtros, tarjetas y gráficos", "#3D6FD9"), ("mapa", "MAPAS · político, 2027, 2025, motor y 10 capas", "#F28C28"),
            ("ficha", "FICHA · todo de un municipio en una página", "#1F3A6E"), ("prospectos", "PROSPECTOS · CRM de 980 personas", "#C62828"),
            ("noticias", "NOTICIAS · 856 titulares con enlace", "#5A5A6E"), ("elecciones", "ELECCIONES · 2007-2025, animado", "#7B2FBE"),
            ("analisis", "ANÁLISIS 2027 · motor de escenarios y hallazgos", "#C40BFF")]
    for i, (dest, txt, c) in enumerate(menu):
        boton(p, f"inicio_menu_{dest}", 24 + (i % 2) * 400, 264 + (i // 2) * 104, 388, 92, txt, destino=dest, relleno=c, tam=13)
    b.texto(p, "inicio_como", 840, 264, 416, 300, [
        [("Cómo usar", {"fontSize": "12pt", "fontWeight": "bold", "color": "#E9B6FF"})],
        [("Los botones de arriba llevan a cada página. Los filtros en botones cruzan todo el tablero. "
          "Pasá el mouse sobre un municipio en cualquier tabla o gráfico para ver su ficha rápida con foto; "
          "clic derecho > Obtener detalles > Ficha para abrir la ficha completa.", {"fontSize": "10pt", "color": "#DCD2EA"})],
        [("Mapa: elegí la capa (espacio 2026, escenario 2027, concejales 2025, oportunidad, ganador de cada elección, motor 2027, NBI, barrios populares). "
          "Lo que queda fuera de los filtros se apaga; el municipio elegido se resalta.", {"fontSize": "10pt", "color": "#DCD2EA"})],
        [("Fuentes: Super Excel Intendencias PBA 2027 (Atlas Analytics), DINE, Junta Electoral PBA, INDEC, RENABAP, Municipios Argentinos.",
          {"fontSize": "8pt", "color": "#8A7AAB"})]])
    boton(p, "inicio_sim", 840, 580, 204, 44, "SIMULADOR 2027 ↗", url=b.SIMULADOR, relleno="#C40BFF", tinta="#12042E", tam=11)
    boton(p, "inicio_web", 1052, 580, 204, 44, "TABLERO WEB ↗", url=b.TABLERO_WEB, tam=11)
    P.append(p)

    # ------------------------------------------------------------ Dashboard
    p = Pagina("dashboard", "Dashboard")
    encabezado(p, "dashboard")
    slicer(p, "dash_s_sec", 10, 56, 232, 112, DM("seccion"), "Sección", horizontal=True)
    slicer(p, "dash_s_esp", 10, 172, 232, 112, esp26, "Espacio 2026", horizontal=True)
    slicer(p, "dash_s_esc", 10, 288, 232, 92, esc27, "Escenario 2027", horizontal=True)
    slicer(p, "dash_s_tam", 10, 384, 232, 92, tam, "Tamaño", horizontal=True)
    slicer(p, "dash_s_conc", 10, 480, 232, 132, conc, "Ganó concejales 2025", horizontal=True)
    slicer(p, "dash_s_op", 10, 616, 232, 96, DM("nivel_oportunidad"), "Nivel de oportunidad", horizontal=True)
    for i, (mm, et, c) in enumerate([("Municipios", "Municipios", "#F2EBFA"), ("Población", "Población", "#F2EBFA"), ("Sucesión abierta", "Sucesión abierta", "#FF8A3D"),
                                     ("Reelección posible", "Reelección posible", "#3DDC97"), ("Zona gris", "Zona gris", "#FFD54F"), ("Prospectos", "Prospectos", "#C40BFF")]):
        tarjeta(p, f"dash_k{i}", 250 + i * 172, 56, 166, 76, mm, et, c)
    barras(p, "dash_esp", 250, 140, 336, 250, esp26, "Municipios", C_ESPACIO26, "Municipios por espacio 2026", orden=(med("Municipios"), "Descending"))
    barras(p, "dash_sec", 594, 140, 336, 250, DM("seccion"), "Población", None, "Población por sección", tipo="clusteredColumnChart",
           orden=(DM("seccion"), "Ascending"))
    p.add("dash_esc", "donutChart", 938, 140, 330, 250, roles={"Category": [esc27], "Y": [med("Municipios")]},
          objetos={"dataPoint": colores_por(esc27, C_ESCENARIO), "legend": [{"properties": {"show": lit(True), "position": lit("Bottom"), "labelColor": color("#DCD2EA")}}],
                   "labels": [{"properties": {"show": lit(True), "labelStyle": lit("Data value, percent of total")}}]},
          contenedor=titulo("Escenario 2027") | tooltip_pagina())
    tabla_v(p, "dash_tabla", 250, 398, 1018, 314,
            [DM("seccion"), DM("municipio"), DM("pob"), DM("en_ejercicio"), esp26, esc27, conc, DM("nivel_oportunidad"), med("Prospectos"), med("% Peronismo"), med("P(peronismo) 2027 en ficha")],
            "Municipios (clic derecho > Obtener detalles > Ficha)", orden=(DM("pob"), "Descending"),
            nombres=["Sec.", "Municipio", "Población", "En ejercicio", "Espacio 2026", "Escenario 2027", "Concejales 2025", "Oportunidad", "Prospectos", "% Peronismo 2025", "P(peronismo) 2027"],
            formato_col=[("dim_municipio.espacio_2026", "Color espacio 2026"), ("dim_municipio.escenario_2027", "Color escenario"),
                         ("dim_municipio.nivel_oportunidad", "Color oportunidad")])
    P.append(p)

    # ------------------------------------------------------------ Mapas interactivos (mapa de formas) + mapa de capas (SVG)
    SUBMAPAS = [("mapa", "POLÍTICO"), ("mapa_2027", "2027"), ("mapa_2025", "2025"), ("mapa_motor", "MOTOR 2027"), ("mapa_capas", "10 CAPAS")]

    def submenu(p, activa):
        for i, (k, txt) in enumerate(SUBMAPAS):
            on = k == activa
            boton(p, f"{p.nombre}_sub_{k}", 10, 56 + i * 38, 232, 34, txt, destino=k, relleno="#C40BFF" if on else "#2B3F7A",
                  tinta="#12042E" if on else "#F2EBFA", tam=9)

    def pagina_mapa(clave, visible, leyenda, pares, tit, extra=None):
        p = Pagina(clave, visible)
        encabezado(p, "mapa")
        submenu(p, clave)
        slicer(p, f"{clave}_s_sec", 10, 252, 232, 112, DM("seccion"), "Sección", horizontal=True)
        slicer(p, f"{clave}_s_tam", 10, 368, 232, 92, tam, "Tamaño", horizontal=True)
        if extra:
            extra(p)
        b.mapa(p, f"{clave}_mapa", 250, 56, 640, 656, leyenda, pares, tit + " · clic en un municipio para filtrar")
        p.visuales[-1]["visual"]["visualContainerObjects"] |= tooltip_pagina()
        tarjeta(p, f"{clave}_k1", 898, 56, 182, 70, "Municipios", "Municipios")
        tarjeta(p, f"{clave}_k2", 1086, 56, 182, 70, "Población", "Población")
        p.add(f"{clave}_ficha", "multiRowCard", 898, 132, 370, 200,
              roles={"Values": [DM("municipio"), DM("en_ejercicio"), esp26, esc27, conc]}, contenedor=titulo("Selección"))
        for prj, n in zip(p.visuales[-1]["visual"]["query"]["queryState"]["Values"]["projections"],
                          ["Municipio", "En ejercicio", "Espacio 2026", "Escenario 2027", "Concejales 2025"]):
            prj["displayName"] = n
        tabla_v(p, f"{clave}_tabla", 898, 338, 370, 374, [DM("municipio"), leyenda, DM("pob")], "Municipios",
                orden=(DM("pob"), "Descending"), nombres=["Municipio", None, "Población"], tam=8)
        return p

    P.append(pagina_mapa("mapa", "Mapa político", esp26, C_ESPACIO26, "Espacio que gobierna cada municipio (2026)",
                         lambda p: slicer(p, "mapa_s_esp", 10, 464, 232, 112, esp26, "Espacio 2026", horizontal=True)))
    P.append(pagina_mapa("mapa_2027", "Mapa 2027", esc27, C_ESCENARIO, "¿El intendente puede reelegir en 2027?",
                         lambda p: slicer(p, "mapa_2027_s_esc", 10, 464, 232, 92, esc27, "Escenario 2027", horizontal=True)))
    P.append(pagina_mapa("mapa_2025", "Mapa 2025", conc, C_CONCEJALES, "Fuerza que ganó concejales (7/9/2025)",
                         lambda p: slicer(p, "mapa_2025_s_conc", 10, 464, 232, 132, conc, "Ganó concejales 2025", horizontal=True)))
    P.append(pagina_mapa("mapa_motor", "Mapa motor 2027", col("fact_motor_2027", "rango_p"), b.RANGOS_P,
                         "Motor 2027: quién gana cada municipio (1.000 simulaciones)",
                         lambda p: slicer(p, "mapa_motor_s_esc", 10, 464, 232, 112, col("fact_motor_2027", "escenario"), "Escenario del motor",
                                          unico=True)))

    p = Pagina("mapa_capas", "Mapa de capas")
    encabezado(p, "mapa")
    submenu(p, "mapa_capas")
    slicer(p, "capas_s_capa", 10, 252, 232, 250, col("capa_mapa", "capa"), "Capa del mapa", unico=True)
    slicer(p, "capas_s_el", 10, 506, 232, 58, col("dim_eleccion", "rotulo"), "Elección (capas de voto)", modo="Dropdown", unico=True)
    slicer(p, "capas_s_mot", 10, 568, 232, 58, col("fact_motor_2027", "escenario"), "Escenario del motor 2027", modo="Dropdown", unico=True)
    slicer(p, "capas_s_sec", 10, 630, 232, 82, DM("seccion"), "Sección", horizontal=True)
    tarjeta(p, "capas_tit", 250, 56, 1018, 44, "Título mapa", "Capa", "#E9B6FF", 13)
    imagen_svg(p, "capas_prov", 250, 106, 420, 606, "Mapa Provincia", 590)
    imagen_svg(p, "capas_conu", 678, 106, 330, 300, "Mapa Conurbano", 285)
    imagen_svg(p, "capas_ley", 678, 412, 330, 300, "Leyenda mapa", 230)
    tabla_v(p, "capas_tabla", 1016, 106, 252, 606, [DM("municipio"), esp26, esc27], "Clic para resaltar en el mapa",
            nombres=["Municipio", "Espacio", "Escenario"], formato_col=[("dim_municipio.espacio_2026", "Color espacio 2026"), ("dim_municipio.escenario_2027", "Color escenario")], tam=8)
    P.append(p)

    # ------------------------------------------------------------ Ficha (obtención de detalles)
    p = Pagina("ficha", "Ficha")
    encabezado(p, "ficha")
    slicer(p, "ficha_s_muni", 10, 56, 232, 58, DM("municipio"), "Municipio", modo="Dropdown", unico=True)
    boton(p, "ficha_atras", 10, 120, 232, 34, "◄ VOLVER", atras=True)
    tabla_v(p, "ficha_foto", 10, 160, 232, 230, [DM("foto_url"), DM("logo_url")], None, nombres=["Intendente", "Fuerza"], imagen=150, tt=False)
    tarjeta(p, "ficha_tit", 250, 56, 1018, 44, "Título ficha", "Ficha", "#E9B6FF", 14)
    p.add("ficha_datos", "multiRowCard", 250, 106, 500, 400,
          roles={"Values": [DM("en_ejercicio"), DM("electo_2023"), esp26, esc27, DM("pct_ganador_2023"), DM("segundo_2023"), conc, DM("bancas_2025"),
                            DM("eleccion_2025_pareja"), DM("oposicion_esperable"), DM("principales_opositores"), tam, DM("pob"), DM("nivel_oportunidad")]},
          contenedor=titulo("Datos del municipio"))
    for pr, n in zip(p.visuales[-1]["visual"]["query"]["queryState"]["Values"]["projections"],
                     ["En ejercicio hoy", "Electo 2023", "Espacio 2026", "Escenario 2027", "% ganador 2023", "Segundo 2023", "Ganó concejales 2025",
                      "Bancas 2025", "Elección 2025 pareja", "Oposición esperable", "Principales opositores", "Tamaño", "Población 2022", "Oportunidad"]):
        pr["displayName"] = n
    for i, (mm, et, c) in enumerate([("% Peronismo", "% peronismo (Dip. 2025)", "#29A3F0"), ("% Derecha", "% LLA-PRO (Dip. 2025)", "#9B4DFF"),
                                     ("P(peronismo) 2027 en ficha", "P(peronismo) 2027", "#C40BFF"), ("Hogares con NBI %", "Hogares con NBI", "#FFB547")]):
        tarjeta(p, f"ficha_k{i}", 758 + (i % 2) * 258, 106 + (i // 2) * 84, 252, 78, mm, et, c)
    p.add("ficha_linea", "lineChart", 758, 274, 510, 232,
          roles={"Category": [col("dim_eleccion", "etiqueta")], "Y": [med("% Peronismo"), med("% Derecha")]},
          objetos={"legend": [{"properties": {"show": lit(True), "position": lit("Top"), "labelColor": color("#DCD2EA")}}]},
          contenedor=titulo("Evolución del voto 2007-2025"), orden=(col("dim_eleccion", "etiqueta"), "Ascending"))
    tabla_v(p, "ficha_links", 10, 396, 232, 110, [DM("google_maps_url"), DM("noticias_url"), DM("perfil_pdf_url"), DM("wikipedia_url")], "Enlaces",
            nombres=["Mapa", "Noticias", "Perfil PDF", "Wikipedia"], tt=False)
    tabla_v(p, "ficha_prosp", 10, 512, 620, 200, [col("prospectos", "nombre"), col("prospectos", "espacio"), col("prospectos", "rol"),
                                                 col("prospectos", "por_que"), col("prospectos", "prioridad")], "Prospectos de este municipio",
            orden=(col("prospectos", "prioridad"), "Ascending"), nombres=["Nombre", "Espacio", "Rol", "Por qué", "Prioridad"],
            formato_col=[("prospectos.prioridad", "Color prioridad")], tt=False)
    tabla_v(p, "ficha_notas", 638, 512, 630, 200, [col("noticias", "fecha"), col("noticias", "titular"), col("noticias", "medio"), col("noticias", "url")],
            "Últimas noticias", orden=(col("noticias", "fecha"), "Descending"), nombres=["Fecha", "Titular", "Medio", "Link"], tt=False)
    p.filtros = [{"name": "dt_municipio", "field": DM("municipio"), "type": "Categorical", "howCreated": "Drillthrough"}]
    p.binding = {"name": "pb_ficha", "type": "Drillthrough", "parameters": [{"name": "par_municipio", "boundFilter": "dt_municipio", "fieldExpr": DM("municipio")}]}
    p.tipo = "Drillthrough"
    P.append(p)

    # ------------------------------------------------------------ Prospectos
    p = Pagina("prospectos", "Prospectos")
    encabezado(p, "prospectos")
    pr = lambda c: col("prospectos", c)  # noqa: E731
    slicer(p, "pro_s_rol", 10, 56, 232, 112, pr("rol"), "Rol", horizontal=True)
    slicer(p, "pro_s_pri", 10, 172, 232, 72, pr("prioridad"), "Prioridad", horizontal=True)
    slicer(p, "pro_s_fam", 10, 248, 232, 112, pr("fuerza_familia"), "Fuerza (familia)", horizontal=True)
    slicer(p, "pro_s_est", 10, 364, 232, 112, pr("estado"), "Estado del contacto", horizontal=True)
    slicer(p, "pro_s_sec", 10, 480, 232, 112, DM("seccion"), "Sección", horizontal=True)
    slicer(p, "pro_s_mun", 10, 596, 232, 58, DM("municipio"), "Municipio", modo="Dropdown")
    for i, (mm, et, c) in enumerate([("Prospectos", "Prospectos", "#F2EBFA"), ("Rivales", "Rivales / oposición", "#E94F4F"), ("Prioridad alta", "Prioridad alta", "#C40BFF"),
                                     ("Contactados", "Contactados", "#3DDC97"), ("% contactados", "% contactados", "#3DDC97")]):
        tarjeta(p, f"pro_k{i}", 250 + i * 204, 56, 198, 76, mm, et, c)
    barras(p, "pro_fam", 250, 140, 500, 220, pr("fuerza_familia"), "Prospectos", C_FAMILIA, "Prospectos por fuerza", orden=(med("Prospectos"), "Descending"), tt=False)
    barras(p, "pro_rol", 758, 140, 510, 220, pr("rol"), "Prospectos", None, "Por rol y prioridad", serie=pr("prioridad"), tipo="barChart", tt=False)
    p.visuales[-1]["visual"]["objects"]["dataPoint"] = colores_por(pr("prioridad"), [("Alta", "#C40BFF"), ("Media", "#5B3FA8"), ("Baja", "#3A2A66")])
    tabla_v(p, "pro_tabla", 250, 368, 1018, 344, [pr("municipio"), pr("nombre"), pr("espacio"), pr("rol"), pr("por_que"), pr("detalle"), pr("prioridad"),
                                                  pr("estado"), pr("proximo_paso"), pr("fuente")], "CRM · prospectos", orden=(pr("prioridad"), "Ascending"),
            nombres=["Municipio", "Nombre", "Espacio", "Rol", "Por qué", "Detalle", "Prioridad", "Estado", "Próximo paso", "Fuente"],
            formato_col=[("prospectos.prioridad", "Color prioridad")], tt=False)
    P.append(p)

    # ------------------------------------------------------------ Noticias
    p = Pagina("noticias", "Noticias")
    encabezado(p, "noticias")
    nt = lambda c: col("noticias", c)  # noqa: E731
    slicer(p, "not_s_fecha", 10, 56, 232, 90, nt("fecha"), "Fecha", modo="Between")
    slicer(p, "not_s_mun", 10, 152, 232, 58, DM("municipio"), "Municipio", modo="Dropdown")
    slicer(p, "not_s_sec", 10, 216, 232, 112, DM("seccion"), "Sección", horizontal=True)
    slicer(p, "not_s_esc", 10, 332, 232, 92, esc27, "Escenario 2027", horizontal=True)
    slicer(p, "not_s_medio", 10, 430, 232, 282, nt("medio"), "Medio")
    tarjeta(p, "not_k1", 250, 56, 250, 76, "Noticias", "Noticias")
    tarjeta(p, "not_k2", 508, 56, 250, 76, "Última noticia", "Última noticia", "#E9B6FF")
    barras(p, "not_mes", 766, 56, 502, 160, nt("mes"), "Noticias", None, "Noticias por mes", tipo="clusteredColumnChart", orden=(nt("mes"), "Ascending"), tt=False)
    barras(p, "not_mun", 250, 140, 508, 200, DM("municipio"), "Noticias", None, "Municipios con más noticias", orden=(med("Noticias"), "Descending"))
    tabla_v(p, "not_tabla", 250, 348, 1018, 364, [nt("fecha"), nt("municipio"), nt("titular"), nt("medio"), nt("url")], "Titulares (Google News)",
            orden=(nt("fecha"), "Descending"), nombres=["Fecha", "Municipio", "Titular", "Medio", "Abrir"], tt=False)
    P.append(p)

    # ------------------------------------------------------------ Elecciones
    p = Pagina("elecciones", "Elecciones")
    encabezado(p, "elecciones")
    slicer(p, "el_s_el", 10, 56, 232, 58, col("dim_eleccion", "rotulo"), "Elección", modo="Dropdown", unico=True)
    slicer(p, "el_s_sec", 10, 120, 232, 112, DM("seccion"), "Sección", horizontal=True)
    slicer(p, "el_s_esp", 10, 236, 232, 112, esp26, "Espacio 2026", horizontal=True)
    slicer(p, "el_s_zona", 10, 352, 232, 58, DM("zona"), "Zona", horizontal=True)
    for i, (mm, et, c) in enumerate([("Ganador", "Ganador", "#E9B6FF"), ("% Ganador", "% del ganador", "#F2EBFA"), ("Margen (pts)", "Margen (pts)", "#F2EBFA"),
                                     ("Participación", "Participación", "#F2EBFA"), ("Electores", "Electores", "#F2EBFA")]):
        tarjeta(p, f"el_k{i}", 250 + i * 204, 56, 198, 76, mm, et, c)
    gan_esp = col("dim_espacio", "espacio_nombre")
    pares_esp = [(r.espacio_nombre, r.color) for r in t["dim_espacio"].itertuples()]
    p.add("el_anim", "scatterChart", 250, 140, 620, 572,
          roles={"Category": [DM("municipio")], "Series": [esp26], "X": [med("Participación")], "Y": [med("% Peronismo")], "Size": [med("Electores")],
                 "Play": [col("dim_eleccion", "etiqueta")]},
          objetos={"dataPoint": colores_por(esp26, C_ESPACIO26), "legend": [{"properties": {"show": lit(True), "position": lit("Top"), "labelColor": color("#DCD2EA")}}]},
          contenedor=titulo("Animación 2007-2025: participación (X) y voto peronista (Y) por municipio · ▶ para reproducir") | tooltip_pagina())
    barras(p, "el_barras", 878, 140, 390, 280, gan_esp, "% Voto", pares_esp, "% sobre votos positivos", orden=(med("% Voto"), "Descending"), tt=False)
    p.add("el_linea", "lineChart", 878, 428, 390, 284, roles={"Category": [col("dim_eleccion", "etiqueta")], "Series": [gan_esp], "Y": [med("% Voto")]},
          objetos={"dataPoint": colores_por(gan_esp, pares_esp), "legend": [{"properties": {"show": lit(False)}}]},
          contenedor=titulo("Evolución por fuerza (todas las elecciones)"), orden=(col("dim_eleccion", "etiqueta"), "Ascending"))
    p.interacciones = [{"source": "el_s_el", "target": "el_linea", "type": "NoFilter"}, {"source": "el_s_el", "target": "el_anim", "type": "NoFilter"}]
    P.append(p)

    # ------------------------------------------------------------ Análisis 2027
    p = Pagina("analisis", "Análisis 2027")
    encabezado(p, "analisis")
    es = lambda c: col("escenarios_2027", c)  # noqa: E731
    slicer(p, "an_s_grupo", 10, 56, 232, 112, es("grupo"), "Tipo de escenario", horizontal=True)
    b.texto(p, "an_hallazgos", 10, 174, 232, 538, [
        [("Lo que encontramos", {"fontSize": "11pt", "fontWeight": "bold", "color": "#E9B6FF"})],
        [("• Si se repite octubre 2025, empate: el peronismo gana el 59 % de las simulaciones (+0,3 pts).", {"fontSize": "9pt", "color": "#DCD2EA"})],
        [("• Con la derecha dividida, el peronismo gana el 99-100 % aunque el PRO sea el 15 % de ella.", {"fontSize": "9pt", "color": "#DCD2EA"})],
        [("• Quién se suma a votar mueve 9 puntos (de −3,7 a +5,4). Más participación pareja no mueve nada.", {"fontSize": "9pt", "color": "#DCD2EA"})],
        [("• El voto perdido de Kicillof en 2025 se abstuvo (12,6 %, ~513.000); ninguno pasó a LLA-PRO.", {"fontSize": "9pt", "color": "#DCD2EA"})],
        [("• Ganar la intendencia no arrastra votos al gobernador (−0,2 pts).", {"fontSize": "9pt", "color": "#DCD2EA"})],
        [("• LLA-PRO avanzó relativamente en barrios populares 2023-2025, más allá del NBI.", {"fontSize": "9pt", "color": "#DCD2EA"})],
        [("• Diputados 2027: el peronismo queda en 41-44 de 92; el Senado lo retiene salvo que se repita octubre.", {"fontSize": "9pt", "color": "#DCD2EA"})]])
    tarjeta(p, "an_k1", 250, 56, 250, 76, "Municipios peronistas esperados", "Municipios peronistas esperados (motor)", "#29A3F0")
    tarjeta(p, "an_k2", 508, 56, 250, 76, "Municipios en disputa", "En disputa (20-80 %)", "#C40BFF")
    slicer(p, "an_s_mot", 766, 56, 502, 76, col("fact_motor_2027", "escenario"), "Escenario para tarjetas y tabla", horizontal=True, unico=True)
    p.add("an_margen", "clusteredBarChart", 250, 140, 620, 572, roles={"Category": [es("escenario")], "Y": [col("escenarios_2027", "margen")]},
          objetos={"labels": [{"properties": {"show": lit(True), "color": color("#F2EBFA")}}],
                   "dataPoint": [{"properties": {"fill": color("#C40BFF")}}]},
          contenedor=titulo("Margen del peronismo por escenario (mediana de 1.000 simulaciones, pts)"), orden=(col("escenarios_2027", "margen"), "Descending"))
    p.visuales[-1]["visual"]["query"]["queryState"]["Y"]["projections"][0]["field"] = {"Aggregation": {"Expression": col("escenarios_2027", "margen"), "Function": 0}}
    p.visuales[-1]["visual"]["query"]["queryState"]["Y"]["projections"][0]["queryRef"] = "Sum(escenarios_2027.margen)"
    p.visuales[-1]["visual"]["query"]["sortDefinition"]["sort"][0]["field"] = {"Aggregation": {"Expression": col("escenarios_2027", "margen"), "Function": 0}}
    tabla_v(p, "an_tabla", 878, 140, 390, 572, [DM("municipio"), col("fact_motor_2027", "p_gana_peronismo"), col("fact_motor_2027", "rango_p"), esp26],
            "Municipios: P(gana el peronismo)", orden=(col("fact_motor_2027", "p_gana_peronismo"), "Descending"),
            nombres=["Municipio", "P(peronismo)", "Categoría", "Espacio 2026"], formato_col=[("dim_municipio.espacio_2026", "Color espacio 2026")], tam=8)
    P.append(p)

    # ------------------------------------------------------------ Tooltip
    p = Pagina(TT, "Información emergente · municipio")
    tabla_v(p, "tt_foto", 4, 4, 112, 150, [DM("foto_url")], None, nombres=["Intendente"], imagen=100, tt=False)
    p.add("tt_datos", "multiRowCard", 120, 4, 196, 232, roles={"Values": [DM("municipio"), DM("en_ejercicio"), esp26, esc27, conc]}, contenedor=titulo(None))
    for prj, n in zip(p.visuales[-1]["visual"]["query"]["queryState"]["Values"]["projections"], ["Municipio", "En ejercicio", "Espacio 2026", "Escenario 2027", "Concejales 2025"]):
        prj["displayName"] = n
    tarjeta(p, "tt_k1", 4, 158, 112, 78, "% Peronismo", "% peronismo", "#29A3F0", 14)
    p.tamano, p.tipo, p.binding = (320, 240), "Tooltip", {"name": "pb_tooltip", "type": "Tooltip"}
    P.append(p)

    escribir_paginas(rep, P)
    if esquemas:
        b.validar(rep, esquemas)


def escribir_paginas(rep: Path, P: list) -> None:
    d = rep / "definition"
    for p in P:
        pd_ = d / "pages" / p.nombre
        (pd_ / "visuals").mkdir(parents=True)
        w, h = getattr(p, "tamano", (1280, 720))
        page = {"$schema": f"{SCHEMA}/page/2.0.0/schema.json", "name": p.nombre, "displayName": p.visible,
                "displayOption": "FitToPage", "height": h, "width": w}
        if getattr(p, "tipo", None):
            page["type"] = p.tipo
        if getattr(p, "binding", None):
            page["pageBinding"] = p.binding
        if getattr(p, "filtros", None):
            page["filterConfig"] = {"filters": p.filtros}
        if p.nombre == TT:
            page["visibility"] = "HiddenInViewMode"
        if p.interacciones:
            page["visualInteractions"] = p.interacciones
        (pd_ / "page.json").write_text(json.dumps(page, indent=2, ensure_ascii=False), encoding="utf-8")
        for v in p.visuales:
            (pd_ / "visuals" / v["name"]).mkdir()
            (pd_ / "visuals" / v["name"] / "visual.json").write_text(json.dumps(v, indent=2, ensure_ascii=False), encoding="utf-8")
    (d / "pages" / "pages.json").write_text(json.dumps({"$schema": f"{SCHEMA}/pagesMetadata/1.0.0/schema.json",
                                                         "pageOrder": [p.nombre for p in P], "activePageName": "inicio"}, indent=2), encoding="utf-8")
    (d / "version.json").write_text(json.dumps({"$schema": f"{SCHEMA}/versionMetadata/1.0.0/schema.json", "version": "2.0.0"}, indent=2), encoding="utf-8")
    (d / "report.json").write_text(json.dumps({
        "$schema": f"{SCHEMA}/report/1.2.0/schema.json",
        "themeCollection": {"customTheme": {"name": "AtlasAnalytics.json", "reportVersionAtImport": "5.55", "type": "RegisteredResources"}},
        "layoutOptimization": "None",
        "resourcePackages": [{"name": "RegisteredResources", "type": "RegisteredResources",
                              "items": [{"name": "AtlasAnalytics.json", "path": "AtlasAnalytics.json", "type": "CustomTheme"},
                                        {"name": b.MAPA, "path": b.MAPA, "type": "ShapeMap"}]}],
        "settings": {"useStylableVisualContainerHeader": True, "defaultDrillFilterOtherVisuals": True, "allowChangeFilterTypes": True,
                     "useEnhancedTooltips": True}}, indent=2), encoding="utf-8")
    (rep / "definition.pbir").write_text(json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
        "version": "4.0", "datasetReference": {"byPath": {"path": f"../{NOMBRE}.SemanticModel"}}}, indent=2), encoding="utf-8")
    print(f"reporte: {len(P)} páginas, {sum(len(p.visuales) for p in P)} visuales")


def main() -> None:
    esq = Path(sys.argv[sys.argv.index("--esquemas") + 1]) if "--esquemas" in sys.argv else None
    if not (PRIV / "intendencias.csv").exists():
        sys.exit("Falta correr 02_SCRIPTS/etl/13_super_excel_intendencias.py (datos privados del Excel).")
    t = datos()
    for n in ["dim_municipio", "dim_espacio", "dim_eleccion", "fact_votos", "fact_participacion", "fact_motor_2027", "dim_fuerza", "capa_mapa", "escenarios_2027"]:
        t[n].to_csv(DATOS / f"{n}.csv", index=False, encoding="utf-8")
    priv = datos_privados()
    for n, df in priv.items():
        df.to_csv(PRIV / f"{n}.csv", index=False, encoding="utf-8")
    b.topojson(t["dim_municipio"])
    escribir_modelo(t, priv)
    construir(t, esq)
    print("modelo:", sorted(x.name for x in (PBI / f"{NOMBRE}.SemanticModel" / "definition" / "tables").iterdir()))


if __name__ == "__main__":
    main()
