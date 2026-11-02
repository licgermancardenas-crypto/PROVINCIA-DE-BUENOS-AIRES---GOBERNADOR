# -*- coding: utf-8 -*-
"""
ATLAS ANALYTICS - PROVINCIA DE BUENOS AIRES
Informe 01: hallazgos rumbo a Gobernador 2027.

Arma el informe con el estilo de casa (`_estilo.py`, el mismo del Atlas CABA) y lo pasa a PDF con
Chrome headless. Los números de escenarios y bancas se leen de las tablas del motor; el resto viene
de `00_DOCS/HALLAZGOS.md`, donde cada número tiene su script y su tabla.

Salidas:
  04_REPORTES/reporte_01_hallazgos.html
  05_ENTREGABLES/ATLAS_PBA_Hallazgos_2027.pdf

El HTML lleva la lámina incrustada (data URI) para que se pueda renderizar desde %TEMP%:
`--print-to-pdf` falla de forma intermitente con rutas con espacios (lección del Atlas CABA).
"""
from pathlib import Path
import base64
import shutil
import subprocess
import sys
import tempfile

import fitz
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _estilo import CSS  # noqa: E402

T = ROOT / "03_OUTPUTS" / "tablas"
HTML = ROOT / "04_REPORTES" / "reporte_01_hallazgos.html"
PDF = ROOT / "05_ENTREGABLES" / "ATLAS_PBA_Hallazgos_2027.pdf"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
SIMULADOR = "https://claude.ai/artifact/3HHPCqam3Q8GVwhqM8xeRo"
REPO = "github.com/licgermancardenas-crypto/PROVINCIA-DE-BUENOS-AIRES---GOBERNADOR"

pc = lambda n, d=1: f"{n:.{d}f}".replace(".", ",")
sg = lambda n, d=1: ("+" if n > 0 else "−" if n < 0 else "") + f"{abs(n):.{d}f}".replace(".", ",")
ACENTO, APAGADO, TEXTO, TENUE, LINEA = "#C40BFF", "#6b5a8c", "#DCD2EA", "#A08FC2", "#2A1750"
folio = [0]


def pg(sec, cuerpo):
    folio[0] += 1
    return (f'<div class="pg"><div class="corriente"><span>Atlas PBA · Hallazgos rumbo a 2027</span>'
            f'<span>{sec}</span></div>{cuerpo}'
            f'<div class="pie"><span class="marca">ATLAS ANALYTICS</span>'
            f'<span class="sec">{sec}</span><span class="folio">{folio[0]:02d}</span></div></div>')


def tabla(cols, filas, clase="media"):
    h = "".join(f"<th>{c}</th>" for c in cols)
    b = "".join("<tr" + (' class="hi"' if f[0] == "__hi__" else "") + ">"
                + "".join(f"<td>{c}</td>" for c in (f[1:] if f[0] == "__hi__" else f)) + "</tr>"
                for f in filas)
    return f'<table class="{clase}"><tr>{h}</tr>{b}</table>'


# ------------------------------------------------------------------ datos de escenarios
E = pd.read_csv(T / "motor_2027_escenarios.csv")
MV = pd.read_csv(T / "movilizacion_2027.csv")
LG = pd.read_csv(T / "legislatura_2027_escenarios.csv")


def esc(pref):
    r = E[E.escenario.str.startswith(pref)].iloc[0]
    return r.margen_p10, r.margen_p50, r.margen_p90, r.p_gana_peronismo


def mov(perfil, derecha="unida"):
    r = MV[(MV.base == "octubre") & (MV.derecha == derecha) & MV.perfil.str.startswith(perfil)].iloc[0]
    return r.margen_p10, r.margen_p50, r.margen_p90, r.p_gana_peronismo


