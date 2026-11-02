"""
p03 · Arma la página del simulador: la plantilla con los datos (p01) y el motor en JavaScript
incrustados, para que abra sin internet (salvo las tipografías).

Salida: 03_OUTPUTS/simulador/simulador_2027.html
"""
from pathlib import Path

AQUI = Path(__file__).parent
SALIDA = AQUI.parents[1] / "03_OUTPUTS" / "simulador"

html = (AQUI / "simulador_plantilla.html").read_text(encoding="utf-8")
datos = (SALIDA / "datos_simulador.json").read_text(encoding="utf-8")
motor = (AQUI / "motor_2027.js").read_text(encoding="utf-8")
assert "</script" not in datos and "</script" not in motor
html = html.replace("__DATOS__", datos, 1).replace("__MOTOR__", motor, 1)
(SALIDA / "simulador_2027.html").write_text(html, encoding="utf-8")
print(f"simulador_2027.html: {len(html.encode()) / 1e6:.2f} MB")
