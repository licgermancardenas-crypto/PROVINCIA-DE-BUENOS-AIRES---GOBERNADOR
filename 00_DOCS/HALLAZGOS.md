# Índice de hallazgos

La bitácora (`00_DOCS/README.md`) está ordenada por **cuándo** se hizo cada cosa. Este documento
la ordena por **qué dice**. Un hallazgo entra acá sólo si se puede señalar el script que lo
produjo y la tabla donde está el número.

| Estado | Qué significa |
|---|---|
| **PROBADO** | Pasa la prueba que corresponde a su diseño (Spearman parcial con control de composición, o un diseño causal con su placebo), Benjamini-Hochberg sobre la batería y la prueba de fragilidad. |
| **DESCRIPTIVO** | Vale como descripción, no como prueba: una cuenta sin contrafáctico. |
| **REFUTADO** | Se probó y no está. Se publica para que nadie lo vuelva a intentar. |

---

## 1 · Intendentes y Gobernador

| Hallazgo | Magnitud | Estado | Script | Tabla |
|---|---|---|---|---|
| Ganar la intendencia **no** mueve el voto a Gobernador de la elección siguiente | −0,2 pp (IC −4,4 a +4,0), 267 municipios-elección con margen de ±10 pp; placebo limpio | REFUTADO (el arrastre de la intendencia) | `100` | `arrastre_rd.csv` |
| Ganar la intendencia sí da ventaja para retenerla | +7,4 pp en Intendente (q = 0,03); peronismo +10,6 pp (q = 0,002); PRO/JxC +2,2 pp, no significativo | PROBADO | `100` | `arrastre_rd.csv` |
| El arrastre va de arriba hacia abajo: lo pone el candidato a gobernador fuerte | Intendentes peronistas 4-8 pp debajo de Scioli (2007, 2011); de Cambiemos 6-7 pp debajo de Vidal (2015) | DESCRIPTIVO | `100` | `arrastre_brecha_espacio.csv` |
| En 2023 LLA no tenía estructura local | Su lista a intendente sacó 8,8 pp menos que Píparo en el interior y 2,9 en el Conurbano; peronismo y JxC retuvieron por encima de su gobernador (+3,6 y +5,0 en el interior) | DESCRIPTIVO | `100` | ídem |
| El intendente que gana casi siempre saca más que su gobernador, y cada vez más | 87 % de los ganadores en 2023 (mediana +6,9 pp), contra 54 % en 2011 | DESCRIPTIVO | `100` | `arrastre_brecha_resumen.csv` |
| El corte de boleta es un fenómeno del interior | Corte pareado mediano 2023: interior 8,8, Conurbano 3,1. En el Conurbano bajó todas las elecciones (6,2 → 5,5 → 3,7 → 3,1) | DESCRIPTIVO (es un piso) | `100` | `corte_boleta_resumen.csv` |
| En uno de cada cinco municipios, Intendente y Gobernador los gana un espacio distinto | 25 en 2023, 31 en 2019, 51 en 2015 | DESCRIPTIVO | `100` | `arrastre_brecha_resumen.csv` |

## 2 · Conurbano e interior

| Hallazgo | Magnitud | Estado | Script | Tabla |
|---|---|---|---|---|
| Con la misma composición social, el Conurbano vota más peronista | +5,6 a +6,6 pp según la elección (brecha bruta +8,0 a +10,2); +4,0 a +4,9 controlando además la urbanización. Sacando cualquier municipio, nunca baja de +5,1 | PROBADO (6 elecciones, q < 0,01, fragilidad) | `101` | `conurbano_interior_brecha.csv` |
| La composición explica cerca de un tercio de la brecha; la urbanización, otro quinto | De +10,2 a +6,0 y a +4,2 pp (Diputados 2019) | DESCRIPTIVO | `101` | ídem |
| Para predecir, la zona casi no agrega si se tiene el perfil censal | R² fuera de muestra (por municipio) 0,60-0,86; sumar la zona lo mejora 0,01-0,03 con modelo lineal y nada con árboles | PROBADO (GroupKFold) | `101` | `conurbano_interior_oos.csv` |
| Los cambios de voto son provinciales: el Conurbano y el interior se mueven igual | Con composición controlada, ninguna brecha en el cambio pasa Benjamini-Hochberg con urbanización (máximo 0,9 pp) | REFUTADO (la «dinámica propia» del Conurbano) | `101` | `conurbano_interior_brecha.csv` |
| El cambio es mucho más parejo que el nivel | Peronismo: dispersión entre circuitos de 10 pp en el nivel y de 3-4 pp en el cambio. 2019→2023: −8,1 Conurbano, −7,3 interior | DESCRIPTIVO | `101` | `conurbano_interior_base.csv` |