FILAS = [("Octubre; se suman con el perfil 2021-2023", *mov("Como 2021-2023")),
         ("Octubre 2025 se repite", *esc("A ·")),
         ("Octubre; se suman con el perfil 2017-2019", *mov("Como 2017-2019")),
         ("Tercera vía fuerte (12 %)", *esc("D ·")),
         ("Octubre; se suman con el perfil 2023-2025", *mov("Como 2023-2025")),
         ("Punto medio septiembre-octubre", *esc("C ·")),
         ("Octubre; derecha dividida (PRO 25 %)", *mov("Parejo", "dividida (PRO 25 %)")),
         ("Septiembre 2025 se repite", *esc("B ·"))]
FILAS.sort(key=lambda f: f[2])
A = esc("A ·")


def grafico_escenarios():
    """Margen del peronismo por escenario: mediana y rango 10-90."""
    W, x0, x1, lo, hi = 760, 300, 715, -8, 18
    y0, paso = 52, 40
    x = lambda v: x0 + (v - lo) / (hi - lo) * (x1 - x0)
    H = y0 + len(FILAS) * paso + 18
    s = [f'<svg viewBox="0 0 {W} {H}" style="width:100%;display:block" font-family="Segoe UI, Arial" font-size="12">']
    for t in (-5, 0, 5, 10, 15):
        s.append(f'<line x1="{x(t)}" x2="{x(t)}" y1="{y0 - 22}" y2="{H - 14}" stroke="{TENUE if t == 0 else LINEA}" '
                 f'stroke-width="{1.4 if t == 0 else 1}"/>')
        s.append(f'<text x="{x(t)}" y="{y0 - 30}" text-anchor="middle" fill="{TENUE}">{sg(t, 0) if t else "empate"}</text>')
    for i, (nom, p10, p50, p90, p) in enumerate(FILAS):
        y = y0 + i * paso
        c = ACENTO if p10 < 0 else APAGADO
        s.append(f'<text x="{x0 - 12}" y="{y + 4}" text-anchor="end" fill="{TEXTO}">{nom}</text>')
        s.append(f'<line x1="{x(p10)}" x2="{x(p90)}" y1="{y}" y2="{y}" stroke="{c}" stroke-width="3.5" stroke-linecap="round"/>')
        s.append(f'<circle cx="{x(p50)}" cy="{y}" r="6.5" fill="{c}"/>')
        lx, anc = (x(p10) - 10, "end") if p90 < 0 else (x(p90) + 10, "start")
        s.append(f'<text x="{lx}" y="{y + 4}" text-anchor="{anc}" fill="#F2EBFA" font-weight="600">{sg(p50)}</text>')
    s.append("</svg>")
    return "".join(s)


def legislatura():
    filas = []
    nombres = {"A · Octubre 2025, derecha unida": "Octubre 2025 se repite",
               "C · Punto medio, derecha unida": "Punto medio septiembre-octubre",
               "B · Septiembre 2025, derecha unida": "Septiembre 2025 se repite",
               "A · Octubre 2025, derecha dividida (PRO 25 %)": "Octubre, derecha dividida (PRO 25 %)",
               "A · Octubre 2025, derecha dividida (PRO 52 %)": "Octubre, derecha dividida (PRO 52 %)"}
    for k, v in nombres.items():
        r = LG[(LG.escenario == k) & LG.bloque.str.contains("completa")].iloc[0]
        filas.append([v, f"{r.diputados_2027_p50:.0f}", f"{r.senadores_2027_p50:.0f}",
                      f"{100 * r.p_mayoria_senado:.0f} %"])
    return tabla(["Escenario", "Diputados peronistas (de 92)", "Senadores peronistas (de 46)",
                  "Mayoría propia en el Senado"], filas, "grande")


lam = base64.b64encode((ROOT / "03_OUTPUTS/laminas/03_escenarios_2027_municipio.png").read_bytes()).decode()

