# Bitácora · Atlas PBA

Cada decisión, cada trampa y cada resultado negativo, en orden. Lo primero que hay que leer.

---

## 01-11-2026 · Arranque

**Repo.** Carpeta propia (`E:\PROVINCIA DE BUENOS AIRES ELECCIONES`) y repo propio
(`licgermancardenas-crypto/PROVINCIA-DE-BUENOS-AIRES---GOBERNADOR`). El Atlas CABA se usa sólo
como referencia y como fuente de copias de ZIP de la DINE ya bajados: se lee, no se escribe.

**Estructura.** La misma del CABA (00_DOCS … 10_PRODUCTOS, `src/` + `config/` para el motor),
con las mismas reglas de la casa. Diferencias de fondo anotadas en el README: simple pluralidad
sin balotaje, Conurbano/interior, Legislatura por sección.

### La DINE trae Gobernador e Intendente por mesa

Los ZIP «provisorios» de la DINE son todo el país y, para PBA, incluyen las categorías
provinciales y municipales cuando la elección fue simultánea. 2011 trae siete: Presidente,
Senadores y Diputados nacionales, **Gobernador**, Senadores y Diputados provinciales e
**Intendente**. Mismo `mesa_id` para todas. Eso permite medir el corte de boleta
Intendente-Gobernador a nivel mesa.

El esquema de columnas es el mismo de 2011 a 2025 pero **el orden cambia** entre años y la
codificación también (2011 UTF-8; los demás latin-1): el ETL 01 lee por nombre y detecta la
codificación por el encabezado.

### Trampa 1 · el tipo extranjero está en `mesa_tipo`

`padron_tipo` vale `NORMAL` en todas las filas de 2011. Lo que separa nativos de extranjeros es
`mesa_tipo` (`NATIVOS` / `EXTRANJEROS`). En 2011, las mesas de extranjeros (10.948 filas) sólo
aparecen en **Intendente**.

### Pregunta abierta · 878 mesas con Gobernador y sin Presidente (2011)

Gobernador tiene 31.658 mesas; Presidente, 30.780. Las 878 de diferencia **no son de
extranjeros** (todas `NATIVOS`) y están repartidas en muchos municipios (las que más: 104 en el
municipio 61, 51 en el 70). Hipótesis: telegramas de categorías nacionales no transmitidos en el
provisorio. Se resuelve contrastando contra el definitivo por municipio (etapa 1.4). Hasta
entonces, **no comparar participación entre categorías del provisorio**.

### MunicipiosArgentinos.net

El cliente lo propuso. Publica sus datos en JS estáticos (robots.txt permite todo salvo
`/admin/` y `/api/`). Para PBA: 135 municipios con código INDEC y ~50 indicadores —población,
servicios del censo 2022, transferencias provinciales 2025, gasto devengado 2025, deuda,
Tribunal de Cuentas, transparencia, delito (SNIC), mortalidad infantil— más el **intendente en
ejercicio con su espacio político** (82 Fuerza Patria, 30 Somos/Provincias Unidas, 11 LLA…).
785 fuentes citadas, 75 % oficiales.

Decisión: se usa como **fuente secundaria**. Cada indicador viene con período y fuente; antes de
publicar un hallazgo que dependa de uno, se contrasta contra la primaria. El índice y el
semáforo del sitio son construcciones propias con sus pesos: no entran como variables
explicativas sin desarmarlos. Cobertura floja en publicidad (16 %), semáforo propio (17 %),
deuda flotante (27 %), recursos propios (30 %).

### Fuentes que no se pudieron bajar

- PASO 2015: el enlace del propio portal de la DINE devuelve 404.
- Octubre 2025: la página de la DINE todavía no lista el ZIP; se copió el del Atlas CABA.

### La serie por mesa quedó armada: 15 elecciones, 2011-2025

`etl/01` corrió sobre los 15 ZIP (falta PASO 2015). Control en
`03_OUTPUTS/tablas/control_dine_pba.csv`. Lo que dice:

- **En 2023 los extranjeros votan Gobernador e Intendente**: 2.127 mesas de extranjeros,
  40.201 mesas y 14,07 M de electores para Gobernador contra 38.074 mesas y 13,12 M para
  Presidente. En 2011 sólo aparecían en Intendente. La regla del denominador por categoría
  no es teórica: es casi un millón de electores.
