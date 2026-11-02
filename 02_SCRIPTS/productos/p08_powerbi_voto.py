"""
p08 · Power BI «Voto PBA»: tablero para visualizar el voto de la Provincia de Buenos Aires, 2007-2025.

Proyecto aparte del de intendencias (no usa datos privados; se puede publicar sin riesgo):
  03_OUTPUTS/powerbi/Atlas_PBA_Voto.pbip

PÁGINAS
-------
Inicio · Mapa del voto (ganador por municipio en la elección elegida) · Mapa peronismo (intensidad del
voto peronista) · Mapa participación · Mapa 2027 (motor de escenarios) · Secciones (voto por sección
electoral) · Evolución (gráfico animado 2007-2025 y municipios ganados por fuerza) · Territorio (voto
vs. censo) · Ficha del municipio (obtención de detalles) · Información emergente (tooltip).

LOS MAPAS
---------
Visual «Mapa de formas» de Power BI con el TopoJSON de los 135 municipios incrustado en el reporte.
Clic en un municipio filtra la página. Requiere activar una vez en Power BI Desktop:
Archivo > Opciones y configuración > Opciones > Características en versión preliminar >
«Objeto visual de mapa de formas».

Uso: python p08_powerbi_voto.py [--esquemas <carpeta con indice.json de esquemas PBIR>]
"""
from __future__ import annotations

import json
import shutil
import sys
import uuid
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import p06_powerbi as b  # noqa: E402
import p07_powerbi_intendencias as h  # noqa: E402  (utilidades de visuales y modelo)

NOMBRE = "Atlas_PBA_Voto"
PBI, DATOS, SCHEMA = b.PBI, b.DATOS, b.SCHEMA
lit, color, col, med, titulo, colores_por, Pagina, q, tag = b.lit, b.color, b.col, b.med, b.titulo, b.colores_por, b.Pagina, b.q, b.tag
boton, slicer, tarjeta, tabla_v, barras = h.boton, h.slicer, h.tarjeta, h.tabla_v, h.barras
DM = lambda c: col("dim_municipio", c)  # noqa: E731
FR = lambda c: col("fact_participacion", c)  # noqa: E731
TT = "tooltip_voto"
h.TT = TT  # los visuales de p07 apuntan su información emergente a esta página

GANADOR = [("Peronismo", "#29A3F0"), ("PRO / JxC", "#F5C518"), ("La Libertad Avanza", "#9B4DFF"), ("LLA + PRO", "#7E57FF"),
           ("UCR / centro", "#E94F4F"), ("Tercera vía", "#FF6FB5"), ("Vecinalismo", "#2FC4A6"), ("Otros", "#8D86A6")]
R_PER = [("55 % o más", "#0B5FA5"), ("45 a 55 %", "#29A3F0"), ("35 a 45 %", "#8CCBF5"), ("25 a 35 %", "#6A5A8C"), ("menos de 25 %", "#3A2D5C")]
R_PART = [("85 % o más", "#3DDC97"), ("80 a 85 %", "#2FA77A"), ("75 a 80 %", "#FFB547"), ("70 a 75 %", "#E5762E"), ("menos de 70 %", "#B23A3A")]
R_MARG = [("Paliza (20 pts o más)", "#C40BFF"), ("Clara (10 a 20 pts)", "#8A4FE0"), ("Ajustada (5 a 10 pts)", "#5B6FD0"), ("Voto a voto (menos de 5)", "#FFD54F")]
PAGS = [("inicio", "Inicio"), ("mapa", "Mapas"), ("secciones", "Secciones"), ("evolucion", "Evolución"), ("territorio", "Territorio"),
        ("ficha", "Ficha")]
SUBMAPAS = [("mapa", "GANADOR"), ("mapa_peronismo", "PERONISMO"), ("mapa_participacion", "PARTICIPACIÓN"), ("mapa_2027", "2027")]


def rango(v, cortes, etiquetas):
    if pd.isna(v):
        return None
    for c, e in zip(cortes, etiquetas):
        if v >= c:
            return e
    return etiquetas[-1]


