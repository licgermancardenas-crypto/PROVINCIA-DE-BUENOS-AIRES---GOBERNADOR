# -*- coding: utf-8 -*-
"""
ETL 00 · Baja el dato crudo automatizable a 01_DATOS/raw/.

    python 02_SCRIPTS/etl/00_descargar_fuentes.py            # baja lo que falta
    python 02_SCRIPTS/etl/00_descargar_fuentes.py --listar   # sólo muestra estado
    python 02_SCRIPTS/etl/00_descargar_fuentes.py dine       # sólo las entradas cuyo destino contiene "dine"

Qué contesta: nada; deja el crudo en su lugar con nombre fijo para que los ETL siguientes no
dependan de la URL del portal.

Qué supone:
- Las URL de la DINE (argentina.gob.ar/dine/resultados-electorales/elecciones-AAAA) y del
  catálogo de datos abiertos de PBA (catalogo.datos.gba.gob.ar) siguen vivas. Se verificaron
  el 01-11-2026.
- Los ZIP de la DINE son **todo el país**: el filtro a PBA (distrito 02) lo hace el ETL 01 en
  streaming. No se descomprimen acá.
- Si existe `ATLAS_CABA_RAW` (o la ruta por defecto del Atlas CABA), los archivos que ya están
  allá se **copian** en vez de rebajarse. Sólo se lee esa carpeta, nunca se escribe.

Qué no puede afirmar: que el archivo bajado sea el definitivo. Los ZIP «provisorios» de la DINE
son el escrutinio provisorio por mesa; el definitivo viene agregado por distrito/sección.
"""
import os
import shutil
import sys
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
RAW = RAIZ / "01_DATOS" / "raw"
CABA_RAW = Path(os.environ.get("ATLAS_CABA_RAW", r"E:\GOBIERNO LA CIUDAD - JEFE DE GOBIERNO\01_DATOS\raw"))

DINE = "https://www.argentina.gob.ar/sites/default/files/"
GBA = "https://catalogo.datos.gba.gob.ar/dataset/"
INFRA = "https://infra.datos.gob.ar/catalog/indec/dataset/"
INDEC_GEO = "https://www.indec.gob.ar/ftp/cuadros/geoestadistica/"
CEP = "https://cdn.produccion.gob.ar/cdn-cep/datos-por-departamento/"

