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

---

## 02-11-2026 · Retención y transferencia 2023 → 2025 (`analisis/102`)

**Qué se compara.** Gobernador 2023 (generales) contra Diputados Nacionales octubre 2025, por
circuito estable (ventana 2023-2025). Es el único par con dato por circuito: la provincial de
septiembre sólo está por municipio. **Mismo padrón en las dos puntas**: Gobernador 2023 se arma
sólo con mesas de nativos (13,12 M de electores; 2025: 13,35 M). «No votó» es una categoría más.
Se descartan 36 circuitos de menos de 50 electores (1.309 electores).

**Estimador.** El de CABA, portado a `analisis/_inferencia.py`: una sola regresión no negativa
con la restricción de filas adentro. Para la provincia y por zona.

### La matriz (% de cada origen 2023)

| 2023 → 2025 | Fuerza Patria | LLA-PRO | Prov. Unidas | Izquierda | Otros | Blanco/nulo | No votó |
|---|---|---|---|---|---|---|---|
| Kicillof (UxP) | **82,2** (79-84) | 0 | 0 | 2,4 | 2,8 | 0 | **12,6** (10-16) |
| Santilli (JxC) | 5,8 (2-8) | **77,4** (75-79) | 7,1 (6-8) | 2,2 | 2,6 | 2,0 | 3,0 |
| Píparo (LLA) | 0 | **70,2** (63-74) | 0 | 0 | 8,0 | 0 | **21,7** (15-29) |
| Izquierda | 0 | 0 | 0 | 73,4 (55-89) | 26,6 | 0 | 0 |
| Blanco y nulo | 0 | 0 | 3,6 | 0,1 | 15,4 | 17,7 | 63,2 |
| No votó | 0 | 1,8 | 0 | 3,8 | 5,2 | 2,9 | 86,2 |

Entre paréntesis, percentiles 5-95 de 200 remuestreos de municipios.

**En votos:** de 4,08 M de Kicillof, 3,36 M votaron Fuerza Patria y 513.000 no fueron. De 2,46 M de
Santilli, 1,90 M fueron a LLA-PRO, 174.000 a Provincias Unidas y 143.000 a Fuerza Patria. De
2,27 M de Píparo, 1,59 M a LLA-PRO y 494.000 no fueron. El voto de LLA-PRO es 54 % Santilli y
45 % Píparo; el de Provincias Unidas, 83 % Santilli; el de Fuerza Patria, 96 % Kicillof.

**Lectura.** Nadie cruzó la grieta en cantidad: el peronismo no perdió votos hacia LLA-PRO, los
perdió hacia la abstención. La alianza LLA-PRO funcionó como suma: retuvo tres de cada cuatro
votantes de JxC. El que más se desmovilizó fue el votante de Píparo (uno de cada cinco).

### Controles

| | Matriz | Ingenua (cada circuito se mueve como la provincia) |
|---|---|---|
| Error de reconstrucción (dentro de muestra) | 0,08 % | — |
| Fuera de muestra, por circuito (pp por categoría) | 0,92 | 1,84 |
| Fuera de muestra, por municipio (% de votos mal ubicados) | 5,0 % | 9,8 % |
| Fuera de muestra, peronismo por municipio (mediana, pp) | 1,18 | 1,61 |

Fuera de muestra = estimada con 4/5 de los municipios, aplicada a los que quedaron afuera. La
matriz le gana a la predicción ingenua por la mitad.

**Cotas de Duncan-Davis** (sin supuestos): Kicillof → Fuerza Patria como mucho 85,5 %;
Santilli → Provincias Unidas como mucho 8,5 %. El resto de las cotas no informa (0 a ~95 %):
el dato agregado sólo identifica esas celdas con ayuda del supuesto de la matriz común.

**Por zona** las matrices se parecen: Kicillof → Fuerza Patria 81,7 % en el Conurbano y 84,0 %
en el interior; Santilli → LLA-PRO 79,3 % y 72,0 %. La abstención de Píparo varía mucho entre
zonas (7,5 % y 28,9 %), dentro del ruido de esa celda.