- Circuitos con voto: 934 en 2011, 1.047 en 2023 y 2025. La capa de polígonos (marzo 2026)
  tiene 1.146. **No hay correspondencia circuito a circuito garantizada entre años**: falta la
  tabla de equivalencias (etapa 1.9).
- La DINE escribe los municipios con nombres que cambian de un año a otro («Rosales» /
  «Coronel Rosales», «J. C. Paz», «Juárez»), pero el `seccion_id` es estable y es **el mismo
  número de distrito de la Junta Electoral** (001 Adolfo Alsina … 135). `etl/02` empareja
  juntando los nombres de todos los años: 135 de 135.

### Geografía: tres trampas de los mapas de ARBA

1. **Chascomús y Lezama comparten el código 06217** (Lezama se separó en 2009). El INDEC 2022
   usa 06218 y 06466. Se corrige por nombre.
2. **La capa de circuitos trae códigos de partido viejos** en 8 partidos (Cañuelas 06133,
   Pilar 06637, Morón 06567, Esteban Echeverría 06259…): 70 circuitos. Manda la ubicación.
3. **La costa de la capa de secciones no coincide con la de partidos**: La Costa, Pinamar y
   Villa Gesell quedan con el punto interior fuera de toda sección. Se asigna por mayor
   superposición. Y 6 de las 8 secciones tienen geometría inválida (`make_valid`).

Los códigos de circuito llegan en tres formas (`0063`, `989`, `0557 `, a veces con letra:
`0164A`): `norm_circuito` los deja en 4 dígitos + letra.

### Provincial 7-09-2025: definitivo por municipio

`etl/05` raspa las 135 páginas del escrutinio definitivo de la Junta. Cierra al voto en los
135 municipios, en la legislativa y en concejales. 41.189 mesas, 14,38 M de electores
(con extranjeros), participación 61,0 %. Fuerza Patria 47,35 % de los positivos, LLA 33,78 %.

Detalle que importa: en **San Nicolás ganó un partido local** (lista 91, Espacio Abierto,
50,9 %). El lector de listas asumía números de 3-4 cifras y lo perdía, y con él no cerraba
ningún municipio de la Segunda Sección. **El vecinalismo existe y hay que mapearlo**, no
tirarlo a «otros».

El mesa a mesa de 2025 no está: el portal provisorio se dio de baja.

### Relevamiento de las fuentes que mandó el cliente

Veredicto por fuente en [`01_DATOS/RELEVAMIENTO.md`](../01_DATOS/RELEVAMIENTO.md). Lo grueso
salió de datos.gob.ar: **los cuatro censos (1991, 2001, 2010, 2022) por radio censal**, con
todas sus variables en conteos (`codigo` de 9 dígitos = provincia + departamento + fracción +
radio), más las tablas de conversión de radios entre censos. Para inventariar sin perder nada,
`etl/04` recorre enteros los catálogos CKAN de PBA y el de Nación (filtrado): 461 datasets.

Trampa: el catálogo de Nación publica para 2010 y 2001 la URL `…-2022.zip`, que da 404; el
archivo real termina en `-2010` / `-2001`. Y en el censo 1991 Buenos Aires es la **02**.

---

## 01-11-2026 · Censo 2022 → circuito (`etl/06`)

**Qué se hizo.** Las tablas del INDEC vienen por radio, en formato largo (radio × variable ×
categoría × cantidad): 4,4 M de filas para las 32 variables elegidas. DuckDB las agrega sin
cargar el archivo de personas (540 MB) en memoria. Los 23.901 radios se reparten entre los
1.146 circuitos por superposición de área: un radio con 95 % o más de su área en un circuito va
entero; si no, se reparte por área. Resultado: 116 columnas por circuito, 43 indicadores con
su numerador y denominador en conteos (se pueden volver a sumar a cualquier escala).

**Cuatro controles, los cuatro pasan:**

1. **Claves.** Todos los radios con tabla tienen polígono (21 polígonos sin tabla, vacíos).
   Población que cae en un circuito de otro partido: 7.809 personas, 0,045 %.
2. **Contra las cifras publicadas por partido.** Agregados a partido, agua, gas, cloaca y NBI
   coinciden con los valores del INDEC (correlación 1,000; diferencia máxima 0,63 pp en agua,
   0,07 pp en NBI). Para cloaca hubo que usar el total de hogares como denominador, como la
   cifra oficial: la pregunta del desagüe (H18) sólo se hace a hogares con inodoro.