# ================================================================== datos
def datos() -> dict:
    t = b.preparar_datos()
    f, v = t["fact_participacion"].copy(), t["fact_votos"]
    per = v[v.espacio == "PERONISMO"].set_index(["eleccion", "cod_indec"]).pct
    f["pct_peronismo"] = [per.get((e, c), np.nan) for e, c in zip(f.eleccion, f.cod_indec)]
    f["rango_peronismo"] = [rango(x, [55, 45, 35, 25], [e for e, _ in R_PER]) for x in f.pct_peronismo]
    f["rango_participacion"] = [rango(x, [85, 80, 75, 70], [e for e, _ in R_PART]) for x in f.participacion]
    f["competencia"] = [rango(x, [20, 10, 5], [e for e, _ in R_MARG]) for x in f.margen]
    f["ganador_nombre"] = f.ganador.map({"CENTRO_UCR": "UCR / centro", "LLA": "La Libertad Avanza", "LLA_PRO": "LLA + PRO", "OTROS": "Otros",
                                         "PERONISMO": "Peronismo", "PRO_JXC": "PRO / JxC", "TERCERA_VIA": "Tercera vía", "VECINAL": "Vecinalismo"})
    for c, pares in [("rango_peronismo", R_PER), ("rango_participacion", R_PART), ("competencia", R_MARG)]:
        f[f"orden_{c}"] = f[c].map({e: i for i, (e, _) in enumerate(pares)})
    f["clave"] = f.eleccion + "-" + f.cod_indec
    t["fact_participacion"] = f
    return t


# ================================================================== modelo
ARCHIVO = {"dim_municipio": "voto_dim_municipio", "fact_participacion": "voto_resultados"}
ORDEN = {"dim_municipio": {"seccion": "seccion_num", "fuerza_intendente": "orden_fuerza"},
         "dim_eleccion": {"etiqueta": "orden", "rotulo": "orden"}, "dim_espacio": {"espacio_nombre": "orden"}, "dim_fuerza": {"fuerza_intendente": "orden"},
         "fact_participacion": {"rango_peronismo": "orden_rango_peronismo", "rango_participacion": "orden_rango_participacion", "competencia": "orden_competencia"}}
TABLAS = ["dim_municipio", "dim_espacio", "dim_eleccion", "dim_fuerza", "fact_votos", "fact_participacion", "fact_motor_2027"]

MEDIDAS_EXTRA = [
    ("Municipios ganados", "DISTINCTCOUNT ( fact_participacion[cod_indec] )", "#,0", "Votación", None),
    ("Título mapa ganador", '"Quién ganó cada municipio · " & [Elección seleccionada]', None, "Títulos", None),
    ("Título mapa peronismo", '"% del peronismo por municipio · " & [Elección seleccionada]', None, "Títulos", None),
    ("Título mapa participación", '"Participación por municipio · " & [Elección seleccionada]', None, "Títulos", None),
    ("Título ficha voto", '[Municipio] & IF ( HASONEVALUE ( dim_municipio[cod_indec] ), " · " & SELECTEDVALUE ( dim_municipio[seccion] ) & " sección electoral · intendente: " & SELECTEDVALUE ( dim_municipio[intendente] ), " · elegí un municipio" )', None, "Títulos", None),
    ("Título mapa 2027", '"Motor 2027: probabilidad de que gane el peronismo · " & SELECTEDVALUE ( fact_motor_2027[escenario], "elegí un escenario" )', None, "Títulos", None),
    ("Votos peronismo", 'CALCULATE ( [Votos], dim_espacio[espacio] = "PERONISMO" )', "#,0", "Votación", None),
    ("Votos derecha", 'CALCULATE ( [Votos], dim_espacio[espacio] IN { "LLA", "LLA_PRO", "PRO_JXC" } )', "#,0", "Votación", None),
    ("Diferencia de votos", "[Votos peronismo] - [Votos derecha]", "+#,0;-#,0;0", "Votación", None),
    ("NBI municipio", "AVERAGE ( dim_municipio[nbi] )", "0.0", "Censo", None),
]