## 3 · Transferencias 2023 → 2025

Gobernador 2023 (sólo mesas de nativos) contra Diputados Nacionales octubre 2025, 997 circuitos
estables. Entre paréntesis, intervalo 5-95 por remuestreo de municipios.

| Hallazgo | Magnitud | Estado | Script | Tabla |
|---|---|---|---|---|
| Fuerza Patria es el votante de Kicillof que fue a votar | 82 % (79-84) de los votantes de Kicillof la votaron; son el 96 % de su voto | PROBADO (error fuera de muestra la mitad que la predicción ingenua; cota superior Duncan-Davis 85,5 %) | `102` | `transferencias_2023_2025_matriz.csv` |
| La pérdida de Kicillof fue abstención, no pase a otro espacio | 12,6 % (10-16) no fue a votar: ~513.000 votos; a LLA-PRO, 0 | PROBADO (ídem) | `102` | ídem |
| La alianza LLA-PRO retuvo a casi todo Santilli | 77 % (75-79) del voto de JxC 2023; 7 % (6-8) a Provincias Unidas y 6 % (2-8) a Fuerza Patria | PROBADO (ídem; Duncan-Davis: Santilli → Provincias Unidas ≤ 8,5 %) | `102` | ídem |
| El voto de LLA-PRO es más JxC que LLA | 54 % viene de Santilli y 45 % de Píparo | DESCRIPTIVO | `102` | ídem |
| El votante de Píparo fue el que más se abstuvo | 22 % (15-29) no fue a votar, contra 13 % de Kicillof y 3 % de Santilli | PROBADO (ídem) | `102` | ídem |
| Provincias Unidas es una escisión de JxC | 83 % de su voto viene de Santilli | DESCRIPTIVO | `102` | ídem |

## 4 · El desdoblamiento de 2025

Septiembre (provincial) contra octubre (nacional), 135 municipios. Septiembre llevado a «sólo
nativos» descontando la parte extranjera estimada.

| Hallazgo | Magnitud | Estado | Script | Tabla |
|---|---|---|---|---|
| El padrón extranjero no explica la diferencia | Sacarlo baja a Fuerza Patria de 47,4 % a 46,9 % en septiembre; la brecha con LLA-PRO pasa de 13,6 a 13,3 pp | DESCRIPTIVO | `103` | `desdoblamiento_resumen.csv` |
| El cambio fue LLA-PRO creciendo, no Fuerza Patria cayendo | LLA-PRO +957.000 votos (2,65 M → 3,61 M); Fuerza Patria −140.000 (3,70 M → 3,56 M); fueron a votar 540.000 nativos más | DESCRIPTIVO | `103` | ídem |
| LLA-PRO creció con los que en septiembre votaron a terceros | 64 % (56-69) de Provincias Unidas, 51 % (43-56) de otros y 49 % (41-59) de blanco y nulo fueron a LLA-PRO; además 10 % (7-14) de Fuerza Patria | PROBADO (fuera de muestra: 0,90 pp contra 2,07 de la ingenua) | `103` | `desdoblamiento_matriz.csv` |
| Fuerza Patria cayó donde gobierna un intendente peronista | Cambio en su voto: −1,8 pp del padrón con intendente peronista, +1,2 sin él. Spearman parcial −0,34 controlando composición y zona | PROBADO (q < 0,001, sobrevive sacando los 3 más influyentes) | `103` | `desdoblamiento_correlatos.csv` |
| LLA-PRO creció más en el interior | Spearman parcial −0,49 con Conurbano (+5,3 pp del padrón en el Conurbano, +9 a +11 en el interior) | PROBADO | `103` | ídem |
| Donde había voto vecinal en septiembre, en octubre ganaron los dos grandes | Spearman parcial +0,23 (LLA-PRO) y +0,32 (Fuerza Patria) con el voto vecinal a concejales | PROBADO | `103` | ídem |
| La mayor participación de octubre no fue a LLA-PRO | Cambio de participación contra cambio de LLA-PRO: −0,09 (no pasa); contra Fuerza Patria: +0,31 | PROBADO (la segunda); REFUTADO («los que no votaron en septiembre fueron a Milei») | `103` | ídem |

## 5 · Lo que el territorio predice y lo que no

Circuitos estables (997 recientes, 918 de largo plazo). R² fuera de muestra con validación agrupada
por municipio.