3. **Contra la población total.** La suma de radios da 0,66 % menos que el INDEC. **Las
   tablas por radio son sólo viviendas particulares** (`VIVIENDA_TIPOVIVG` tiene una sola
   categoría): faltan cárceles, geriátricos y cuarteles. Por eso General Alvear da −19,6 % y
   Magdalena −14,9 % (unidades penales), y Marcos Paz y Olavarría (Sierra Chica), −3 %.
4. **Contra el padrón — el que importa.** Población de 16+ del censo contra electores nativos
   de la DINE por circuito. En 2025: razón total 1,005, correlación de logaritmos 0,98, y
   **98,5 % del padrón en circuitos con razón entre 0,6 y 1,5**. En 2023, 97,0 %. Los que se
   salen vienen de a pares vecinos (Almirante Brown 0019 con 2,08 y 0020 con 0,55 en 2023): el
   votante anotado del otro lado del límite. Y circuitos rurales chicos con razón baja, donde
   la gente del campo vota en el pueblo. Queda una marca por circuito, `calidad_cruce`:
   886 `ok`, 160 `revisar`, 100 `sin_padron` (circuitos de la capa sin mesas en 2025; 31.604
   habitantes en total).

**Límites que hay que tener presentes.** El 6,6 % de la población vive en radios partidos
entre circuitos y se reparte por área, que en el campo es una aproximación (el pueblo puede
estar todo de un lado). Las tablas son univariadas: «universitarios» es sobre todo el universo
de la pregunta, no sobre los de 25+, así que la educación queda confundida con la edad del
circuito y en los modelos la edad va como control. Y la distribución es muy despareja:
mediana 3.259 habitantes por circuito, máximo 211.487. **Con `log(pob)` siempre.**

**Definiciones a cuidar:** «hacinamiento crítico» es más de 3 personas por cuarto (2,0 % de
los hogares en el circuito mediano, igual que el componente de NBI). Más de 2 queda como
`pct_hog_hacinamiento` (13,7 %).

---

## 01-11-2026 · Censos 1991, 2001 y 2010 → circuito (`etl/07`)

**Método.** Cada censo se reparte sobre **sus propios radios** con la misma función que el 2022
(`repartir`, en `etl/06`): área, entero si ≥ 95 %. No se usan las tablas de conversión del
INDEC: un solo método para los cuatro censos y ninguna cadena de conversiones que acumule
error.

**Qué publica el INDEC por radio, y qué no.** 2010 trae sólo el cuestionario básico (37
variables: sin cobertura de salud, jubilación ni aportes, que fueron por muestra). 2001 trae 81
y 1991, 24. De ahí sale un juego de **19 indicadores comparables**; lo que cambió de pregunta
queda NA en ese censo en vez de forzarse:

| Indicador | 1991 | 2001 | 2010 | 2022 |
|---|---|---|---|---|
| Población, sexo, edad (0-14, 15-29, 30-44, 45-64, 65+) | ✅ | ✅ | ✅ | ✅ |
| Cloaca, propietarios | ✅ | ✅ | ✅ | ✅ |
| Nacidos en otro país | ✅* | — | ✅ | ✅ |
| Llegó a la universidad, NBI, hacinamiento crítico, computadora, materiales | — | ✅ | ✅ | ✅ |
| Desocupación | — | ✅** | ✅ | ✅ |
| Agua de red, gas de red | — | — | ✅ | ✅ |
| Vivienda rural | — | ✅ | ✅ | ✅ |
| Villa de emergencia | ✅ | — | — | — |

\* 1991 trae lugar de nacimiento con códigos 1-4 sin etiqueta; 3 y 4 se leen como otro país
(6,3 %, coherente con 6,0 % en 2010). \*\* Ver trampa 3.

**Controles.**
- Población: las tablas cierran **exacto** con el total oficial de cada censo (12.594.974 /
  13.827.203 / 15.625.084). Por partido, contra cifras oficiales: La Matanza 1991 da 1.120.247
  (oficial 1.121.298), Pilar 2001 232.456 (232.463), Morón 2001 310.295 (309.380). Y los
  partidos creados en 1994 (José C. Paz, Malvinas Argentinas, San Miguel, Ezeiza, Presidente
  Perón, Hurlingham, Ituzaingó) **reciben su población de 1991** por geometría.
