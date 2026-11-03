"""
pbi_atlas.py · Piezas para escribir un proyecto de Power BI (PBIP) desde Python.

Copia de la biblioteca del tablero ATLAS CABA 2027 (10_PRODUCTOS/powerbi/scripts/pbi.py, a su vez
derivada del tablero del balotaje de Brasil): el formato de botones, segmentadores, tarjetas e
imágenes que abre bien Power BI Desktop 2.152 (marzo 2026). Se copia, no se importa, para no tocar
el proyecto de la Ciudad.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

# paleta ATLAS
INK, VIO, MUTED, BG, LINEA, ORO = "#1D1631", "#5B3F99", "#6B6480", "#F4F1F9", "#E4DFEE", "#E0A526"
W, H = 1600, 900
X0 = 222  # comienzo del área de contenido (a la derecha de la barra de navegación)
V_VISUAL, V_PAGE, V_REPORT = "2.4.0", "2.0.0", "3.0.0"
SCH = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"
TIPOS_M = {"string": "type text", "int64": "Int64.Type", "double": "type number", "dateTime": "type date"}


# ===========================================================================
# MODELO (TMDL)
# ===========================================================================

def q(nombre: str) -> str:
    """Nombre TMDL o DAX de tabla, entre comillas simples si hace falta."""
    if nombre.replace("_", "").isalnum() and nombre.isascii() and not nombre[0].isdigit():
        return nombre
    return "'" + nombre.replace("'", "''") + "'"


def medida(m) -> list[str]:
    nombre, expr, fmt, carpeta = m[:4]
    extra = m[4] if len(m) > 4 else {}
    lineas = [ln.rstrip() for ln in expr.strip("\n").split("\n") if ln.strip()]
    ind = min(len(ln) - len(ln.lstrip()) for ln in lineas)
    # TMDL no admite una línea menos sangrada que la primera de la expresión: con fragmentos DAX
    # insertados (capas de mapas, flechas) esas sangrías se mezclan, así que se conserva la relativa
    # sólo si ninguna línea queda por debajo de la primera; si no, todas van al mismo nivel
    rel = [len(ln) - len(ln.lstrip()) - ind for ln in lineas]
    if any(r < rel[0] for r in rel):
        cuerpo = ["\t\t\t" + ln.lstrip() for ln in lineas]
    else:
        cuerpo = ["\t\t\t" + ln[ind:] for ln in lineas]
    out = [f"\tmeasure {q(nombre)} ="] + cuerpo
    if fmt:
        out.append(f"\t\tformatString: {fmt}")
    if carpeta:
        out.append(f"\t\tdisplayFolder: {carpeta}")
    for k, v in extra.items():
        sep = " = " if k == "formatStringDefinition" else ": "  # el formato dinámico es una expresión DAX
        out.append(f"\t\t{k}{sep}{v}")
    out.append("")
    return out


def tipo_pbi(serie: pd.Series) -> str:
    if pd.api.types.is_integer_dtype(serie):
        return "int64"
    if pd.api.types.is_float_dtype(serie):
        return "double"
    if pd.api.types.is_bool_dtype(serie):
        return "string"
    return "string"


def tabla_csv(nombre, carpeta: Path, archivo, formatos=None, ocultas=(), extra_col=None, sumar=(), fechas=(),
              oculta_tabla=False, solo=None) -> str:
    """Tabla importada de un CSV; tipos inferidos de los datos.
    formatos: {col: formatString}; extra_col: {col: {propiedad: valor}}; sumar: columnas con summarizeBy sum."""
    formatos, extra_col = formatos or {}, extra_col or {}
    df = pd.read_csv(carpeta / archivo, nrows=5000, low_memory=False)
    if solo:
        df = df[solo]
    cols = []
    for c in df.columns:
        t = "dateTime" if c in fechas else tipo_pbi(df[c])
        cols.append((c, t))
    out = [f"table {q(nombre)}"] + (["\tisHidden"] if oculta_tabla else []) + [""]
    for c, t in cols:
        out += [f"\tcolumn {q(c)}", f"\t\tdataType: {t}"]
        if c in formatos:
            out.append(f"\t\tformatString: {formatos[c]}")
        elif t == "int64":
            out.append("\t\tformatString: 0")
        out.append(f"\t\tsummarizeBy: {'sum' if c in sumar else 'none'}")
        out.append(f"\t\tsourceColumn: {c}")
        if c in ocultas:
            out.append("\t\tisHidden")
        for k, v in extra_col.get(c, {}).items():
            out.append(f"\t\t{k}: {v}" if v != "" else f"\t\t{k}")
        out.append("")
    tipos = ", ".join(f'{{"{c}", {TIPOS_M[t]}}}' for c, t in cols)
    sel = ""
    if solo:
        sel = "\t\t\t\t    Solo = Table.SelectColumns(Encabezados, {" + ", ".join(f'"{c}"' for c in solo) + "}),\n"
    prev = "Solo" if solo else "Encabezados"
    out += [f"\tpartition {q(nombre)} = m", "\t\tmode: import", "\t\tsource =", "\t\t\t\tlet",
            f'\t\t\t\t    Origen = Csv.Document(File.Contents(CarpetaDatos & "{archivo}"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),',
            "\t\t\t\t    Encabezados = Table.PromoteHeaders(Origen, [PromoteAllScalars = true]),"]
    if sel:
        out.append(sel.rstrip("\n"))
    out += [f'\t\t\t\t    Tipos = Table.TransformColumnTypes({prev}, {{{tipos}}}, "en-US")',
            "\t\t\t\tin", "\t\t\t\t    Tipos", ""]
    return "\n".join(out) + "\n"


def tabla_calculada(nombre, dax, columnas, medidas=(), oculta=False) -> str:
    """columnas: [(nombre, tipo, formato, {extra}, sourceColumn|None)]"""
    out = [f"table {q(nombre)}"] + (["\tisHidden"] if oculta else []) + [""]
    for m in medidas:
        out += medida(m)
    for col in columnas:
        c, t, fmt, extra = col[:4]
        src = col[4] if len(col) > 4 and col[4] else f"[{c}]"
        out += [f"\tcolumn {q(c)}", f"\t\tdataType: {t}"]
        if fmt:
            out.append(f"\t\tformatString: {fmt}")
        out += ["\t\tsummarizeBy: none", f"\t\tsourceColumn: {src}"]
        for k, v in (extra or {}).items():
            if v is True:
                out.append(f"\t\t{k}")
            elif isinstance(v, list):
                out.append(f"\t\t{k}")
                out += [f"\t\t\t{x}" for x in v]
            else:
                out.append(f"\t\t{k}: {v}")
        out.append("")
    out += [f"\tpartition {q(nombre)} = calculated", "\t\tmode: import", "\t\tsource =",
            *["\t\t\t\t" + ln for ln in dax.strip().split("\n")], ""]
    return "\n".join(out) + "\n"


def parametro(nombre, col, ini, fin, paso, fmt) -> str:
    return tabla_calculada(nombre, f"GENERATESERIES({ini}, {fin}, {paso})", [(col, "double", fmt, {}, "[Value]")])


def parametro_campo(nombre, filas: list[tuple[str, str]]) -> str:
    """Parámetro de campo: el usuario elige qué medida muestra el visual. filas: [(etiqueta, medida)]"""
    val = ",\n".join(f'    ("{e}", NAMEOF(Medidas[{m}]), {i})' for i, (e, m) in enumerate(filas))
    cf, co = f"{nombre} campos", f"{nombre} orden"
    out = [f"table {q(nombre)}", "",
           f"\tcolumn {q(nombre)}", "\t\tdataType: string", "\t\tsummarizeBy: none", "\t\tsourceColumn: [Value1]",
           f"\t\tsortByColumn: {q(co)}", "", "\t\trelatedColumnDetails", f"\t\t\tgroupByColumn: {q(cf)}", "",
           f"\tcolumn {q(cf)}", "\t\tdataType: string", "\t\tisHidden", "\t\tsummarizeBy: none", "\t\tsourceColumn: [Value2]",
           f"\t\tsortByColumn: {q(co)}", "", "\t\textendedProperty ParameterMetadata =",
           "\t\t\t\t{", '\t\t\t\t  "version": 3,', '\t\t\t\t  "kind": 2', "\t\t\t\t}", "",
           f"\tcolumn {q(co)}", "\t\tdataType: int64", "\t\tisHidden", "\t\tformatString: 0", "\t\tsummarizeBy: sum",
           "\t\tsourceColumn: [Value3]", "",
           f"\tpartition {q(nombre)} = calculated", "\t\tmode: import", "\t\tsource =", "\t\t\t\t{"]
    out += ["\t\t\t\t" + ln for ln in val.split("\n")]
    out += ["\t\t\t\t}", ""]
    return "\n".join(out) + "\n"


def relaciones(pares) -> str:
    out = []
    for i, (desde, hasta) in enumerate(pares):
        (t1, c1), (t2, c2) = desde, hasta
        out += [f"relationship rel_{i:02d}", f"\tfromColumn: {q(t1)}.{q(c1)}", f"\ttoColumn: {q(t2)}.{q(c2)}", ""]
    return "\n".join(out)


def svg_uri(expr: str) -> str:
    return f'"data:image/svg+xml;utf8," & SUBSTITUTE(SUBSTITUTE({expr}, "%", "%25"), "#", "%23")'


# ===========================================================================
# INFORME (PBIR)
# ===========================================================================

def lit(v):
    if isinstance(v, bool):
        s = "true" if v else "false"
    elif isinstance(v, (int, float)):
        s = f"{float(v):g}D"
    else:
        s = "'" + str(v).replace("'", "''") + "'"
    return {"expr": {"Literal": {"Value": s}}}


def color(c):
    return {"solid": {"color": lit(c)}}


def C(t, c):
    return {"Column": {"Expression": {"SourceRef": {"Entity": t}}, "Property": c}}


def Me(m, t="Medidas"):
    return {"Measure": {"Expression": {"SourceRef": {"Entity": t}}, "Property": m}}


def color_fx(m):
    return {"solid": {"color": {"expr": Me(m)}}}


def qref(campo):
    k = "Column" if "Column" in campo else "Measure"
    return f'{campo[k]["Expression"]["SourceRef"]["Entity"]}.{campo[k]["Property"]}'


def proj(campo, nombre=None):
    k = "Column" if "Column" in campo else "Measure"
    p = {"field": campo, "queryRef": qref(campo), "nativeQueryRef": (nombre or "").strip() or campo[k]["Property"]}
    if nombre:
        p["displayName"] = nombre
    return p


TODOS = {"data": [{"dataViewWildcard": {"matchingOption": 1}}]}
SIN_CAJA = {"background": [{"properties": {"show": lit(False)}}], "border": [{"properties": {"show": lit(False)}}],
            "dropShadow": [{"properties": {"show": lit(False)}}], "title": [{"properties": {"show": lit(False)}}],
            "visualHeader": [{"properties": {"show": lit(False)}}]}


class Pagina:
    def __init__(self, nombre, titulo, subtitulo="", tipo=None, w=W, h=H, oculta=False, cabecera=True, corte=""):
        self.nombre, self.titulo, self.tipo, self.w, self.h = nombre, titulo, tipo, w, h
        self.visuales, self.n, self.oculta = [], 0, oculta
        self.binding, self.filtros, self.interacciones = None, [], []
        if cabecera:
            self.encabezado(titulo, subtitulo, corte)

    def add(self, tipo, x, y, w, h, query=None, objects=None, vco=None, sort=None, titulo=None, extra=None, filtros=None):
        self.n += 1
        nombre = f"{self.nombre[:18]}_{self.n:02d}_{tipo[:12]}"
        v = {"visualType": tipo}
        if query:
            v["query"] = {"queryState": {r: {"projections": ps} for r, ps in query.items()}}
            # un parámetro de campo se declara aparte, si no Power BI lo toma como columna de texto suelta
            for r, ps in query.items():
                for i, pr in enumerate(ps):
                    if pr.pop("_parametro", False):
                        v["query"]["queryState"][r]["fieldParameters"] = [{"parameterExpr": pr["field"], "index": i, "length": 1}]
            if sort:
                v["query"]["sortDefinition"] = {"sort": [{"field": f, "direction": d} for f, d in sort], "isDefaultSort": False}
        if objects:
            v["objects"] = objects
        vco = dict(vco or {})
        if titulo is not None:
            if isinstance(titulo, dict):  # título dinámico (medida)
                vco.setdefault("title", [{"properties": {"show": lit(True), "text": {"expr": titulo}}}])
            else:
                vco.setdefault("title", [{"properties": {"show": lit(bool(titulo)), **({"text": lit(titulo)} if titulo else {})}}])
        if vco:
            v["visualContainerObjects"] = vco
        if extra:
            v.update(extra)
        vis = {"$schema": f"{SCH}/visualContainer/{V_VISUAL}/schema.json", "name": nombre,
               "position": {"x": x, "y": y, "z": self.n * 100, "width": w, "height": h, "tabOrder": self.n * 100},
               "visual": v}
        if filtros:
            vis["filterConfig"] = {"filters": filtros}
        self.visuales.append(vis)
        return vis

    def texto(self, x, y, w, h, parrafos, fondo=None, borde=False):
        pars = []
        for p in parrafos:
            if isinstance(p, str):
                p = [(p, {})]
            runs = []
            for txt, est in p:
                st = {"fontFamily": est.get("font", "Segoe UI"), "fontSize": f"{est.get('size', 11)}pt", "color": est.get("color", INK)}
                if est.get("bold"):
                    st["fontWeight"] = "bold"
                r = {"value": txt, "textStyle": st}
                if est.get("url"):
                    r["url"] = est["url"]
                runs.append(r)
            par = {"textRuns": runs}
            if p and p[0][1].get("align"):
                par["horizontalTextAlignment"] = p[0][1]["align"]
            pars.append(par)
        vco = {"background": [{"properties": {"show": lit(bool(fondo)), **({"color": color(fondo), "transparency": lit(0)} if fondo else {})}}],
               "border": [{"properties": {"show": lit(borde)}}], "dropShadow": [{"properties": {"show": lit(False)}}],
               "visualHeader": [{"properties": {"show": lit(False)}}]}
        return self.add("textbox", x, y, w, h, objects={"general": [{"properties": {"paragraphs": pars}}]}, vco=vco)

    def boton(self, x, y, w, h, texto, destino=None, tipo="PageNavigation", fondo=VIO, fg="#FFFFFF", size=11,
              hover=None, alin="left", web=None, web_fx=None, borde=None, transp=0, transp_hover=0, texto_fx=None):
        link = {"show": lit(True), "type": lit(tipo)}
        if tipo == "PageNavigation":
            link["navigationSection"] = lit(destino)
        elif tipo == "Drillthrough":
            link["drillthroughSection"] = lit(destino)
        elif tipo == "WebUrl":
            link["webUrl"] = {"expr": Me(web_fx)} if web_fx else lit(web)
        txt = {"expr": Me(texto_fx)} if texto_fx else lit(texto)
        objs = {
            "icon": [{"properties": {"shapeType": lit("blank")}, "selector": {"id": "default"}}, {"properties": {"show": lit(False)}}],
            "text": [{"properties": {"show": lit(True)}},
                     {"properties": {"text": txt, "fontColor": color(fg), "fontSize": lit(size), "fontFamily": lit("Segoe UI Semibold"),
                                     "horizontalAlignment": lit(alin), "leftMargin": lit(14)}, "selector": {"id": "default"}}],
            "fill": [{"properties": {"show": lit(True)}},
                     {"properties": {"fillColor": color(fondo), "transparency": lit(transp)}, "selector": {"id": "default"}},
                     {"properties": {"fillColor": color(hover or ORO), "transparency": lit(transp_hover)}, "selector": {"id": "hover"}}],
            "outline": [{"properties": {"show": lit(bool(borde)), **({"lineColor": color(borde), "weight": lit(1)} if borde else {})}}],
            "shape": [{"properties": {"tileShape": lit("rectangleRounded"), "roundEdge": lit(8)}}],
        }
        vco = {"visualLink": [{"properties": link}], "visualHeader": [{"properties": {"show": lit(False)}}],
               "dropShadow": [{"properties": {"show": lit(False)}}], "background": [{"properties": {"show": lit(False)}}],
               "border": [{"properties": {"show": lit(False)}}]}
        return self.add("actionButton", x, y, w, h, objects=objs, vco=vco)

    def tarjeta(self, x, y, w, h, campo, etiqueta, fx=None, size=24, fg=INK):
        objs = {"labels": [{"properties": {"color": color_fx(fx) if fx else color(fg), "fontSize": lit(size),
                                           "fontFamily": lit("Segoe UI Semibold"), "labelDisplayUnits": lit(1)}}],
                "categoryLabels": [{"properties": {"show": lit(True), "color": color(MUTED), "fontSize": lit(10)}}],
                "wordWrap": [{"properties": {"show": lit(True)}}]}
        return self.add("card", x, y, w, h, query={"Values": [proj(campo, etiqueta)]}, objects=objs, titulo="")

    def rotulo(self, x, y, w, h, medida, size=10, fg=VIO, font="Segoe UI Semibold", fondo=None):
        vco = dict(SIN_CAJA)
        if fondo:
            vco["background"] = [{"properties": {"show": lit(True), "color": color(fondo), "transparency": lit(0)}}]
        return self.add("card", x, y, w, h, query={"Values": [proj(Me(medida), " ")]},
                        objects={"labels": [{"properties": {"fontSize": lit(size), "color": color(fg), "fontFamily": lit(font)}}],
                                 "categoryLabels": [{"properties": {"show": lit(False)}}], "wordWrap": [{"properties": {"show": lit(True)}}]},
                        vco=vco)

    def imagen(self, x, y, w, h, medida=None, url=None, titulo=None, escala="Fit"):
        src = {"expr": Me(medida)} if medida else lit(url)
        objs = {"image": [{"properties": {"sourceType": lit("imageUrl"), "sourceUrl": src}}],
                "imageScaling": [{"properties": {"imageScalingType": lit(escala)}}]}
        return self.add("image", x, y, w, h, objects=objs, titulo=titulo, vco={"visualHeader": [{"properties": {"show": lit(False)}}]})

    def segmentador(self, x, y, w, h, campo, titulo, modo="Dropdown", sync=None, unico=False, horizontal=False, presel=None,
                    buscar=False):
        objs = {"data": [{"properties": {"mode": lit(modo)}}],
                "header": [{"properties": {"show": lit(True), "text": lit(titulo), "fontColor": color(INK), "textSize": lit(10)}}],
                "items": [{"properties": {"textSize": lit(10), "fontColor": color(INK)}}]}
        if unico:
            objs["selection"] = [{"properties": {"singleSelect": lit(True), "strictSingleSelect": lit(presel is not None)}}]
        else:
            objs["selection"] = [{"properties": {"selectAllCheckboxEnabled": lit(True)}}]
        if horizontal:
            objs["general"] = [{"properties": {"orientation": lit(1)}}]
        if presel is not None:
            ent, prop = campo["Column"]["Expression"]["SourceRef"]["Entity"], campo["Column"]["Property"]
            objs.setdefault("general", [{"properties": {}}])[0]["properties"]["filter"] = {"filter": {
                "Version": 2, "From": [{"Name": "t", "Entity": ent, "Type": 0}],
                "Where": [{"Condition": {"In": {"Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "t"}}, "Property": prop}}],
                                                "Values": [[lit(presel)["expr"]]]}}}]}}
        if buscar:  # caja de búsqueda dentro del segmentador
            objs.setdefault("general", [{"properties": {}}])[0]["properties"]["selfFilterEnabled"] = lit(True)
        extra = {"syncGroup": {"groupName": sync, "fieldChanges": True, "filterChanges": True}} if sync else None
        return self.add("slicer", x, y, w, h, query={"Values": [proj(campo)]}, objects=objs, titulo="", extra=extra)

    def encabezado(self, titulo, sub, corte):
        self.texto(X0, 8, 1000, 50, [[(titulo, {"size": 22, "bold": True, "font": "Segoe UI Semibold"})]])  # 50 de alto: con 44 aparecía una barra de desplazamiento
        if sub:
            self.texto(X0, 52, 1180, 30, [[(sub, {"size": 10, "color": MUTED})]])
        if corte:
            self.rotulo(1260, 18, 320, 44, corte, size=8.5, fg=MUTED, font="Segoe UI")

    def json(self):
        p = {"$schema": f"{SCH}/page/{V_PAGE}/schema.json", "name": self.nombre, "displayName": self.titulo,
             "displayOption": "FitToPage", "height": self.h, "width": self.w}
        if self.tipo:
            p["type"] = self.tipo
        if self.binding:
            p["pageBinding"] = self.binding
        if self.filtros:
            p["filterConfig"] = {"filters": self.filtros}
        if self.oculta:
            p["visibility"] = "HiddenInViewMode"
        if self.interacciones:
            p["visualInteractions"] = [{"source": a, "target": b, "type": "NoFilter"} for a, b in self.interacciones]
        return p

    def sin_filtro(self, campo, destino):
        """El segmentador de `campo` deja de filtrar el visual `destino`."""
        for v in self.visuales:
            if v["visual"]["visualType"] == "slicer" and campo in json.dumps(v["visual"].get("query", {}), ensure_ascii=False):
                self.interacciones.append((v["name"], destino["name"]))


def fx_valores(campo_fmt, medida_color, prop="backColor"):
    return {"properties": {prop: color_fx(medida_color)}, "selector": {**TODOS, "metadata": qref(campo_fmt)}}


def tabla(pg, x, y, w, h, campos, titulo, fx=(), fx_texto=(), sort=None, size=10, img=None, filtros=None, links=False):
    objs = {"columnHeaders": [{"properties": {"fontColor": color("#FFFFFF"), "backColor": color(INK), "fontSize": lit(size),
                                              "wordWrap": lit(True)}}],
            "values": [{"properties": {"fontSize": lit(size), "backColorPrimary": color("#FFFFFF"),
                                       "backColorSecondary": color("#F8F6FC"), **({"urlIcon": lit(True)} if links else {})}}]
            + [fx_valores(c, m) for c, m in fx] + [fx_valores(c, m, "fontColor") for c, m in fx_texto],
            "grid": [{"properties": {"gridHorizontalColor": color(LINEA), "rowPadding": lit(3),
                                     **({"imageHeight": lit(img)} if img else {})}}],
            "total": [{"properties": {"totals": lit(False)}}]}
    return pg.add("tableEx", x, y, w, h, query={"Values": [proj(c, n) for c, n in campos]}, objects=objs, titulo=titulo,
                  sort=sort, filtros=filtros)


def barras(pg, x, y, w, h, cat, val, titulo, fx=None, tipo="clusteredBarChart", sort=None, etiquetas=True, nombre_val=None,
           ejes=True, size_et=9, rango=None, tooltip=None, serie=None):
    va = {"show": lit(ejes), "gridlineShow": lit(False), "showAxisTitle": lit(False)}
    if rango:
        va.update({"start": lit(rango[0]), "end": lit(rango[1])})
    objs = {"labels": [{"properties": {"show": lit(etiquetas), "fontSize": lit(size_et), "color": color(INK)}}],
            "valueAxis": [{"properties": va}],
            "categoryAxis": [{"properties": {"fontSize": lit(9), "labelColor": color(INK), "showAxisTitle": lit(False)}}],
            "legend": [{"properties": {"show": lit(serie is not None), "position": lit("Top")}}]}
    if fx:
        objs["dataPoint"] = [{"properties": {"fill": color_fx(fx)}, "selector": TODOS}]
    query = {"Category": [proj(cat)], "Y": [proj(val, nombre_val)]}
    if serie:
        query["Series"] = [proj(serie)]
    vco = {"visualTooltip": [{"properties": {"show": lit(True), "type": lit("ReportPage"), "section": lit(tooltip)}}]} if tooltip else None
    return pg.add(tipo, x, y, w, h, query=query, objects=objs, titulo=titulo, sort=sort or [(val, "Descending")], vco=vco)


def filtro_no_es(entidad, columna, valores, nombre="flt"):
    return {"name": nombre, "field": C(entidad, columna), "type": "Categorical", "howCreated": "User",
            "filter": {"Version": 2, "From": [{"Name": "t", "Entity": entidad, "Type": 0}],
                       "Where": [{"Condition": {"Not": {"Expression": {"In": {
                           "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "t"}}, "Property": columna}}],
                           "Values": [[lit(v)["expr"]] for v in valores]}}}}}]}}


def filtro_es(entidad, columna, valores, nombre="flt"):
    return {"name": nombre, "field": C(entidad, columna), "type": "Categorical", "howCreated": "User",
            "filter": {"Version": 2, "From": [{"Name": "t", "Entity": entidad, "Type": 0}],
                       "Where": [{"Condition": {"In": {
                           "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "t"}}, "Property": columna}}],
                           "Values": [[lit(v)["expr"]] for v in valores]}}}]}}


def escribir(archivos: dict, base: Path):
    for rel, cont in archivos.items():
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        txt = cont if isinstance(cont, str) else json.dumps(cont, ensure_ascii=False, indent=2)
        p.write_text(txt, encoding="utf-8", newline="\n" if rel.endswith(".tmdl") else None)