H = []
# ------------------------------------------------------------------ portada
H.append(pg("Portada", f"""
  <div style="height:3cm"></div>
  <div class="kicker">Informe 01 · Gobernador 2027</div>
  <h1>La Provincia no se gana en el mapa:<br>se gana con tres perillas.</h1>
  <div class="rule"></div>
  <p class="lead" style="max-width:20cm">
    Si en 2027 se repite el voto de octubre de 2025, la Gobernación es un <b>empate</b>: el
    peronismo gana el {A[3] * 100:.0f} % de las simulaciones, por {sg(A[1])} puntos. Lo que la define no es
    el territorio, que se reproduce con precisión, sino tres cosas: <b>el nivel provincial</b>,
    <b>si la derecha va unida</b> y <b>quién se suma a votar</b>.</p>
  <div style="height:.8cm"></div>
  <div class="cols3">
    <div><h3>Lo que sí dice</h3><p>Dado un resultado provincial, cuánto da cada municipio,
      sección y banca de la Legislatura, con un margen de error medido contra 13 elecciones.</p></div>
    <div><h3>Lo que no dice</h3><p>Cuánto va a sacar cada fuerza en la Provincia. Ese número lo
      ponen las encuestas: el pasado no lo anticipa.</p></div>
    <div><h3>Con qué está hecho</h3><p>Cada mesa de las elecciones 2011-2025, unos 1.000 circuitos
      cruzados con cuatro censos, los barrios populares, las escuelas y los centros de salud.</p></div>
  </div>"""))

# ------------------------------------------------------------------ en pocas palabras
H.append(pg("En pocas palabras", f"""
  <div class="kicker">01 · En pocas palabras</div>
  <h2>Todo el informe, en una hoja.</h2>
  <div class="rule"></div>
  <div class="tiles">
    <div class="tile"><div class="tn">{A[3] * 100:.0f} %</div><div class="tl">de las simulaciones gana el peronismo si se repite octubre 2025</div></div>
    <div class="tile"><div class="tn">2,7 pp</div><div class="tl">error medio por municipio del motor, dado el nivel provincial (13 elecciones)</div></div>
    <div class="tile"><div class="tn">9 pts</div><div class="tl">de margen mueve quién se suma a votar: de −3,7 a +5,4</div></div>
    <div class="tile"><div class="tn">99 %</div><div class="tl">gana el peronismo si la derecha va dividida, aunque el PRO sea el 15 % de ella</div></div>
  </div>
  <div style="height:.45cm"></div>
  <div class="cols2">
    <div>
      <h3>El mapa es previsible; el nivel, no</h3>
      <p>El motor reproduce cada municipio con 2,7 puntos de error y acierta el 89 % de los ganadores
      municipales. Pero de una legislativa a la Gobernación siguiente el margen se movió entre +2,5 y
      +19,8 puntos: ningún dato del pasado anticipa el nivel de 2027.</p>
      <h3>El voto que perdió Kicillof se abstuvo</h3>
      <p>El 12,6 % de sus votantes de 2023 no fue a votar en octubre de 2025, unos 513.000. Ninguno
      pasó a LLA-PRO. Es voto recuperable sin convencer a nadie de cambiar.</p>
      <h3>Más participación no alcanza: importa quién</h3>
      <p>Subir la participación de 64 % a 80 % con el mismo perfil mueve ±0,1 puntos. Según qué
      votante se sume, en cambio, el margen va de −3,7 a +5,4.</p>
    </div>
    <div>
      <h3>El Conurbano es otro nivel, no otra dinámica</h3>
      <p>Con la misma composición social vota entre 3,4 y 5,9 puntos más peronista que el interior,
      pero cambia igual: los movimientos de voto son provinciales.</p>
      <h3>El desdoblamiento lo explicó LLA-PRO creciendo</h3>
      <p>De septiembre a octubre sumó 957.000 votos, sobre todo de votantes de terceras fuerzas.
      Fuerza Patria perdió 140.000.</p>
      <h3>Legislatura: Diputados se escapa</h3>
      <p>En ningún escenario base el peronismo llega a 47 diputados (queda entre 41 y 44). El Senado
      lo retiene salvo que se repita octubre.</p>
    </div>
  </div>"""))

