# -*- coding: utf-8 -*-
"""
ETL 01 · Escrutinio provisorio de la DINE (todo el país) -> mesas de PBA, un parquet por elección.

    python 02_SCRIPTS/etl/01_mesas_dine_pba.py            # todas las que estén en raw/ y falten
    python 02_SCRIPTS/etl/01_mesas_dine_pba.py 2023 2019  # sólo esas (rehace)

Qué contesta: deja `01_DATOS/processed/mesas_dine_pba_<año>_<tipo>.parquet` con una fila por
mesa × categoría × agrupación × tipo de voto, con las cuatro escalas en la fila: sección
electoral (`seccionprovincial_id`, 1-8), municipio (`seccion_id`), circuito y mesa. Y una tabla
versionada de control, `03_OUTPUTS/tablas/control_dine_pba.csv`, con totales por elección y
categoría para contrastar contra el definitivo del catálogo PBA.

Qué supone:
- Todos los ZIP de 2011 a 2025 comparten el esquema de 22-26 columnas (verificado el 01-11-2026);
  las columnas se leen **por nombre**, porque el orden cambia entre años.
- La codificación cambia entre años (2011 viene en UTF-8; 2013, 2019, 2021, 2023 y 2025 en
  latin-1): se detecta por el encabezado.
- La máquina tiene poca RAM y el CSV de 2023 pesa 1 GB descomprimido: se filtra en streaming y
  se escribe en bloques. Nunca se carga el país entero.

- El año de cada fila es el del archivo. La columna año de la DINE no es confiable: el ZIP de 2013
  trae los Diputados provinciales con 2017. Queda el original en `anio_dato`.

Qué no puede afirmar: es el **provisorio**. Faltan mesas (telegramas no transmitidos) y los
totales no coinciden al voto con el definitivo; el control lo cuantifica. En elecciones con
Gobernador, la categoría provincial va en el mismo archivo con el mismo `mesa_id`.
"""
import csv
import io
import sys
import zipfile
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

RAIZ = Path(__file__).resolve().parents[2]
RAW = RAIZ / "01_DATOS" / "raw" / "electoral" / "dine"
OUT = RAIZ / "01_DATOS" / "processed"
CONTROL = RAIZ / "03_OUTPUTS" / "tablas" / "control_dine_pba.csv"

COLS = ["anio", "eleccion_tipo", "recuento_tipo", "padron_tipo", "seccionprovincial_id",
        "seccionprovincial_nombre", "seccion_id", "seccion_nombre", "circuito_id", "circuito_nombre",
        "mesa_id", "mesa_tipo", "mesa_electores", "cargo_id", "cargo_nombre", "agrupacion_id",
        "agrupacion_nombre", "lista_numero", "lista_nombre", "votos_tipo", "votos_cantidad"]
ENTEROS = ["seccionprovincial_id", "seccion_id", "mesa_electores", "cargo_id", "votos_cantidad"]
BLOQUE = 400_000


def abrir_resultados(z: zipfile.ZipFile):
    # El archivo de resultados es siempre el CSV más grande; los otros son ámbitos y colores.
    infos = [i for i in z.infolist() if i.filename.lower().endswith(".csv") and "__MACOSX" not in i.filename]
    return max(infos, key=lambda i: i.file_size)


def detectar_codificacion(z, info) -> str:
    with z.open(info) as h:
        cab = h.readline()
    try:
        cab.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        return "latin-1"


def normalizar_nombre(c: str) -> str:
    # «año» llega como año, aÃ±o o a�o según la codificación: se reconoce por la forma.
    c = c.strip().strip('"').lower()
    return "anio" if c.startswith("a") and c.endswith("o") and 3 <= len(c) <= 4 else c


def a_tabla(filas: list[list[str]], anio_archivo: int) -> pa.Table:
    df = pd.DataFrame(filas, columns=COLS)
    for c in df.columns:
        df[c] = df[c].str.strip()
    for c in ENTEROS:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")
    # El año sale del archivo, no de la columna: el ZIP de 2013 trae los Diputados provinciales
    # con «2017» en la columna año (169.361 filas en PBA). El original queda en `anio_dato`.
    df["anio_dato"] = pd.to_numeric(df["anio"], errors="coerce").astype("Int16")
    df["anio"] = pd.Series(anio_archivo, index=df.index, dtype="Int16")
    return pa.Table.from_pandas(df, preserve_index=False)


