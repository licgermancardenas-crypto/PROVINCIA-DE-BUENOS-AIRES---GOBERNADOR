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
