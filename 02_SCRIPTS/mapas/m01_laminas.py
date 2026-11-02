"""
m01 · Láminas: los resultados principales en mapas.

Cinco láminas estáticas (PNG, 300 dpi), proyección cónica equivalente de Albers (la del proyecto),
con recuadro del Conurbano y La Plata (sus circuitos no se ven a escala provincial).

1. Voto peronista a Gobernador 2023 por circuito (% de los positivos).
2. Cambio del voto peronista 2023 -> 2025 por circuito (Diputados Nacionales, pp de los positivos).
3. Escenarios 2027: probabilidad de que el peronismo gane cada municipio (tres escenarios).
4. Qué elige cada sección en 2027 y la probabilidad de que el peronismo la gane (octubre se repite).
5. Desdoblamiento: crecimiento de LLA-PRO de septiembre a octubre 2025 por municipio (pp del padrón).

Decisiones (ver bitácora): cortes manuales y fijos (comparables entre paneles y con otras
láminas), escalas aptas para daltonismo (YlGnBu secuencial; PuOr divergente con centro en 0 o en
50 %), sin dato en gris con su propia entrada en la leyenda.

Salida: 03_OUTPUTS/laminas/*.png
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Patch, Rectangle

RAIZ = Path(__file__).resolve().parents[2]
PROC = RAIZ / "01_DATOS" / "processed"
TABLAS = RAIZ / "03_OUTPUTS" / "tablas"
OUT = RAIZ / "03_OUTPUTS" / "laminas"
ALBERS = "+proj=aea +lat_1=-34 +lat_2=-39 +lat_0=-36.5 +lon_0=-60 +datum=WGS84 +units=m"
NO_POS = {"BLANCO", "NULO", "RECURRIDO", "IMPUGNADO", "COMANDO"}
GRIS = "#d9d9d9"
FUENTE = ("Fuente: Atlas PBA, sobre escrutinio provisorio DINE, Junta Electoral PBA y cartografía electoral. "
          "Proyección cónica equivalente de Albers. Noviembre 2026.")
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8})


# ----------------------------------------------------------------------------- capas
def capas():
    part = gpd.read_file(PROC / "geo" / "partidos.gpkg").to_crs(ALBERS)
    secc = gpd.read_file(PROC / "geo" / "secciones.gpkg").to_crs(ALBERS)
    return part, secc, capa_ce(part)


def capa_ce(part):
    """Circuitos estables 2023-2025 que cubren toda la provincia. Los polígonos de circuitos
    rurales absorbidos antes de 2023 (96, el 15 % de la superficie) no están en esa ventana: se
    asignan al circuito que los absorbió según `circuitos_uniones_motivos.csv` (ETL 10) y, si no
    figura, al circuito vecino del mismo municipio con el que comparten más borde."""
    c = gpd.read_file(PROC / "geo" / "circuitos.gpkg").to_crs(ALBERS)
    eq = pd.read_csv(PROC / "circuitos_equivalencias.csv", dtype=str)
    ce23 = eq[eq.ventana == "2023_2025"].set_index("circuito").ce_id
    mot = pd.read_csv(TABLAS / "circuitos_uniones_motivos.csv", dtype=str)
    mot = mot[mot.motivo.str.startswith("desaparece")].drop_duplicates("circuito_a", keep="last")
    destino = mot.set_index("circuito_a").circuito_b
    c["ce_id"] = c.circuito.map(ce23)
    for i in c.index[c.ce_id.isna()]:
        x, vistos = c.at[i, "circuito"], set()
        while x in destino.index and x not in ce23.index and x not in vistos:
            vistos.add(x)
            x = destino[x]
        if x in ce23.index:
            c.at[i, "ce_id"] = ce23[x]
    falta = c.index[c.ce_id.isna()]
    con = c[c.ce_id.notna()]
    for i in falta:
        geo, mun = c.at[i, "geometry"], c.at[i, "cod_indec"]
        cand = con[(con.cod_indec == mun) & con.intersects(geo.buffer(200))]
        if len(cand):
            c.at[i, "ce_id"] = cand.loc[cand.geometry.intersection(geo.buffer(200)).length.idxmax(), "ce_id"]
    return c.dissolve(by="ce_id").reset_index()[["ce_id", "geometry"]]


def caja_conurbano(part):
    """Extensión del Conurbano y La Plata, para el recuadro."""
    claves = pd.read_csv(PROC / "municipios_claves.csv", dtype=str)
    cods = set(claves[claves.conurbano == "True"].cod_indec) | {"06441"}  # La Plata
    return part[part.cod_indec.isin(cods)].total_bounds


def escala(ax, km: int, x0: float, y0: float):
    ax.add_patch(Rectangle((x0, y0), km * 1000, km * 40, color="black"))
    ax.text(x0 + km * 500, y0 + km * 120, f"{km} km", ha="center", va="bottom", fontsize=7)


def pie(fig):
    fig.text(0.01, 0.01, FUENTE, fontsize=6, color="#555555", ha="left", va="bottom")


def leyenda(ax, cortes, colores, fmt, titulo, sin_dato=True, loc="lower right"):
    etq = []
    for i in range(len(colores)):
        lo, hi = cortes[i], cortes[i + 1]
        if np.isinf(lo):
            etq.append(f"menos de {fmt(hi)}")
        elif np.isinf(hi):
            etq.append(f"{fmt(lo)} o más")
        else:
            etq.append(f"{fmt(lo)} a {fmt(hi)}")
    h = [Patch(facecolor=c, edgecolor="none", label=t) for c, t in zip(colores, etq)]
    if sin_dato:
        h.append(Patch(facecolor=GRIS, edgecolor="none", label="sin dato"))
    ax.legend(handles=h, title=titulo, loc=loc, frameon=False, fontsize=7, title_fontsize=7.5, alignment="left")


def pintar(ax, gdf, col, cortes, colores, borde=None, lw=0.0):
    cmap = ListedColormap(colores)
    norm = BoundaryNorm(cortes, len(colores))
    gdf[gdf[col].isna()].plot(ax=ax, color=GRIS, linewidth=0)
    g = gdf[gdf[col].notna()]
    g.plot(ax=ax, column=col, cmap=cmap, norm=norm, linewidth=lw, edgecolor=borde or "none")


def contexto(ax, part, secc, lw_part=0.15, lw_secc=0.6):
    part.boundary.plot(ax=ax, color="white", linewidth=lw_part)
    secc.boundary.plot(ax=ax, color="#333333", linewidth=lw_secc)
    ax.set_axis_off()
    ax.set_aspect("equal")


def lamina_doble(titulo, subtitulo, dibujar, part, secc, nombre, leyenda_args):
    """Mapa provincial + recuadro del Conurbano y La Plata."""
    fig = plt.figure(figsize=(11, 8.5))
    ax = fig.add_axes([0.0, 0.05, 0.62, 0.83])
    ins = fig.add_axes([0.60, 0.25, 0.39, 0.60])
    dibujar(ax)
    contexto(ax, part, secc)
    dibujar(ins)
    contexto(ins, part, secc, lw_part=0.3, lw_secc=0.9)
    x0, y0, x1, y1 = caja_conurbano(part)
    m = 8000
    ins.set_xlim(x0 - m, x1 + m)
    ins.set_ylim(y0 - m, y1 + m)
    ax.add_patch(Rectangle((x0 - m, y0 - m), x1 - x0 + 2 * m, y1 - y0 + 2 * m, fill=False, edgecolor="black", linewidth=0.8))
    ins.set_title("Conurbano y La Plata", fontsize=8, loc="left")
    for s in ins.spines.values():
        s.set_visible(True)
    bx0, by0, bx1, by1 = part.total_bounds
    escala(ax, 100, bx0 + 20000, by0 + 20000)
    escala(ins, 20, x0, y0 - m + 1500)
    leyenda(ins if leyenda_args.pop("en_recuadro", False) else ax, **leyenda_args)
    fig.suptitle(titulo, x=0.01, y=0.975, ha="left", fontsize=13, fontweight="bold")
    fig.text(0.01, 0.925, subtitulo, ha="left", fontsize=8.5, color="#333333")
    pie(fig)
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / nombre, dpi=300)
    plt.close(fig)
    print(f"  {nombre}")


# ----------------------------------------------------------------------------- datos
def voto_ce(anio: int, cargo: str) -> pd.DataFrame:
    eq = pd.read_csv(PROC / "circuitos_equivalencias.csv", dtype=str)
    eq = eq[eq.ventana == "2023_2025"][["circuito", "ce_id"]]
    p = pd.read_parquet(PROC / "panel_circuito.parquet", columns=["anio", "tipo", "cargo", "circuito", "espacio", "votos"])
    x = p[(p.anio == anio) & (p.tipo == "GENERALES") & (p.cargo == cargo) & ~p.espacio.isin(NO_POS)].merge(eq, on="circuito")
    pos = x.groupby("ce_id").votos.sum()
    per = x[x.espacio == "PERONISMO"].groupby("ce_id").votos.sum().reindex(pos.index, fill_value=0)
    return pd.DataFrame({"pct_peronismo": 100 * per / pos, "positivos": pos})


def main() -> None:
    part, secc, ce = capas()

    # 1 · Gobernador 2023
    v = voto_ce(2023, "GOBERNADOR")
    g = ce.merge(v, left_on="ce_id", right_index=True, how="left")
    g.loc[g.positivos < 20, "pct_peronismo"] = np.nan
    cortes = [-np.inf, 30, 40, 50, 60, np.inf]
    col = ["#ffffcc", "#a1dab4", "#41b6c4", "#2c7fb8", "#253494"]
    lamina_doble("El voto peronista a Gobernador en 2023",
                 "Kicillof (Unión por la Patria), % de los votos positivos por circuito electoral. Ganó con 45,0 % en la provincia.",
                 lambda ax: pintar(ax, g, "pct_peronismo", cortes, col), part, secc, "01_peronismo_gobernador_2023.png",
                 dict(cortes=cortes, colores=col, fmt=lambda x: f"{x:.0f} %", titulo="% peronismo"))

    # 2 · Cambio 2023 -> 2025
    a, b = voto_ce(2023, "DIPUTADOS NACIONALES"), voto_ce(2025, "DIPUTADOS NACIONALES")
    d = (b.pct_peronismo - a.pct_peronismo).rename("cambio").to_frame()
    d.loc[(a.positivos.reindex(d.index) < 20) | (b.positivos.reindex(d.index) < 20), "cambio"] = np.nan
    g2 = ce.merge(d, left_on="ce_id", right_index=True, how="left")
    cortes2 = [-np.inf, -8, -4, 0, 4, 8, np.inf]
    col2 = ["#b35806", "#f1a340", "#fee0b6", "#d8daeb", "#998ec3", "#542788"]
    lamina_doble("Dónde ganó y dónde perdió el peronismo entre 2023 y 2025",
                 "Cambio del voto peronista a Diputados Nacionales (Unión por la Patria 2023 → Fuerza Patria 2025), puntos de los votos positivos, por circuito.",
                 lambda ax: pintar(ax, g2, "cambio", cortes2, col2), part, secc, "02_cambio_peronismo_2023_2025.png",
                 dict(cortes=cortes2, colores=col2, fmt=lambda x: f"{x:+.0f}", titulo="cambio (pp)"))

    # 3 · Escenarios 2027 por municipio (tres paneles, mismos cortes)
    mm = pd.read_csv(TABLAS / "motor_2027_municipio.csv", dtype={"cod_indec": str})
    esc = [("A · Octubre 2025 se repite", "Se repite octubre 2025\n(empate: peronismo gana el 59 %)"),
           ("C · Punto medio entre septiembre y octubre", "Punto medio\n(peronismo +6,8)"),
           ("B · Septiembre 2025 se repite", "Se repite septiembre 2025\n(peronismo +13,4)")]
    cortes3 = [0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0001]
    col3 = ["#b35806", "#f1a340", "#fee0b6", "#d8daeb", "#998ec3", "#542788"]
    fig, axs = plt.subplots(1, 3, figsize=(13, 6.2))
    for ax, (e, rot) in zip(axs, esc):
        x = part.merge(mm[mm.escenario == e][["cod_indec", "p_gana_peronismo"]], on="cod_indec", how="left")
        pintar(ax, x, "p_gana_peronismo", cortes3, col3)
        contexto(ax, part, secc, lw_part=0.25, lw_secc=0.7)
        n = int((x.p_gana_peronismo >= 0.5).sum())
        ax.set_title(f"{rot}\n{n} municipios con 50 % o más", fontsize=9, loc="left")
    bx0, by0, _, _ = part.total_bounds
    escala(axs[0], 100, bx0 + 20000, by0 + 20000)
    leyenda(axs[2], cortes3, col3, lambda x: f"{min(x, 1) * 100:.0f} %", "P(gana el peronismo)", sin_dato=True, loc="lower right")
    fig.suptitle("2027: dónde gana el peronismo según el escenario", x=0.01, y=0.98, ha="left", fontsize=13, fontweight="bold")
    fig.text(0.01, 0.925, "Probabilidad de que el peronismo saque más votos que el resto en cada municipio, en 1.000 simulaciones del motor (análisis 106). "
             "Derecha unida; padrón 2027 con extranjeros.", fontsize=8.5, color="#333333")
    pie(fig)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.78, bottom=0.05, wspace=0.02)
    fig.savefig(OUT / "03_escenarios_2027_municipio.png", dpi=300)
    plt.close(fig)
    print("  03_escenarios_2027_municipio.png")

    # 4 · Secciones 2027
    sec = pd.read_csv(TABLAS / "motor_2027_seccion.csv", dtype={"seccion": str})
    sec = sec[sec.escenario == "A · Octubre 2025 se repite"].set_index("seccion")
    camara = {"1": ("Diputados", 15), "4": ("Diputados", 14), "5": ("Diputados", 11), "7": ("Diputados", 6),
              "2": ("Senadores", 5), "3": ("Senadores", 9), "6": ("Senadores", 6), "8": ("Senadores", 3)}
    nombre_sec = {"1": "1ª", "2": "2ª", "3": "3ª", "4": "4ª", "5": "5ª", "6": "6ª", "7": "7ª", "8": "8ª (La Plata)"}
    s4 = secc.copy()
    colsec = [c for c in s4.columns if "seccion" in c.lower()][0]
    s4["sec"] = s4[colsec].astype(str).str.extract(r"(\d)")[0]
    s4["camara"] = s4.sec.map(lambda k: camara[k][0])
    fig, ax = plt.subplots(figsize=(9, 8.5))
    colores = {"Diputados": "#fdb863", "Senadores": "#b2abd2"}
    for cam, c in colores.items():
        s4[s4.camara == cam].plot(ax=ax, color=c, edgecolor="#333333", linewidth=0.8)
    part.boundary.plot(ax=ax, color="white", linewidth=0.2)
    for _, r in s4.iterrows():
        k = r.sec
        cam, nb = camara[k]
        p = sec.loc[k, "p_gana_peronismo"] if k in sec.index else np.nan
        pt = r.geometry.representative_point()
        if k in ("1", "3", "8"):
            continue
        ax.text(pt.x, pt.y, f"{nombre_sec[k]}\n{nb} {cam.lower()}\nperonismo gana: {p:.0%}", ha="center", va="center", fontsize=7.5)
    # las secciones del Conurbano y La Plata, en notas
    notas = [f"{nombre_sec[k]}: {camara[k][1]} {camara[k][0].lower()} · peronismo gana: {sec.loc[k, 'p_gana_peronismo']:.0%}"
             for k in ("1", "3", "8")]
    ax.text(0.98, 0.98, "Conurbano y La Plata\n" + "\n".join(notas), transform=ax.transAxes, ha="right", va="top", fontsize=7.5,
            bbox=dict(facecolor="white", edgecolor="#999999", linewidth=0.5))
    ax.legend(handles=[Patch(facecolor=c, edgecolor="#333333", label=f"elige {k.lower()}") for k, c in colores.items()],
              loc="lower left", frameon=False, fontsize=8)
    ax.set_axis_off()
    bx0, by0, _, _ = part.total_bounds
    escala(ax, 100, bx0 + 20000, by0 + 20000)
    fig.suptitle("La Legislatura 2027: qué elige cada sección", x=0.01, y=0.975, ha="left", fontsize=13, fontweight="bold")
    fig.text(0.01, 0.925, "46 diputados en la 1ª, 4ª, 5ª y 7ª; 23 senadores en la 2ª, 3ª, 6ª y 8ª.\n"
             "Probabilidad de que el peronismo gane cada sección si se repite octubre 2025 (análisis 106 y 108).",
             fontsize=8.5, color="#333333")
    pie(fig)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.88, bottom=0.04)
    fig.savefig(OUT / "04_secciones_2027.png", dpi=300)
    plt.close(fig)
    print("  04_secciones_2027.png")

    # 5 · Desdoblamiento
    dd = pd.read_csv(TABLAS / "desdoblamiento_municipio.csv", dtype={"cod_indec": str})
    s5 = dd[dd.eleccion == "Septiembre (sólo nativos)"].set_index("cod_indec")
    o5 = dd[dd.eleccion == "Octubre"].set_index("cod_indec")
    cambio = (100 * (o5.LLA_PRO / o5.electores - s5.LLA_PRO / s5.electores)).rename("cambio_lla").to_frame()
    g5 = part.merge(cambio, left_on="cod_indec", right_index=True, how="left")
    cortes5 = [-np.inf, 3, 6, 9, 12, np.inf]
    col5 = ["#ffffcc", "#a1dab4", "#41b6c4", "#2c7fb8", "#253494"]
    lamina_doble("De septiembre a octubre de 2025, LLA-PRO creció más en el interior",
                 "Cambio del voto de LLA-PRO entre la provincial del 7/9 (sólo nativos, estimado) y la nacional del 26/10, en puntos del padrón, por municipio (análisis 103).",
                 lambda ax: pintar(ax, g5, "cambio_lla", cortes5, col5), part, secc, "05_desdoblamiento_lla_pro.png",
                 dict(cortes=cortes5, colores=col5, fmt=lambda x: f"{x:+.0f}", titulo="cambio (pp del padrón)"))

    # Verificación: tres valores de la tabla contra lo que se pintó.
    for cod in ("06427", "06357", "06063"):
        r = g5[g5.cod_indec == cod]
        if len(r):
            print(f"  control {cod} {r.municipio_nombre.iloc[0] if 'municipio_nombre' in r else ''}: cambio LLA-PRO {r.cambio_lla.iloc[0]:+.1f} pp")


if __name__ == "__main__":
    main()
