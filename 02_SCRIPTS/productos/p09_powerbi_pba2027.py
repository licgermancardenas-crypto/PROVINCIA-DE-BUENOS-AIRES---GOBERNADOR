"""
p09 · Power BI «ATLAS PBA 2027»: el tablero electoral de la Provincia de Buenos Aires con el
sistema de diseño de los tableros ATLAS (Brasil 2026, CABA 2027).

    03_OUTPUTS/powerbi/ATLAS_PBA_2027.pbip        <- abrir este
    03_OUTPUTS/powerbi/datos_2027/*.csv           <- datos públicos (sin CRM)

Entrega 1: Inicio · Resumen provincial · Mapa de municipios · Conurbano · Ficha del municipio
(Obtener detalles) · Tooltip del municipio. Las demás páginas figuran en el menú como «próximamente».

EL MAPA
-------
Una medida DAX dibuja los 135 municipios en SVG (contornos de `svg_mapa.py`) y los pinta según la
métrica elegida (ganador, % peronismo, % LLA-PRO, margen, participación, cambio vs. 2023, pronóstico
2027, NBI, barrios populares, electores), con nombre y valor sobre cada municipio, recuadro del
Conurbano y leyenda. No depende de visuales en versión preliminar: se ve igual en Desktop y en la web.
Lo que se elige en el ranking o la tabla se resalta en el mapa (el resto queda en gris).

Uso: python p09_powerbi_pba2027.py [--esquemas <carpeta con indice.json de esquemas PBIR>]
"""
from __future__ import annotations

import json
import re
import shutil
import sys
import uuid
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import box

sys.path.insert(0, str(Path(__file__).parent))
import p06_powerbi as b  # noqa: E402
import p08_powerbi_voto as v8  # noqa: E402
import svg_mapa  # noqa: E402
from pbi_atlas import (BG, INK, LINEA, MUTED, ORO, SCH, SIN_CAJA, TODOS, V_PAGE, V_REPORT, V_VISUAL, VIO, X0, H, C, Me,  # noqa: E402
                       Pagina, barras, color, color_fx, escribir, filtro_es, lit, proj, q, tabla, tabla_calculada, tabla_csv,
                       medida, relaciones, svg_uri)

RAIZ = b.RAIZ
PBI = b.PBI
DATOS = PBI / "datos_2027"
NOMBRE = "ATLAS_PBA_2027"
PBI_TEMAS = Path(r"C:\Program Files\Microsoft Power BI Desktop\bin\WebView2Resources\minerva\sharedresources\BaseThemes")
BASE_THEME = "CY26SU02"
TEMA = "AtlasPBA.json"

PER, DER, ROJO, VERDE = "#2F80ED", "#6A1B9A", "#C62828", "#2E9C8F"
GRIS = "#E4DFEE"
# animaciones SVG (corren cada vez que la imagen se recalcula: al cambiar un filtro o una métrica)
ANIM_MAPA = "<animate attributeName='opacity' values='0;1' dur='0.8s' fill='freeze'/>"
ANIM_ROT = "<animate attributeName='opacity' values='0;0;1' keyTimes='0;0.5;1' dur='1.4s' fill='freeze'/>"
HALO = "stroke='#FFFFFF' stroke-width='3' stroke-opacity='0.9' paint-order='stroke' stroke-linejoin='round'"
COLOR_ESPACIO = {"PERONISMO": PER, "LLA": DER, "LLA_PRO": "#A04BB5", "PRO_JXC": "#F2B705", "CENTRO_UCR": VERDE,
                 "TERCERA_VIA": "#F2994A", "IZQUIERDA": ROJO, "VECINAL": "#43A047", "OTROS": "#9A93AD"}
ESC_BASE = "Se repite octubre 2025"

# ------------------------------------------------------------------ métricas del mapa
# id, nombre, valor (DAX), modo (1 secuencial, 2 categórica, 3 divergente), color base, color negativo, formato,
# color de categoría, nombre de categoría
METRICAS = [
    (1, "Ganador de la elección", "[% Ganador]", 2, None, None, "0%", "[Color ganador]", "[Ganador]"),
    (2, "% del peronismo", "[% Peronismo]", 1, f'"{PER}"', None, "0%", None, None),
    (3, "% de LLA y PRO", "[% Derecha]", 1, f'"{DER}"', None, "0%", None, None),
    (4, "Margen peronismo − LLA/PRO (pts)", "[Margen P-D (pts)]", 3, f'"{PER}"', f'"{DER}"', "+0;-0;0", None, None),
    (5, "Participación", "[Participación]", 1, f'"{VIO}"', None, "0%", None, None),
    (6, "Cambio del peronismo vs. Gobernador 2023 (pts)", "[Cambio peronismo vs 2023 (pts)]", 3, f'"{PER}"', f'"{ROJO}"', "+0;-0;0", None, None),
    (7, "Pronóstico 2027 · probabilidad de que gane el peronismo", "[P(peronismo) 2027 base]", 1, f'"{PER}"', None, "0%", None, None),
    (8, "Hogares con NBI (censo 2022)", "[Hogares con NBI %]", 1, f'"{ROJO}"', None, "0.0%", None, None),
    (9, "Hogares en barrios populares", "[Hogares en barrios populares %]", 1, f'"{ORO}"', None, "0.0%", None, None),
    (10, "Electores", "[Electores]", 1, f'"{INK}"', None, "#,0", None, None),
]

NAV = [("inicio", "Inicio", "⌂"), ("mapa_completo", "Mapa completo", "▣"), ("resumen", "Resumen provincial", "◉"), ("mapa", "Mapa de municipios", "▦"),
       ("conurbano", "Conurbano", "◎"), (None, "Secciones electorales", "▤"), (None, "Mapa fino · circuitos", "▩"),
       (None, "Explorador", "✛"), (None, "Corrimientos", "↗"), (None, "Dónde se decide", "⚑"), (None, "Intendentes 2027", "★"),
       (None, "Pronóstico 2027", "◔"), (None, "Simulador", "⚙"), ("historia", "Historia 2007-2025", "≋"), (None, "Metodología", "ℹ")]
TT = "tt_municipio"
DM = lambda c: C("dim_municipio", c)  # noqa: E731


# ================================================================== datos
def corto(n: str) -> str:
    for a, z in [("General ", "Gral. "), ("Coronel ", "Cnel. "), ("Capitán ", "Cap. "), ("Presidente ", "Pte. "), ("Teniente ", "Tte. "),
                 ("Almirante ", "Alte. "), ("Comandante ", "Cte. ")]:
        n = n.replace(a, z)
    return n.replace("&", "y")


def etiquetas() -> pd.DataFrame:
    """Punto de rótulo y superficie (en píxeles del lienzo) de cada municipio, en el mapa provincial y en el recuadro."""
    g = gpd.read_file(RAIZ / "01_DATOS" / "processed" / "geo" / "partidos.gpkg").to_crs(svg_mapa.ALBERS)
    x0, y0, x1, y1 = g.total_bounds
    k = svg_mapa.ANCHO / (x1 - x0)
    sub = g[(g.conurbano.astype(str) == "True") | g.cod_indec.isin(svg_mapa.RECUADRO_EXTRA)]
    bx0, by0, bx1, by1 = sub.total_bounds
    bx0, by0, bx1, by1 = bx0 - 3000, by0 - 3000, bx1 + 3000, by1 + 3000
    kc = svg_mapa.ANCHO / (bx1 - bx0)
    caja = box(bx0, by0, bx1, by1)
    fil = []
    for r in g.itertuples():
        pt = r.geometry.representative_point()
        d = {"cod_indec": r.cod_indec, "cx_p": round((pt.x - x0) * k), "cy_p": round((y1 - pt.y) * k),
             "area_p": r.geometry.area * k * k, "cx_c": None, "cy_c": None, "area_c": 0.0}
        if r.geometry.intersects(caja):
            gc = r.geometry.intersection(caja)
            pc = gc.representative_point()
            d.update(cx_c=round((pc.x - bx0) * kc), cy_c=round((by1 - pc.y) * kc), area_c=gc.area * kc * kc)
        fil.append(d)
    return pd.DataFrame(fil)