### Lo que no dice

- Ecológico: supone que la matriz es la misma en todos los circuitos de un ámbito.
- Los ceros son el borde de la estimación (no negativa), no la certeza de cero.
- El padrón cambia entre 2023 y 2025 (entran jóvenes, salen fallecidos): se trabaja con
  proporciones de cada padrón.
- Octubre, no septiembre: en la provincial de septiembre Fuerza Patria le ganó a LLA-PRO por unos 13 puntos. Eso es
  el análisis de desdoblamiento.

---

## 02-11-2026 · El desdoblamiento: septiembre contra octubre 2025 (`analisis/103`)

**Qué se compara.** La provincial del 7 de septiembre (legisladores; cada municipio vota diputados
o senadores según su sección) contra Diputados Nacionales del 26 de octubre, **por municipio**:
septiembre no está por mesa.

**Los dos padrones.** En septiembre votan los extranjeros: 14,38 M de electores contra 13,35 M en
octubre. La parte extranjera se estimó por municipio: electores = padrón de septiembre − padrón de
octubre (1,03 M); votantes y reparto = los de las mesas de extranjeros de Gobernador 2023 en ese
municipio (≈302.000 votantes). Sacándola queda un septiembre «sólo nativos».

### Los resultados

| | Participación | Fuerza Patria | LLA-PRO | Prov. Unidas | Izquierda | Otros |
|---|---|---|---|---|---|---|
| Septiembre, bruto | 61,0 | 47,4 | 33,8 | 5,2 | 5,4 | 8,2 |
| Septiembre, sólo nativos | 63,5 | 46,9 | 33,6 | 5,4 | 5,5 | 8,5 |
| Octubre | 67,5 | 40,9 | 41,5 | 2,4 | 6,2 | 9,0 |

(% de los positivos; participación sobre el padrón.) **El padrón extranjero no es la explicación**:
mueve a Fuerza Patria medio punto. En votos (nativos): **LLA-PRO pasó de 2,65 M a 3,61 M
(+957.000); Fuerza Patria, de 3,70 M a 3,56 M (−140.000)**; votaron 540.000 más. Por zona, LLA-PRO
ganó 5,4 puntos de los positivos en el Conurbano y 11,3 en el interior.

### La matriz septiembre → octubre (sólo nativos, % de cada origen)

| Sept. → Oct. | Fuerza Patria | LLA-PRO | Prov. Unidas | Izquierda | Otros | Blanco/nulo | No votó |
|---|---|---|---|---|---|---|---|
| Fuerza Patria | **67,9** (63-74) | **10,4** (7-14) | 0,6 | 4,9 | 6,8 | 2,1 | 7,3 |
| LLA-PRO | 0 | **87,4** (81-92) | 5,1 | 3,2 | 2,3 | 0,5 | 1,5 |
| Provincias Unidas | 5,6 | **64,2** (56-69) | 3,7 | 0 | 5,6 | 7,1 | 13,9 |
| Izquierda | 77,7 (54-89) | 0 | 0 | 22,3 | 0 | 0 | 0 |
| Otros | 18,4 | **51,1** (43-56) | 3,7 | 2,9 | 12,5 | 6,2 | 5,2 |
| Blanco y nulo | 12,2 | **48,9** (41-59) | 2,4 | 1,9 | 11,1 | 6,7 | 16,8 |
| No votó | 10,1 (5-16) | 0 (0-3) | 0 | 3,0 | 6,0 | 2,3 | 78,6 |

Intervalos: percentiles 5-95 de 300 remuestreos de municipios. Controles: reconstrucción 0,08 %;
fuera de muestra (5 grupos de municipios) 0,90 pp por categoría contra 2,07 de la predicción
ingenua, y 6,3 % de votos mal ubicados contra 14,5 %. Las cotas de Duncan-Davis no informan con 135
municipios (0 a 73-100 %).