| Hallazgo | Magnitud | Estado | Script | Tabla |
|---|---|---|---|---|
| El nivel de voto lo predice la elección anterior; el censo casi no agrega | Inercia 0,89-0,96; censo solo 0,62-0,80; censo + inercia 0,90-0,96 (+0,005 a +0,016) | PROBADO (GroupKFold) | `104` | `territorio_prediccion.csv` |
| La participación es la excepción | Inercia 0,28 (de una presidencial a una de medio término); censo + inercia 0,54 | PROBADO | `104` | ídem |
| El cambio de voto es sobre todo proporcional al nivel de partida | Peronismo 2023-2025: nivel inicial 0,16, + censo 0,19. Captura de LLA-PRO: 0,50 y 0,56. Gobernador 2019-2023: 0,45 y 0,59 | PROBADO | `104` | ídem |
| A diferencia de CABA, el cambio no es impredecible: es proporcional | En CABA la retención del PRO dio R² validado negativo; acá el nivel de partida solo explica entre 0,16 y 0,50 | DESCRIPTIVO (comparación entre proyectos) | `104` | ídem |
| Más allá del nivel, el territorio dice poco del cambio de voto | 81 de 202 pruebas pasan los tres filtros, pero en los cambios de voto ninguna supera \|ρ\| = 0,28 | PROBADO | `104` | `territorio_bateria.csv` |
| 2011-2023: el peronismo cayó más donde más se extendieron el gas y el agua de red | Spearman parcial −0,24 (gas) y −0,18 (agua) en Gobernador, con el nivel de 2011 y la composición de 2010 controlados | PROBADO | `104` | ídem |
| 2023-2025: la caída de la participación fue rural y de baja educación | Densidad +0,38, viviendas rurales −0,34, secundario incompleto −0,30 (con la participación de 2023 controlada) | PROBADO | `104` | ídem |
| 2023-2025: LLA-PRO avanzó relativamente en barrios populares con migrantes; el peronismo resistió en lo rural y entre jubilados | Captura de LLA-PRO: NBI de vivienda +0,17, hogares migrantes +0,16, jubilados −0,15. Peronismo: rural +0,17, jubilados +0,15 | PROBADO (efectos chicos) | `104` | ídem |

## 6 · El motor 2027

| Hallazgo | Magnitud | Estado | Script | Tabla |
|---|---|---|---|---|
| Dado el nivel provincial, el mapa se reproduce bien | Error medio por municipio 2,7 pp con la regla mezcla, contra 12,4 sin traslado; 89 % de ganadores municipales y 97 % de secciones | PROBADO (13 pares, 2011-2025) | `105` | `motor_backtest.csv` |
| El ruido territorial depende del tamaño del municipio y de si entra una fuerza nueva | Desvío del cociente peronismo/derecha: 0,22 en un municipio de 10.000 votos, 0,07 en uno de 500.000; con oferta nueva, ~0,28 en todos | PROBADO (calibración dejando un par afuera: 52/79/90/95 % de cobertura para 50/80/90/95 %) | `105` | `motor_ruido_modelo.csv`, `motor_calibracion.csv` |
| El nivel provincial de 2027 no se puede anticipar con el pasado | De la legislativa a la de Gobernador siguiente el margen se movió +19,8 pp (2017→2019) y +2,5 (2021→2023) | DESCRIPTIVO | `105` | — |
| Si se repite octubre 2025, es un empate | Peronismo 41,5, derecha 41,3; margen +0,3 (−2,0 a +2,5); el peronismo gana el 57 % de las simulaciones y 39 municipios | DESCRIPTIVO (escenario) | `106` | `motor_2027_escenarios.csv` |
| Si se repite septiembre 2025, el peronismo gana cómodo | Margen +13,4 (+11,1 a +15,6), 100 municipios | DESCRIPTIVO (escenario) | `106` | ídem |
| Padrón 2027 y extranjeros le suman al peronismo menos de un punto | El padrón 2027 con los extranjeros lleva el margen de octubre de −0,6 a +0,3; extranjeros al 45 % en vez de 29 %: +0,2 | DESCRIPTIVO | `106` | ídem |
| La participación, sola, casi no mueve el margen | De 64 % a 80 % con el mismo patrón territorial: ±0,1 pp | DESCRIPTIVO (sin movilización diferencial) | `106` | ídem |
| Con empate provincial, el peronismo gana 40 de 135 municipios | Necesita +4 de margen para ganar la mitad de los municipios y +12 para 78; la sección 3 la gana siempre, la 1 se da vuelta en el empate, la 8 cerca de +4 y las del interior recién arriba de +10 | DESCRIPTIVO | `106` | `motor_2027_grilla.csv` |