# ------------------------------------------------------------------ método
H.append(pg("Datos y método", f"""
  <div class="kicker">02 · Datos y método</div>
  <h2>Mil circuitos, quince años, y cuatro filtros<br>antes de dar algo por probado.</h2>
  <div class="rule"></div>
  <div class="cols2">
    <div>
      {tabla(["Fuente", "Qué aporta", "Escala"], [
          ["Dirección Nacional Electoral", "Escrutinio 2011-2025, mesas de nativos y de extranjeros", "Mesa → circuito"],
          ["Junta Electoral PBA", "Elección provincial del 7 de septiembre de 2025", "Municipio"],
          ["INDEC", "Censos 1991, 2001, 2010 y 2022", "Radio → circuito"],
          ["RENABAP", "2.065 barrios populares, familias y servicios", "Polígono → circuito"],
          ["DGCyE y Salud PBA", "21.592 escuelas y 3.052 centros de salud públicos", "Punto → circuito"]], "media")}
      <div style="height:.35cm"></div>
      <p><b>Circuitos estables.</b> Los circuitos se crean, se parten y se fusionan entre elecciones.
      Para comparar en el tiempo se agrupan en circuitos que conservan el mismo territorio en cada
      período: entre 969 y 997 según la ventana.</p>
    </div>
    <div>
      <h3>Cuándo algo está probado</h3>
      <ul>
        <li><b>Composición controlada:</b> correlación de rangos parcial, descontando necesidades básicas,
          educación, edad y el voto de partida.</li>
        <li><b>Pruebas múltiples:</b> corrección de Benjamini-Hochberg sobre toda la batería, no prueba por prueba.</li>
        <li><b>Fragilidad:</b> el resultado se mantiene sacando la unidad más influyente y las tres más influyentes.</li>
        <li><b>Robustez espacial:</b> se mantiene con un modelo de error espacial, porque los lugares vecinos
          se parecen y eso infla la significación.</li>
      </ul>
      <div style="height:.25cm"></div>
      <div class="caja"><p style="margin:0">Las predicciones se validan fuera de muestra, dejando municipios
      enteros afuera. <b>Los resultados negativos se publican igual</b>: lo que se probó y no está ahorra
      tiempo y evita decisiones sobre supuestos falsos.</p></div>
    </div>
  </div>"""))

# ------------------------------------------------------------------ territorio
H.append(pg("Conurbano e interior", """
  <div class="kicker">03 · Conurbano, interior e intendentes</div>
  <h2>El Conurbano vota más peronista, pero se mueve<br>igual que el interior.</h2>
  <div class="rule"></div>
  <div class="cols2">
    <div>
      <p>Con la misma composición social, el Conurbano vota entre <b>+5,6 y +6,6 puntos</b> más peronista
      que el interior según la elección, y entre +3,4 y +5,9 con el modelo de error espacial. La brecha
      bruta es de 8 a 10 puntos: la composición social explica cerca de un tercio y la urbanización otro
      quinto. Sacando cualquier municipio, el efecto nunca baja de +5,1.</p>
      <p>La diferencia es de <b>nivel, no de dinámica</b>. Con la composición controlada, el Conurbano y el
      interior cambian de voto igual: ninguna diferencia en el cambio pasa la corrección, y la mayor es de
      0,9 puntos. Entre 2019 y 2023 el peronismo perdió 8,1 puntos en el Conurbano y 7,3 en el interior.</p>
      <div class="caja"><p style="margin:0"><b>Para la campaña:</b> una estrategia «para el interior»
      y otra «para el Conurbano» no tienen sustento en cómo cambia el voto. El movimiento es provincial;
      lo territorial es el punto de partida.</p></div>
    </div>
    <div>
      <h3>Los intendentes no arrastran al gobernador</h3>
      <p>En 267 elecciones municipales definidas por menos de 10 puntos, ganar la intendencia no mueve el
      voto a Gobernador de la elección siguiente: <b>−0,2 puntos</b> (intervalo −4,4 a +4,0). Sí da ventaja
      para retenerla: +7,4 puntos, y +10,6 para el peronismo.</p>
      <h3>El arrastre va de arriba hacia abajo</h3>
      <ul>
        <li>Los intendentes peronistas sacaron 4 a 8 puntos menos que Scioli (2007, 2011), y los de
          Cambiemos 6 a 7 menos que Vidal (2015).</li>
        <li>El intendente ganador saca cada vez más que su gobernador: el 87 % en 2023 (mediana +6,9
          puntos), contra el 54 % en 2011.</li>
        <li>LLA no tenía estructura local en 2023: sus candidatos a intendente sacaron 8,8 puntos menos
          que Píparo en el interior.</li>
        <li>El corte de boleta es del interior: 8,8 puntos de corte mediano contra 3,1 en el Conurbano.</li>
      </ul>
    </div>
  </div>"""))

