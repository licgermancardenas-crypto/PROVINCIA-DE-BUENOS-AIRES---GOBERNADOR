"""
p09 · entrega 2 del tablero ATLAS PBA 2027: Secciones electorales · Mapa fino (circuitos) · Explorador ·
Corrimientos · Dónde se decide · Intendentes 2027 · Pronóstico 2027 · Simulador · Metodología.

Lo usa `p09_powerbi_pba2027.py` (datos, medidas, tablas y páginas); no se corre solo.
"""
from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import box

import p06_powerbi as b
import p09_powerbi_pba2027 as p
import svg_mapa
from pbi_atlas import INK, MUTED, ORO, VIO, X0, C, Me, barras, filtro_es, lit, parametro, proj, tabla, tabla_calculada, tabla_csv, svg_uri, color

PER, DER, ROJO, VERDE, GRIS, HALO = p.PER, p.DER, p.ROJO, p.VERDE, p.GRIS, p.HALO
DM = p.DM
CI = lambda c: C("circuitos", c)  # noqa: E731

REELECCION = [("Puede ir por la reelección", "#2E9C8F"), ("No puede: cumple su segundo mandato", "#E0A526"), ("Intendente interino", "#9A93AD")]
BANCAS = {1: (15, 8), 2: (11, 5), 3: (18, 9), 4: (14, 7), 5: (11, 5), 6: (11, 6), 7: (6, 3), 8: (6, 3)}  # (diputados, senadores)
REGION = {1: "Norte y oeste del Conurbano", 2: "Norte del interior", 3: "Sur del Conurbano", 4: "Noroeste", 5: "Costa y sudeste",
          6: "Sudoeste", 7: "Centro", 8: "La Plata (Capital)"}
# rótulos de las secciones chicas, fuera del mapa (sobre el río y el mar), con una línea al centro
ROTULO_FUERA = {1: (540, 70), 3: (560, 150), 8: (570, 230)}

# métricas del mapa fino: id, nombre, modo (1 secuencial, 3 divergente, 4 binaria), color base, color negativo, formato
METRICAS_C = [(1, "Ganador 2025 (peronismo o LLA + PRO)", 4, PER, DER, "+0;-0;0"), (2, "% del peronismo 2025", 1, PER, None, "0%"),
              (3, "% de LLA + PRO 2025", 1, DER, None, "0%"), (4, "Margen peronismo − LLA/PRO 2025 (pts)", 3, PER, DER, "+0;-0;0"),
              (5, "Cambio del peronismo, Gobernador 2023 → Diputados 2025 (pts)", 3, PER, ROJO, "+0;-0;0"), (6, "Participación 2025", 1, VIO, None, "0%"),
              (7, "Hogares con NBI (censo 2022)", 1, ROJO, None, "0.0%"), (8, "Hogares en barrios populares", 1, ORO, None, "0.0%")]


# ================================================================== datos
def datos(t: dict) -> None:
    m = t["dim_municipio"]
    m["reeleccion_2027"] = np.where(m.intendente_situacion == "interino", REELECCION[2][0],
                                    np.where(m.reelecto_2023.astype(str) == "True", REELECCION[1][0], REELECCION[0][0]))
    m["color_reeleccion"] = m.reeleccion_2027.map(dict(REELECCION))
    m["orden_reeleccion"] = m.reeleccion_2027.map({n: i for i, (n, _) in enumerate(REELECCION)})

    part = gpd.read_file(p.RAIZ / "01_DATOS" / "processed" / "geo" / "partidos.gpkg").to_crs(svg_mapa.ALBERS)
    x0, y0, x1, y1 = part.total_bounds
    k = svg_mapa.ANCHO / (x1 - x0)
    sub = part[(part.conurbano.astype(str) == "True") | part.cod_indec.isin(svg_mapa.RECUADRO_EXTRA)]
    bx0, by0, bx1, by1 = sub.total_bounds
    bx0, by0, bx1, by1 = bx0 - 3000, by0 - 3000, bx1 + 3000, by1 + 3000
    kc = svg_mapa.ANCHO / (bx1 - bx0)
    caja = box(bx0, by0, bx1, by1)

    # secciones electorales
    nombre = dict(zip(m.seccion_num, m.seccion))
    # cada sección = unión de sus municipios (el gpkg de secciones trae colecciones con líneas sueltas)
    s = part.merge(m[["cod_indec", "seccion_num"]], on="cod_indec").dissolve("seccion_num").reset_index()
    s["geometry"] = s.geometry.buffer(1).buffer(-1)
    s = s.rename(columns={"seccion_num": "seccion_electoral"})
    fil = []
    for r in s.itertuples():
        n = int(r.seccion_electoral)
        pt = r.geometry.representative_point()
        cx, cy = round((pt.x - x0) * k), round((y1 - pt.y) * k)
        lx, ly = ROTULO_FUERA.get(n, (cx, cy))
        fil.append({"seccion": nombre[n], "seccion_num": n, "region": REGION[n], "diputados": BANCAS[n][0], "senadores": BANCAS[n][1],
                    "path_p": svg_mapa._path(r.geometry.simplify(900), x0, y1, k), "cx": cx, "cy": cy, "lx": lx, "ly": ly,
                    "fuera": int(n in ROTULO_FUERA)})
    t["secciones"] = pd.DataFrame(fil).sort_values("seccion_num")

    # circuitos electorales
    g = gpd.read_file(p.RAIZ / "01_DATOS" / "processed" / "geo" / "circuitos.gpkg")
    g["circuito"] = g.circuito.astype(str).str.zfill(4)
    pt = g.geometry.representative_point()
    g["lon"], g["lat"] = pt.x.round(4), pt.y.round(4)
    ga = g.to_crs(svg_mapa.ALBERS)
    g["path_p"] = [svg_mapa._path(x.simplify(900), x0, y1, k) for x in ga.geometry]
    g["path_c"] = [svg_mapa._path(x.intersection(caja).simplify(150), bx0, by1, kc) if x.intersects(caja) else "" for x in ga.geometry]
    d = pd.read_csv(b.DATOS / "dim_circuito.csv", dtype={"circuito": str, "cod_indec": str})
    d["circuito"] = d.circuito.str.zfill(4)
    g["cod_indec"] = g.cod_indec.astype(str).str.zfill(5)
    c = g[["circuito", "cod_indec", "lon", "lat", "path_p", "path_c"]].merge(
        d[["circuito", "cabecera", "per_D2025", "der_D2025", "part_D2025", "votos_D2025", "per_G2023", "der_G2023", "nbi", "univ", "pob", "bp"]],
        on="circuito", how="left")
    c["ganador_2025"] = np.where(c.per_D2025.isna(), None, np.where(c.per_D2025 >= c.der_D2025, "Peronismo", "LLA + PRO"))
    c["margen_2025"] = (c.per_D2025 - c.der_D2025).round(1)
    c["cambio_peronismo"] = (c.per_D2025 - c.per_G2023).round(1)
    c["circuito_n"] = "Circuito " + c.circuito + " · " + c.cabecera.fillna("")
    t["circuitos"] = c.drop_duplicates("circuito")