- NBI provincial: 13,0 % (2001), 8,2 % (2010), 6,4 % (2022), como lo publicado.
- Estabilidad: la población de un circuito entre censos consecutivos correlaciona 0,986 /
  0,994 / 0,991 (circuitos de 500+), y casi ninguno se triplica o cae a un tercio.

**Trampas.**
1. **En 1991 Buenos Aires es la 02 en las tablas y la 06 en los polígonos.**
2. **2001 no tiene país de nacimiento por radio**: la variable que el diccionario llama «lugar
   de nacimiento» (P7) da 5.899 nacidos en otro país en toda la provincia; no es esa pregunta.
3. **La desocupación del censo 2001 es 32,9 %** en PBA: ese censo la medía muy por encima de la
   EPH. Sirve para ordenar circuitos dentro de 2001, no para medir el cambio: no se calculan
   diferencias desde 2001 para ese indicador.
4. **La población de 1991-2010 incluye viviendas colectivas y la de 2022 por radio no** (ver
   `etl/06`). El crecimiento 2010-2022 de los partidos con cárceles sale subestimado.
5. **Capa de radios 2010 corrida.** Comparando el mismo código de radio en 2010 y 2022, la
   mediana provincial se mueve 97 m, pero en cinco partidos más de 1 km: Tres Lomas (4,9 km),
   Exaltación de la Cruz (2,7 km), General Rodríguez, Salliqueló y General Alvear. Sus 16
   circuitos quedan no confiables para 2010-2022. (Con 2001 la prueba no sirve: el INDEC
   renumeró los radios del Conurbano entre 2001 y 2022.)
6. **Junín rural en 2010**: las tablas dejan vacíos radios rurales (0701, 0702) y cargan la
   gente en otros códigos; un circuito rural «tenía» 89,8 % de cloaca en 2010 y 5 % en 2022.
   Los polígonos coinciden con 2022: es error de la fuente.
7. **Circuitos chicos inventan cambios.** Con 0 a 200 habitantes, el reparto por área da
   crecimientos de hasta +25.892 %. Los cambios se anulan con menos de 200 habitantes en
   alguno de los dos censos, y `cambio_confiable_*` exige 500+: quedan **801 circuitos
   confiables para 2010-2022, con el 98,3 % de la población**.

Las caídas grandes de cobertura que sobreviven a esos filtros son reales: circuitos que
crecieron mucho y diluyeron la cobertura con barrios nuevos (La Plata 0463: +84 % de
población, cloaca de 99 % a 82 %).

---

## 01-11-2026 · Mapeo de espacios políticos (`etl/08`)

**Validado por Germán el 01-11-2026 (D1-D9).** Inventario de todas las listas que compitieron en PBA entre 2005 y 2025, en
todas las fuentes y categorías: DINE por mesa (2011-2025), definitivo de la Provincia por
municipio (generales 2005-2023 y PASO 2011-2021: es la única fuente de Gobernador 2007) y
Junta Electoral 2025. Son 3.607 filas y 688 nombres distintos. Las reglas
(`config/reglas_mapeo.yaml`) llevan cada una a uno de nueve espacios; el detalle y las nueve
decisiones abiertas, con su peso, en [`mapeo_espacios.md`](mapeo_espacios.md).

**El espacio nuevo es `TERCERA_VIA`**: el peronismo no K y sus alianzas de centro (Massa,
Duhalde, De Narváez, Randazzo, Lavagna, Schiaretti, Somos). En PBA ganó en 2013 con 43,5 %.

**Trampa 1 · la DINE puso el año equivocado.** El ZIP de 2013 trae los Diputados provinciales
de 2013 con «2017» en la columna año (169.361 filas). En el inventario aparecían un Frente
para la Victoria y un Frente Renovador de 1,6 millones de votos cada uno en 2017. `etl/01`
ahora toma el año del nombre del archivo y guarda el original en `anio_dato`; se reprocesaron
las 15 elecciones.

**Trampa 2 · «Unión Celeste y Blanco» no es voto en blanco.** El catálogo de la Provincia
trae los blancos y nulos como si fueran listas; detectarlos buscando la palabra «BLANCO» se
comía al Partido Unión Celeste y Blanco (2,5 % en 2021). Se detectan por nombre completo.