# ------------------------------------------------------------------ 2023-2025
H.append(pg("De 2023 a 2025", f"""
  <div class="kicker">04 · De 2023 a 2025</div>
  <h2>Kicillof no perdió votantes hacia la derecha:<br>los perdió hacia la abstención.</h2>
  <div class="rule"></div>
  <div class="cols2">
    <div>
      <p>Gobernador 2023 contra Diputados de octubre 2025, en 997 circuitos estables. Dónde fue cada
      votante de 2023:</p>
      {tabla(["Votantes de 2023", "Fuerza Patria", "LLA-PRO", "Prov. Unidas", "Otras, blanco y nulo", "No votó"], [
          ["__hi__", "Kicillof (peronismo)", "82,2 %", "0 %", "0 %", "5,3 %", "12,6 %"],
          ["Santilli (JxC)", "5,8 %", "77,4 %", "7,1 %", "6,8 %", "3,0 %"],
          ["Píparo (LLA)", "0 %", "70,2 %", "0 %", "8,1 %", "21,7 %"]], "grande")}
      <p class="nota" style="margin-top:.2cm">Inferencia ecológica por circuito, validada fuera de muestra. Intervalos 5-95 por remuestreo de
      municipios: Kicillof → Fuerza Patria 79 a 84 %; Píparo → no votó 15 a 29 %.</p>
      <p>El voto de LLA-PRO de 2025 viene 54 % de Santilli y 45 % de Píparo: es más Juntos por el Cambio
      que LLA. Provincias Unidas es una escisión de JxC: el 83 % de su voto viene de Santilli.</p>
    </div>
    <div>
      <h3>El desdoblamiento: LLA-PRO creció, Fuerza Patria no cayó</h3>
      <p>De septiembre (provincial) a octubre (nacional) 2025, Fuerza Patria pasó de 13 puntos arriba a un empate.</p>
      <ul>
        <li>LLA-PRO sumó <b>957.000 votos</b> (2,65 → 3,61 millones); Fuerza Patria perdió 140.000 (3,70 → 3,56).</li>
        <li>Creció con los que en septiembre votaron a terceros: el 64 % de Provincias Unidas, el 51 % de otras
          listas y el 49 % del blanco y nulo.</li>
        <li>Los 540.000 nativos que se sumaron en octubre no fueron a LLA-PRO: donde subió la participación
          mejoró Fuerza Patria.</li>
        <li>Fuerza Patria cayó donde gobierna un intendente peronista: −1,8 puntos del padrón, contra +1,2 donde no.</li>
        <li>LLA-PRO creció más en el interior (+9 a +11 puntos del padrón) que en el Conurbano (+5,3).</li>
        <li>El voto extranjero no explica la diferencia: sacarlo mueve la brecha de septiembre de 13,6 a 13,3.</li>
      </ul>
    </div>
  </div>"""))