**Lectura.** LLA-PRO creció recogiendo lo que en septiembre se había dispersado: dos tercios de
Provincias Unidas, la mitad de «otros» (vecinales y chicos) y la mitad del blanco, más uno de cada
diez votantes de Fuerza Patria. Los que se sumaron a votar en octubre no fueron a LLA-PRO. **Celdas
a tomar con cuidado:** Izquierda → Fuerza Patria (78 %) y No votó → Fuerza Patria (10 %) tienen
intervalos anchos y pueden estar compensando la pérdida de Fuerza Patria hacia LLA-PRO; con 135
unidades la matriz no separa bien esos flujos cruzados.

### Dónde cambió (cambio en % del padrón, Spearman parcial descontando universitarios, NBI, mayores de 65 y log población / electores)

| Variable | Cambio LLA-PRO | Cambio Fuerza Patria |
|---|---|---|
| Conurbano | **−0,49** | −0,05 |
| Intendente peronista (2023) | **−0,25** | **−0,34** |
| Voto vecinal a concejales en septiembre | **+0,23** | **+0,32** |
| Cambio de participación | −0,09 | **+0,31** |
| Nacidos en otro país / extranjeros en el padrón | **−0,42 / −0,41** | 0,0 |
| Universitarios, NBI, mayores de 65 | no pasan | no pasan |

En negrita lo que pasa los tres filtros (Benjamini-Hochberg sobre las 18 pruebas, y mismo signo y
|ρ| ≥ 0,1 sacando el municipio más influyente y los tres más influyentes).

- **El intendente peronista.** Con la zona también controlada el efecto sigue (−0,34 en Fuerza
  Patria, −0,22 en LLA-PRO). Con intendente peronista Fuerza Patria perdió 1,8 pp del padrón de
  septiembre a octubre; sin él, ganó 1,2. **En septiembre, con concejales en la boleta, el aparato
  municipal le sumó a Fuerza Patria; en octubre no estuvo.** No contradice al `100`: ahí la
  intendencia no arrastra en la elección *siguiente*; acá el intendente pesa cuando su lista está
  en la misma boleta.
- **El vecinalismo.** Donde había listas vecinales fuertes a concejal, ese voto se repartió en
  octubre entre los dos grandes.
- **Los extranjeros** van con el Conurbano: con la zona controlada su efecto es el de la zona.

### Lo que no dice

- 135 unidades, todo ecológico; la parte extranjera de septiembre es una estimación (la de 2023
  aplicada al padrón de 2025).
- Las categorías no son iguales: legisladores provinciales contra diputados nacionales, con
  candidatos distintos.

**Para el motor 2027:** la elección de Gobernador lleva intendentes y concejales en la misma
boleta, como septiembre y no como octubre. La diferencia entre municipios con y sin intendente
peronista (unos 3 pp del padrón entre una elección y otra) es una medida del peso del aparato
municipal cuando está en la boleta; es correlacional, no causal, y entra en el motor como
parámetro con rango, no como dato.

---

## 02-11-2026 · Lo que el territorio predice y lo que no (`analisis/104`)

**Por qué antes del motor.** En CABA el censo predecía muy bien el **nivel** de voto y nada el
**cambio**. Si en PBA es igual, el motor modela niveles con el territorio y cambios con un
movimiento común. Dos preguntas que en CABA no estaban: si el censo le gana a la **inercia** (el
mismo resultado en la elección anterior), y si el **cambio social 2010-2022** predice el cambio de
voto 2011-2023.

**Método.** Circuitos estables (997 para 2019-2025, 918 para 2011-2025). Voto en porcentajes,
nunca razones (la trampa del denominador de CABA). Fuera de muestra: GroupKFold por municipio,
ponderado por electores. Modelos: media, inercia, censo (elastic net y árboles), censo + inercia
y, para los cambios, **el nivel de partida solo** y censo + nivel de partida.

### R² fuera de muestra