# ================================================================== medidas
def capa_circ(path: str, stroke: float) -> str:
    """Formas de los circuitos, con la escala lo/hi/ma calculada afuera (misma en provincia y recuadro)."""
    return f"""
        VAR filas = ADDCOLUMNS(FILTER(ALL(circuitos[circuito], circuitos[{path}], circuitos[per_D2025], circuitos[der_D2025], circuitos[part_D2025],
                circuitos[per_G2023], circuitos[nbi], circuitos[bp]), circuitos[{path}] <> ""), "v", IF(circuitos[circuito] IN selc, {valor_c()}))
        RETURN "<g stroke='#FFFFFF' stroke-width='{stroke}' stroke-linejoin='round'>{p.ANIM_MAPA}" & CONCATENATEX(filas,
            VAR v = [v]
            VAR t = IF(modo = 3, DIVIDE(ABS(v), ma), DIVIDE(v - lo, hi - lo, 1))
            VAR col = SWITCH(TRUE(), ISBLANK(v), "{GRIS}", modo = 4, IF(v >= 0, base, neg), modo = 3 && v < 0, neg, base)
            VAR o = IF(ISBLANK(v) || modo = 4, 92, INT(14 + 85 * t))
            RETURN "<path d='" & circuitos[{path}] & "' fill='" & col & "' fill-opacity='0." & FORMAT(o, "00") & "'/>", "") & "</g>"
        """


def valor_c() -> str:
    c = lambda x: f"circuitos[{x}]"  # noqa: E731
    return (f"SWITCH(idc, 1, {c('per_D2025')} - {c('der_D2025')}, 2, {c('per_D2025')} / 100, 3, {c('der_D2025')} / 100, "
            f"4, {c('per_D2025')} - {c('der_D2025')}, 5, IF(ISBLANK({c('per_G2023')}) || ISBLANK({c('per_D2025')}), BLANK(), {c('per_D2025')} - {c('per_G2023')}), "
            f"6, {c('part_D2025')} / 100, 7, {c('nbi')} / 100, 8, {c('bp')} / 100)")


def swc(i: int) -> str:
    casos = [f'{m[0]}, ' + (f'"{m[i]}"' if isinstance(m[i], str) else str(m[i])) for m in METRICAS_C if m[i] is not None]
    return "SWITCH(idc, " + ", ".join(casos) + ", BLANK())"


def mapa_fino(meta) -> str:
    pw, ph, cw, ch = meta["prov_w"], meta["prov_h"], meta["conu_w"], meta["conu_h"]
    ley = (f"IF(modo = 4, \"<rect x='392' y='4' width='20' height='16' rx='3' fill='{PER}'/><text x='420' y='17' font-family='Segoe UI' font-size='13' fill='{INK}'>Ganó el peronismo</text>"
           f"<rect x='392' y='28' width='20' height='16' rx='3' fill='{DER}'/><text x='420' y='41' font-family='Segoe UI' font-size='13' fill='{INK}'>Ganó LLA + PRO</text>\", "
           f"\"<rect x='392' y='4' width='170' height='16' fill='\" & IF(modo = 3, neg, base) & \"' fill-opacity='0.25'/><rect x='477' y='4' width='85' height='16' fill='\" & base & \"'/>"
           f"<text x='392' y='38' font-family='Segoe UI' font-size='13' fill='{INK}'>\" & FORMAT(IF(modo = 3, -ma, lo), fmtc) & \"</text>"
           f"<text x='562' y='38' text-anchor='end' font-family='Segoe UI' font-size='13' fill='{INK}'>\" & FORMAT(IF(modo = 3, ma, hi), fmtc) & \"</text>\")")
    return f"""
        VAR idc = SELECTEDVALUE(metrica_circuito[id], 1)
        VAR modo = {swc(2)}
        VAR base = {swc(3)}
        VAR neg = {swc(4)}
        VAR fmtc = {swc(5)}
        VAR selc = VALUES(circuitos[circuito])
        VAR todos = ADDCOLUMNS(ALL(circuitos[circuito], circuitos[per_D2025], circuitos[der_D2025], circuitos[part_D2025], circuitos[per_G2023],
                circuitos[nbi], circuitos[bp]), "v", IF(circuitos[circuito] IN selc, {valor_c()}))
        VAR lo = MINX(todos, [v])
        VAR hi = MAXX(todos, [v])
        VAR ma = MAXX(todos, ABS([v]))
        VAR prov = {capa_circ("path_p", 0.25)}
        VAR conu = {capa_circ("path_c", 0.5)}
        VAR bordes = "<g fill='none' stroke='{INK}' stroke-opacity='0.45' stroke-width='0.7'>" & CONCATENATEX(FILTER(ALL(dim_municipio[svg_prov]), dim_municipio[svg_prov] <> ""), "<path d='" & dim_municipio[svg_prov] & "'/>", "") & "</g>"
        VAR bordes_c = "<g fill='none' stroke='{INK}' stroke-opacity='0.55' stroke-width='1.2'>" & CONCATENATEX(FILTER(ALL(dim_municipio[svg_conu]), dim_municipio[svg_conu] <> ""), "<path d='" & dim_municipio[svg_conu] & "'/>", "") & "</g>"
        VAR svg = "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {pw + 40 + cw} {ph + 40}'>" & prov & bordes
            & "<g transform='translate(0 640)'>" & {ley} & "</g>"
            & "<g transform='translate({pw + 40} 44)'><rect x='0' y='0' width='{cw}' height='{ch}' rx='10' fill='#FFFFFF' stroke='#E4DFEE' stroke-width='2'/>" & conu & bordes_c & "</g>"
            & "<text x='{pw + 40}' y='30' font-family='Segoe UI' font-size='18' font-weight='700' fill='{VIO}'>Conurbano y Gran La Plata · circuito por circuito</text></svg>"
        RETURN {svg_uri("svg")}"""


