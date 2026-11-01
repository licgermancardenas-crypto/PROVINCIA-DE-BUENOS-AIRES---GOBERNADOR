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