def escribir_modelo(t: dict) -> None:
    sm = PBI / f"{NOMBRE}.SemanticModel"
    shutil.rmtree(sm, ignore_errors=True)
    d = sm / "definition"
    (d / "tables").mkdir(parents=True)
    (sm / "definition.pbism").write_text(json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
        "version": "4.0", "settings": {}}, indent=2), encoding="utf-8")
    (d / "database.tmdl").write_text("database\n\tcompatibilityLevel: 1567\n", encoding="utf-8")
    nombres = TABLAS + ["Medidas"]
    (d / "model.tmdl").write_text(
        "model Model\n\tculture: es-AR\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n\tsourceQueryCulture: es-AR\n"
        "\tdataAccessOptions\n\t\tlegacyRedirects\n\t\treturnErrorValuesAsNull\n\n"
        f"annotation PBI_QueryOrder = {json.dumps(['CarpetaDatos'] + nombres)}\n\n"
        "annotation __PBI_TimeIntelligenceEnabled = 0\n\n" + "\n".join(f"ref table {q(n)}" for n in nombres) + "\n", encoding="utf-8")
    (d / "expressions.tmdl").write_text(
        f'expression CarpetaDatos = "{str(DATOS)}\\" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]\n'
        f"\tlineageTag: {tag()}\n\n\tannotation PBI_ResultType = Text\n", encoding="utf-8")
    ocultas_extra = {"clave", "orden_rango_peronismo", "orden_rango_participacion", "orden_competencia", "ganador", "foto_credito",
                     "electo_foto_licencia", "electo_foto_autor", "electo_foto_fuente", "misma_persona"}
    for n in TABLAS:
        df = t[n]
        oc = ocultas_extra | ({"cod_indec", "eleccion", "espacio"} if n.startswith("fact") else set())
        orden = ORDEN.get(n, {})
        cols = [h.columna(c, h.m_tipo(df, c)[0], c in h.OCULTAS or c in oc, orden.get(c), h.CATEG.get(c), c in h.SUMA) for c in df.columns]
        (d / "tables" / f"{n}.tmdl").write_text(h.tabla(n, cols, h.csv_m("CarpetaDatos", ARCHIVO.get(n, n), df), "Tipos"), encoding="utf-8")
    propias = {x[0] for x in MEDIDAS_EXTRA}
    out = [f"table Medidas\n\tlineageTag: {tag()}\n"]
    for n, expr, fmt, carpeta, cat in [x for x in b.MEDIDAS if x[0] not in propias] + MEDIDAS_EXTRA:
        s = (f"\tmeasure {q(n)} =\n" + "\n".join("\t\t\t" + x for x in expr.split("\n")) + "\n") if "\n" in expr else f"\tmeasure {q(n)} = {expr}\n"
        s += (f"\t\tformatString: {fmt}\n" if fmt else "") + (f"\t\tdataCategory: {cat}\n" if cat else "")
        out.append(s + f"\t\tdisplayFolder: {carpeta}\n\t\tlineageTag: {tag()}\n")
    out.append(f"\tcolumn x\n\t\tdataType: string\n\t\tisHidden\n\t\tlineageTag: {tag()}\n\t\tsummarizeBy: none\n\t\tsourceColumn: x\n")
    out.append("\tpartition Medidas = m\n\t\tmode: import\n\t\tsource = #table(type table [x = text], {})\n\n\tannotation PBI_ResultType = Table\n")
    (d / "tables" / "Medidas.tmdl").write_text("\n".join(out), encoding="utf-8")
    (d / "relationships.tmdl").write_text("\n".join(
        f"relationship {uuid.uuid5(uuid.NAMESPACE_URL, a + ca + bb)}\n\tfromColumn: {a}.{ca}\n\ttoColumn: {bb}.{cb}\n" for a, ca, bb, cb in b.RELACIONES),
        encoding="utf-8")


# ================================================================== reporte
def encabezado(p, activa):
    b.texto(p, f"{p.nombre}_marca", 10, 4, 260, 50, [[("ATLAS ANALYTICS", {"fontSize": "8pt", "fontWeight": "bold", "color": "#C40BFF"})],
                                                     [("Voto PBA 2007-2025", {"fontSize": "15pt", "fontWeight": "bold", "color": "#F2EBFA"})]])
    x = 290
    for clave, vis in PAGS:
        on = clave == activa
        boton(p, f"{p.nombre}_nav_{clave}", x, 12, 158, 32, vis.upper(), destino=clave, relleno="#C40BFF" if on else "#1F3A6E",
              tinta="#12042E" if on else "#F2EBFA", tam=9)
        x += 164


def filtro_inicial(valor="Diputados nacionales 2025", entidad="dim_eleccion", prop="rotulo") -> dict:
    """Selección inicial de un slicer de selección única (mapas con una sola elección o escenario a la vez)."""
    return {"filter": {"filter": {"Version": 2, "From": [{"Name": "d", "Entity": entidad, "Type": 0}],
                                  "Where": [{"Condition": {"In": {"Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "d"}}, "Property": prop}}],
                                                                  "Values": [[{"Literal": {"Value": f"'{valor}'"}}]]}}}]}}}