| Objetivo | Inercia | Censo | Censo + inercia | Nivel de partida | Censo + nivel |
|---|---|---|---|---|---|
| Peronismo, Diputados 2025 | 0,89 | 0,62 / 0,68 | 0,90 | — | — |
| LLA-PRO, Diputados 2025 | 0,96 | 0,76 / 0,80 | 0,96 | — | — |
| Peronismo, Gobernador 2023 | 0,93 | 0,75 / 0,78 | 0,95 | — | — |
| Participación 2025 | 0,28 | 0,38 / 0,37 | 0,54 | — | — |
| Cambio peronismo, Gobernador 2019-2023 | 0,56 | 0,58 / 0,47 | 0,70 | 0,45 | 0,59 |
| Cambio peronismo, Diputados 2023-2025 | −0,08 | 0,18 / −0,06 | 0,18 | 0,16 | 0,19 |
| Captura de LLA-PRO, 2023-2025 | 0,05 | 0,38 / 0,42 | 0,39 | 0,50 | 0,56 |
| Cambio participación 2023-2025 | 0,45 | 0,28 / 0,11 | 0,62 | 0,02 | 0,39 |
| Cambio peronismo, Gobernador 2011-2023 | — | 0,28 / 0,33 | — | 0,26 | 0,34 |
| Cambio peronismo, Diputados 2011-2023 | — | 0,41 / 0,46 | — | 0,30 | 0,40 |

Censo: elastic net / árboles. Inercia en los cambios = el cambio de la elección anterior.

**Tres lecturas:**

1. **El nivel es inercia.** La elección anterior predice 0,89-0,96 del nivel de cada circuito; el
   censo agrega entre medio punto y punto y medio de R². Para el motor, el punto de partida de
   cada circuito es su último resultado, no su perfil censal.
2. **El cambio es proporcional.** Casi todo lo que «se predice» del cambio es que los circuitos
   con más voto de una fuerza pierden (o ganan) más puntos: es el nivel de partida (0,16 a 0,50
   solo). El censo agrega encima entre 0,03 y 0,14. **Diferencia con CABA**: allá el cambio era
   impredecible; acá es predecible en la medida en que es proporcional. El motor tiene que aplicar
   el movimiento común en forma **proporcional**, no uniforme (mismos puntos en todos lados).
3. **La participación es otra cosa.** La inercia la predice mal (0,28: se pasa de una presidencial
   a una de medio término) y el censo ayuda de verdad (0,54 juntos). Su cambio tiene la señal
   territorial más fuerte de todo el análisis.

### La batería sobre los cambios

Spearman parcial descontando NBI, universitarios, dos tramos de edad, log(población / electores)
**y el nivel de partida** (sin él, la batería redescubre el cambio proporcional: en la primera
corrida pasaban 98 pruebas, con él 81). Benjamini-Hochberg sobre las 202 pruebas y fragilidad por
Cook (sin el circuito más influyente y sin los tres).

| Cambio | Pasan | Lo más fuerte (Spearman parcial) |
|---|---|---|
| Participación 2023-2025 | 26 de 41 | densidad +0,38, viviendas rurales −0,34, mujeres +0,32, secundario incompleto −0,30 |
| Peronismo, Gobernador 2019-2023 | 16 de 41 | patrones −0,20, servicio doméstico −0,17, densidad +0,16, nacidos en otro país +0,16 |
| Peronismo, Diputados 2023-2025 | 12 de 41 | rural +0,17, cuentapropia −0,17, densidad −0,15, jubilados +0,15 |
| Captura de LLA-PRO 2023-2025 | 8 de 41 | NBI de vivienda +0,17, hogares migrantes +0,16, jubilados −0,15, nacidos en otro país +0,15 |
| Peronismo, Gobernador 2011-2023 | 10 de 19 | cambio en gas de red −0,24, en agua de red −0,18, en ruralidad +0,17 |
| Peronismo, Diputados 2011-2023 | 9 de 19 | cambio en gas de red −0,28, en ruralidad +0,21, en agua de red −0,17 |

- **Efectos chicos.** En el voto, nada pasa de |ρ| = 0,28. Pasan muchos porque con ~1.000
  circuitos hay potencia; la magnitud es lo que importa.
- **2011-2023:** el peronismo cayó más donde más se extendieron el gas y el agua de red, y menos
  donde aumentaron la ruralidad, el hacinamiento y los materiales precarios. Es ecológico: el gas
  nuevo marca barrios que se consolidaron y cambiaron de composición, no un efecto del gas.