# (destino relativo a raw/, URL o None, archivo equivalente en el raw del Atlas CABA o None, nota)
FUENTES = [
    # --- DINE · escrutinio provisorio por mesa, todo el país -----------------------------
    # Gobernador PBA va en la misma boleta en 2011, 2015, 2019 y 2023: la DINE lo trae como
    # categoría provincial en el mismo archivo, con el mismo mesa_id.
    ("electoral/dine/2011_generales.zip", DINE + "2011-provisorios_generales.zip", None, "Gobernador 2011 (Scioli)"),
    ("electoral/dine/2011_paso.zip", DINE + "2011-provisorios_paso.zip", None, ""),
    ("electoral/dine/2013_generales.zip", DINE + "2013-provisorios_generales.zip", "electoral/nac_2013_gen.zip", "legislativa"),
    ("electoral/dine/2013_paso.zip", DINE + "2013-provisorios_paso.zip", None, ""),
    ("electoral/dine/2015_generales.zip", DINE + "2015-provisorios_generales.zip", None, "Gobernador 2015 (Vidal)"),
    ("electoral/dine/2015_paso.zip", DINE + "dine-resultados/2015-PROVISORIOS_PASO.zip", None, ""),
    ("electoral/dine/2015_balotaje.zip", DINE + "2015-provisorios_ballotage.zip", "electoral/2015-provisorios_ballotage.zip", ""),
    ("electoral/dine/2017_generales.zip", DINE + "2017-provisorios_generales.zip", None, "legislativa"),
    ("electoral/dine/2017_paso.zip", DINE + "2017-provisorios_paso.zip", None, ""),
    ("electoral/dine/2019_generales.zip", DINE + "2019-provisorios_generales.zip", "electoral/nac2019_prov.zip", "Gobernador 2019 (Kicillof)"),
    ("electoral/dine/2019_paso.zip", DINE + "2019-provisorios_paso.zip", None, ""),
    ("electoral/dine/2021_generales.zip", DINE + "2021-provisorios_generales.zip", "electoral/nac_2021_gen.zip", "legislativa"),
    ("electoral/dine/2021_paso.zip", DINE + "2021-provisorios_paso.zip", "electoral/paso2021_provisorios.zip", ""),
    ("electoral/dine/2023_generales.zip", DINE + "2023_generales_1.zip", "electoral/gen2023_nac.zip", "Gobernador 2023 (Kicillof reelecto)"),
    ("electoral/dine/2023_balotaje.zip", DINE + "2023_segundavuelta.zip", None, ""),
    # Octubre 2025 nacional: la página de la DINE todavía no lista el ZIP; la copia del CABA
    # es el provisorio por mesa de todo el país (resultados2025.csv + locales y mesas).
    ("electoral/dine/2025_generales.zip", None, "electoral/nac_2025.zip", "legislativa nacional 26-10-2025"),

    # --- PBA · catálogo de datos abiertos ---------------------------------------------------
    ("electoral/gba/generales_provinciales_2005_2023.csv",
     GBA + "0db2279b-b3d0-44a8-b985-261fc2e1f0dc/resource/7920d25d-d822-4b19-ae76-45b6379ec143/download/elecciones-generales-2005-2023.csv",
     None, "definitivo por municipio, categorías provinciales"),
    ("electoral/gba/paso_provinciales_2011_2021.csv",
     GBA + "0db2279b-b3d0-44a8-b985-261fc2e1f0dc/resource/b3c81c28-0930-4b33-95cf-27ae39d4106a/download/elecciones-paso-2011-2021.csv",
     None, ""),
    ("electoral/gba/nacionales_paso_generales_2015_2023.csv",
     GBA + "1ae289f8-532c-4f69-a3c8-0268fe0ee390/resource/0af75e2c-d174-4ab6-a505-f7a2ae759a37/download/elecciones-nacionales-2015-2023.csv",
     None, "definitivo por municipio, categorías nacionales"),
    ("geo/limite_partidos_pba.zip",
     GBA + "627f65de-2510-4bf4-976b-16035828b5ae/resource/2cc73f96-98f7-42fa-a180-e56c755cf59a/download/limite-partidos-pba.zip",
     None, "135 partidos"),
    ("geo/secciones_electorales_pba.zip",
     GBA + "015aac76-3a1a-4f4d-a796-a55d2cbd315a/resource/8f3acc5e-a6ed-43eb-bba0-0c1dea304941/download/secciones-electorales-pba.zip",
     None, "8 secciones"),
    ("geo/circuitos_electorales_pba.zip",
     GBA + "4fe68b69-c788-4c06-ac67-26e4ebc7416b/resource/37bd466c-4a80-4e2e-be11-a68cfe60aa1e/download/circuitos-electorales-pba.zip",
     None, "polígonos de circuitos"),
    ("geo/circuitos_electorales_pba.csv",
     GBA + "4fe68b69-c788-4c06-ac67-26e4ebc7416b/resource/43d4314f-c540-4b00-8c41-1104141bda19/download/circuitos-electorales-pba.csv",
     None, ""),

    # --- territorio ---------------------------------------------------------------------------
    ("social/renabap.geojson", "https://archivo.infraestructura.gob.ar/dataset/ssisu/20231205_info_publica.geojson",
     "gestion/renabap.geojson", "barrios populares, país"),

    # --- censos (INDEC vía datos.gob.ar) --------------------------------------------------------
    # Bases REDATAM por provincia. Para 2010 y 2001 el catálogo publica la URL «...-2022.zip»,
    # que da 404: el archivo real termina en -2010 / -2001 (verificado el 01-11-2026).
    ("censo/c2022_pba.zip", INFRA + "48/distribution/48.2/download/06-buenos-aires-2022.zip", None, "Censo 2022 PBA"),
    ("censo/c2022_diccionario_variables.csv", INFRA + "48/distribution/48.26/download/diccionario-variables.csv", None, ""),
    ("censo/c2022_diccionario_categorias.csv", INFRA + "48/distribution/48.25/download/diccionario-categorias.csv", None, ""),
    ("censo/c2010_pba.zip", INFRA + "57/06-buenos-aires-2010.zip", None, "Censo 2010 PBA"),
    ("censo/c2010_diccionario_variables.csv", INFRA + "57/diccionario-variables.csv", None, ""),
    ("censo/c2010_diccionario_categorias.csv", INFRA + "57/diccionario-categorias.csv", None, ""),
    ("censo/c2001_pba.zip", INFRA + "56/06-buenos-aires-2001.zip", None, "Censo 2001 PBA"),
    ("censo/c2001_diccionario_variables.csv", INFRA + "56/diccionario-variables.csv", None, ""),
    ("censo/c1991_pba.zip", INFRA + "55/02-buenos-aires-1991.zip", None, "Censo 1991: PBA es la 02 en ese censo"),
    ("censo/c1991_diccionario_variables.csv", INFRA + "55/diccionario-variables.csv", None, ""),
    ("geo/radios_2022_pba.zip",
     GBA + "33b080d2-e369-4076-acd4-511db0e9bffb/resource/151d80d2-87c1-4981-9bea-9aab38a82ec9/download/radios-censales-2022-geojson.zip",
     None, "radios 2022, recorte PBA"),
    ("geo/radios_2010_pba.zip",
     GBA + "33b080d2-e369-4076-acd4-511db0e9bffb/resource/97b854f7-3390-442e-a167-a55960d6ebca/download/radios-censales-geojson.zip",
     None, "radios 2010, recorte PBA"),
    ("geo/radios_2001_pais.zip", INFRA + "50/distribution/50.9/download/radios-censales-2001.zip", None, "país"),
    ("geo/radios_1991_pais.zip", INFRA + "50/distribution/50.12/download/radios-censales-1991.zip", None, "país"),
    ("geo/conversion_radios_2010_2022.zip", INDEC_GEO + "conversion_radios_2010_2022.zip", None, ""),
    ("geo/conversion_radios_2001_2010.zip", INDEC_GEO + "Tablas_conversion_radios_2001_2010.zip", None, ""),
    *[(f"geo/indec_codigos_{n}.xlsx", INDEC_GEO + f"c2022_codigos_{n}.xlsx", None, "")
      for n in ("departamentos", "gobiernos_locales", "aglomerados", "localidades")],

    # --- economía, fisco y gestión por municipio --------------------------------------------------
    ("presupuesto/transferencias_municipios_mensual.csv",
     GBA + "96ee21b4-b116-4b83-9228-ba664af1b480/resource/d13acdb6-bd59-4c09-b954-8f3258a65e8a/download/transferencias-municipios-012010_072026.csv",
     None, "2010-07/2026, por fondo"),
    ("presupuesto/tributos_descentralizados_anual.csv",
     GBA + "96ee21b4-b116-4b83-9228-ba664af1b480/resource/c588d20c-0ce5-4596-b8b1-441155381a70/download/serie-anual-tributos-descentralizados-2003_2025_v2.csv",
     None, ""),
    ("social/pbg_partidos_2021_2023.xlsx",
     "https://datos.estadistica.ec.gba.gov.ar/dataset/8f2662b9-3af8-4eef-9fa0-af65251548f5/resource/5ddfde05-44b8-499d-9984-fc1db9fade71/download/pbg-por-municipio-2021-2022-2023-en-pesos-corrientes-y-constantes.xlsx",
     None, "PBG por partido"),
    ("servicios/salud_establecimientos_2025.csv",
     GBA + "91743f68-bc82-4475-baca-7d5d6908eee8/resource/c52f9497-9eab-4ecd-a382-b4e4c6033a02/download/establecimientos_salud_publicos-2025.csv",
     None, ""),
    ("social/empleo_puestos_depto.csv", CEP + "puestos/puestos_depto_total.csv", None, "SIPA, asalariados registrados"),
    ("social/empleo_puestos_depto_priv.csv", CEP + "puestos/puestos_depto_priv.csv", None, ""),
    ("social/empleo_puestos_depto_pub.csv", CEP + "puestos/puestos_depto_pub.csv", None, ""),
    ("social/salario_mediano_depto.csv", CEP + "salarios/w_median_depto_total.csv", None, ""),
    ("social/cep_diccionario_depto.csv", CEP + "diccionario_cod_depto.csv", None, ""),
    ("social/snic_departamentos_anual.csv", "https://cloud-snic.minseg.gob.ar/Bases/SNIC/snic-departamentos-anual.csv", None, "delito por partido"),
    ("social/refeglo_gobiernos_locales.csv",
     "http://datos.mininterior.gob.ar/dataset/8431ab79-3f44-41ee-b72b-cdc645f68d1e/resource/ebe52783-6a7f-4112-8a7f-a17c91cb6b4e/download/brgl_-portal-andino-23_12.csv",
     None, "Registro Federal de Gobiernos Locales"),
]