**Trampa 3 · cinco maneras de escribir la misma lista.** «ALIANZA JUNTOS» / «JUNTOS»,
«NUEVO ENCUENTRO (NE)», «FTE DE IZQ. Y DE TRABAJADORES-UNIDAD», «GOBERNADOR/A»,
«GENERAL» / «GENERALES». La normalización saca el prefijo ALIANZA y las siglas entre
paréntesis, y expande FTE e IZQ.

**Control.** El mismo mapeo aplicado al provisorio de la DINE y al definitivo de la Provincia
da los mismos porcentajes por espacio (ver la tabla al final de esta entrada): las reglas no
dependen de la fuente.

**Resultado del control, con los archivos reprocesados.** Diferencia máxima por espacio entre
el provisorio DINE y el definitivo de la Provincia, en puntos:

| | Gobernador | Diputados prov. | Senadores prov. |
|---|---|---|---|
| 2011 | 0,12 | 0,17 | 0,10 |
| 2013 | — | 0,06 | 0,08 |
| 2015 | 0,11 | 0,08 | 0,14 |
| 2017 | — | 0,04 | 0,02 |
| 2019 | 0,11 | 0,12 | 0,11 |
| 2021 | — | 0,08 | 0,08 |
| 2023 | 0,08 | 0,09 | 0,04 |

Cobertura: 0,08 % de los votos positivos queda sin regla.

---

## 01-11-2026 · Panel armonizado (`etl/09`)

`panel_circuito.parquet`: 433.636 filas, circuito × elección × categoría × espacio, 71
elecciones × categorías de 2011 a 2025, con electores y votantes **separados en nativos y
extranjeros**. Suma exactamente lo mismo que el ETL 01 (0 votos de diferencia), y en cada
circuito los votos por espacio suman los votantes.

`panel_municipio.parquet`: 91.781 filas, las tres fuentes con la columna `fuente`: DINE
agregada, definitivo de la Provincia (2005-2023, PASO 2011-2021) y Junta 2025. Es donde vive
Gobernador 2007 y el definitivo oficial.

**Gobernador, definitivo de la Provincia, % de los positivos:**

| | Peronismo | Tercera vía | PRO/JxC | LLA | Centro/UCR | Izquierda | Participación |
|---|---|---|---|---|---|---|---|
| 2007 | 48,2 | — | 15,9 | — | 21,6 | 4,5 | 77,3 |
| 2011 | 61,7* | 21,8 | — | — | 13,5 | 3,1 | 80,8 |
| 2015 | 35,3 | 19,3 | 39,4 | — | 2,4 | 3,7 | 80,5 |
| 2019 | 52,4 | 5,1 | 38,3 | — | — | 2,8 | 80,0 |
| 2023 | 45,0 | — | 26,6 | 24,6 | — | 3,9 | 75,5 |

\* Scioli 55,1 % + Nuevo Encuentro 6,5 % (D8).

**Marca de calidad.** 711 de 63.698 circuito-elección-categoría (0,02 % de los votantes)
tienen participación de más de 100 % o de menos de 30 %: circuitos de ~80 electores con el
padrón mal cargado en el provisorio. Quedan marcados en `participacion_anomala`, no borrados.

**Lo que todavía no permitía:** seguir un circuito en el tiempo. Resuelto en la etapa 1.9
(entrada siguiente).

---

## 01-11-2026 · Circuitos estables 2011-2025 (`etl/10`) y la marca de extranjeros

### Primero, un error de la DINE que estaba en el panel

En cinco archivos la marca de mesa de extranjeros (`mesa_tipo`) falla: 2011 y 2013 generales
la traen como NATIVOS, 2017 generales la trae en singular y, en concejales, todas las mesas como
NATIVOS; 2017 PASO la trae vacía. Resultado: en esos años los extranjeros se sumaban al padrón de
nativos, y en las categorías nacionales de 2013, 2015 y 2017 (donde la DINE lista las mesas de
extranjeros con padrón y casi sin votos) inflaban el padrón nacional.

**Las mesas de extranjeros se numeran desde 9000** y las de nativos, que se numeran por
municipio, nunca llegan (máximo 9280 en 2023, todas de extranjeros). Ahora una mesa es de
extranjeros si tiene la marca **o** número 9000 o más (`es_extranjera` en `etl/01`, mismo
criterio en `etl/09`). Ejemplo: Gobernador 2011 pasa de 0 a 878 mesas de extranjeros. Los votos
por espacio no cambian; cambian electores y votantes nativos de esos años.

### La tabla de equivalencias