def datos() -> dict:
    t = v8.datos()
    m = t["dim_municipio"].copy()
    prov, conu, meta = svg_mapa.paths()
    et = etiquetas()
    m = m.merge(et, on="cod_indec", how="left")
    m["svg_prov"] = m.cod_indec.map(prov).fillna("")
    m["svg_conu"] = m.cod_indec.map(conu).fillna("")
    m["nombre_corto"] = m.municipio.map(corto)
    # rótulo en el mapa provincial: 2 = nombre y valor, 1 = sólo valor, 0 = nada
    m["rotulo_p"] = [2 if a > 2600 and z == "Interior" else (1 if a > 900 and z == "Interior" else 0) for a, z in zip(m.area_p, m.zona)]
    m["rotulo_c"] = [2 if a > 1400 else (1 if a > 500 else 0) for a in m.area_c]
    m = m.drop(columns=["area_p", "area_c"])
    for c in ("cx_p", "cy_p", "cx_c", "cy_c"):
        m[c] = m[c].astype("Int64")
    t["dim_municipio"] = m
    e = t["dim_espacio"].copy()
    e["color"] = e.espacio.map(COLOR_ESPACIO).fillna(e.color)
    t["dim_espacio"] = e
    t["escenarios_2027"] = pd.read_csv(b.DATOS / "escenarios_2027.csv")
    t["meta"] = meta
    return t


# ================================================================== modelo
def sw(i: int) -> str:
    casos = [f"{m[0]}, " + (f'"{m[i]}"' if i == 6 else str(m[i])) for m in METRICAS if m[i] is not None]
    return "SWITCH(idm, " + ", ".join(casos) + ", BLANK())"


def cabecera() -> str:
    return f"""
        VAR idm = [Métrica]
        VAR modo = {sw(3)}
        VAR base = {sw(4)}
        VAR neg = {sw(5)}
        VAR fmtv = {sw(6)}"""


def capa(path: str, cx: str, cy: str, rot: str, fs: float, stroke: float, rango_global=False) -> str:
    """Formas + rótulos + leyenda de los municipios (usa las VAR de cabecera() y x_ley, y_ley)."""
    T = "dim_municipio"
    cols = f"{T}[cod_indec], {T}[{path}], {T}[{cx}], {T}[{cy}], {T}[nombre_corto], {T}[{rot}]"
    et = (f"SWITCH({T}[{rot}], "
          f"2, \"<text x='\" & {T}[{cx}] & \"' y='\" & {T}[{cy}] & \"' text-anchor='middle' font-family='Segoe UI' font-size='{fs}' font-weight='600' fill='{INK}' {HALO}>\""
          f" & {T}[nombre_corto] & \"</text><text x='\" & {T}[{cx}] & \"' y='\" & ({T}[{cy}] + {round(fs + 1)}) & \"' text-anchor='middle' font-family='Segoe UI' font-size='{fs}' font-weight='700' fill='{INK}' {HALO}>\" & FORMAT([v], fmtv) & \"</text>\", "
          f"1, \"<text x='\" & {T}[{cx}] & \"' y='\" & ({T}[{cy}] + 3) & \"' text-anchor='middle' font-family='Segoe UI' font-size='{fs}' font-weight='700' fill='{INK}' {HALO}>\" & FORMAT([v], fmtv) & \"</text>\", \"\")")
    return f"""
        VAR sel = VALUES({T}[cod_indec])
        VAR filas = ADDCOLUMNS(FILTER(ALL({cols}), {T}[{path}] <> ""),
            "v", IF({T}[cod_indec] IN sel, [Valor métrica]),
            "cc", IF(modo = 2 && {T}[cod_indec] IN sel, {sw(7)}),
            "nn", IF(modo = 2 && {T}[cod_indec] IN sel, {sw(8)}))
        VAR lo = {"lo_g" if rango_global else "MINX(filas, [v])"}
        VAR hi = {"hi_g" if rango_global else "MAXX(filas, [v])"}
        VAR ma = {"ma_g" if rango_global else "MAXX(filas, ABS([v]))"}
        VAR formas = CONCATENATEX(filas,
            VAR v = [v]
            VAR t = IF(modo = 3, DIVIDE(ABS(v), ma), DIVIDE(v - lo, hi - lo, 1))
            VAR col = SWITCH(TRUE(), ISBLANK(v), "{GRIS}", modo = 2, [cc], modo = 3 && v < 0, neg, base)
            VAR o = IF(ISBLANK(v) || modo = 2, 99, INT(14 + 85 * t))
            RETURN "<path d='" & {T}[{path}] & "' fill='" & col & "' fill-opacity='0." & FORMAT(o, "00") & "'/>", "")
        VAR rotulos = CONCATENATEX(FILTER(filas, NOT ISBLANK([v])), {et}, "")
        VAR cats = DISTINCT(SELECTCOLUMNS(FILTER(filas, NOT ISBLANK([cc])), "c", [cc], "n", [nn]))
        VAR catsI = ADDCOLUMNS(cats, "i", VAR yo = [n] RETURN COUNTROWS(FILTER(cats, [n] < yo)))
        VAR ley = IF(modo = 2,
            CONCATENATEX(catsI, "<rect x='" & x_ley & "' y='" & (4 + [i] * 24) & "' width='20' height='16' rx='3' fill='" & [c] & "'/><text x='" & (x_ley + 28) & "' y='" & (17 + [i] * 24) & "' font-family='Segoe UI' font-size='13' fill='{INK}'>" & [n] & "</text>", ""),
            "<rect x='" & x_ley & "' y='4' width='34' height='16' fill='" & IF(modo = 3, neg, base) & "' fill-opacity='" & IF(modo = 3, "0.99", "0.14") & "'/>"
            & "<rect x='" & (x_ley + 34) & "' y='4' width='34' height='16' fill='" & IF(modo = 3, neg, base) & "' fill-opacity='" & IF(modo = 3, "0.45", "0.35") & "'/>"
            & "<rect x='" & (x_ley + 68) & "' y='4' width='34' height='16' fill='" & IF(modo = 3, "{GRIS}", base) & "' fill-opacity='" & IF(modo = 3, "0.99", "0.56") & "'/>"
            & "<rect x='" & (x_ley + 102) & "' y='4' width='34' height='16' fill='" & base & "' fill-opacity='" & IF(modo = 3, "0.45", "0.77") & "'/>"
            & "<rect x='" & (x_ley + 136) & "' y='4' width='34' height='16' fill='" & base & "' fill-opacity='0.99'/>"
            & "<text x='" & x_ley & "' y='38' font-family='Segoe UI' font-size='13' fill='{INK}'>" & FORMAT(IF(modo = 3, -ma, lo), fmtv) & "</text>"
            & "<text x='" & (x_ley + 170) & "' y='38' text-anchor='end' font-family='Segoe UI' font-size='13' fill='{INK}'>" & FORMAT(IF(modo = 3, ma, hi), fmtv) & "</text>")
        VAR uno = COUNTROWS(sel) = 1 && COUNTROWS(ALL({T}[cod_indec])) > 1
        VAR resalte = IF(uno, "<path d='" & MAXX(FILTER(filas, {T}[cod_indec] IN sel), {T}[{path}])
            & "' fill='none' stroke='{INK}' stroke-width='2' stroke-linejoin='round'><animate attributeName='stroke-width' values='1.5;5;1.5' dur='1.6s' repeatCount='indefinite'/></path>", "")
        RETURN "<g stroke='#FFFFFF' stroke-width='{stroke}' stroke-linejoin='round'>{ANIM_MAPA}" & formas & "</g>"
            & "<g>{ANIM_ROT}" & rotulos & "</g>" & resalte
            & IF(mostrar_ley, "<g transform='translate(0 " & y_ley & ")'>{ANIM_ROT}" & ley & "</g>", "")
        """