# ------------------------------------------------------------------ territorio y voto
H.append(pg("Territorio y voto", f"""
  <div class="kicker">05 · Qué dice el territorio del voto</div>
  <h2>El censo dice dónde vota fuerte cada uno.<br>Del cambio dice poco.</h2>
  <div class="rule"></div>
  <div class="cols2">
    <div>
      {tabla(["Qué se predice (R² fuera de muestra)", "Elección anterior", "Sólo censo", "Censo + anterior"], [
          ["Nivel de voto de cada fuerza", "0,89-0,96", "0,62-0,80", "0,90-0,96"],
          ["Participación (presidencial → legislativa)", "0,28", "—", "0,54"]], "media")}
      <div style="height:.25cm"></div>
      <p>La elección anterior predice mejor que el perfil social: el motor 2027 parte del último resultado
      de cada circuito. El cambio de voto es sobre todo <b>proporcional al nivel de partida</b>. Más allá
      de eso, los rasgos del territorio asociados al cambio son pocos y chicos (ninguno supera 0,28):</p>
      <ul>
        <li><b>2011-2023:</b> el peronismo cayó más donde más se extendió el gas de red (−0,24 en Gobernador, −0,28 en Diputados).</li>
        <li><b>2023-2025:</b> la participación cayó más en lo rural y con menos educación.</li>
        <li><b>2023-2025:</b> LLA-PRO avanzó relativamente en circuitos con más necesidades de vivienda y hogares
          migrantes; el peronismo resistió en lo rural y entre jubilados.</li>
      </ul>
    </div>
    <div>
      <h3>Barrios populares: el avance de LLA-PRO se confirma</h3>
      <p>El 9,7 % de los hogares de la Provincia vive en uno de los 2.065 barrios del RENABAP (34 % en
      Presidente Perón, 22 % en Berisso y Lomas de Zamora). Con una fuente que no sale del censo, el dato
      confirma el avance de LLA-PRO entre 2023 y 2025:</p>
      {tabla(["Prueba", "Parcial", "Con densidad", "Error espacial"], [
          ["__hi__", "Barrios populares → avance LLA-PRO", "+0,12", "+0,11", "resiste"],
          ["__hi__", "Barrios populares → caída del peronismo", "−0,16", "−0,11", "resiste"],
          ["Barrios populares → participación", "+0,19", "+0,01", "—"],
          ["Escuelas y salud por habitante (6 pruebas)", "hasta ±0,22", "< 0,06", "—"]], "media")}
      <p class="nota" style="margin-top:.2cm">Escuelas y salitas por habitante parecían asociarse al cambio, pero era
      ruralidad: en los pueblos chicos hay más por habitante. Con la densidad controlada desaparecen.</p>
    </div>
  </div>"""))

# ------------------------------------------------------------------ motor
H.append(pg("El motor 2027", f"""
  <div class="kicker">06 · El motor 2027</div>
  <h2>Sólo con la derecha unida y el voto de octubre<br>la elección queda abierta.</h2>
  <div class="rule"></div>
  <div class="cols2" style="gap:.8cm">
    <div style="flex:.8">
      <p>El motor no adivina el nivel provincial: lo toma como dato y lo baja al territorio con un error
      calibrado. Dado el nivel, reproduce el mapa: en 13 pares de elecciones 2011-2025 erró
      <b>2,7 puntos por municipio</b> (12,4 sin ajustar) y acertó el 89 % de los ganadores municipales y
      el 97 % de las secciones.</p>
      <ul>
        <li><b>Quién se suma decide una elección abierta:</b> con octubre y la derecha unida, de −3,7 a +5,4
          según el perfil del que se sume.</li>
        <li><b>La derecha dividida pierde aunque el PRO sea chico:</b> con el PRO en el 10 % de la derecha, el
          peronismo puede ceder unos 4 puntos y seguir primero; con el 20 %, unos 10; con el 30 %, unos 15.</li>
        <li><b>El mapa favorece a la derecha:</b> con empate, el peronismo gana 40 de 135 municipios y necesita
          +4 para la mitad. La 3ª sección la gana siempre; la 1ª, en el 72 % de los empates.</li>
        <li><b>Padrón nuevo y extranjeros</b> suman menos de un punto: llevan el margen de octubre de −0,6 a +0,3.</li>
      </ul>
    </div>
    <div style="flex:1.2">
      <h3>Margen del peronismo sobre el segundo, en puntos</h3>
      {grafico_escenarios()}
      <p class="nota">Mediana y rango que contiene 8 de cada 10 de las 1.000 simulaciones. En magenta, los escenarios en
      que el peronismo puede perder. Derecha unida salvo donde se indica. Análisis 106, 107 y 109.</p>
    </div>
  </div>"""))