Los códigos de circuito son únicos en la provincia, pero cambian: se subdividen (0022 →
0022A/B/C), los rurales chicos se absorben en un vecino y a veces se pasa padrón de un código a
otro (Almirante Brown 2025: 0019 pierde 35 mil electores que ganan 0020 y 0022). La capa de
polígonos es una sola partición de una fecha intermedia (1.146 códigos, sin superposiciones) y no
guarda la historia. Así que las equivalencias salen del padrón:

- Entre dos elecciones consecutivas, en cada municipio, se mide el **exceso** de electores de cada
  circuito respecto de lo que habría tenido creciendo como su municipio.
- Cada circuito que **pierde** (más de 150 electores y más de 15 %, o desaparece) se une con los
  que **ganan** siendo sus vecinos en el mapa o de su familia de código (mismo número). Si gana uno
  de una familia, se suman todos los de esa familia que ganan.
- Un código sin polígono usa los vecinos de su familia; uno que desaparece sin polígono ni familia
  va al que más ganó en su municipio.
- Un bajón o pico de un solo año que se revierte en la elección siguiente **no es un cambio de
  límites**: son mesas que faltan en el provisorio. No une nada y queda marcado
  `padron_incompleto` en la serie.
- Las uniones se acumulan en la ventana: cada grupo es un **circuito estable (CE)**.

| Ventana | CE | De un solo código | Con fusión | Máx. códigos | Años-CE con padrón incompleto | Saltos sostenidos |
|---|---|---|---|---|---|---|
| 2011-2025 | 919 | 816 | 103 | 21 | 77 | 8 |
| 2015-2025 | 933 | 832 | 101 | 21 | 60 | 11 |
| 2019-2025 | 998 | 906 | 92 | 17 | 36 | 12 |
| 2023-2025 | 1.033 | 1.024 | 9 | 8 | 0 | 0 |

En todas las ventanas el 100 % del padrón 2025 queda en CE presentes en todos los años. Los
saltos sostenidos que quedan (0,3 % del padrón en la ventana larga) se revisaron uno por uno: son
barrios que crecen elección tras elección (Pilar 0107, Ensenada 0445-0446, Gral. Rodríguez 0575,
0915, 0926, Mar del Plata 0369) y un circuito de Chascomús que se despuebla (0203). Ninguno es una
equivalencia mal resuelta.

**Usar la ventana más corta que alcance.** Las subdivisiones encadenadas obligan a fusionar: en
2011-2025 Pilar 0768-0772 es un solo CE de 21 códigos y 288 mil electores, y Mar del Plata
0364-0368 uno de 17. Para 2023 → 2025 la ventana 2023-2025 casi no fusiona (9 grupos).

**Control externo contra el censo 2022.** Si los grupos están bien, la población de 16 años y
más de cada CE tiene que acompañar a su padrón. Porcentaje del padrón en unidades donde la razón
padrón / población cae fuera de 0,6-1,5:

| Padrón de | Por código | Por CE 2011-2025 |
|---|---|---|
| 2011 | 16,6 % | 10,2 % |
| 2019 | 8,0 % | 2,0 % |
| 2023 | 3,0 % | 1,2 % |

Lo que queda en 2011 es crecimiento real entre 2011 y 2022.

**Salidas:** `01_DATOS/processed/circuitos_equivalencias.csv` (ventana, código → `ce_id`),
`circuitos_estables_serie.csv` (padrón por CE y año, con `padron_incompleto`),
`geo/circuitos_estables.gpkg` (una capa por ventana; 7 códigos sin polígono quedan dentro del CE
pero no en el mapa), `03_OUTPUTS/tablas/circuitos_uniones_motivos.csv` (cada unión con su motivo)
y `control_circuitos_estables.csv`.

---

## 01-11-2026 · Arrastre del intendente y corte de boleta (`analisis/100`)

Primer análisis de la etapa 3. Intendente y Gobernador se votan el mismo día en 2007, 2011,
2015, 2019 y 2023, con **boleta partidaria de papel**: votar distinto exige cortar la boleta con la
mano, así que la diferencia es una decisión con costo, y todo lo que se mide es un piso (los
cortes en direcciones opuestas se cancelan en el agregado).

### La pregunta: ¿un intendente propio suma votos a Gobernador?