- **2023-2025:** el peronismo resistió en lo rural y entre jubilados; LLA-PRO avanzó relativamente
  en barrios populares con migrantes; la participación cayó más en lo rural y de baja educación.

### Para el motor 2027

- **Nivel:** el último resultado de cada circuito.
- **Movimiento:** común a toda la provincia (`101`) y **proporcional** al nivel de cada fuerza.
- **Ajuste territorial:** chico, con el censo; sirve sobre todo para la participación.
- **La participación** se modela aparte: depende del tipo de elección y del desdoblamiento (`103`),
  y es lo que más varía entre territorios.

---

## 02-11-2026 · El motor 2027 (`analisis/105` y `106`)

### Qué hace y qué no

Gobernador se gana por **simple pluralidad provincial**, sin balotaje. El nivel provincial de
cada fuerza en 2027 es un **parámetro del escenario**, no algo que el motor adivine: de la
legislativa a la de Gobernador siguiente el margen peronismo − derecha se movió +19,8 puntos
(2017 → 2019) y +2,5 (2021 → 2023). Lo que el motor sí hace es lo que se puede examinar contra el
pasado: **bajar ese nivel al territorio** y contar lo que es aritmética (padrón 2027, extranjeros,
participación), con una incertidumbre calibrada.

### Paso 1: el backtest (`105`)

Dado el resultado provincial **real** de la elección t1, ¿qué regla reproduce mejor el mapa
partiendo de t0? 13 pares 2011-2025 (Gobernador → Gobernador, Diputados → Diputados y los
**análogos a 2027**: de la legislativa a la de Gobernador, 2013→2015, 2017→2019, 2021→2023).
Bloques: peronismo, derecha (PRO/JxC + LLA + LLA-PRO), tercera (tercera vía + centro/UCR),
izquierda, resto.

| Regla | Error medio por municipio (pp) | Error del margen (pp) | Acierta ganador municipal | Acierta ganador de sección |
|---|---|---|---|---|
| Sin cambio | 12,4 | 21,7 | 55 % | 61 % |
| Uniforme | 2,9 | 4,8 | 88 % | 96 % |
| Proporcional | 2,7 | 5,0 | 90 % | 96 % |
| **Mezcla (mitad y mitad)** | **2,7** | **4,8** | **89 %** | **97 %** |

La proporcional gana en error medio y la uniforme en el margen; en 2023, cuando entró LLA, la
uniforme anduvo mejor. La mezcla queda cerca de la mejor en todo: es la que usa el motor. Los
peores pares son los de 2013-2015 (entra el Frente Renovador): 5-6 pp por municipio.

**El ruido.** Residuo por municipio de la mezcla, en cociente logarítmico peronismo / derecha.
Calibrarlo enseñó tres cosas, en este orden:

1. Un único desvío mezcla regímenes: con oferta estable es 0,09-0,15; cuando entra una fuerza
   grande nueva, 0,21-0,34. Se separan.
2. Aun separado, el intervalo del 80 % cubría 69 %. La causa: **el error depende del tamaño del
   municipio** (0,30 en los más chicos, 0,09 en los más grandes), y se estaba midiendo con
   cuantiles dominados por los grandes y cobertura dominada por los chicos. Se modela
   σ ∝ votos^−0,29.
3. Con eso y una t de 5 grados (oferta estable) o normal (oferta nueva), la calibración dejando un
   par afuera da **52 / 79 / 90 / 95 %** de cobertura para intervalos de 50 / 80 / 90 / 95 %
   (oferta estable) y 54 / 80 / 89 / 94 % (oferta nueva).

### Paso 2: el motor (`106`)

- **Bases.** Octubre 2025 por circuito (nativos): peronismo 40,9, derecha 41,5. Septiembre 2025
  sólo nativos (el `103`), bajado a circuito con el patrón de octubre dentro de cada municipio:
  46,7 y 33,9.