def mapa_secciones() -> str:
    return f"""
        VAR filas = ADDCOLUMNS(ALL(secciones[seccion], secciones[path_p], secciones[cx], secciones[cy], secciones[lx], secciones[ly], secciones[fuera]),
            "c", [Color ganador], "p", [% Peronismo], "d", [% Derecha])
        VAR formas = CONCATENATEX(filas, "<path d='" & secciones[path_p] & "' fill='" & [c] & "' fill-opacity='0.88' stroke='#FFFFFF' stroke-width='2.5' stroke-linejoin='round'/>", "")
        VAR bordes = "<g fill='none' stroke='#FFFFFF' stroke-width='0.5' stroke-opacity='0.75'>" & CONCATENATEX(FILTER(ALL(dim_municipio[svg_prov]), dim_municipio[svg_prov] <> ""), "<path d='" & dim_municipio[svg_prov] & "'/>", "") & "</g>"
        VAR rot = CONCATENATEX(filas,
            IF(secciones[fuera] = 1, "<line x1='" & secciones[cx] & "' y1='" & secciones[cy] & "' x2='" & (secciones[lx] - 30) & "' y2='" & (secciones[ly] - 6) & "' stroke='{INK}' stroke-width='1'/>", "")
            & "<text x='" & secciones[lx] & "' y='" & secciones[ly] & "' text-anchor='middle' font-family='Segoe UI' font-size='20' font-weight='800' fill='{INK}' {HALO}>" & secciones[seccion] & "</text>"
            & "<text x='" & secciones[lx] & "' y='" & (secciones[ly] + 17) & "' text-anchor='middle' font-family='Segoe UI' font-size='12' font-weight='600' fill='{INK}' {HALO}>P " & FORMAT([p], "0%") & " · L " & FORMAT([d], "0%") & "</text>", "")
        VAR svg = "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 640 894'><g>{p.ANIM_MAPA}" & formas & bordes & "</g><g>{p.ANIM_ROT}" & rot & "</g>"
            & "<text x='392' y='700' font-family='Segoe UI' font-size='13' fill='{MUTED}'>P = peronismo · L = LLA + PRO</text>"
            & "<text x='392' y='718' font-family='Segoe UI' font-size='13' fill='{MUTED}'>Color: quién ganó la sección</text></svg>"
        RETURN {svg_uri("svg")}"""


