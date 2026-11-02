"""
p05 · Arma la página del tablero: la plantilla con los datos de p04 incrustados (abre sin servidor;
necesita internet sólo para la librería de gráficos y las tipografías).

Salida: 03_OUTPUTS/tablero/tablero_pba.html
"""
from pathlib import Path

AQUI = Path(__file__).parent
SALIDA = AQUI.parents[1] / "03_OUTPUTS" / "tablero"
html = (AQUI / "tablero_plantilla.html").read_text(encoding="utf-8")
datos = (SALIDA / "tablero_datos.json").read_text(encoding="utf-8").replace("</", r"<\/")
(SALIDA / "tablero_pba.html").write_text(html.replace("__DATOS__", datos, 1), encoding="utf-8")
print(f"tablero_pba.html: {(SALIDA / 'tablero_pba.html').stat().st_size / 1e6:.1f} MB")