- **Padrón 2027:** el de 2025 crecido al ritmo de 2023-2025 de cada circuito: 13,60 M de nativos.
  Extranjeros: 1,05 M, con la participación y el reparto de sus mesas de Gobernador 2023 en cada
  municipio (votan Gobernador).
- **Participación:** parámetro provincial; cada circuito conserva su distancia al promedio
  (escala del odds), con el patrón de Gobernador 2023. Por defecto 76 %.
- **Monte Carlo** (1.000 simulaciones): shock provincial en el margen, t de 5 grados con desvío de
  2 pp (confianza en el nivel del escenario, no pronóstico); ruido municipal del `105`; el ruido
  se reajusta para no cambiar el nivel provincial.

**Control:** sin ruido, el escenario octubre da 39 municipios donde el peronismo le gana a la
derecha (reales: 36) y el de septiembre 100 (reales: 104). Contando el primer puesto entre todas
las fuerzas, septiembre da 95: en 4 municipios sale primera la tercera vía. La diferencia es el padrón 2027 y el voto extranjero.

### Escenarios

| Escenario | Peronismo | Derecha | Margen (p10 a p90) | P(gana el peronismo) | Municipios peronistas |
|---|---|---|---|---|---|
| A · Octubre 2025 se repite | 41,5 | 41,3 | +0,3 (−2,0 a +2,5) | 57 % | 39 |
| B · Septiembre 2025 se repite | 47,2 | 33,9 | +13,4 (+11,1 a +15,6) | 100 % | 95 |
| C · Punto medio | 44,4 | 37,6 | +6,8 (+4,5 a +9,0) | 100 % | 58 |
| D · Tercera vía fuerte (12 %, 2/3 de la derecha) | 38,7 | 35,7 | +3,1 (+0,8 a +5,3) | 95 % | 46 |
| A1 · Octubre, participación 64 % | 41,6 | 41,3 | +0,4 | 61 % | 39 |
| A2 · Octubre, participación 80 % | 41,5 | 41,3 | +0,3 | 56 % | 38 |
| A3 · Octubre, extranjeros al 45 % | 41,7 | 41,3 | +0,5 | 62 % | 39 |

(% de los votos positivos, con nativos y extranjeros y el padrón 2027.)

**Lecturas:**

- **La elección la decide la preferencia, no el padrón.** El padrón 2027 con los extranjeros le
  suma al peronismo menos de un punto de margen; que los extranjeros voten al 45 % en vez de al
  29 %, 0,2; subir o bajar la participación con el mismo patrón territorial, 0,1. Lo que mueve
  13 puntos es que el votante se comporte como en septiembre o como en octubre (`103`).
- **La tercera vía le saca a la derecha.** Con Provincias Unidas en 12 % (dos tercios desde la
  derecha), el peronismo gana con 38,7 %.
- **El mapa.** Con empate provincial el peronismo gana 40 de 135 municipios: su voto está
  concentrado. Necesita +4 de margen para ganar la mitad y +12 para 78. Por sección: la 3ª la
  gana siempre, la 1ª se da vuelta en el empate, la 8ª (La Plata) cerca de +4 y las del interior
  (2ª, 4ª, 5ª, 6ª, 7ª) recién arriba de +10 (`motor_2027_grilla.csv`).

### Lo que falta (PLAN 4.3-4.5)

- **Derecha dividida**: LLA y PRO por separado, con el patrón de 2023.
- **Legislatura** por sección con cociente.
- **Movilización diferencial**: hoy la participación sube o baja pareja respecto del patrón; el
  `103` y el `104` muestran que quién va a votar cambia según la elección. Eso es lo que separa
  septiembre de octubre, y el motor todavía no lo modela: lo trata como preferencia.

---

## 02-11-2026 · La derecha dividida (`analisis/107`)

**La pregunta.** En 2025 LLA y el PRO fueron juntos. Si en 2027 van separados, con simple
pluralidad y sin balotaje el peronismo gana con menos votos. La pregunta útil es cuánto.