def medidas(meta) -> list:
    F = {"sec": "05 · Secciones", "cir": "06 · Circuitos", "cor": "07 · Corrimientos", "dec": "08 · Dónde se decide", "int": "09 · Intendentes",
         "pro": "03 · Pronóstico 2027", "sim": "10 · Simulador", "txt": "04 · Textos y colores"}
    s = "SELECTEDVALUE(sim_swing[Corrimiento uniforme (pts)], 0) / 100"
    tr = "SELECTEDVALUE(sim_terceros[Terceros que van al peronismo (%)], 0) / 100"
    dv = "SELECTEDVALUE(sim_division[LLA + PRO que se va a otra lista (%)], 0) / 100"
    tot = "CALCULATE([Votos], REMOVEFILTERS(dim_espacio))"
    simP = f"SUMX(VALUES(dim_municipio[cod_indec]), VAR T = {tot} VAR P = [Votos peronismo] VAR D = [Votos derecha] RETURN MAX(0, P + T * ({s}) + (T - P - D) * ({tr})))"
    simD = f"SUMX(VALUES(dim_municipio[cod_indec]), VAR T = {tot} VAR D = [Votos derecha] RETURN MAX(0, D * (1 - ({dv})) - T * ({s})))"
    return [
        # secciones
        ("Diputados", "SUM(secciones[diputados])", "0", F["sec"]),
        ("Senadores", "SUM(secciones[senadores])", "0", F["sec"]),
        ("SVG mapa secciones", mapa_secciones(), None, F["sec"], {"dataCategory": "ImageUrl"}),
        # circuitos
        ("Circuitos con datos", "COUNTROWS(FILTER(circuitos, NOT ISBLANK(circuitos[per_D2025])))", "#,0", F["cir"]),
        ("Votos circuitos", "SUM(circuitos[votos_D2025])", "#,0", F["cir"]),
        ("% peronismo circuitos", "DIVIDE(SUMX(circuitos, circuitos[per_D2025] * circuitos[votos_D2025]), SUM(circuitos[votos_D2025])) / 100", "0.0%", F["cir"]),
        ("% LLA+PRO circuitos", "DIVIDE(SUMX(circuitos, circuitos[der_D2025] * circuitos[votos_D2025]), SUM(circuitos[votos_D2025])) / 100", "0.0%", F["cir"]),
        ("Lon", "AVERAGE(circuitos[lon])", "0.000", F["cir"]),
        ("Lat", "AVERAGE(circuitos[lat])", "0.000", F["cir"]),
        ("Título mapa fino", 'SELECTEDVALUE(metrica_circuito[metrica], "Ganador 2025") & "  ·  circuito por circuito (1.146 circuitos electorales)"', None, F["cir"]),
        ("SVG mapa fino", mapa_fino(meta), None, F["cir"], {"dataCategory": "ImageUrl"}),
        # corrimientos
        ("Elección base elegida", 'SELECTEDVALUE(eleccion_base[Elección base], "Gobernador 2023")', None, F["cor"]),
        ("% Peronismo base", 'VAR e = SELECTEDVALUE(eleccion_base[eleccion], "G2023") RETURN CALCULATE([% Peronismo], REMOVEFILTERS(dim_eleccion), dim_eleccion[eleccion] = e)', "0.0%", F["cor"]),
        ("% Derecha base", 'VAR e = SELECTEDVALUE(eleccion_base[eleccion], "G2023") RETURN CALCULATE([% Derecha], REMOVEFILTERS(dim_eleccion), dim_eleccion[eleccion] = e)', "0.0%", F["cor"]),
        ("Corrimiento peronismo (pts)", "([% Peronismo] - [% Peronismo base]) * 100", "+0.0;-0.0;0", F["cor"]),
        ("Corrimiento LLA/PRO (pts)", "([% Derecha] - [% Derecha base]) * 100", "+0.0;-0.0;0", F["cor"]),
        ("Color corrimiento", f'IF([Corrimiento peronismo (pts)] >= 0, "{PER}", "{ROJO}")', None, F["txt"]),
        ("Municipios donde creció el peronismo", "COUNTROWS(FILTER(VALUES(dim_municipio[cod_indec]), [Corrimiento peronismo (pts)] > 0))", "0", F["cor"]),
        ("Municipios donde cayó el peronismo", "COUNTROWS(FILTER(VALUES(dim_municipio[cod_indec]), [Corrimiento peronismo (pts)] < 0))", "0", F["cor"]),
        # dónde se decide
        ("Tamaño por electores", "[Electores]", "#,0", F["dec"]),
        # enlaces de la ficha
        ("URL Wikipedia", 'VAR u = SELECTEDVALUE(dim_municipio[wikipedia_url]) RETURN IF(ISBLANK(u) || u = "", "https://es.wikipedia.org/wiki/Partido_de_" & SUBSTITUTE(SELECTEDVALUE(dim_municipio[municipio], "Buenos_Aires"), " ", "_"), u)',
         None, F["txt"], {"dataCategory": "WebUrl"}),
        ("URL Google Maps", '"https://www.google.com/maps/search/Partido+de+" & SUBSTITUTE(SELECTEDVALUE(dim_municipio[municipio], "Buenos Aires"), " ", "+") & "+Buenos+Aires"',
         None, F["txt"], {"dataCategory": "WebUrl"}),
        ("URL Noticias", '"https://news.google.com/search?q=%22" & SUBSTITUTE(SELECTEDVALUE(dim_municipio[municipio], "Provincia de Buenos Aires"), " ", "+") & "%22+intendente&hl=es-419&gl=AR"',
         None, F["txt"], {"dataCategory": "WebUrl"}),
        ("Margen absoluto (pts)", "ABS([Margen P-D (pts)])", "0.0", F["dec"]),
        ("Votos para dar vuelta", "ABS([Diferencia de votos]) / 2", "#,0", F["dec"]),
        ("Municipios bisagra", "COUNTROWS(FILTER(VALUES(dim_municipio[cod_indec]), ABS([Margen P-D (pts)]) < 5))", "0", F["dec"]),
        ("Electores en bisagras", "SUMX(FILTER(VALUES(dim_municipio[cod_indec]), ABS([Margen P-D (pts)]) < 5), [Electores])", "#,0", F["dec"]),
        ("% del padrón en bisagras", "DIVIDE([Electores en bisagras], [Electores provincia])", "0.0%", F["dec"]),
        # intendentes
        ("Color intendente", 'SELECTEDVALUE(dim_municipio[color_fuerza], "#9A93AD")', None, F["txt"]),
        ("Fuerza del intendente", 'SELECTEDVALUE(dim_municipio[fuerza_intendente], "—")', None, F["int"]),
        ("Color reelección", 'SELECTEDVALUE(dim_municipio[color_reeleccion], "#9A93AD")', None, F["txt"]),
        ("Reelección 2027", 'SELECTEDVALUE(dim_municipio[reeleccion_2027], "—")', None, F["int"]),
        ("Uno", "IF(HASONEVALUE(dim_municipio[cod_indec]), 1)", "0", F["int"]),
        ("Intendentes de Fuerza Patria", 'CALCULATE([Municipios], dim_municipio[fuerza_intendente] = "Fuerza Patria")', "0", F["int"]),
        ("Pueden reelegir", f'CALCULATE([Municipios], dim_municipio[reeleccion_2027] = "{REELECCION[0][0]}")', "0", F["int"]),
        ("No pueden reelegir", f'CALCULATE([Municipios], dim_municipio[reeleccion_2027] = "{REELECCION[1][0]}")', "0", F["int"]),
        ("Interinos", f'CALCULATE([Municipios], dim_municipio[reeleccion_2027] = "{REELECCION[2][0]}")', "0", F["int"]),
        # pronóstico
        ("% peronismo esperado 2027", 'IF(ISFILTERED(fact_motor_2027[escenario]), AVERAGE(fact_motor_2027[pct_peronismo]), CALCULATE(AVERAGE(fact_motor_2027[pct_peronismo]), fact_motor_2027[escenario_clave] = "A")) / 100',
         "0.0%", F["pro"]),
        # simulador
        ("Sim votos peronismo", simP, "#,0", F["sim"]),
        ("Sim votos LLA+PRO", simD, "#,0", F["sim"]),
        ("Sim votos total", f"SUMX(VALUES(dim_municipio[cod_indec]), {tot})", "#,0", F["sim"]),
        ("Sim % peronismo", "DIVIDE([Sim votos peronismo], [Sim votos total])", "0.0%", F["sim"]),
        ("Sim % LLA+PRO", "DIVIDE([Sim votos LLA+PRO], [Sim votos total])", "0.0%", F["sim"]),
        ("Sim margen (pts)", "DIVIDE([Sim votos peronismo] - [Sim votos LLA+PRO], [Sim votos total]) * 100", "+0.0;-0.0;0", F["sim"]),
        ("Sim ganador", 'IF([Sim votos peronismo] >= [Sim votos LLA+PRO], "Peronismo", "LLA + PRO")', None, F["sim"]),
        ("Sim municipios peronistas", "COUNTROWS(FILTER(VALUES(dim_municipio[cod_indec]), [Sim votos peronismo] > [Sim votos LLA+PRO]))", "0", F["sim"]),
        ("Sim municipios que cambian", "COUNTROWS(FILTER(VALUES(dim_municipio[cod_indec]), ([Sim votos peronismo] > [Sim votos LLA+PRO]) <> ([Votos peronismo] > [Votos derecha])))", "0", F["sim"]),
        ("Color sim", f'IF([Sim margen (pts)] >= 0, "{PER}", "{DER}")', None, F["txt"]),
        ("SVG barra simulación", p.barra_dos("[Sim votos peronismo]", "[Sim votos LLA+PRO]", ""), None, F["sim"], {"dataCategory": "ImageUrl"}),
    ]


