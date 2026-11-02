"""
13 · Importa el «Super Excel» de Intendencias PBA 2027 (sólo lectura) para el Power BI.

FUENTE
------
E:\\INTENDENTES 2027 PBA\\SUPER_EXCEL_Intendencias_PBA_2027.xlsx (material de Atlas Analytics, fuera
de este repositorio). Hojas MUNICIPIOS (135 filas: escenario 2027, espacio 2026, concejales 2025,
opositores, oportunidad), PROSPECTOS (CRM de ~980 personas) y NOTICIAS (~860 titulares con enlace).

PRIVACIDAD
----------
El repositorio es público y el CRM es material comercial. Las salidas van a
`03_OUTPUTS/powerbi/datos_privados/`, que está en `.gitignore`: este script se versiona, los datos no.

Salidas (03_OUTPUTS/powerbi/datos_privados/)
- intendencias.csv : un renglón por municipio (cod_indec)
- prospectos.csv   : una persona por renglón, con cod_indec
- noticias.csv     : un titular por renglón, con fecha, medio y URL
"""
from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

import openpyxl
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
EXCEL = Path(r"E:\INTENDENTES 2027 PBA\SUPER_EXCEL_Intendencias_PBA_2027.xlsx")
PERFILES = Path(r"E:\INTENDENTES 2027 PBA\PERFILES_135_Municipios_PBA_2027.pdf")
SALIDA = RAIZ / "03_OUTPUTS" / "powerbi" / "datos_privados"


def tabla(ws, fila_encabezado: int) -> tuple[pd.DataFrame, list]:
    """Encabezados en `fila_encabezado`; devuelve valores y, aparte, los hipervínculos por celda."""
    cab = [c.value for c in ws[fila_encabezado]]
    filas, links = [], []
    for r in ws.iter_rows(min_row=fila_encabezado + 1):
        if all(c.value is None for c in r):
            continue
        filas.append([c.value for c in r])
        links.append([c.hyperlink.target if c.hyperlink else None for c in r])
    return pd.DataFrame(filas, columns=cab), links


def norm(t) -> str:
    t = unicodedata.normalize("NFKD", str(t)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", t)


def pct(x):
    if isinstance(x, (int, float)):
        return float(x) if x > 1 else float(x) * 100
    m = re.search(r"([\d.,]+)\s*%", str(x or ""))
    return float(m.group(1).replace(".", "").replace(",", ".")) if m else None


def main() -> None:
    if not EXCEL.exists():
        sys.exit(f"No encuentro el Excel: {EXCEL}")
    SALIDA.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.load_workbook(EXCEL, read_only=False, data_only=False)

    m, _ = tabla(wb["MUNICIPIOS"], 4)
    m = m.dropna(subset=["Municipio"])
    m["cod_indec"] = m["Código INDEC"].astype(int).astype(str).str.zfill(5)
    orden = {mun: i for i, mun in enumerate(m.Municipio)}
    out = pd.DataFrame({
        "cod_indec": m.cod_indec, "municipio_excel": m.Municipio, "tamano": m["Tamaño"],
        "electo_2023": m["Intendente electo 2023"], "en_ejercicio": m["En ejercicio hoy"],
        "espacio_2026": m["Espacio 2026"], "escenario_2027": m["Escenario 2027"],
        "pct_ganador_2023": m["Pct ganador 2023"].map(pct), "segundo_2023": m["Segundo en 2023"],
        "gano_concejales_2025": m["Ganó concejales 2025"], "bancas_2025": m["Bancas 2025"],
        "eleccion_2025_pareja": m["Elección 2025 pareja"], "oposicion_esperable": m["Oposición esperable"],
        "principales_opositores": m["Principales opositores"], "oportunidad": pd.to_numeric(m["Oportunidad"], errors="coerce"),
        "nivel_oportunidad": m["Nivel oportunidad"],
    })
    q = m.Municipio.str.replace(" ", "+")
    out["google_maps_url"] = "https://www.google.com/maps/search/" + q + "+partido+Buenos+Aires"
    out["noticias_url"] = "https://news.google.com/search?q=%22" + q + "%22+intendente+2027&hl=es-419&gl=AR"
    out["perfil_pdf_url"] = [PERFILES.as_uri() + f"#page={orden[x] + 3}" for x in m.Municipio]
    out.to_csv(SALIDA / "intendencias.csv", index=False, encoding="utf-8")
    cod = dict(zip(m.Municipio.map(norm), m.cod_indec))

    p, _ = tabla(wb["PROSPECTOS"], 4)
    p = p.dropna(subset=["Nombre"])
    p = pd.DataFrame({
        "cod_indec": p.Municipio.map(norm).map(cod), "municipio": p.Municipio, "nombre": p.Nombre,
        "espacio": p["Espacio / fuerza"], "fuerza_familia": p["Fuerza (familia)"], "rol": p.Rol,
        "por_que": p["Por qué está"], "detalle": p.Detalle, "prioridad": p.Prioridad, "fuente": p.Fuente,
        "estado": p["Estado contacto"].fillna("Pendiente"), "notas": p.Notas, "proximo_paso": p["Próximo paso"],
        "fecha_proximo_paso": pd.to_datetime(p["Fecha próximo paso"], errors="coerce").dt.date,
    })
    p["orden_prioridad"] = p.prioridad.map({"Alta": 1, "Media": 2, "Baja": 3}).fillna(4).astype(int)
    p.to_csv(SALIDA / "prospectos.csv", index=False, encoding="utf-8")

    n, links = tabla(wb["NOTICIAS"], 4)
    i_link = list(n.columns).index("Link")
    n["url"] = [r[i_link] for r in links]
    n = n.dropna(subset=["Titular"])
    n = pd.DataFrame({"cod_indec": n.Municipio.map(norm).map(cod), "municipio": n.Municipio,
                      "fecha": pd.to_datetime(n.Fecha, errors="coerce").dt.date, "titular": n.Titular,
                      "medio": n.Medio, "url": n.url})
    n.to_csv(SALIDA / "noticias.csv", index=False, encoding="utf-8")

    print(f"intendencias: {len(out)} · prospectos: {len(p)} (sin municipio: {p.cod_indec.isna().sum()}) · "
          f"noticias: {len(n)} (con enlace: {n.url.notna().sum()}, sin municipio: {n.cod_indec.isna().sum()})")
    print(out.escenario_2027.value_counts().to_string())


if __name__ == "__main__":
    main()