**Cómo.** El motor (`106`) se generalizó: en cada simulación el bloque de la derecha de cada
circuito se parte entre LLA y el PRO con el patrón de **Gobernador 2023** (Píparo contra Santilli,
sólo nativos), corrido para dar el reparto provincial del escenario (más una incertidumbre de 3
pp en ese reparto). Ruido municipal del reparto: calibrado con el único par con las dos fuerzas,
Diputados 2021 → Gobernador 2023, que tiene error medio de 5 pp por municipio y correlación 0,72 (el
reparto PRO / LLA es tres veces más ruidoso que el de peronismo / derecha; en 2019 no hubo lista
libertaria a diputados en PBA). Los extranjeros se reparten con el patrón de su municipio. **No se
modela el voto útil**: concentrarse en el que mejor mide equivale a un reparto más desparejo, y la
grilla lo cubre.

### Escenarios (% de los positivos, padrón 2027 con extranjeros)

| Base | Derecha | Peronismo | LLA | PRO | P(gana el peronismo) | Municipios peronismo / LLA / PRO |
|---|---|---|---|---|---|---|
| Octubre 2025 | unida | 41,5 | 41,3 (juntos) | — | 57 % | 39 / 96 (juntos) |
| Octubre 2025 | PRO 52 % (como 2023) | 41,6 | 19,9 | 21,4 | 100 % | 102 / 7 / 26 |
| Octubre 2025 | PRO 35 % | 41,6 | 26,9 | 14,4 | 100 % | 99 / 31 / 5 |
| Octubre 2025 | PRO 25 % | 41,6 | 31,0 | 10,2 | 100 % | 82 / 52 / 1 |
| Octubre 2025 | PRO 15 % | 41,6 | 35,2 | 6,1 | 99 % | 63 / 72 / 0 |
| Punto medio | PRO 25 % | 44,4 | 28,3 | 9,3 | 100 % | 103 / 32 / 0 |
| Septiembre 2025 | PRO 25 % | 47,2 | 25,5 | 8,4 | 100 % | 111 / 13 / 0 |

### La grilla: cuánto puede perder el peronismo contra la derecha unida

Probabilidad de que el peronismo salga primero, según su margen sobre la derecha **unida** (base
octubre) y la parte del PRO dentro de la derecha:

| Margen sobre la derecha unida | PRO 10 % | 20 % | 30 % | 40 % | 50 % |
|---|---|---|---|---|---|
| −20 | 0 | 0 | 0,01 | 0,81 | 1 |
| −16 | 0 | 0 | 0,41 | 0,95 | 1 |
| −12 | 0 | 0,35 | 0,96 | 1 | 1 |
| −8 | 0,10 | 0,76 | 1 | 1 | 1 |
| −4 | 0,76 | 1 | 1 | 1 | 1 |
| 0 | 1 | 1 | 1 | 1 | 1 |

Coincide con la cuenta a mano (el peronismo gana si su margen sobre la derecha unida supera
−T·p/(2−p), con T la suma de los dos y p la parte del PRO), corrida ~1 punto a favor del
peronismo por el padrón 2027 y los extranjeros.

**Lecturas.**

- **La división de la derecha vale más que cualquier palanca de padrón.** Con el PRO en un 20 % de
  la derecha, el peronismo puede perder por ~10 puntos contra la derecha unida y seguir primero.
  La participación y los extranjeros juntos mueven menos de un punto (`106`).
- **Para la derecha, la unidad decide la elección**; dividida, sólo gana si el PRO queda reducido
  a menos del ~10 % de su espacio y la derecha unida le ganaría al peronismo por más de 4 puntos.
- **El mapa.** Dividida, la derecha pierde también los municipios: con un reparto como el de 2023
  el PRO conserva 26 municipios del interior y LLA casi ninguno.

### Lo que no dice

- El patrón PRO / LLA de 2023 puede no ser el de 2027 (en 2023 LLA recién llegaba); por eso su ruido
  es grande.
- No hay voto útil ni transferencias hacia otros espacios al dividirse: la derecha dividida suma lo
  mismo que unida. Si al dividirse pierde votos hacia la tercera vía o la abstención, el resultado
  es todavía mejor para el peronismo.