# ================================================================== tablas y relaciones
def tablas(t: dict) -> dict:
    T = {}
    T["secciones"] = tabla_csv("secciones", p.DATOS, "secciones.csv", ocultas=("path_p", "cx", "cy", "lx", "ly", "fuera", "seccion_num"),
                               extra_col={"seccion": {"isKey": "", "sortByColumn": "seccion_num"}})
    T["circuitos"] = tabla_csv("circuitos", p.DATOS, "circuitos.csv", ocultas=("path_p", "path_c", "lon", "lat", "cod_indec"),
                               sumar=("votos_D2025", "pob"), extra_col={"circuito": {"isKey": ""}})
    filas = ",\n".join(f'    {{{m[0]}, "{m[1]}"}}' for m in METRICAS_C)
    T["metrica_circuito"] = tabla_calculada("metrica_circuito", f'DATATABLE("id", INTEGER, "metrica", STRING, {{\n{filas}\n}})',
                                            [("id", "int64", None, {"isHidden": True}), ("metrica", "string", None, {"sortByColumn": "id"})])
    T["eleccion_base"] = tabla_calculada("eleccion_base", 'SELECTCOLUMNS(dim_eleccion, "eleccion", dim_eleccion[eleccion], "Elección base", dim_eleccion[rotulo], "orden", dim_eleccion[orden])',
                                         [("eleccion", "string", None, {"isHidden": True}), ("Elección base", "string", None, {"sortByColumn": "orden"}),
                                          ("orden", "int64", None, {"isHidden": True})])
    T["sim_swing"] = parametro("sim_swing", "Corrimiento uniforme (pts)", -10, 10, 1, "+0;-0;0")
    T["sim_terceros"] = parametro("sim_terceros", "Terceros que van al peronismo (%)", 0, 100, 10, "0")
    T["sim_division"] = parametro("sim_division", "LLA + PRO que se va a otra lista (%)", 0, 50, 5, "0")
    return T


RELACIONES = [(("circuitos", "cod_indec"), ("dim_municipio", "cod_indec")), (("dim_municipio", "seccion"), ("secciones", "seccion"))]


# ================================================================== páginas
def mapa_grande(pg, medida_svg, medida_titulo, x=X0, y=252, w=860, h=638):
    pg.rotulo(x, y, w, 28, medida_titulo, size=11, fg=VIO)
    p.caja(pg, x, y + 30, w, h - 30, "")
    pg.imagen(x + 6, y + 34, w - 12, h - 38, medida_svg)


def solo_metrica(pg, ids):
    """Fija la métrica del mapa de la página (filtro de página sobre la tabla de métricas)."""
    pg.filtros = pg.filtros + [filtro_es("metrica_mapa", "metrica", [m[1] for m in p.METRICAS if m[0] in ids], f"flt_metrica_{pg.nombre}")]