def slicer_eleccion(p, x, y, w, h=58):
    slicer(p, f"{p.nombre}_s_el", x, y, w, h, col("dim_eleccion", "rotulo"), "Elección", modo="Dropdown", unico=True)
    p.visuales[-1]["visual"]["objects"]["general"] = [{"properties": filtro_inicial()}]


def tooltip():
    return h.tooltip_pagina()


def mapa(p, nombre, x, y, w, ht, leyenda, pares, tit_medida):
    b.mapa(p, nombre, x, y, w, ht, leyenda, pares, "")
    v = p.visuales[-1]["visual"]
    v["query"]["queryState"]["Tooltips"] = {"projections": [b.proj(DM("municipio"))]}
    v["visualContainerObjects"] = h.titulo_medida(tit_medida) | tooltip()


def kpis_eleccion(p, x, y, w=150):
    for i, (mm, et, c) in enumerate([("Ganador", "Ganador", "#E9B6FF"), ("% Ganador", "% del ganador", "#F2EBFA"), ("Margen (pts)", "Margen (pts)", "#F2EBFA"),
                                     ("Participación", "Participación", "#3DDC97")]):
        tarjeta(p, f"{p.nombre}_k{i}", x + (i % 2) * (w + 6), y + (i // 2) * 76, w, 70, mm, et, c, 16)


def pagina_mapa(clave, visible, leyenda, pares, tit_medida, extra_slicer=None):
    p = Pagina(clave, visible)
    encabezado(p, "mapa")
    for i, (k, txt) in enumerate(SUBMAPAS):
        on = k == clave
        boton(p, f"{clave}_sub_{k}", 10, 56 + i * 38, 232, 34, txt, destino=k, relleno="#F2A65A" if on else "#2B3F7A", tinta="#12042E" if on else "#F2EBFA", tam=9)
    if extra_slicer:
        extra_slicer(p)
    else:
        slicer_eleccion(p, 10, 214, 232)
    slicer(p, f"{clave}_s_sec", 10, 278, 232, 112, DM("seccion"), "Sección electoral", horizontal=True)
    slicer(p, f"{clave}_s_zona", 10, 394, 232, 58, DM("zona"), "Zona", horizontal=True)
    slicer(p, f"{clave}_s_leg", 10, 458, 232, 254, leyenda, "Filtrar por categoría")
    mapa(p, f"{clave}_mapa", 250, 56, 620, 656, leyenda, pares, tit_medida)
    return p


def construir(t: dict, esquemas: Path | None) -> None:
    rep = PBI / f"{NOMBRE}.Report"
    shutil.rmtree(rep, ignore_errors=True)
    (rep / "definition" / "pages").mkdir(parents=True)
    (rep / "StaticResources" / "RegisteredResources").mkdir(parents=True)
    shutil.copy2(PBI / "Atlas_PBA.Report" / "StaticResources" / "RegisteredResources" / "AtlasAnalytics.json",
                 rep / "StaticResources" / "RegisteredResources" / "AtlasAnalytics.json")
    shutil.copy2(DATOS / "pba_municipios.topojson", rep / "StaticResources" / "RegisteredResources" / b.MAPA)
    esp = col("dim_espacio", "espacio_nombre")
    pares_esp = [(r.espacio_nombre, r.color) for r in t["dim_espacio"].itertuples()]
    eti = col("dim_eleccion", "etiqueta")
    P = []

    # ------------------------------------------------------------ Inicio
    p = Pagina("inicio", "Inicio")
    encabezado(p, "inicio")
    b.texto(p, "inicio_hero", 24, 64, 1232, 96, [[("EL VOTO DE LA PROVINCIA DE BUENOS AIRES", {"fontSize": "28pt", "fontWeight": "bold", "color": "#F2EBFA"})],
                                                [("17 elecciones de 2007 a 2025 · 135 municipios · 8 secciones electorales · censo 2022 · escenarios 2027",
                                                  {"fontSize": "12pt", "color": "#E9B6FF"})]])
    slicer_eleccion(p, 24, 170, 300)
    for i, (mm, et, c) in enumerate([("Ganador", "Ganador", "#E9B6FF"), ("% Ganador", "% del ganador", "#F2EBFA"), ("Margen (pts)", "Margen (pts)", "#F2EBFA"),
                                     ("Electores", "Electores", "#F2EBFA"), ("Participación", "Participación", "#3DDC97")]):
        tarjeta(p, f"inicio_k{i}", 332 + i * 186, 170, 180, 76, mm, et, c)
    menu = [("mapa", "MAPAS · ganador, peronismo, participación y 2027", "#3D6FD9"), ("secciones", "SECCIONES · el voto en las 8 secciones electorales", "#F28C28"),
            ("evolucion", "EVOLUCIÓN · 2007-2025, gráfico animado", "#7B2FBE"), ("territorio", "TERRITORIO · voto y censo (pobreza, edad, estudios)", "#1F8A6E"),
            ("ficha", "FICHA · todo de un municipio en una página", "#C62828")]
    for i, (dest, txt, c) in enumerate(menu):
        boton(p, f"inicio_menu_{dest}", 24 + (i % 2) * 400, 262 + (i // 2) * 104, 388, 92, txt, destino=dest, relleno=c, tam=13)
    barras(p, "inicio_fuerzas", 840, 262, 416, 300, esp, "% Voto", pares_esp, "Resultado provincial por fuerza", orden=(med("% Voto"), "Descending"), tt=False)
    b.texto(p, "inicio_fuente", 24, 580, 800, 60, [[("Cómo usar: elegí la elección arriba; los botones llevan a cada página. En los mapas, clic en un municipio filtra todo; "
                                                    "pasá el mouse para ver el detalle; clic derecho > Obtener detalles > Ficha.", {"fontSize": "10pt", "color": "#DCD2EA"})],
                                                  [("Fuentes: DINE, Junta Electoral PBA, INDEC (censo 2022), RENABAP. Elaboración: Atlas Analytics.", {"fontSize": "8pt", "color": "#8A7AAB"})]])
    P.append(p)

    # ------------------------------------------------------------ Mapas
    p = pagina_mapa("mapa", "Mapa del voto", FR("ganador_nombre"), GANADOR, "Título mapa ganador")
    kpis_eleccion(p, 878, 56, 192)
    barras(p, "mapa_fuerzas", 878, 212, 390, 210, esp, "% Voto", pares_esp, "% por fuerza (lo filtrado)", orden=(med("% Voto"), "Descending"), tt=False)
    tabla_v(p, "mapa_tabla", 878, 428, 390, 284, [DM("municipio"), FR("ganador_nombre"), med("% Ganador"), med("Margen (pts)")], "Municipios",
            orden=(DM("municipio"), "Ascending"), nombres=["Municipio", "Ganó", "% ganador", "Margen"], tam=8)
    p.visuales[-1]["visual"]["visualContainerObjects"] |= tooltip()
    P.append(p)

    p = pagina_mapa("mapa_peronismo", "Mapa peronismo", FR("rango_peronismo"), R_PER, "Título mapa peronismo")
    kpis_eleccion(p, 878, 56, 192)
    tarjeta(p, "mper_kp", 878, 212, 192, 70, "% Peronismo", "% peronismo", "#29A3F0", 16)
    tarjeta(p, "mper_kd", 1076, 212, 192, 70, "% Derecha", "% LLA / PRO", "#9B4DFF", 16)
    tabla_v(p, "mper_tabla", 878, 288, 390, 424, [DM("municipio"), med("% Peronismo"), med("% Derecha"), med("Diferencia de votos")], "Municipios",
            orden=(med("% Peronismo"), "Descending"), nombres=["Municipio", "% peronismo", "% LLA / PRO", "Dif. de votos"], tam=8)
    P.append(p)

    p = pagina_mapa("mapa_participacion", "Mapa participación", FR("rango_participacion"), R_PART, "Título mapa participación")
    tarjeta(p, "mpar_k1", 878, 56, 192, 70, "Participación", "Participación", "#3DDC97", 16)
    tarjeta(p, "mpar_k2", 1076, 56, 192, 70, "Votantes", "Votantes", "#F2EBFA", 16)
    tarjeta(p, "mpar_k3", 878, 132, 192, 70, "Electores", "Electores", "#F2EBFA", 16)
    tarjeta(p, "mpar_k4", 1076, 132, 192, 70, "Ganador", "Ganador", "#E9B6FF", 16)
    tabla_v(p, "mpar_tabla", 878, 208, 390, 504, [DM("municipio"), med("Participación"), med("Electores"), FR("ganador_nombre")], "Municipios",
            orden=(med("Participación"), "Ascending"), nombres=["Municipio", "Participación", "Electores", "Ganó"], tam=8)
    P.append(p)

    mot = lambda c: col("fact_motor_2027", c)  # noqa: E731
    p = pagina_mapa("mapa_2027", "Mapa 2027", mot("rango_p"), b.RANGOS_P, "Título mapa 2027",
                    lambda p: slicer(p, "mapa_2027_s_esc", 10, 214, 232, 58, mot("escenario"), "Escenario del motor 2027", modo="Dropdown", unico=True)
                    or p.visuales[-1]["visual"]["objects"].__setitem__("general", [{"properties": filtro_inicial("Octubre 2025 se repite", "fact_motor_2027", "escenario")}]))
    tarjeta(p, "m27_k1", 878, 56, 192, 70, "Municipios peronistas esperados", "Municipios peronistas esperados", "#29A3F0", 16)
    tarjeta(p, "m27_k2", 1076, 56, 192, 70, "Municipios en disputa", "En disputa (20-80 %)", "#C40BFF", 16)
    tabla_v(p, "m27_tabla", 878, 132, 390, 580, [DM("municipio"), mot("p_gana_peronismo"), mot("pct_peronismo"), mot("rango_p")],
            "P(gana el peronismo) · 1.000 simulaciones", orden=(mot("p_gana_peronismo"), "Descending"),
            nombres=["Municipio", "P(peronismo)", "% peronismo esperado", "Categoría"], tam=8)
    P.append(p)

    # ------------------------------------------------------------ Secciones
    p = Pagina("secciones", "Secciones")
    encabezado(p, "secciones")
    slicer_eleccion(p, 10, 56, 232)
    slicer(p, "sec_s_sec", 10, 120, 232, 150, DM("seccion"), "Sección electoral")
    b.texto(p, "sec_nota", 10, 276, 232, 200, [[("Las 8 secciones", {"fontSize": "11pt", "fontWeight": "bold", "color": "#E9B6FF"})],
                                               [("La 1.ª (norte y oeste del Conurbano) y la 3.ª (sur del Conurbano) concentran casi dos tercios de los electores; "
                                                 "la 3.ª es el bastión peronista y la 1.ª define la elección. El interior (2.ª, 4.ª, 5.ª, 6.ª, 7.ª) suele votar distinto; "
                                                 "la 8.ª es La Plata.", {"fontSize": "9pt", "color": "#DCD2EA"})]])
    p.add("sec_100", "hundredPercentStackedBarChart", 250, 56, 620, 340,
          roles={"Category": [DM("seccion")], "Series": [esp], "Y": [med("Votos")]},
          objetos={"dataPoint": colores_por(esp, pares_esp), "labels": [{"properties": {"show": lit(True), "color": color("#12042E")}}],
                   "legend": [{"properties": {"show": lit(True), "position": lit("Top"), "labelColor": color("#DCD2EA")}}]},
          contenedor=h.titulo_medida("Título elección"), orden=(DM("seccion"), "Ascending"))
    barras(p, "sec_electores", 878, 56, 390, 340, DM("seccion"), "Electores", None, "Electores por sección", orden=(DM("seccion"), "Ascending"), tt=False)
    tabla_v(p, "sec_tabla", 250, 404, 1018, 308, [DM("seccion"), med("Electores"), med("Participación"), med("Ganador"), med("% Peronismo"), med("% Derecha"),
                                                  med("Diferencia de votos"), med("Municipios")], "Resumen por sección",
            orden=(DM("seccion"), "Ascending"), nombres=["Sección", "Electores", "Participación", "Ganador", "% peronismo", "% LLA / PRO", "Dif. de votos", "Municipios"], tt=False)
    P.append(p)

    # ------------------------------------------------------------ Evolución
    p = Pagina("evolucion", "Evolución")
    encabezado(p, "evolucion")
    slicer(p, "ev_s_grupo", 10, 56, 232, 150, col("dim_eleccion", "grupo"), "Tipo de elección")
    slicer(p, "ev_s_sec", 10, 212, 232, 112, DM("seccion"), "Sección electoral", horizontal=True)
    slicer(p, "ev_s_mun", 10, 330, 232, 58, DM("municipio"), "Municipio", modo="Dropdown")
    p.add("ev_anim", "scatterChart", 250, 56, 620, 400,
          roles={"Category": [DM("municipio")], "Series": [DM("seccion")], "X": [med("Participación")], "Y": [med("% Peronismo")], "Size": [med("Electores")],
                 "Play": [eti]},
          objetos={"legend": [{"properties": {"show": lit(True), "position": lit("Top"), "labelColor": color("#DCD2EA")}}]},
          contenedor=titulo("▶ Animación 2007-2025: participación (X) y % peronismo (Y) de cada municipio") | tooltip())
    p.add("ev_linea", "lineChart", 878, 56, 390, 400, roles={"Category": [eti], "Series": [esp], "Y": [med("% Voto")]},
          objetos={"dataPoint": colores_por(esp, pares_esp), "legend": [{"properties": {"show": lit(True), "position": lit("Top"), "labelColor": color("#DCD2EA")}}]},
          contenedor=titulo("% por fuerza en cada elección"), orden=(eti, "Ascending"))
    p.add("ev_ganados", "columnChart", 250, 464, 1018, 248, roles={"Category": [eti], "Series": [FR("ganador_nombre")], "Y": [med("Municipios ganados")]},
          objetos={"dataPoint": colores_por(FR("ganador_nombre"), GANADOR), "labels": [{"properties": {"show": lit(True), "color": color("#12042E")}}],
                   "legend": [{"properties": {"show": lit(True), "position": lit("Right"), "labelColor": color("#DCD2EA")}}]},
          contenedor=titulo("Municipios ganados por cada fuerza, elección por elección"), orden=(eti, "Ascending"))
    P.append(p)

    # ------------------------------------------------------------ Territorio (voto y censo)
    p = Pagina("territorio", "Territorio")
    encabezado(p, "territorio")
    slicer_eleccion(p, 10, 56, 232)
    slicer(p, "ter_s_sec", 10, 120, 232, 112, DM("seccion"), "Sección electoral", horizontal=True)
    slicer(p, "ter_s_zona", 10, 238, 232, 58, DM("zona"), "Zona", horizontal=True)
    for i, (mm, et) in enumerate([("Población", "Población 2022"), ("Hogares con NBI %", "Hogares con NBI"), ("Hogares en barrios populares %", "En barrios populares"),
                                  ("Universitarios %", "Universitarios")]):
        tarjeta(p, f"ter_k{i}", 10, 302 + i * 102, 232, 96, mm, et, "#FFB547" if i else "#F2EBFA", 18)
    p.add("ter_nbi", "scatterChart", 250, 56, 509, 400,
          roles={"Category": [DM("municipio")], "Series": [FR("ganador_nombre")], "X": [med("NBI municipio")], "Y": [med("% Peronismo")], "Size": [med("Población")]},
          objetos={"dataPoint": colores_por(FR("ganador_nombre"), GANADOR), "legend": [{"properties": {"show": lit(True), "position": lit("Top"), "labelColor": color("#DCD2EA")}}]},
          contenedor=titulo("Pobreza (hogares con NBI, X) y % peronismo (Y)") | tooltip())
    p.add("ter_bp", "scatterChart", 767, 56, 501, 400,
          roles={"Category": [DM("municipio")], "Series": [FR("ganador_nombre")], "X": [med("Hogares en barrios populares %")], "Y": [med("% Derecha")], "Size": [med("Población")]},
          objetos={"dataPoint": colores_por(FR("ganador_nombre"), GANADOR), "legend": [{"properties": {"show": lit(False)}}]},
          contenedor=titulo("Barrios populares (X) y % LLA / PRO (Y)") | tooltip())
    tabla_v(p, "ter_tabla", 250, 464, 1018, 248, [DM("municipio"), DM("pob"), DM("nbi"), DM("pct_barrio_popular"), DM("pct_univ"), DM("pct_65"),
                                                  med("% Peronismo"), med("% Derecha"), med("Participación")], "Municipios: censo y voto",
            orden=(DM("pob"), "Descending"), nombres=["Municipio", "Población", "NBI %", "Barrios pop. %", "Universitarios %", "65+ %", "% peronismo", "% LLA / PRO", "Participación"])
    p.visuales[-1]["visual"]["visualContainerObjects"] |= tooltip()
    P.append(p)

    # ------------------------------------------------------------ Ficha (obtención de detalles)
    p = Pagina("ficha", "Ficha")
    encabezado(p, "ficha")
    slicer(p, "ficha_s_muni", 10, 56, 232, 58, DM("municipio"), "Municipio", modo="Dropdown", unico=True)
    boton(p, "ficha_atras", 10, 120, 232, 34, "◄ VOLVER", atras=True)
    tabla_v(p, "ficha_foto", 10, 160, 232, 220, [DM("foto_url"), DM("logo_url")], None, nombres=["Intendente", "Fuerza"], imagen=140, tt=False)
    tarjeta(p, "ficha_tit", 250, 56, 1018, 44, "Título ficha voto", "Ficha", "#E9B6FF", 13)
    p.add("ficha_datos", "multiRowCard", 10, 386, 232, 326,
          roles={"Values": [DM("intendente"), DM("fuerza_intendente"), DM("pob"), DM("hogares"), DM("nbi"), DM("pct_univ"), DM("pct_65")]},
          contenedor=titulo("Datos del municipio"))
    for pr, n in zip(p.visuales[-1]["visual"]["query"]["queryState"]["Values"]["projections"],
                     ["Intendente", "Fuerza", "Población 2022", "Hogares", "Hogares con NBI %", "Universitarios %", "Mayores de 65 %"]):
        pr["displayName"] = n
    p.add("ficha_linea", "lineChart", 250, 106, 620, 300, roles={"Category": [eti], "Series": [esp], "Y": [med("% Voto")]},
          objetos={"dataPoint": colores_por(esp, pares_esp), "legend": [{"properties": {"show": lit(True), "position": lit("Top"), "labelColor": color("#DCD2EA")}}]},
          contenedor=titulo("Cómo votó, elección por elección"), orden=(eti, "Ascending"))
    mapa(p, "ficha_mapa", 878, 106, 390, 300, FR("ganador_nombre"), GANADOR, "Título mapa ganador")
    p.visuales[-1]["visual"]["objects"]["legend"] = [{"properties": {"show": lit(False)}}]
    tabla_v(p, "ficha_hist", 250, 414, 1018, 298, [col("dim_eleccion", "rotulo"), FR("ganador_nombre"), med("% Ganador"), med("Margen (pts)"), med("% Peronismo"),
                                                    med("% Derecha"), med("Participación"), med("Electores")], "Todas las elecciones",
            orden=(col("dim_eleccion", "rotulo"), "Descending"),
            nombres=["Elección", "Ganó", "% ganador", "Margen", "% peronismo", "% LLA / PRO", "Participación", "Electores"], tt=False)
    p.interacciones = [{"source": "ficha_mapa", "target": t_, "type": "NoFilter"} for t_ in ("ficha_linea", "ficha_hist")]
    p.filtros = [{"name": "dt_municipio", "field": DM("municipio"), "type": "Categorical", "howCreated": "Drillthrough"}]
    p.binding = {"name": "pb_ficha", "type": "Drillthrough", "parameters": [{"name": "par_municipio", "boundFilter": "dt_municipio", "fieldExpr": DM("municipio")}]}
    p.tipo = "Drillthrough"
    P.append(p)

    # ------------------------------------------------------------ Tooltip
    p = Pagina(TT, "Información emergente · voto")
    tarjeta(p, "tt_mun", 4, 4, 312, 40, "Municipio", "Municipio", "#E9B6FF", 13)
    for i, (mm, et, c) in enumerate([("Ganador", "Ganó", "#E9B6FF"), ("% Ganador", "% ganador", "#F2EBFA"), ("% Peronismo", "% peronismo", "#29A3F0"),
                                     ("% Derecha", "% LLA / PRO", "#9B4DFF"), ("Margen (pts)", "Margen (pts)", "#F2EBFA"), ("Participación", "Participación", "#3DDC97")]):
        tarjeta(p, f"tt_k{i}", 4 + (i % 2) * 158, 48 + (i // 2) * 64, 154, 60, mm, et, c, 13)
    p.tamano, p.tipo, p.binding = (320, 240), "Tooltip", {"name": "pb_tooltip", "type": "Tooltip"}
    P.append(p)

    h.NOMBRE = NOMBRE  # escribir_paginas usa este nombre
    h.escribir_paginas(rep, P)
    (PBI / f"{NOMBRE}.pbip").write_text(json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
        "version": "1.0", "artifacts": [{"report": {"path": f"{NOMBRE}.Report"}}], "settings": {"enableAutoRecovery": True}}, indent=2), encoding="utf-8")
    if esquemas:
        b.validar(rep, esquemas)


def main() -> None:
    esq = Path(sys.argv[sys.argv.index("--esquemas") + 1]) if "--esquemas" in sys.argv else None
    t = datos()
    for n in TABLAS:
        t[n].to_csv(DATOS / f"{ARCHIVO.get(n, n)}.csv", index=False, encoding="utf-8")
    if not (DATOS / "pba_municipios.topojson").exists():
        b.topojson(t["dim_municipio"])
    escribir_modelo(t)
    construir(t, esq)


if __name__ == "__main__":
    main()