def mapa_dax(path, cx, cy, rot, fs, stroke, vb, x_ley, y_ley, ley=True, marco="") -> str:
    return f"""
        {cabecera()}
        VAR x_ley = {x_ley}
        VAR y_ley = {y_ley}
        VAR mostrar_ley = {"TRUE()" if ley else "FALSE()"}
        VAR cuerpo = {capa(path, cx, cy, rot, fs, stroke)}
        VAR svg = "<svg xmlns='http://www.w3.org/2000/svg' viewBox='{vb}'>{marco}" & cuerpo & "</svg>"
        RETURN {svg_uri("svg")}"""


def mapa_completo(meta) -> str:
    """Provincia y, al lado, el recuadro del Conurbano en una sola imagen apaisada, con la misma escala de color."""
    pw, ph, cw, ch = meta["prov_w"], meta["prov_h"], meta["conu_w"], meta["conu_h"]
    return f"""
        {cabecera()}
        VAR selg = VALUES(dim_municipio[cod_indec])
        VAR todos = ADDCOLUMNS(ALL(dim_municipio[cod_indec]), "v", IF(dim_municipio[cod_indec] IN selg, [Valor métrica]))
        VAR lo_g = MINX(todos, [v])
        VAR hi_g = MAXX(todos, [v])
        VAR ma_g = MAXX(todos, ABS([v]))
        VAR x_ley = 392
        VAR y_ley = 640
        VAR mostrar_ley = TRUE()
        VAR prov = {capa("svg_prov", "cx_p", "cy_p", "rotulo_p", 8.5, 0.6, True)}
        VAR conu = {capa("svg_conu", "cx_c", "cy_c", "rotulo_c", 10, 0.9, True).replace("mostrar_ley", "FALSE()")}
        VAR svg = "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {pw + 40 + cw} {ph + 40}'>" & prov
            & "<g transform='translate({pw + 40} 44)'><rect x='0' y='0' width='{cw}' height='{ch}' rx='10' fill='#FFFFFF' stroke='{LINEA}' stroke-width='2'/>" & conu & "</g>"
            & "<text x='{pw + 40}' y='30' font-family='Segoe UI' font-size='18' font-weight='700' fill='{VIO}'>Conurbano y Gran La Plata</text></svg>"
        RETURN {svg_uri("svg")}"""


def barra_dos(per: str, der: str, titulo: str) -> str:
    """Barra Peronismo vs. LLA-PRO con la línea del 50 % (como la de Lula vs. Flávio)."""
    return f"""
        VAR p = {per}
        VAR d = {der}
        VAR w = INT(1000 * DIVIDE(p, p + d))
        VAR svg = "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1000 120'>"
            & "<text x='500' y='18' text-anchor='middle' font-family='Segoe UI' font-size='15' fill='{INK}'>50 %</text>"
            & "<rect x='0' y='30' width='" & w & "' height='70' fill='{PER}'><animate attributeName='width' from='500' to='" & w & "' dur='1.2s' calcMode='spline' keySplines='0.2 0.8 0.2 1' keyTimes='0;1'/></rect>"
            & "<rect x='" & w & "' y='30' width='" & (1000 - w) & "' height='70' fill='{DER}'><animate attributeName='x' from='500' to='" & w & "' dur='1.2s' calcMode='spline' keySplines='0.2 0.8 0.2 1' keyTimes='0;1'/><animate attributeName='width' from='500' to='" & (1000 - w) & "' dur='1.2s' calcMode='spline' keySplines='0.2 0.8 0.2 1' keyTimes='0;1'/></rect>"
            & "<line x1='500' y1='24' x2='500' y2='108' stroke='{INK}' stroke-width='3' stroke-dasharray='7 5'/>"
            & "<text x='18' y='76' font-family='Segoe UI' font-size='30' font-weight='700' fill='#FFFFFF'>PERONISMO " & FORMAT(DIVIDE(p, p + d), "0.0%") & "</text>"
            & "<text x='982' y='76' text-anchor='end' font-family='Segoe UI' font-size='30' font-weight='700' fill='#FFFFFF'>LLA + PRO " & FORMAT(DIVIDE(d, p + d), "0.0%") & "</text>"
            & "</svg>"
        RETURN {svg_uri("svg")}"""