**No se detecta.** Regresión discontinua: municipios donde un espacio ganó la intendencia por poco
contra municipios donde la perdió por poco, y su voto a Gobernador en la elección siguiente
(desvío respecto de su resultado provincial, efectos fijos de espacio × transición, error
agrupado por municipio). Peronismo y PRO/JxC, transiciones 2007→2011 a 2019→2023.

| Banda de margen | Casos | Efecto sobre Gobernador (pp) | IC 95 % | Placebo: Gobernador anterior | Referencia: Intendente siguiente |
|---|---|---|---|---|---|
| ±7,5 pp | 199 | +0,4 | −4,2 a +5,0 | −0,7 | **+9,1** (p < 0,01) |
| ±10 pp | 267 | −0,2 | −4,4 a +4,0 | −1,0 | **+7,4** (p < 0,01) |
| ±15 pp | 374 | −0,1 | −3,6 a +3,5 | −0,5 | **+6,6** (p = 0,01) |

- **El diseño funciona:** el placebo no salta, ganadores y perdedores por poco están parejos (96
  contra 103 en ±7,5 pp) y el mismo método sí detecta la ventaja del oficialismo en su propia
  categoría.
- **La ventaja del intendente se queda en el intendente.** Gobernar el municipio da +7 a +9 pp en
  la elección siguiente de Intendente (peronismo +10,6, q = 0,002; PRO/JxC sin efecto medible) y
  nada medible en Gobernador. Un efecto de más de 4 pp queda descartado.
- Benjamini-Hochberg sobre las 60 pruebas (4 resultados × 5 bandas × 3 grupos): sólo sobreviven
  los efectos en Intendente.

### La brecha: el arrastre va de arriba hacia abajo

Brecha media Intendente − Gobernador de cada espacio, donde compite en las dos (pp):

| | Conurbano | Interior |
|---|---|---|
| 2007 Peronismo (Scioli) | −7,3 | −4,3 |
| 2011 Peronismo (Scioli) | −8,2 | −6,7 |
| 2015 Cambiemos (Vidal) | −5,7 | −7,1 |
| 2015 Peronismo (Aníbal Fernández) | +1,7 | +6,4 |
| 2023 LLA (Píparo) | −2,9 | −8,8 |
| 2023 Peronismo (Kicillof) | +1,0 | +3,6 |
| 2023 JxC (Santilli) | +1,7 | +5,0 |

Cuando el candidato a gobernador es fuerte, sus intendentes sacan menos que él (Scioli, Vidal).
Cuando es débil, o el espacio no tiene estructura local (LLA 2023), los intendentes retienen por
encima. El intendente que gana saca más que su gobernador en el 87 % de los municipios en 2023
(mediana +6,9 pp), contra el 54 % en 2011.

### El corte de boleta, por circuito

Índice 0,5 · Σ |%int − %gob|, **pareado**: sólo espacios con lista en las dos categorías del
municipio, renormalizados. El bruto suma la oferta desigual, sobre todo vecinalismos sin
candidato a gobernador. Mediana por circuito:

| | 2011 | 2015 | 2019 | 2023 |
|---|---|---|---|---|
| Conurbano | 6,2 | 5,5 | 3,7 | 3,1 |
| Interior | 7,6 | 9,5 | 4,5 | 8,8 |

En el Conurbano el corte baja en todas las elecciones. En el interior sube con terceras fuerzas
fuertes (Frente Renovador 2015, LLA 2023). En 25 municipios (2023) Intendente y Gobernador los
ganó un espacio distinto; en 2015 fueron 51.

### Dos trampas que casi se publican

1. **UDESO 2011.** La regla D6 la mandaba a Tercera vía sólo en Gobernador y Legislatura; en
   Intendente caía en Centro/UCR. Como iban en la misma boleta de papel, eso fabricaba un corte
   de boleta de 12 puntos en 2011 (mediana 19,4 contra 7,3 corregido). D6 se amplió: lo municipal
   va con la boleta provincial. **A validar por Germán.**
2. **Ofertas con 0 votos.** El definitivo de la Provincia lista partidos con 0 votos en municipios
   donde no compiten. Contados como oferta, escondían a los 25 intendentes vecinales ganadores de
   2007 (Acción Marplatense, Nuevo Morón, San Isidro es Distinto…).

### Lo que no dice

- Mide el efecto de que **el espacio** gobierne el municipio, no el de un intendente con nombre
  propio: no hay base de quién fue candidato a reelección.