H.append(pg("El motor 2027", f"""
  <div class="kicker">07 · El mapa de los escenarios</div>
  <h2>Del empate a +13: dónde gana el peronismo en cada caso.</h2>
  <div class="rule"></div>
  <div style="background:#fff;border-radius:4px;padding:.25cm">
    <img src="data:image/png;base64,{lam}" style="width:100%;display:block"></div>
  <p class="nota" style="margin-top:.2cm">Probabilidad de que el peronismo salga primero en cada municipio, con la derecha unida. Los escenarios
  se pueden recorrer con perillas en el simulador: {SIMULADOR}</p>"""))

# ------------------------------------------------------------------ legislatura
H.append(pg("Legislatura", f"""
  <div class="kicker">08 · La Legislatura 2027-2029</div>
  <h2>Diputados se le escapa al peronismo en todos los escenarios;<br>el Senado, sólo si se repite octubre.</h2>
  <div class="rule"></div>
  <div class="cols2">
    <div style="flex:1.3">
      {legislatura()}
      <p class="nota" style="margin-top:.2cm">Cámara completa: electos en 2027 (mediana de las simulaciones) más los electos en 2025, que
      siguen hasta 2029. Mayoría: 47 diputados, 24 senadores.</p>
    </div>
    <div>
      <p>La Legislatura se renueva por mitades y cada sección alterna cámara. En 2027 eligen
      <b>diputados la 1ª, 4ª, 5ª y 7ª</b>, las más disputadas o favorables a la derecha, y senadores la
      2ª, 3ª, 6ª y 8ª.</p>
      <p>Las bancas se reparten por cociente (Ley 5.109): la lista que no llega al cociente queda afuera.
      Aplicada a 2025, la regla reproduce el escrutinio publicado banca por banca.</p>
      <div class="caja"><p style="margin:0">Con 23 senadores, el empate lo desempata el vicegobernador.
      Diputados sólo llega a 47 con el voto de septiembre más una movilización peronista fuerte.</p></div>
    </div>
  </div>"""))

# ------------------------------------------------------------------ robustez
H.append(pg("Lo que no se sostuvo", f"""
  <div class="kicker">09 · Lo que resiste y lo que no</div>
  <h2>Casi todo resiste la corrección espacial.<br>Y varias ideas instaladas no están en los datos.</h2>
  <div class="rule"></div>
  <div class="cols2">
    <div style="flex:.75">
      <p>Los lugares vecinos se parecen, y eso hace que una correlación parezca más firme de lo que es.
      Con un modelo de error espacial se sostienen las <b>3</b> pruebas del efecto Conurbano, <b>67 de 91</b>
      sobre territorio y cambio (con efectos a la mitad) y <b>7 de 8</b> del desdoblamiento.</p>
      <p>El error del motor también se agrupa por sección electoral, y el motor lo sortea así: no cambia el
      resultado provincial pero hace más inciertas las secciones (la 1ª, con empate, pasa de 92 % a 72 %
      peronista).</p>
    </div>
    <div style="flex:1.25">
      {tabla(["Lo que se suele decir", "Lo que dicen los datos"], [
          ["Ganar la intendencia arrastra votos al gobernador", "No: −0,2 puntos (−4,4 a +4,0) en elecciones reñidas"],
          ["El Conurbano tiene una dinámica de cambio propia", "No: con la composición controlada cambia igual que el interior"],
          ["Los que no votaron en septiembre fueron a Milei", "No: donde subió la participación mejoró Fuerza Patria"],
          ["Escuelas y salud explican el cambio de voto", "No: era ruralidad; con densidad controlada desaparece"],
          ["Los barrios populares nuevos explican la caída peronista 2011-2023", "No: sin asociación"],
          ["El voto vecinal de septiembre empujó a LLA-PRO", "En el borde: no resiste la corrección espacial"],
          ["Vivienda, computadora y agua de red explican el cambio 2011-2023", "No resisten la corrección espacial (el agua, sólo en Gobernador)"]], "media txt")}
    </div>
  </div>"""))