def procesar(zpath: Path) -> dict:
    anio, tipo = zpath.stem.split("_", 1)
    destino = OUT / f"mesas_dine_pba_{anio}_{tipo}.parquet"
    z = zipfile.ZipFile(zpath)
    info = abrir_resultados(z)
    cod = detectar_codificacion(z, info)
    escritor, filas, n_pais, n_pba = None, [], 0, 0
    with z.open(info) as h:
        lector = csv.reader(io.TextIOWrapper(h, encoding=cod, newline=""))
        cab = [normalizar_nombre(c) for c in next(lector)]
        idx = {c: i for i, c in enumerate(cab)}
        faltan = [c for c in COLS if c not in idx]
        if faltan:
            raise ValueError(f"{zpath.name}: faltan columnas {faltan}; encabezado = {cab}")
        i_dist = idx["distrito_id"]
        orden = [idx[c] for c in COLS]
        for fila in lector:
            n_pais += 1
            if fila[i_dist].strip().lstrip("0") != "2":
                continue
            filas.append([fila[i] for i in orden])
            n_pba += 1
            if len(filas) >= BLOQUE:
                t = a_tabla(filas, int(anio))
                escritor = escritor or pq.ParquetWriter(destino, t.schema, compression="zstd")
                escritor.write_table(t.cast(escritor.schema))
                filas = []
    if filas:
        t = a_tabla(filas, int(anio))
        escritor = escritor or pq.ParquetWriter(destino, t.schema, compression="zstd")
        escritor.write_table(t.cast(escritor.schema))
    if escritor:
        escritor.close()
    print(f"  {zpath.name}: {n_pba:,} filas PBA de {n_pais:,} ({cod}) -> {destino.name}")
    return {"anio": anio, "tipo": tipo, "destino": destino}


def control(destino: Path, anio: str, tipo: str) -> pd.DataFrame:
    d = pd.read_parquet(destino, columns=["cargo_nombre", "seccion_id", "circuito_id", "mesa_id",
                                          "mesa_electores", "votos_tipo", "votos_cantidad", "mesa_tipo"])
    mesas = d.drop_duplicates(["cargo_nombre", "seccion_id", "mesa_id", "mesa_tipo"])
    tot = d.groupby("cargo_nombre").agg(votos=("votos_cantidad", "sum")).reset_index()
    pos = d[d.votos_tipo == "POSITIVO"].groupby("cargo_nombre")["votos_cantidad"].sum().rename("positivos")
    mm = mesas.groupby("cargo_nombre").agg(mesas=("mesa_id", "size"), electores=("mesa_electores", "sum"),
                                           municipios=("seccion_id", "nunique"))
    circ = d.drop_duplicates(["cargo_nombre", "seccion_id", "circuito_id"]).groupby("cargo_nombre").size().rename("circuitos")
    ext = mesas[mesas.mesa_tipo.str.upper().str.startswith("EXTRANJ")].groupby("cargo_nombre").size().rename("mesas_extranjeros")
    out = (tot.join(pos, on="cargo_nombre").join(mm, on="cargo_nombre").join(circ, on="cargo_nombre")
           .join(ext, on="cargo_nombre"))
    out["mesas_extranjeros"] = out["mesas_extranjeros"].fillna(0).astype(int)
    out.insert(0, "tipo", tipo)
    out.insert(0, "anio", int(anio))
    out["participacion"] = (out.votos / out.electores).round(4)
    return out


def main() -> None:
    pedidos = [a for a in sys.argv[1:] if a.isdigit()]
    OUT.mkdir(parents=True, exist_ok=True)
    CONTROL.parent.mkdir(parents=True, exist_ok=True)
    tablas = []
    for zpath in sorted(RAW.glob("*.zip")):
        anio, tipo = zpath.stem.split("_", 1)
        destino = OUT / f"mesas_dine_pba_{anio}_{tipo}.parquet"
        if (pedidos and anio not in pedidos) or (not pedidos and destino.exists()):
            if destino.exists():
                tablas.append(control(destino, anio, tipo))
            continue
        procesar(zpath)
        tablas.append(control(destino, anio, tipo))
    if tablas:
        c = pd.concat(tablas).sort_values(["anio", "tipo", "cargo_nombre"])
        c.to_csv(CONTROL, index=False, encoding="utf-8")
        print(f"\ncontrol -> {CONTROL.relative_to(RAIZ)}\n")
        print(c.to_string(index=False))


if __name__ == "__main__":
    main()