def bajar(url: str, destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(destino.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Atlas PBA)"})
    with urllib.request.urlopen(req, timeout=300) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f, length=1 << 20)
    tmp.replace(destino)


def es_zip_valido(p: Path) -> bool:
    # La DINE devuelve una página 404 con status 200 y extensión .zip (pasó en el CABA).
    if p.suffix != ".zip":
        return p.stat().st_size > 0
    with open(p, "rb") as f:
        return f.read(2) == b"PK"


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    listar = "--listar" in sys.argv
    faltan = 0
    for dest, url, caba, nota in FUENTES:
        if args and not any(a in dest for a in args):
            continue
        p = RAW / dest
        if p.exists() and es_zip_valido(p):
            print(f"  ok      {dest}  ({p.stat().st_size / 1e6:.1f} MB)")
            continue
        if listar:
            print(f"  FALTA   {dest}  {'[copia CABA]' if caba and (CABA_RAW / caba).exists() else ''} {nota}")
            faltan += 1
            continue
        try:
            if caba and (CABA_RAW / caba).exists() and es_zip_valido(CABA_RAW / caba):
                p.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(CABA_RAW / caba, p)
                print(f"  copiado {dest}  <- Atlas CABA")
            elif url:
                print(f"  bajando {dest} ...", flush=True)
                bajar(url, p)
                if not es_zip_valido(p):
                    p.unlink()
                    raise RuntimeError("el portal devolvió algo que no es ZIP (¿404 disfrazado?)")
                print(f"  bajado  {dest}  ({p.stat().st_size / 1e6:.1f} MB)")
            else:
                print(f"  MANUAL  {dest}: sin URL automatizable, ver FUENTES.md")
                faltan += 1
        except Exception as e:  # noqa: BLE001 — seguir con el resto y reportar
            print(f"  ERROR   {dest}: {e}")
            faltan += 1
    print(f"\n{faltan} pendientes." if faltan else "\nTodo en su lugar.")


if __name__ == "__main__":
    main()