# ------------------------------------------------------------------ limitaciones
H.append(pg("Limitaciones", f"""
  <div class="kicker">10 · Limitaciones y próximos pasos</div>
  <h2>El motor dice qué pasa dado un nivel provincial.<br>El nivel lo tienen que dar las encuestas.</h2>
  <div class="rule"></div>
  <div class="cols2">
    <div>
      <h3>Límites</h3>
      <ul>
        <li><b>Inferencia ecológica:</b> transferencias y perfiles de movilización salen de comparar circuitos,
          no personas. Están validadas fuera de muestra, pero no son una encuesta de panel.</li>
        <li><b>Escala:</b> el circuito es la unidad más fina disponible. Bajar a la escuela requiere el listado
          de locales de votación, que no es público.</li>
        <li><b>Septiembre 2025 sólo por municipio:</b> no hay resultados provinciales públicos por mesa; se bajó
          a circuito con el patrón de octubre.</li>
        <li><b>Derecha dividida:</b> calibrada con un solo par de elecciones (2021-2023).</li>
        <li><b>Sin balotaje ni candidatos:</b> el motor trabaja con bloques, no modela campaña.</li>
      </ul>
    </div>
    <div>
      <h3>Próximos pasos</h3>
      <ul>
        <li>Cargar las encuestas 2026-2027 como nivel provincial del motor.</li>
        <li>Sumar la movilización diferencial al simulador.</li>
        <li>Presentar el pedido de acceso a la información por los locales de votación (Junta Electoral PBA
          y Dirección Nacional Electoral) y rehacer el análisis por escuela.</li>
      </ul>
      <div style="height:.3cm"></div>
      <h3>Fuentes y reproducibilidad</h3>
      <p>Dirección Nacional Electoral (escrutinio por mesa 2011-2025), Junta Electoral PBA (septiembre 2025),
      INDEC (censos 1991-2022), RENABAP, DGCyE y Ministerio de Salud PBA.</p>
      <p class="dim">Cada número tiene su script y su tabla en el repositorio: {REPO}
      (índice en 00_DOCS/HALLAZGOS.md). Simulador: {SIMULADOR}</p>
    </div>
  </div>"""))

HTML.write_text('<!doctype html><html lang="es"><head><meta charset="utf-8">'
                f'<title>Atlas PBA · Hallazgos rumbo a 2027</title><style>{CSS}'
                '.txt th, .txt td { text-align: left; }</style>'
                '</head><body>' + "\n".join(H) + '</body></html>', encoding="utf-8")
print(f"  {folio[0]} hojas · {HTML.relative_to(ROOT)} · {HTML.stat().st_size / 1024:.0f} KB")

# ------------------------------------------------------------------ PDF
tmp = Path(tempfile.gettempdir())
h, out, perfil = tmp / "_atlas_pba_r01.html", tmp / "_atlas_pba_r01.pdf", tmp / "_perfil_atlas_pba_r01"
shutil.copy2(HTML, h)
out.unlink(missing_ok=True)
shutil.rmtree(perfil, ignore_errors=True)
subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-sandbox", "--no-first-run", "--no-pdf-header-footer",
                "--run-all-compositor-stages-before-draw", "--virtual-time-budget=30000",
                f"--user-data-dir={perfil}", f"--print-to-pdf={out}", h.as_uri()],
               capture_output=True, timeout=600)
shutil.rmtree(perfil, ignore_errors=True)
if not out.exists():
    raise RuntimeError("Chrome no escribió el PDF")
with fitz.open(out) as d:
    if d.page_count != folio[0]:
        raise RuntimeError(f"el PDF tiene {d.page_count} páginas y el HTML {folio[0]} hojas: algo desborda")
PDF.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(out, PDF)
out.unlink(missing_ok=True)
h.unlink(missing_ok=True)
print(f"-> {PDF.relative_to(ROOT)} · {PDF.stat().st_size / 1048576:.1f} MB")