def paginas(t: dict) -> list:
    pags = []
    esp = C("dim_espacio", "espacio_nombre")
    pares_esp = {r.espacio_nombre: r.color for r in t["dim_espacio"].itertuples()}

    # =================================================================== SECCIONES ELECTORALES
    pg = p.pagina("secciones", "Secciones electorales", "Las 8 secciones eligen la Legislatura bonaerense: 92 diputados y 46 senadores (se renueva la mitad cada dos años)")
    p.seg_eleccion(pg, X0, 88, 520)
    p.seg_zona(pg, X0 + 530, 88, 400)
    kp = [(Me("Electores"), "Electores", INK), (Me("% Peronismo"), "Peronismo", PER), (Me("% Derecha"), "LLA + PRO", DER),
          (Me("Diferencia de votos"), "Diferencia peronismo − LLA/PRO", INK), (Me("Participación"), "Participación", VIO)]
    for i, (m, et, c) in enumerate(kp):
        pg.tarjeta(X0 + i * 276, 156, 266, 86, m, et, size=22, fg=c)
    p.caja(pg, X0, 252, 470, 638, "Quién ganó cada sección")
    pg.imagen(X0 + 6, 278, 458, 606, "SVG mapa secciones")
    v = pg.add("hundredPercentStackedBarChart", 702, 252, 888, 300,
               query={"Category": [proj(C("secciones", "seccion"))], "Series": [proj(esp)], "Y": [proj(Me("Votos"), "Votos")]},
               objects={"dataPoint": p.colores_serie("dim_espacio", "espacio_nombre", pares_esp),
                        "labels": [{"properties": {"show": lit(True), "fontSize": lit(8), "color": color("#FFFFFF")}}],
                        "legend": [{"properties": {"show": lit(True), "position": lit("Top")}}],
                        "categoryAxis": [{"properties": {"fontSize": lit(10), "showAxisTitle": lit(False)}}],
                        "valueAxis": [{"properties": {"show": lit(False)}}]},
               titulo="Cómo votó cada sección", sort=[(C("secciones", "seccion"), "Ascending")])
    tabla(pg, 702, 562, 888, 328, [(C("secciones", "seccion"), "Sección"), (C("secciones", "region"), "Región"), (Me("Electores"), "Electores"),
                                   (Me("% del padrón provincial"), "% del padrón"), (Me("% Peronismo"), "Peronismo"), (Me("% Derecha"), "LLA + PRO"),
                                   (Me("Margen P-D (pts)"), "Margen"), (Me("Diputados"), "Diputados"), (Me("Senadores"), "Senadores")],
          "Sección por sección", sort=[(C("secciones", "seccion"), "Ascending")], size=10, fx=[(Me("Margen P-D (pts)"), "Color diferencia")])
    pags.append(pg)

    # =================================================================== MAPA FINO (circuitos)
    pg = p.pagina("mapa_fino", "Mapa fino · circuitos", "Los 1.146 circuitos electorales, con los resultados de 2025 y 2023 por circuito · elegí la métrica a la derecha")
    pg.rotulo(X0, 88, 1100, 30, "Título mapa fino", size=13, fg=VIO)
    p.caja(pg, X0, 120, 1100, 770, "")
    pg.imagen(X0 + 6, 124, 1088, 762, "SVG mapa fino")
    xr, wr = 1332, 258
    pg.segmentador(xr, 88, wr, 58, C("metrica_circuito", "metrica"), "Métrica del mapa fino", unico=True, presel=METRICAS_C[0][1])
    p.seg_seccion(pg, xr, 154, wr)
    p.seg_zona(pg, xr, 220, wr)
    pg.segmentador(xr, 286, wr, 58, DM("municipio"), "Buscar un municipio", buscar=True)
    kp = [(Me("Circuitos con datos"), "Circuitos con datos", INK), (Me("% peronismo circuitos"), "Peronismo 2025", PER),
          (Me("% LLA+PRO circuitos"), "LLA + PRO 2025", DER), (Me("Votos circuitos"), "Votos 2025", INK)]
    for i, (m, et, c) in enumerate(kp):
        pg.tarjeta(xr, 354 + i * 88, wr, 80, m, et, size=17, fg=c)
    pg.texto(xr, 710, wr, 180, [[("Para acercarse", {"size": 10, "bold": True, "color": VIO})],
                                [("Elegí una sección, una zona o un municipio: el resto de los circuitos queda en gris. "
                                  "Las líneas finas son los límites de los municipios. Los circuitos sin datos de 2025 van en gris.",
                                  {"size": 8.5, "color": MUTED})]], fondo="#FFFFFF", borde=True)
    pags.append(pg)

    # =================================================================== EXPLORADOR (puntos clicables)
    pg = p.pagina("explorador", "Explorador", "Cada punto es un circuito electoral, ubicado en el mapa · clic en un punto para ver su detalle · elegí una zona o un municipio para acercarte")
    p.seg_seccion(pg, X0, 88, 330)
    p.seg_zona(pg, X0 + 340, 88, 330)
    pg.segmentador(X0 + 680, 88, 340, 58, DM("municipio"), "Municipio", buscar=True)
    pg.segmentador(X0 + 1030, 88, 338, 58, CI("ganador_2025"), "Ganó en 2025")
    sc = pg.add("scatterChart", X0, 156, 700, 734,
                query={"Category": [proj(CI("circuito_n"))], "Series": [proj(CI("ganador_2025"))], "X": [proj(Me("Lon"), "Longitud")],
                       "Y": [proj(Me("Lat"), "Latitud")], "Size": [proj(Me("Votos circuitos"), "Votos 2025")]},
                objects={"dataPoint": p.colores_serie("circuitos", "ganador_2025", {"Peronismo": PER, "LLA + PRO": DER}),
                         "legend": [{"properties": {"show": lit(True), "position": lit("Top")}}],
                         "categoryAxis": [{"properties": {"show": lit(False), "gridlineShow": lit(False)}}],
                         "valueAxis": [{"properties": {"show": lit(False), "gridlineShow": lit(False)}}],
                         "bubbles": [{"properties": {"bubbleSize": lit(-35)}}]},
                titulo="El mapa de los circuitos (el tamaño es la cantidad de votos)")
    tabla(pg, 932, 156, 658, 470, [(CI("circuito"), "Circuito"), (CI("cabecera"), "Municipio"), (Me("% peronismo circuitos"), "Peronismo 2025"),
                                   (Me("% LLA+PRO circuitos"), "LLA+PRO 2025"), (CI("margen_2025"), "Margen"), (CI("cambio_peronismo"), "Cambio vs. 2023"),
                                   (Me("Votos circuitos"), "Votos"), (CI("nbi"), "NBI %")],
          "Circuitos", sort=[(Me("Votos circuitos"), "Descending")], size=9)
    kp = [(Me("Circuitos con datos"), "Circuitos", INK), (Me("% peronismo circuitos"), "Peronismo", PER), (Me("% LLA+PRO circuitos"), "LLA + PRO", DER)]
    for i, (m, et, c) in enumerate(kp):
        pg.tarjeta(932 + i * 222, 636, 214, 86, m, et, size=20, fg=c)
    pg.texto(932, 732, 658, 158, [[("Cómo usarlo", {"size": 10, "bold": True, "color": VIO})],
                                  [("Los puntos están ubicados por su latitud y longitud, así que forman el mapa de la Provincia. "
                                    "Clic en un punto: la tabla y las tarjetas muestran ese circuito (Ctrl+clic para varios). "
                                    "Al elegir una zona o un municipio, el gráfico se acerca solo.", {"size": 9, "color": MUTED})]], fondo="#FFFFFF", borde=True)
    pags.append(pg)

    # =================================================================== CORRIMIENTOS
    pg = p.pagina("corrimientos", "Corrimientos", "Cuántos puntos ganó o perdió el peronismo en cada municipio entre dos elecciones · elegí la elección y la elección base")
    solo_metrica(pg, [12])
    p.seg_eleccion(pg, X0, 88, 400)
    pg.segmentador(X0 + 410, 88, 400, 58, C("eleccion_base", "Elección base"), "Comparar con (elección base)", sync="base", unico=True, presel="Gobernador 2023")
    p.seg_seccion(pg, X0 + 820, 88, 270)
    p.seg_zona(pg, X0 + 1100, 88, 268)
    kp = [(Me("Corrimiento peronismo (pts)"), "Corrimiento del peronismo (pts)", PER), (Me("Corrimiento LLA/PRO (pts)"), "Corrimiento de LLA + PRO (pts)", DER),
          (Me("Municipios donde creció el peronismo"), "Municipios donde creció el peronismo", VERDE),
          (Me("Municipios donde cayó el peronismo"), "Municipios donde cayó", ROJO)]
    for i, (m, et, c) in enumerate(kp):
        pg.tarjeta(X0 + i * 345, 156, 335, 86, m, et, size=22, fg=c)
    mapa_grande(pg, "SVG mapa completo", "Título del mapa")
    p.tooltip(barras(pg, 1092, 252, 498, 400, DM("municipio"), Me("Corrimiento peronismo (pts)"), "Ranking: corrimiento del peronismo (pts)",
                     fx="Color corrimiento", nombre_val="Corrimiento", size_et=8))
    sc = pg.add("scatterChart", 1092, 662, 498, 228,
                query={"Category": [proj(DM("municipio"))], "X": [proj(Me("Hogares con NBI %"), "NBI")], "Y": [proj(Me("Corrimiento peronismo (pts)"), "Corrimiento")],
                       "Size": [proj(Me("Electores"), "Electores")]},
                objects={"dataPoint": [{"properties": {"fill": color(PER)}}], "categoryAxis": [{"properties": {"showAxisTitle": lit(True), "fontSize": lit(8)}}],
                         "valueAxis": [{"properties": {"showAxisTitle": lit(True), "fontSize": lit(8)}}]},
                titulo="¿Dónde se movió? Pobreza (NBI) y corrimiento")
    p.tooltip(sc)
    pags.append(pg)

    # =================================================================== DÓNDE SE DECIDE
    pg = p.pagina("decide", "Dónde se decide", "Municipios bisagra: muchos electores y margen chico entre el peronismo y LLA + PRO")
    p.seg_eleccion(pg, X0, 88, 520)
    p.seg_seccion(pg, X0 + 530, 88, 420)
    p.seg_zona(pg, X0 + 960, 88, 408)
    kp = [(Me("Municipios bisagra"), "Municipios bisagra (margen menor a 5 pts)", VIO), (Me("Electores en bisagras"), "Electores en esos municipios", INK),
          (Me("% del padrón en bisagras"), "del padrón provincial", INK), (Me("Votos para dar vuelta"), "Votos que tendrían que cambiar para dar vuelta la Provincia", INK)]
    for i, (m, et, c) in enumerate(kp):
        pg.tarjeta(X0 + i * 345, 156, 335, 86, m, et, size=22, fg=c)
    sc = pg.add("scatterChart", X0, 252, 760, 638,
                query={"Category": [proj(DM("municipio"))], "Series": [proj(DM("zona"))], "X": [proj(Me("Margen P-D (pts)"), "Margen (pts)")],
                       "Y": [proj(Me("Electores"), "Electores")], "Size": [proj(Me("Tamaño por electores"), "Tamaño: electores")]},
                objects={"dataPoint": p.colores_serie("dim_municipio", "zona", {"Conurbano": PER, "Interior": ORO}),
                         "legend": [{"properties": {"show": lit(True), "position": lit("Top")}}],
                         "categoryAxis": [{"properties": {"showAxisTitle": lit(True), "fontSize": lit(9)}}],
                         "valueAxis": [{"properties": {"showAxisTitle": lit(True), "fontSize": lit(9)}}]},
                titulo="Arriba y cerca del centro (margen 0) están los municipios que deciden: muchos votos y margen chico")
    p.tooltip(sc)
    p.tooltip(tabla(pg, 992, 252, 598, 638, [(DM("municipio"), "Municipio"), (Me("Ganador"), "Ganó"), (Me("Margen P-D (pts)"), "Margen (pts)"),
                                              (Me("Electores"), "Electores"), (Me("Votos para dar vuelta"), "Votos para dar vuelta")],
                    "Los más parejos primero", sort=[(Me("Margen absoluto (pts)"), "Ascending")], size=10, fx=[(Me("Margen P-D (pts)"), "Color diferencia")]))
    pags.append(pg)

    # =================================================================== INTENDENTES 2027
    pg = p.pagina("intendentes", "Intendentes 2027", "Quién gobierna cada municipio y si puede ir por la reelección en 2027 · intendentes en ejercicio (oct. 2026)")
    m11, m13 = [m[1] for m in p.METRICAS if m[0] == 11][0], [m[1] for m in p.METRICAS if m[0] == 13][0]
    s = pg.segmentador(X0, 88, 520, 58, C("metrica_mapa", "metrica"), "Mostrar en el mapa", unico=True, presel=m11)
    s["filterConfig"] = {"filters": [filtro_es("metrica_mapa", "metrica", [m11, m13], "flt_metricas_int")]}
    p.seg_seccion(pg, X0 + 530, 88, 420)
    p.seg_zona(pg, X0 + 960, 88, 408)
    kp = [(Me("Intendentes de Fuerza Patria"), "Intendentes de Fuerza Patria", PER), (Me("Pueden reelegir"), "Pueden ir por la reelección", VERDE),
          (Me("No pueden reelegir"), "No pueden: segundo mandato", ORO), (Me("Interinos"), "Intendentes interinos", MUTED)]
    for i, (m, et, c) in enumerate(kp):
        pg.tarjeta(X0 + i * 345, 156, 335, 86, m, et, size=22, fg=c)
    mapa_grande(pg, "SVG mapa completo", "Título del mapa")
    fz = DM("fuerza_intendente")
    v = pg.add("clusteredBarChart", 1092, 252, 498, 230, query={"Category": [proj(fz)], "Y": [proj(Me("Municipios"), "Municipios")]},
               objects={"dataPoint": p.colores_serie("dim_municipio", "fuerza_intendente", dict(b.FUERZAS)),
                        "labels": [{"properties": {"show": lit(True), "fontSize": lit(9)}}],
                        "valueAxis": [{"properties": {"show": lit(False)}}], "categoryAxis": [{"properties": {"fontSize": lit(9), "showAxisTitle": lit(False)}}]},
               titulo="Municipios por fuerza del intendente", sort=[(Me("Municipios"), "Descending")])
    tabla(pg, 1092, 492, 498, 398, [(DM("foto_url"), "Foto"), (DM("municipio"), "Municipio"), (DM("intendente"), "Intendente"), (fz, "Fuerza"),
                                     (DM("reeleccion_2027"), "2027"), (DM("wikipedia_url"), "Wiki")], "Intendentes", sort=[(DM("municipio"), "Ascending")], size=9, img=40, links=True,
          fx=[(DM("reeleccion_2027"), "Color reelección")])
    pags.append(pg)

    # =================================================================== PRONÓSTICO 2027
    pg = p.pagina("pronostico", "Pronóstico 2027", "Motor ATLAS: 1.000 simulaciones por escenario a partir de los resultados 2023-2025 · elegí el escenario")
    solo_metrica(pg, [7])
    pg.segmentador(X0, 88, 520, 58, C("fact_motor_2027", "escenario"), "Escenario del motor", sync="motor", unico=True, presel="Octubre 2025 se repite")
    p.seg_seccion(pg, X0 + 530, 88, 420)
    p.seg_zona(pg, X0 + 960, 88, 408)
    kp = [(Me("Pronóstico P(gana)"), "Probabilidad de que gane el peronismo (escenario base)", PER), (Me("Pronóstico margen"), "Margen esperado (pts)", INK),
          (Me("Municipios peronistas esperados"), "Municipios peronistas esperados (escenario elegido)", PER), (Me("Municipios en disputa"), "Municipios en disputa (20-80 %)", VIO)]
    for i, (m, et, c) in enumerate(kp):
        pg.tarjeta(X0 + i * 345, 156, 335, 86, m, et, size=22, fg=c)
    mapa_grande(pg, "SVG mapa completo", "Título del mapa")
    barras(pg, 1092, 252, 498, 330, C("escenarios_2027", "escenario"), Me("Margen escenario"), "Margen del peronismo por escenario (pts, mediana)",
           fx="Color escenario", nombre_val="Margen", size_et=8)
    p.tooltip(tabla(pg, 1092, 592, 498, 298, [(DM("municipio"), "Municipio"), (Me("P(peronismo) 2027 base"), "P(peronismo)"),
                                               (Me("% peronismo esperado 2027"), "% esperado"), (C("fact_motor_2027", "rango_p"), "Categoría")],
                    "Municipio por municipio", sort=[(Me("P(peronismo) 2027 base"), "Descending")], size=9))
    pags.append(pg)

    # =================================================================== SIMULADOR
    pg = p.pagina("simulador", "Simulador", "Mové los supuestos y mirá cómo cambia el resultado · parte de la elección elegida, municipio por municipio")
    p.seg_eleccion(pg, X0, 88, 330)
    pg.segmentador(X0 + 340, 88, 330, 58, C("sim_swing", "Corrimiento uniforme (pts)"), "Corrimiento hacia el peronismo (pts)", unico=True, presel=0.0)
    pg.segmentador(X0 + 680, 88, 340, 58, C("sim_terceros", "Terceros que van al peronismo (%)"), "Voto de terceros que va al peronismo (%)", unico=True, presel=0.0)
    pg.segmentador(X0 + 1030, 88, 338, 58, C("sim_division", "LLA + PRO que se va a otra lista (%)"), "LLA + PRO que se va a otra lista (%)", unico=True, presel=0.0)
    p.caja(pg, X0, 156, 1368, 150, "Resultado simulado (dos fuerzas principales)")
    pg.imagen(X0 + 30, 184, 1308, 116, "SVG barra simulación")
    kp = [(Me("Sim % peronismo"), "Peronismo simulado", PER), (Me("Sim % LLA+PRO"), "LLA + PRO simulado", DER), (Me("Sim margen (pts)"), "Margen simulado (pts)", INK),
          (Me("Sim municipios peronistas"), "Municipios que gana el peronismo", PER), (Me("Sim municipios que cambian"), "Municipios que cambian de manos", VIO)]
    for i, (m, et, c) in enumerate(kp):
        pg.tarjeta(X0 + i * 276, 316, 266, 86, m, et, size=22, fg=c)
    barras(pg, X0, 412, 680, 478, DM("seccion"), Me("Sim margen (pts)"), "Margen simulado por sección (pts)", fx="Color sim",
           sort=[(DM("seccion"), "Ascending")], nombre_val="Margen")
    p.tooltip(tabla(pg, 912, 412, 678, 478, [(DM("municipio"), "Municipio"), (Me("Margen P-D (pts)"), "Margen real"), (Me("Sim margen (pts)"), "Margen simulado"),
                                              (Me("Sim ganador"), "Ganaría"), (Me("Electores"), "Electores")],
                    "Municipio por municipio", sort=[(Me("Electores"), "Descending")], size=9.5, fx=[(Me("Sim margen (pts)"), "Color sim")]))
    pags.append(pg)

    # =================================================================== METODOLOGÍA
    pg = p.pagina("metodologia", "Metodología", "Fuentes, definiciones y límites de cada número del tablero")
    txt = [
        ("Fuentes", ["Resultados: Dirección Nacional Electoral (DINE, por mesa) y Junta Electoral de la Provincia de Buenos Aires (escrutinios definitivos), 2007-2025.",
                     "Censo 2022 (INDEC) por radio censal, llevado a municipios y circuitos. Barrios populares: RENABAP.",
                     "Intendentes en ejercicio: Wikipedia y fuentes periodísticas, actualizado a octubre de 2026. Contornos: IGN e INDEC."]),
        ("Cómo se agrupan las fuerzas", ["Peronismo: Frente para la Victoria, Unidad Ciudadana, Frente de Todos, Unión por la Patria, Fuerza Patria y antecesores.",
                                         "LLA + PRO: La Libertad Avanza, PRO / Juntos por el Cambio y la alianza de 2025. Se suman en los porcentajes «LLA + PRO».",
                                         "Los porcentajes son sobre votos positivos (sin blancos ni nulos)."]),
        ("Pronóstico 2027", ["Motor ATLAS: 1.000 simulaciones por escenario, con incertidumbre por municipio a partir de las elecciones 2023-2025.",
                             "«Probabilidad de que gane el peronismo»: parte de las simulaciones en que el peronismo saca más votos que LLA + PRO.",
                             "Es un ejercicio de escenarios, no una encuesta: no incorpora candidatos ni campañas."]),
        ("Simulador", ["Parte de la elección elegida y aplica, municipio por municipio: un corrimiento uniforme (puntos de los votos positivos que pasan de LLA + PRO al peronismo), "
                       "la parte del voto de terceras fuerzas que va al peronismo y la parte de LLA + PRO que se va a otra lista."]),
        ("Reelección de intendentes 2027", ["Según la ley 14.836 (modificada por la ley 15.315), los intendentes pueden tener una sola reelección consecutiva.",
                                            "«No puede»: intendentes reelectos en 2023. «Interino»: quien ejerce el cargo sin haber sido electo. "
                                            "Es una clasificación aproximada: casos con interpretaciones judiciales pueden diferir."]),
        ("Límites", ["Los circuitos sin resultados publicados por circuito en 2025 aparecen en gris en el mapa fino.",
                     "Las secciones con menos superficie (1.ª, 3.ª y 8.ª) llevan su rótulo afuera del mapa, unido con una línea."]),
    ]
    col_x = [X0, X0 + 694]
    for i, (tit, items) in enumerate(txt):
        x, y = col_x[i % 2], 96 + (i // 2) * 268
        pg.texto(x, y, 674, 258, [[(tit, {"size": 12, "bold": True, "color": VIO})]] + [[("▸ " + it, {"size": 9.5})] for it in items], fondo="#FFFFFF", borde=True)
    fuentes = [("DINE  ↗", "https://www.argentina.gob.ar/dine"), ("Junta Electoral PBA  ↗", "https://www.juntaelectoral.gba.gov.ar"),
               ("Censo 2022 · INDEC  ↗", "https://censo.gob.ar"), ("RENABAP  ↗", "https://www.argentina.gob.ar/habitat/renabap")]
    for i, (txt_, url) in enumerate(fuentes):
        pg.boton(X0 + 14 + i * 162, 316, 154, 30, txt_, tipo="WebUrl", web=url, fondo="#FFFFFF", fg=VIO, size=9, hover=GRIS, borde="#E4DFEE", alin="center")
    pags.append(pg)
    return pags