def medidas(meta) -> list:
    F = {"vot": "01 · Votos", "map": "02 · Mapa", "pro": "03 · Pronóstico 2027", "txt": "04 · Textos y colores"}
    base = [(n, e, f, F["vot"] if c not in ("Formato", "Ficha") else F["txt"], {"dataCategory": cat} if cat else {})
            for n, e, f, c, cat in b.MEDIDAS + v8.MEDIDAS_EXTRA if n not in ("Color fuerza", "Color espacio", "Título ficha")]
    esc = lambda c: f'LOOKUPVALUE(escenarios_2027[{c}], escenarios_2027[escenario], "{ESC_BASE}")'  # noqa: E731
    pw, ph, cw, ch = meta["prov_w"], meta["prov_h"], meta["conu_w"], meta["conu_h"]
    nuevas = [
        ("Color espacio", "SELECTEDVALUE(dim_espacio[color], \"#9A93AD\")", None, F["txt"]),
        ("Color ganador", 'LOOKUPVALUE(dim_espacio[color], dim_espacio[espacio_nombre], [Ganador], "#9A93AD")', None, F["txt"]),
        ("Margen P-D (pts)", "([% Peronismo] - [% Derecha]) * 100", "+0.0;-0.0;0", F["vot"]),
        ("Cambio peronismo vs 2023 (pts)", '([% Peronismo] - CALCULATE([% Peronismo], REMOVEFILTERS(dim_eleccion), dim_eleccion[eleccion] = "G2023")) * 100',
         "+0.0;-0.0;0", F["vot"]),
        ("P(peronismo) 2027 base", 'CALCULATE(AVERAGE(fact_motor_2027[p_gana_peronismo]), fact_motor_2027[escenario_clave] = "A")', "0%", F["pro"]),
        ("Electores provincia", "CALCULATE([Electores], REMOVEFILTERS(dim_municipio))", "#,0", F["vot"]),
        ("% del padrón provincial", "DIVIDE([Electores], [Electores provincia])", "0.0%", F["vot"]),
        ("Color diferencia", f'IF([Diferencia de votos] >= 0, "{PER}", "{DER}")', None, F["txt"]),
        ("Margen escenario", "SUM(escenarios_2027[margen])", "+0.0;-0.0;0", F["pro"]),
        ("Color escenario", f'IF([Margen escenario] >= 0, "{PER}", "{DER}")', None, F["txt"]),
        ("Pronóstico P(gana)", esc("p_gana_peronismo"), "0%", F["pro"]),
        ("Pronóstico margen", esc("margen"), "+0.0;-0.0;0", F["pro"]),
        ("Pronóstico rango", f'FORMAT({esc("margen_p10")}, "+0.0;-0.0") & " a " & FORMAT({esc("margen_p90")}, "+0.0;-0.0") & " pts"', None, F["pro"]),
        ("Pronóstico municipios", esc("municipios_peronistas"), "0", F["pro"]),
        ("Métrica", "SELECTEDVALUE(metrica_mapa[id], 1)", "0", F["map"]),
        ("Valor métrica", f"VAR idm = [Métrica] RETURN {sw(2)}", None, F["map"], {"formatStringDefinition": f"VAR idm = [Métrica] RETURN {sw(6)}"}),
        ("Valor métrica (texto)", f"VAR idm = [Métrica] VAR v = [Valor métrica] RETURN IF(ISBLANK(v), \"—\", FORMAT(v, {sw(6)}) & IF(idm = 1, \" · \" & [Ganador], \"\"))",
         None, F["map"]),
        ("Color métrica", f"{cabecera()}\nVAR v = [Valor métrica]\nRETURN SWITCH(TRUE(), modo = 2, [Color ganador], modo = 3 && v < 0, neg, base)", None, F["txt"]),
        ("Título del mapa", 'VAR m = SELECTEDVALUE(metrica_mapa[metrica], "Ganador de la elección")\nVAR idm = [Métrica]\n'
                            'RETURN m & IF(idm <= 6, "  ·  " & [Elección seleccionada], IF(idm = 7, "  ·  escenario: se repite octubre 2025", "  ·  censo 2022"))',
         None, F["map"]),
        ("Corte", '"Elección: " & [Elección seleccionada] & "  ·  datos DINE, Junta Electoral PBA, INDEC 2022  ·  motor ATLAS (1.000 simulaciones)"', None, F["txt"]),
        ("Título ficha", 'IF(HASONEVALUE(dim_municipio[cod_indec]), SELECTEDVALUE(dim_municipio[municipio]), "Elegí un municipio")', None, F["txt"]),
        ("Subtítulo ficha", 'IF(HASONEVALUE(dim_municipio[cod_indec]), SELECTEDVALUE(dim_municipio[seccion]) & " sección electoral  ·  " & SELECTEDVALUE(dim_municipio[zona]) '
                            '& "  ·  intendente: " & SELECTEDVALUE(dim_municipio[intendente]) & " (" & SELECTEDVALUE(dim_municipio[fuerza_intendente]) & ")", '
                            '"Clic derecho sobre un municipio en cualquier página › Obtener detalles › Ficha del municipio")', None, F["txt"]),
        ("SVG mapa provincia", mapa_dax("svg_prov", "cx_p", "cy_p", "rotulo_p", 8.5, 0.6, f"0 0 {pw} {ph + 40}", 392, 640), None, F["map"],
         {"dataCategory": "ImageUrl"}),
        ("SVG mapa conurbano", mapa_dax("svg_conu", "cx_c", "cy_c", "rotulo_c", 10, 0.9, f"0 0 {cw} {ch}", 0, 0, ley=False), None, F["map"],
         {"dataCategory": "ImageUrl"}),
        ("SVG mapa completo", mapa_completo(meta), None, F["map"], {"dataCategory": "ImageUrl"}),
        ("SVG barra pronóstico", barra_dos(f"(50 + {esc('margen')} / 2)", f"(50 - {esc('margen')} / 2)", ""), None, F["pro"], {"dataCategory": "ImageUrl"}),
        ("SVG barra elección", barra_dos("[% Peronismo]", "[% Derecha]", ""), None, F["vot"], {"dataCategory": "ImageUrl"}),
    ]
    return base + nuevas


def modelo(t: dict) -> dict:
    pct, mil = "0.0%", "#,0"
    T = {}
    oc_m = ("svg_prov", "svg_conu", "cx_p", "cy_p", "cx_c", "cy_c", "rotulo_p", "rotulo_c", "nombre_corto", "seccion_num", "orden",
            "color_fuerza", "ubicacion", "simulador_url", "foto_credito", "electo_foto_licencia", "electo_foto_autor", "electo_foto_fuente",
            "misma_persona", "orden_fuerza")
    T["dim_municipio"] = tabla_csv("dim_municipio", DATOS, "dim_municipio.csv", sumar=tuple(c for c in b.SUMA if c in t["dim_municipio"].columns),
                                   ocultas=oc_m, extra_col={"cod_indec": {"isKey": ""}, "seccion": {"sortByColumn": "seccion_num"},
                                                            "foto_url": {"dataCategory": "ImageUrl"}, "logo_url": {"dataCategory": "ImageUrl"},
                                                            "wikipedia_url": {"dataCategory": "WebUrl"}})
    T["dim_eleccion"] = tabla_csv("dim_eleccion", DATOS, "dim_eleccion.csv", ocultas=("orden", "fuente"),
                                  extra_col={"eleccion": {"isKey": ""}, "rotulo": {"sortByColumn": "orden"}, "etiqueta": {"sortByColumn": "orden"}})
    T["dim_espacio"] = tabla_csv("dim_espacio", DATOS, "dim_espacio.csv", ocultas=("orden", "color", "logo_url"),
                                 extra_col={"espacio": {"isKey": ""}, "espacio_nombre": {"sortByColumn": "orden"}})
    T["fact_votos"] = tabla_csv("fact_votos", DATOS, "fact_votos.csv", ocultas=("eleccion", "cod_indec", "espacio"), sumar=("votos",))
    T["fact_participacion"] = tabla_csv("fact_participacion", DATOS, "fact_participacion.csv",
                                        ocultas=("eleccion", "cod_indec", "ganador", "clave", "orden_rango_peronismo", "orden_rango_participacion", "orden_competencia"),
                                        extra_col={"rango_peronismo": {"sortByColumn": "orden_rango_peronismo"},
                                                   "rango_participacion": {"sortByColumn": "orden_rango_participacion"},
                                                   "competencia": {"sortByColumn": "orden_competencia"}})
    T["fact_motor_2027"] = tabla_csv("fact_motor_2027", DATOS, "fact_motor_2027.csv", ocultas=("cod_indec", "escenario_clave"), formatos={"p_gana_peronismo": "0%"})
    T["escenarios_2027"] = tabla_csv("escenarios_2027", DATOS, "escenarios_2027.csv", formatos={"p_gana_peronismo": "0%"})
    filas = ",\n".join(f'    {{{m[0]}, "{m[1]}"}}' for m in METRICAS)
    T["metrica_mapa"] = tabla_calculada("metrica_mapa", f'DATATABLE("id", INTEGER, "metrica", STRING, {{\n{filas}\n}})',
                                        [("id", "int64", None, {"isHidden": True}), ("metrica", "string", None, {"sortByColumn": "id"})])
    T["Medidas"] = tabla_calculada("Medidas", "{BLANK()}", [("Valor", "string", None, {"isHidden": True}, "[Value]")], medidas(t["meta"]))
    A = {f"definition/tables/{n}.tmdl": s for n, s in T.items()}
    A["definition/expressions.tmdl"] = (f'expression CarpetaDatos = "{DATOS}\\" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]\n'
                                        "\tannotation PBI_ResultType = Text\n")
    A["definition/relationships.tmdl"] = relaciones([
        (("fact_votos", "cod_indec"), ("dim_municipio", "cod_indec")), (("fact_votos", "eleccion"), ("dim_eleccion", "eleccion")),
        (("fact_votos", "espacio"), ("dim_espacio", "espacio")), (("fact_participacion", "cod_indec"), ("dim_municipio", "cod_indec")),
        (("fact_participacion", "eleccion"), ("dim_eleccion", "eleccion")), (("fact_motor_2027", "cod_indec"), ("dim_municipio", "cod_indec"))])
    A["definition/database.tmdl"] = "database\n\tcompatibilityLevel: 1601\n"
    A["definition/model.tmdl"] = (
        "model Model\n\tculture: es-ES\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n\tdiscourageImplicitMeasures\n"
        "\tsourceQueryCulture: es-AR\n\tdataAccessOptions\n\t\tlegacyRedirects\n\t\treturnErrorValuesAsNull\n\n"
        f"annotation PBI_QueryOrder = {json.dumps(['CarpetaDatos'] + list(T), ensure_ascii=False)}\n\n"
        "annotation __PBI_TimeIntelligenceEnabled = 0\n\n" + "\n".join(f"ref table {q(n)}" for n in T) + "\n")
    A["definition.pbism"] = json.dumps({"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
                                        "version": "4.2", "settings": {}}, indent=2)
    return A