- Vale para municipios competitivos (margen de ±10 pp), no para los de 70 %.
- PRO/JxC tiene pocos casos (92 en ±10 pp): su estimación es imprecisa.

**Para el motor 2027:** el arrastre de la intendencia no entra como parámetro; sí la brecha
intendente-gobernador, que depende de la fuerza relativa del candidato provincial.

---

## 02-11-2026 · Conurbano contra interior (`analisis/101`)

La pregunta, en forma de prueba: **¿un circuito del Conurbano vota como un circuito del interior
con la misma composición social?** Unidad: los 997 circuitos estables 2019-2025 (222 del
Conurbano), con el censo 2022 recalculado desde los conteos. Voto: Diputados Nacionales
2019-2025 (única categoría presente los cuatro años) y Gobernador 2019 y 2023; bloques
peronismo y derecha (PRO/JxC + LLA + LLA-PRO). Regresión ponderada por electores con error
agrupado por municipio, y dos juegos de controles: **composición** (educación, edad, NBI,
privación, obra social, desocupación, migración, inquilinos, cuentapropismo, log población /
electores) y **+ urbanización** (densidad, rural, cloaca, gas).

### En el nivel, son dos electorados

Brecha Conurbano − interior en el voto peronista (pp):

| | Bruta | Con composición | + urbanización | Sin el municipio que más pesa (rango) |
|---|---|---|---|---|
| Diputados 2019 | +10,2 | +6,0 | +4,2 | +5,2 a +6,8 |
| Diputados 2021 | +8,4 | +5,9 | +4,1 | +5,3 a +6,7 |
| Diputados 2023 | +9,8 | +6,6 | +4,9 | +6,1 a +7,4 |
| Diputados 2025 | +8,0 | +5,6 | +4,0 | +5,1 a +6,4 |
| Gobernador 2019 | +10,0 | +5,9 | +4,3 | +5,3 a +6,8 |
| Gobernador 2023 | +9,1 | +6,2 | +4,7 | +5,7 a +7,0 |

La derecha, espejo: −9 a −12 bruta, −6 a −7 con composición. Todas pasan Benjamini-Hochberg
(q ≤ 0,02) y la prueba de fragilidad (sacar cada municipio, y los tres que más mueven el
coeficiente). La composición explica cerca de un tercio de la brecha y la urbanización otro
quinto; quedan **4 a 6 puntos que son del lugar**: sindicatos, redes territoriales, historia, o
composición que el censo no mide. No es causal.

### Pero el perfil censal ya sabe dónde está el circuito

Validación agrupada por municipio (el modelo predice municipios que no vio): R² de 0,60 a 0,86 en
los niveles. Sumar la zona mejora el lineal en 0,01-0,03 y no mejora nada a los árboles: un
modelo no lineal con el censo reproduce el «efecto Conurbano» sin que se le diga la zona (el
residuo medio del Conurbano queda en ~1 pp). **Para el motor: modelar por tipo de circuito con el
censo; la etiqueta de zona sobra.**

### En el cambio, es una sola elección

| Cambio en el voto peronista | Bruta | Con composición | + urbanización | Media Conurbano / interior |
|---|---|---|---|---|
| Gobernador 2019 → 2023 | −0,8 | +0,4 | +0,4 | −8,1 / −7,3 |
| Diputados 2021 → 2025 | −0,4 | −0,2 | −0,1 | +2,0 / +2,4 |
| Diputados 2023 → 2025 | −1,7 | −1,0 | −0,9 | −3,3 / −1,6 |

Ninguna pasa Benjamini-Hochberg (q > 0,2). La única diferencia en la derecha (2023 → 2025, +1,2
con composición, q = 0,02) desaparece con urbanización (+0,6, q = 0,29). Y el cambio es mucho más
parejo que el nivel: el voto peronista varía 10 pp entre circuitos, su cambio entre elecciones
3-4 pp.

**Lectura:** el Conurbano tiene un piso peronista más alto que el que le corresponde por
composición, pero no tiene una dinámica propia. Las olas son provinciales. Para el motor 2027:
**niveles por circuito (dependen del lugar), cambios con un movimiento común** ajustado por
composición, no por zona.

### Lo que no dice

- Ecológico: habla de circuitos, no de votantes.
- El censo es de 2022 y se usa también para 2019 y 2021.
- Los 4-6 puntos «del lugar» no tienen explicación acá: son lo que la composición medida no
  alcanza a explicar.
