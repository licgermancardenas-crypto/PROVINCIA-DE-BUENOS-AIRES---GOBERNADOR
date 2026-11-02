# -*- coding: utf-8 -*-
"""
ATLAS ANALYTICS - PROVINCIA DE BUENOS AIRES
El estilo de casa de los informes, copiado del Atlas CABA (`02_SCRIPTS/analisis/_estilo.py` de ese
repositorio) para que los entregables de los dos proyectos se vean iguales. Si cambia allá, se copia
de nuevo; no se importa entre repositorios.

La caja es apaisada 29,7 x 21 cm, que es lo que Chrome headless respeta sin pelear. Los comentarios
de adentro del CSS son historia del proyecto CABA: explican por qué cada medida es la que es.
"""

CSS = """
@page { size: 29.7cm 21cm; margin: 0; }
* { box-sizing: border-box; margin: 0; padding: 0; }
/* Segoe UI trae familia completa de pesos y cifras tabulares, que es lo que hace
   que las columnas de numeros alineen. Arial no las tiene. */
body { font-family: "Segoe UI", Arial, sans-serif; background: #12042E; color: #F2EBFA;
       font-variant-numeric: tabular-nums; -webkit-font-feature-settings: "tnum" 1; }
.pg { width: 29.7cm; height: 21cm; page-break-after: always; position: relative;
      padding: 1.35cm 1.7cm 1.55cm; overflow: hidden; background: #12042E; }
.pg:last-child { page-break-after: auto; }
/* El pie es una franja propia al pie de la hoja: antes marca y folio iban
   absolutos y el contenido largo se les montaba encima. */
.corriente { position: absolute; left: 1.7cm; right: 1.7cm; top: .72cm;
             display: flex; justify-content: space-between; font-size: 6.6pt;
             letter-spacing: .16em; color: #4E3A78; text-transform: uppercase; }
.pie { position: absolute; left: 1.7cm; right: 1.7cm; bottom: .62cm; height: .5cm;
       display: flex; align-items: center; justify-content: space-between;
       border-top: 1px solid #2A1750; padding-top: .16cm; }
.marca { font-size: 7.2pt; letter-spacing: .2em; color: #C40BFF; font-weight: bold; }
.sec { font-size: 7.2pt; letter-spacing: .12em; color: #6b5a8c; text-transform: uppercase; }
.folio { font-size: 8pt; color: #A08FC2; font-weight: bold; }
/* padding .05 -> .025: al sumar las dos láminas nuevas al bloque "Láminas de
   análisis" el índice creció 44 px dentro de la franja del pie. Se baja el ritmo
   de fila, nunca el cuerpo: los 8,2 pt quedan como estaban. */
.ix { display: flex; justify-content: space-between; align-items: baseline;
      font-size: 8.2pt; color: #DCD2EA; padding: .025cm 0;
      border-bottom: 1px solid #241246; gap: .3cm; }
/* El bloque de láminas va en tres columnas y la fila queda angosta: con el
   cuerpo de 8,2 pt el nombre se corta antes de terminar la palabra.
   El padding va más apretado que el de `.ix` general porque cada folio nuevo
   suma una fila acá: se baja el ritmo vertical, nunca el cuerpo.
   Segunda vuelta: con los folios del benchmark nacional, el backtest y el
   multinivel el índice volvió a rozar el pie por 15 px, y el padding bajó de
   .012 a .004. Si vuelve a pasar, lo que hay que partir es la lista en dos
   hojas, no seguir apretando. */
.ix3 .ix { font-size: 7.4pt; gap: .18cm; padding: .004cm 0; }
.ix span:first-child { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ixp { color: #C40BFF; font-weight: bold; flex: none; }
.kicker { font-size: 8pt; letter-spacing: .22em; color: #C40BFF; font-weight: bold;
          text-transform: uppercase; margin-bottom: .3cm; }
h1 { font-size: 30pt; line-height: 1.04; letter-spacing: -.025em; font-weight: 600;
     margin-bottom: .35cm; }
h2 { font-size: 18pt; line-height: 1.11; letter-spacing: -.018em; font-weight: 600;
     margin-bottom: .22cm; }
h3 { font-size: 9.5pt; color: #E9B6FF; margin-bottom: .14cm; letter-spacing: .01em; }
p  { font-size: 9.4pt; line-height: 1.5; color: #DCD2EA; margin-bottom: .21cm; }
.lead { font-size: 12pt; line-height: 1.45; color: #F2EBFA; }
.dim { color: #A08FC2; }
.rule { height: 2px; background: #C40BFF; width: 2.4cm; margin: .24cm 0 .3cm; }
.cols2 { display: flex; gap: 1cm; } .cols2 > * { flex: 1; }
.cols3 { display: flex; gap: .7cm; } .cols3 > * { flex: 1; }
table { width: 100%; border-collapse: collapse; font-size: 8pt;
        font-variant-numeric: tabular-nums; }
th { text-align: right; padding: .11cm .18cm; color: #A08FC2; font-weight: normal;
     border-bottom: 1px solid #3D2A63; font-size: 7.2pt; }
th:first-child, td:first-child { text-align: left; }
td { padding: .09cm .18cm; border-bottom: 1px solid #241246; text-align: right; }
tr:last-child td { border-bottom: none; }
.hi td { background: #1F0A47; color: #F2EBFA; font-weight: bold; }
table.mini { font-size: 6.9pt; }
table.media { font-size: 8.4pt; }
table.media th { font-size: 7.6pt; padding: .16cm .2cm; }
table.media td { padding: .125cm .2cm; }
table.grande { font-size: 8.6pt; }
table.grande th { font-size: 7.4pt; padding: .14cm .22cm; line-height: 1.25;
                  vertical-align: bottom; }
table.grande td { padding: .13cm .22cm; white-space: nowrap; }
table.loc { font-size: 7.8pt; }
table.loc th { font-size: 7pt; padding: .13cm .14cm; }
table.loc td { padding: .06cm .14cm; white-space: nowrap; }
table.loc td:nth-child(2), table.loc td:nth-child(3) { white-space: normal; }
table.mini th { font-size: 6.3pt; padding: .085cm .1cm; }
table.mini td { padding: .065cm .1cm; }
.caja { background: #1B0A3D; border-radius: 4px; padding: .34cm .44cm; }
.nota { font-size: 7.2pt; color: #8A7AAB; line-height: 1.4; }
ul { margin-left: .42cm; }
li { font-size: 8.6pt; line-height: 1.36; color: #DCD2EA; margin-bottom: .075cm; }
.tiles { display: flex; gap: .45cm; }
.tile { flex: 1; border-radius: 5px; padding: .32cm .4cm; background: #1B0A3D; }
.tile .tn { font-size: 19.5pt; font-weight: 600; line-height: 1; letter-spacing: -.025em;
             font-variant-numeric: tabular-nums; }
.tile .tl { font-size: 7.4pt; color: #A08FC2; margin-top: .14cm; line-height: 1.3; }
.splitbar { display: flex; height: .95cm; border-radius: 3px; overflow: hidden; margin-top: .22cm; }
.splitbar > div { display: flex; align-items: center; justify-content: center;
                  font-size: 6.5pt; font-weight: bold; color: #12042E; text-align: center;
                  line-height: 1.15; }
.bar { display: flex; height: .55cm; border-radius: 2px; overflow: hidden; margin: .12cm 0; }
.bar > div { font-size: 6pt; color: #12042E; font-weight: bold; text-align: center;
             line-height: .55cm; overflow: hidden; }
.sw { display:inline-block; width:.28cm; height:.28cm; border-radius:2px;
      vertical-align:-.03cm; margin-right:.12cm; }
.hero-num { font-size: 84pt; font-weight: bold; line-height: .92; letter-spacing: -.03em;
            color: #C40BFF; }
.card { background: #1B0A3D; border-radius: 5px; padding: .34cm .42cm; height: 100%; }
.card .cn { font-size: 12.5pt; font-weight: bold; letter-spacing: -.02em; line-height: 1.1; }
.card .cc { font-size: 7pt; color: #A08FC2; letter-spacing: .1em; text-transform: uppercase;
            margin-bottom: .18cm; }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr;
         gap: .45cm; height: 16.9cm; margin-top: .25cm; }
.card { overflow: hidden; }
.card table.mini { font-size: 6.2pt; }
.card table.mini th { font-size: 5.7pt; padding: .055cm .05cm; }
.card table.mini td { padding: .05cm .05cm; }
.card .kv { padding: .05cm 0; font-size: 7.1pt; }
.kv { display: flex; justify-content: space-between; font-size: 7.2pt; color: #A08FC2;
      border-bottom: 1px solid #241246; padding: .036cm 0; }
.kv b { color: #F2EBFA; font-weight: bold; }
.tag { display: inline-block; font-size: 6.8pt; letter-spacing: .1em; text-transform: uppercase;
       color: #12042E; background: #C40BFF; padding: .05cm .2cm; border-radius: 2px;
       font-weight: bold; }
"""