# ================================================================== informe
def colores_serie(entidad, columna, mapa):
    return [{"properties": {"fill": color(c)},
             "selector": {"data": [{"scopeId": {"Comparison": {"ComparisonKind": 0, "Left": C(entidad, columna),
                                                               "Right": {"Literal": {"Value": "'" + v.replace("'", "''") + "'"}}}}}]}}
            for v, c in mapa.items()]


def barra_nav(pg: Pagina, activa: str):
    pg.texto(0, 0, 200, H, [[("ATLAS", {"size": 20, "bold": True, "color": "#FFFFFF", "font": "Segoe UI Black"})],
                             [("ANALYTICS", {"size": 9, "bold": True, "color": ORO})],
                             [("Provincia de Buenos Aires · 2027", {"size": 9, "color": "#CFC7E2"})]], fondo=INK)
    for i, (dest, et, ic) in enumerate(NAV):
        y = 92 + i * 36
        if dest:
            act = dest == activa
            pg.boton(10, y, 180, 31, f"{ic}   {et}", dest, fondo=VIO if act else "#2A2147", fg="#FFFFFF" if act else "#D9D2EA", size=9.5, hover="#3D3166")
        else:  # página de la próxima entrega
            pg.texto(10, y, 180, 31, [[(f"{ic}   {et}", {"size": 9, "color": "#6F6790"})]])
    pg.texto(10, 640, 180, 254, [[("Cómo navegar", {"size": 9, "bold": True, "color": ORO})],
                                 [("• Botones: saltan de página (en Desktop, Ctrl+clic)", {"size": 8.5, "color": "#CFC7E2"})],
                                 [("• Clic en una barra o una fila: el municipio se resalta en el mapa", {"size": 8.5, "color": "#CFC7E2"})],
                                 [("• Clic derecho › Obtener detalles: ficha del municipio", {"size": 8.5, "color": "#CFC7E2"})],
                                 [("• Pasá el mouse: resultado del municipio", {"size": 8.5, "color": "#CFC7E2"})],
                                 [("• Elección, sección y zona se sincronizan entre páginas", {"size": 8.5, "color": "#CFC7E2"})],
                                 [("En gris: páginas de la próxima entrega", {"size": 8, "color": "#6F6790"})]])


def pagina(nombre, titulo, sub):
    pg = Pagina(nombre, titulo, sub, corte="Corte")
    barra_nav(pg, nombre)
    return pg


def tooltip(vis):
    vis["visual"].setdefault("visualContainerObjects", {})["visualTooltip"] = [
        {"properties": {"show": lit(True), "type": lit("ReportPage"), "section": lit(TT)}}]
    return vis


def seg_eleccion(pg, x, y, w):
    return pg.segmentador(x, y, w, 58, C("dim_eleccion", "rotulo"), "Elección", sync="eleccion", unico=True, presel="Diputados nacionales 2025")


def seg_seccion(pg, x, y, w):
    return pg.segmentador(x, y, w, 58, DM("seccion"), "Sección electoral", sync="seccion")


def seg_zona(pg, x, y, w):
    return pg.segmentador(x, y, w, 58, DM("zona"), "Zona", sync="zona")


def seg_metrica(pg, x, y, w):
    return pg.segmentador(x, y, w, 58, C("metrica_mapa", "metrica"), "Métrica del mapa", sync="metrica", unico=True, presel="Ganador de la elección")


def tile(pg, x, y, w, h, dest, t, d):
    pg.texto(x, y, w, h, [[(t, {"size": 12, "bold": True, "font": "Segoe UI Semibold"})], [(d, {"size": 9, "color": MUTED})]], fondo="#FFFFFF", borde=True)
    if dest:
        pg.boton(x, y, w, h, " ", dest, fondo="#FFFFFF", fg=INK, size=1, hover=VIO, transp=100, transp_hover=88)


def caja(pg, x, y, w, h, titulo):
    """Recuadro blanco con título (detrás de mapas e imágenes)."""
    pg.texto(x, y, w, h, [[(titulo, {"size": 11, "bold": True, "font": "Segoe UI Semibold", "color": VIO})]], fondo="#FFFFFF", borde=True)


def informe(t: dict) -> dict:
    pags: list[Pagina] = []
    esp = C("dim_espacio", "espacio_nombre")
    eti = C("dim_eleccion", "etiqueta")

    # =================================================================== INICIO
    pg = Pagina("inicio", "Inicio", cabecera=False)
    barra_nav(pg, "inicio")
    pg.texto(X0, 14, 1000, 130, [
        [("PROVINCIA DE BUENOS AIRES · ELECCIÓN DE GOBERNADOR 2027", {"size": 10.5, "bold": True, "color": VIO})],
        [("El mapa del voto bonaerense", {"size": 32, "bold": True, "font": "Segoe UI Black"})],
        [("135 municipios · 8 secciones electorales · 1.146 circuitos · 17 elecciones de 2007 a 2025 · censo 2022 · "
          "motor de pronóstico de 1.000 simulaciones", {"size": 11, "color": MUTED})]])
    caja(pg, X0, 150, 1010, 150, "Pronóstico ATLAS 2027 · si se repite octubre 2025 (dos fuerzas principales)")
    pg.imagen(X0 + 30, 178, 950, 116, "SVG barra pronóstico")
    kp = [("Pronóstico P(gana)", "Probabilidad de que gane el peronismo", PER), ("Pronóstico margen", "Margen esperado del peronismo (pts)", INK),
          ("Pronóstico rango", "Rango del 80 % (10 a 90)", INK), ("Pronóstico municipios", "Municipios peronistas esperados", PER)]
    for i, (m, et, c) in enumerate(kp):
        pg.tarjeta(X0 + i * 256, 312, 246, 100, Me(m), et, size=24, fg=c)
    caja(pg, 1242, 14, 348, 430, "Quién ganó cada municipio · Dip. 2025")
    pg.imagen(1250, 40, 332, 400, "SVG mapa provincia")
    pg.texto(X0, 424, 1010, 30, [[("EXPLORÁ EL TABLERO", {"size": 11, "bold": True, "color": VIO})]])
    tiles = [("mapa_completo", "▣  Mapa completo", "El mapa en pantalla grande, 10 métricas"), ("resumen", "◉  Resumen provincial", "Resultado, secciones y escenarios"), ("mapa", "▦  Mapa de municipios", "10 métricas, ranking y tabla"),
             ("conurbano", "◎  Conurbano", "Los 24 partidos que definen la elección"), (None, "▤  Secciones electorales", "Próxima entrega"),
             (None, "▩  Mapa fino", "Próxima entrega · 1.146 circuitos"), ("historia", "≋  Historia 2007-2025", "Animación ▶ elección por elección"),
             (None, "⚙  Simulador", "Próxima entrega")]
    for i, (dest, tt, d) in enumerate(tiles):
        tile(pg, X0 + (i % 4) * 344, 458 + (i // 4) * 92, 334, 82, dest, tt, d)
    pg.texto(X0, 650, 1368, 240, [
        [("LO QUE HAY QUE SABER", {"size": 11, "bold": True, "color": VIO})],
        [("▸ Si se repite octubre 2025, es un empate: el peronismo gana el 59 % de las simulaciones, con +0,3 puntos de margen esperado.", {"size": 10.5})],
        [("▸ Con la derecha dividida, el peronismo gana el 99-100 % de las simulaciones aunque el PRO sea sólo el 15 % de ese voto.", {"size": 10.5})],
        [("▸ Quién se suma a votar mueve 9 puntos (de −3,7 a +5,4). Más participación pareja no mueve nada.", {"size": 10.5})],
        [("▸ El voto que Kicillof perdió en 2025 se abstuvo (12,6 %, unas 513.000 personas); ninguno pasó a LLA-PRO.", {"size": 10.5})],
        [("▸ El Conurbano es el 64 % del padrón: la 1.ª sección define y la 3.ª es el bastión peronista.", {"size": 10.5})]],
        fondo="#FFFFFF", borde=True)
    pags.append(pg)

    # =================================================================== RESUMEN PROVINCIAL
    pg = pagina("resumen", "Resumen provincial", "Resultado de la elección elegida · las segmentaciones filtran toda la página y se sincronizan entre páginas")
    seg_eleccion(pg, X0, 88, 520)
    seg_seccion(pg, X0 + 530, 88, 420)
    seg_zona(pg, X0 + 960, 88, 408)
    kp = [(Me("% Peronismo"), "Peronismo", PER), (Me("% Derecha"), "LLA + PRO", DER), (Me("Ganador"), "Ganador", INK),
          (Me("Diferencia de votos"), "Diferencia peronismo − LLA/PRO", INK), (Me("Participación"), "Participación", VIO), (Me("Electores"), "Electores", INK)]
    for i, (m, et, c) in enumerate(kp):
        pg.tarjeta(X0 + i * 230, 156, 220, 86, m, et, size=22, fg=c)
    caja(pg, X0, 252, 520, 638, "Ganador por municipio")
    pg.imagen(X0 + 6, 278, 508, 606, "SVG mapa provincia")
    v = barras(pg, 752, 252, 410, 300, esp, Me("% Voto"), "% por fuerza", fx="Color espacio", nombre_val="% de los votos")
    v = barras(pg, 1172, 252, 418, 300, DM("seccion"), Me("Diferencia de votos"), "Diferencia de votos por sección (peronismo − LLA/PRO)",
               fx="Color diferencia", sort=[(DM("seccion"), "Ascending")], nombre_val="Diferencia")
    barras(pg, 752, 562, 838, 328, C("escenarios_2027", "escenario"), Me("Margen escenario"),
           "Pronóstico 2027: margen del peronismo por escenario (mediana de 1.000 simulaciones, pts)", fx="Color escenario", nombre_val="Margen")
    pags.append(pg)

    # =================================================================== MAPA COMPLETO (pantalla grande)
    pg = pagina("mapa_completo", "Mapa completo", "La Provincia y el Conurbano en pantalla grande · elegí la métrica a la derecha · buscá un municipio para resaltarlo")
    pg.rotulo(X0, 88, 1100, 30, "Título del mapa", size=13, fg=VIO)
    caja(pg, X0, 120, 1100, 770, "")
    pg.imagen(X0 + 6, 124, 1088, 762, "SVG mapa completo")
    xr, wr = 1332, 258
    seg_metrica(pg, xr, 88, wr)
    seg_eleccion(pg, xr, 154, wr)
    seg_seccion(pg, xr, 220, wr)
    seg_zona(pg, xr, 286, wr)
    pg.segmentador(xr, 352, wr, 58, DM("municipio"), "Buscar un municipio", buscar=True)
    pg.rotulo(xr, 420, wr, 40, "Municipio", size=13, fg="#FFFFFF", font="Segoe UI Semibold", fondo=INK)
    pg.tarjeta(xr, 464, wr, 86, Me("Valor métrica (texto)"), "Valor de la métrica", size=17, fg=VIO)
    pg.tarjeta(xr, 556, wr, 80, Me("Ganador"), "Ganador de la elección", size=16)
    pg.tarjeta(xr, 642, wr, 80, Me("Electores"), "Electores", size=16)
    pg.texto(xr, 730, wr, 160, [[("Cómo leer el mapa", {"size": 10, "bold": True, "color": VIO})],
                                [("El color sale de la métrica elegida. Las métricas en % van de claro (menos) a oscuro (más); "
                                  "las de margen y cambio, de un color al otro. Lo que queda fuera de los filtros va en gris y "
                                  "el municipio elegido late con un borde.", {"size": 8.5, "color": MUTED})]], fondo="#FFFFFF", borde=True)
    pags.append(pg)

    # =================================================================== MAPA DE MUNICIPIOS
    pg = pagina("mapa", "Mapa de municipios", "Elegí la métrica · clic en una barra del ranking o en una fila: el municipio se resalta en el mapa · clic derecho › Obtener detalles")
    seg_metrica(pg, X0, 88, 470)
    seg_eleccion(pg, X0 + 480, 88, 340)
    seg_seccion(pg, X0 + 830, 88, 280)
    seg_zona(pg, X0 + 1120, 88, 248)
    pg.rotulo(X0, 152, 1368, 30, "Título del mapa", size=12, fg=VIO)
    caja(pg, X0, 186, 540, 704, "Provincia")
    pg.imagen(X0 + 6, 210, 528, 676, "SVG mapa provincia")
    caja(pg, 772, 186, 380, 470, "Conurbano y Gran La Plata")
    pg.imagen(778, 210, 368, 442, "SVG mapa conurbano")
    tooltip(barras(pg, 1162, 186, 428, 704, DM("municipio"), Me("Valor métrica"), "Ranking por la métrica elegida", fx="Color métrica",
                   nombre_val="Valor", size_et=8))
    tooltip(tabla(pg, 772, 666, 380, 224, [(DM("municipio"), "Municipio"), (Me("Valor métrica (texto)"), "Valor"), (Me("Electores"), "Electores")],
                  "Municipios", sort=[(Me("Electores"), "Descending")], size=9))
    pags.append(pg)

    # =================================================================== CONURBANO
    pg = pagina("conurbano", "Conurbano", "Los 24 partidos del Gran Buenos Aires: dos de cada tres electores de la Provincia · elegí la métrica del mapa")
    pg.filtros = [filtro_es("dim_municipio", "zona", ["Conurbano"], "flt_conurbano")]
    seg_metrica(pg, X0, 88, 520)
    seg_eleccion(pg, X0 + 530, 88, 420)
    seg_seccion(pg, X0 + 960, 88, 408)
    kp = [(Me("% del padrón provincial"), "del padrón provincial", INK), (Me("% Peronismo"), "Peronismo", PER), (Me("% Derecha"), "LLA + PRO", DER),
          (Me("Diferencia de votos"), "Diferencia peronismo − LLA/PRO", INK), (Me("Participación"), "Participación", VIO)]
    for i, (m, et, c) in enumerate(kp):
        pg.tarjeta(X0 + i * 276, 156, 266, 86, m, et, size=22, fg=c)
    pg.rotulo(X0, 250, 600, 28, "Título del mapa", size=11, fg=VIO)
    caja(pg, X0, 282, 600, 608, "")
    pg.imagen(X0 + 6, 288, 588, 596, "SVG mapa conurbano")
    tooltip(barras(pg, 832, 252, 360, 638, DM("municipio"), Me("Valor métrica"), "Ranking por la métrica elegida", fx="Color métrica", nombre_val="Valor"))
    tooltip(tabla(pg, 1202, 252, 388, 638, [(DM("municipio"), "Partido"), (Me("% Peronismo"), "Peronismo"), (Me("% Derecha"), "LLA+PRO"),
                                             (Me("Margen P-D (pts)"), "Margen"), (Me("Electores"), "Electores")],
                  "Partido por partido", sort=[(Me("Electores"), "Descending")], size=9))
    pags.append(pg)

    # =================================================================== HISTORIA 2007-2025 (animada)
    pg = pagina("historia", "Historia 2007-2025", "Tocá ▶ en el gráfico grande: cada burbuja es un municipio que se mueve elección por elección")
    pg.segmentador(X0, 88, 450, 58, C("dim_eleccion", "grupo"), "Tipo de elección", sync="grupo")
    seg_seccion(pg, X0 + 460, 88, 450)
    seg_zona(pg, X0 + 920, 88, 448)
    anim = pg.add("scatterChart", X0, 156, 820, 734,
                  query={"Category": [proj(DM("municipio"))], "Series": [proj(DM("zona"))], "X": [proj(Me("Participación"), "Participación")],
                         "Y": [proj(Me("% Peronismo"), "% peronismo")], "Size": [proj(Me("Electores"), "Electores")], "Play": [proj(eti)]},
                  objects={"dataPoint": colores_serie("dim_municipio", "zona", {"Conurbano": PER, "Interior": ORO}),
                           "legend": [{"properties": {"show": lit(True), "position": lit("Top")}}],
                           "categoryAxis": [{"properties": {"showAxisTitle": lit(True), "fontSize": lit(9)}}],
                           "valueAxis": [{"properties": {"showAxisTitle": lit(True), "fontSize": lit(9)}}],
                           "bubbles": [{"properties": {"bubbleSize": lit(-20)}}]},
                  titulo="▶ El voto peronista (vertical) y la participación (horizontal), municipio por municipio, 2007-2025")
    tooltip(anim)
    lin = pg.add("lineChart", 1052, 156, 538, 360, query={"Category": [proj(eti)], "Series": [proj(esp)], "Y": [proj(Me("% Voto"), "% de los votos")]},
                 objects={"dataPoint": colores_serie("dim_espacio", "espacio_nombre", {r.espacio_nombre: r.color for r in t["dim_espacio"].itertuples()}),
                          "legend": [{"properties": {"show": lit(True), "position": lit("Top")}}],
                          "valueAxis": [{"properties": {"gridlineShow": lit(False)}}],
                          "categoryAxis": [{"properties": {"fontSize": lit(8), "showAxisTitle": lit(False)}}]},
                 titulo="% de cada fuerza en la Provincia, elección por elección", sort=[(eti, "Ascending")])
    gan = pg.add("columnChart", 1052, 526, 538, 364, query={"Category": [proj(eti)], "Series": [proj(C("fact_participacion", "ganador_nombre"))],
                                                          "Y": [proj(Me("Municipios ganados"), "Municipios")]},
                 objects={"dataPoint": colores_serie("fact_participacion", "ganador_nombre", {r.espacio_nombre: r.color for r in t["dim_espacio"].itertuples()}),
                          "legend": [{"properties": {"show": lit(True), "position": lit("Top")}}],
                          "categoryAxis": [{"properties": {"fontSize": lit(8), "showAxisTitle": lit(False)}}]},
                 titulo="Municipios que ganó cada fuerza", sort=[(eti, "Ascending")])
    pags.append(pg)

    # =================================================================== FICHA DEL MUNICIPIO (Obtener detalles)
    pg = Pagina("ficha", "Ficha del municipio", cabecera=False)
    barra_nav(pg, "ficha")
    pg.rotulo(X0, 8, 1000, 50, "Título ficha", size=24, fg=INK, font="Segoe UI Black")
    pg.rotulo(X0, 56, 940, 28, "Subtítulo ficha", size=10, fg=MUTED, font="Segoe UI")
    pg.boton(1430, 18, 160, 34, "◄  Volver", tipo="Back", fondo="#FFFFFF", fg=INK, size=10, hover=GRIS, borde=LINEA)
    seg_eleccion(pg, 1180, 60, 410)
    caja(pg, X0, 128, 230, 300, "Intendente")
    pg.imagen(X0 + 10, 154, 210, 230, "Foto intendente")
    pg.rotulo(X0 + 6, 388, 218, 36, "Intendente", size=10.5, fg=INK)
    kp = [(Me("% Peronismo"), "Peronismo", PER), (Me("% Derecha"), "LLA + PRO", DER), (Me("Ganador"), "Ganador", INK),
          (Me("Margen P-D (pts)"), "Margen (pts)", INK), (Me("Participación"), "Participación", VIO)]
    for i, (m, et, c) in enumerate(kp):
        pg.tarjeta(462 + i * 224, 128, 214, 86, m, et, size=20, fg=c)
    lin = pg.add("lineChart", 462, 224, 760, 330, query={"Category": [proj(eti)], "Y": [proj(Me("% Peronismo"), "Peronismo"), proj(Me("% Derecha"), "LLA + PRO")]},
                 objects={"dataPoint": [{"properties": {"fill": color(PER)}, "selector": {"metadata": "Medidas.% Peronismo"}},
                                        {"properties": {"fill": color(DER)}, "selector": {"metadata": "Medidas.% Derecha"}}],
                          "labels": [{"properties": {"show": lit(True), "fontSize": lit(8), "labelDisplayUnits": lit(1)}}],
                          "legend": [{"properties": {"show": lit(True), "position": lit("Top")}}],
                          "valueAxis": [{"properties": {"show": lit(False), "gridlineShow": lit(False)}}],
                          "categoryAxis": [{"properties": {"fontSize": lit(8), "showAxisTitle": lit(False)}}]},
                 titulo="Cómo votó, elección por elección (2007-2025)", sort=[(eti, "Ascending")])
    pg.sin_filtro('"Entity": "dim_eleccion"}}, "Property": "rotulo"', lin)
    caja(pg, 1232, 224, 358, 330, "Dónde queda")
    pg.imagen(1238, 248, 346, 302, "SVG mapa provincia")
    kc = [(Me("Población"), "Población 2022"), (Me("Electores"), "Electores"), (Me("Hogares con NBI %"), "Hogares con NBI"),
          (Me("Hogares en barrios populares %"), "En barrios populares"), (Me("Universitarios %"), "Universitarios")]
    for i, (m, et) in enumerate(kc):
        pg.tarjeta(X0 + (i % 1) * 0, 438 + i * 90, 230, 82, m, et, size=18)
    hist = tabla(pg, 462, 564, 1128, 326, [(C("dim_eleccion", "rotulo"), "Elección"), (Me("Ganador"), "Ganó"), (Me("% Peronismo"), "Peronismo"),
                                           (Me("% Derecha"), "LLA + PRO"), (Me("Margen P-D (pts)"), "Margen (pts)"), (Me("Participación"), "Participación"),
                                           (Me("Electores"), "Electores")],
                 "Todas las elecciones", sort=[(C("dim_eleccion", "rotulo"), "Descending")], size=9.5)
    pg.sin_filtro('"Entity": "dim_eleccion"}}, "Property": "rotulo"', hist)
    pg.tipo = "Drillthrough"
    pg.filtros = [{"name": "dt_municipio", "field": DM("municipio"), "type": "Categorical", "howCreated": "Drillthrough"}]
    pg.binding = {"name": "pb_ficha", "type": "Drillthrough", "parameters": [{"name": "par_municipio", "boundFilter": "dt_municipio", "fieldExpr": DM("municipio")}]}
    pags.append(pg)

    # =================================================================== TOOLTIP
    pg = Pagina(TT, "Tooltip municipio", w=340, h=250, cabecera=False, oculta=True)
    pg.rotulo(4, 4, 332, 40, "Municipio", size=14, fg="#FFFFFF", font="Segoe UI Semibold", fondo=INK)
    for i, (m, et, c) in enumerate([(Me("Ganador"), "Ganó", INK), (Me("Margen P-D (pts)"), "Margen (pts)", INK), (Me("% Peronismo"), "Peronismo", PER),
                                    (Me("% Derecha"), "LLA + PRO", DER), (Me("Participación"), "Participación", VIO), (Me("Electores"), "Electores", INK)]):
        pg.tarjeta(4 + (i % 2) * 168, 50 + (i // 2) * 66, 164, 62, m, et, size=15, fg=c)
    pg.tipo, pg.binding = "Tooltip", {"name": "pb_tooltip", "type": "Tooltip"}
    pags.append(pg)

    # =================================================================== archivos
    A: dict = {}
    for p in pags:
        A[f"definition/pages/{p.nombre}/page.json"] = p.json()
        for vv in p.visuales:
            A[f"definition/pages/{p.nombre}/visuals/{vv['name']}/visual.json"] = vv
    A["definition/pages/pages.json"] = {"$schema": f"{SCH}/pagesMetadata/1.0.0/schema.json", "pageOrder": [p.nombre for p in pags], "activePageName": "inicio"}
    A["definition/version.json"] = {"$schema": f"{SCH}/versionMetadata/1.0.0/schema.json", "version": "2.0.0"}
    ver = {"visual": V_VISUAL, "report": V_REPORT, "page": V_PAGE}
    tema_base = (PBI_TEMAS / f"{BASE_THEME}.json").exists()
    tc = {"customTheme": {"name": TEMA, "reportVersionAtImport": ver, "type": "RegisteredResources"}}
    paquetes = [{"name": "RegisteredResources", "type": "RegisteredResources", "items": [{"name": TEMA, "path": TEMA, "type": "CustomTheme"}]}]
    if tema_base:
        tc["baseTheme"] = {"name": BASE_THEME, "reportVersionAtImport": ver, "type": "SharedResources"}
        paquetes.insert(0, {"name": "SharedResources", "type": "SharedResources",
                            "items": [{"name": BASE_THEME, "path": f"BaseThemes/{BASE_THEME}.json", "type": "BaseTheme"}]})
    A["definition/report.json"] = {
        "$schema": f"{SCH}/report/{V_REPORT}/schema.json", "themeCollection": tc,
        "objects": {"outspacePane": [{"properties": {"expanded": lit(False)}}], "section": [{"properties": {"verticalAlignment": lit("Top")}}]},
        "resourcePackages": paquetes,
        "settings": {"useStylableVisualContainerHeader": True, "exportDataMode": "AllowSummarized", "defaultDrillFilterOtherVisuals": True,
                     "allowChangeFilterTypes": True, "useEnhancedTooltips": True, "useDefaultAggregateDisplayName": True}}
    A[f"StaticResources/RegisteredResources/{TEMA}"] = tema()
    A["definition.pbir"] = {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
                            "version": "4.0", "datasetReference": {"byPath": {"path": f"../{NOMBRE}.SemanticModel"}}}
    return A


def tema() -> dict:
    caja_ = {"border": [{"show": True, "color": {"solid": {"color": LINEA}}, "radius": 12}],
             "dropShadow": [{"show": True, "color": {"solid": {"color": VIO}}, "transparency": 88, "position": "Outer",
                             "preset": "Custom", "shadowSpread": 0, "shadowBlur": 10, "angle": 90, "shadowDistance": 3}],
             "background": [{"show": True, "color": {"solid": {"color": "#FFFFFF"}}, "transparency": 0}],
             "title": [{"fontColor": {"solid": {"color": INK}}, "fontSize": 11, "fontFamily": "Segoe UI Semibold"}],
             "padding": [{"top": 8, "bottom": 8, "left": 10, "right": 10}],
             "visualHeader": [{"foreground": {"solid": {"color": MUTED}}, "transparency": 0}]}
    return {"name": "ATLAS PBA 2027",
            "dataColors": [PER, DER, "#F2B705", "#A04BB5", VERDE, "#F2994A", ROJO, "#9A93AD", ORO, INK],
            "foreground": INK, "foregroundNeutralSecondary": MUTED, "foregroundNeutralTertiary": "#9A93AD",
            "background": "#FFFFFF", "backgroundLight": BG, "backgroundNeutral": LINEA, "tableAccent": VIO,
            "good": VERDE, "neutral": ORO, "bad": ROJO, "maximum": VIO, "center": "#C9B8E3", "minimum": "#F4F1F9",
            "hyperlink": VIO, "visitedHyperlink": VIO,
            "textClasses": {"callout": {"fontSize": 26, "fontFace": "Segoe UI Semibold", "color": INK},
                            "title": {"fontSize": 11, "fontFace": "Segoe UI Semibold", "color": INK},
                            "header": {"fontSize": 11, "fontFace": "Segoe UI Semibold", "color": INK},
                            "label": {"fontSize": 10, "fontFace": "Segoe UI", "color": INK}},
            "visualStyles": {
                "*": {"*": caja_},
                "page": {"*": {"background": [{"color": {"solid": {"color": BG}}, "transparency": 0}],
                               "outspace": [{"color": {"solid": {"color": "#E9E4F2"}}}]}},
                "textbox": {"*": {"border": [{"show": False}], "dropShadow": [{"show": False}],
                                  "background": [{"show": False}], "padding": [{"top": 4, "bottom": 4, "left": 6, "right": 6}]}},
                "actionButton": {"*": {"border": [{"show": False}], "dropShadow": [{"show": False}], "background": [{"show": False}],
                                       "padding": [{"top": 0, "bottom": 0, "left": 0, "right": 0}]}},
                "image": {"*": {"padding": [{"top": 4, "bottom": 4, "left": 4, "right": 4}], "border": [{"show": False}],
                                "dropShadow": [{"show": False}], "background": [{"show": False}]}},
                "slicer": {"*": {"padding": [{"top": 4, "bottom": 4, "left": 8, "right": 8}]}}}}


# ================================================================== proyecto
def generar(esquemas: Path | None = None) -> Path:
    t = datos()
    DATOS.mkdir(parents=True, exist_ok=True)
    for n in ["dim_municipio", "dim_eleccion", "dim_espacio", "fact_votos", "fact_participacion", "fact_motor_2027", "escenarios_2027"]:
        t[n].to_csv(DATOS / f"{n}.csv", index=False, encoding="utf-8")
    sm, rp = PBI / f"{NOMBRE}.SemanticModel", PBI / f"{NOMBRE}.Report"
    for d in (rp / "definition", sm / "definition"):
        shutil.rmtree(d, ignore_errors=True)
    escribir(modelo(t), sm)
    escribir(informe(t), rp)
    if (PBI_TEMAS / f"{BASE_THEME}.json").exists():
        dst = rp / "StaticResources" / "SharedResources" / "BaseThemes" / f"{BASE_THEME}.json"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(PBI_TEMAS / f"{BASE_THEME}.json", dst)
    for carpeta, tipo in ((sm, "SemanticModel"), (rp, "Report")):
        plat = carpeta / ".platform"
        lid = json.loads(plat.read_text())["config"]["logicalId"] if plat.exists() else str(uuid.uuid4())
        plat.write_text(json.dumps({"$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
                                    "metadata": {"type": tipo, "displayName": NOMBRE}, "config": {"version": "2.0", "logicalId": lid}}, indent=2))
    (PBI / f"{NOMBRE}.pbip").write_text(json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
        "version": "1.0", "artifacts": [{"report": {"path": f"{NOMBRE}.Report"}}], "settings": {"enableAutoRecovery": True}}, indent=2))
    print(f"proyecto: {PBI / (NOMBRE + '.pbip')} · {sum(1 for _ in rp.rglob('visual.json'))} visuales")
    if esquemas:
        b.validar(rp, esquemas)
    return PBI / f"{NOMBRE}.pbip"


if __name__ == "__main__":
    generar(Path(sys.argv[sys.argv.index("--esquemas") + 1]) if "--esquemas" in sys.argv else None)
