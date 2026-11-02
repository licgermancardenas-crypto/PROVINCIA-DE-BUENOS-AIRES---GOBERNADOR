# Atlas PBA · proyecto de Power BI

Tablero electoral de la Provincia de Buenos Aires para **Power BI Desktop** (formato de proyecto
PBIP: modelo en TMDL y reporte en PBIR, todo texto y versionable).

## Abrir

1. Power BI Desktop (2024 o posterior). Si es anterior a 2025, activar en *Archivo > Opciones >
   Características en versión preliminar* «Formato de proyecto de Power BI (.pbip)» y «Almacenar
   informes con el formato de metadatos mejorado (PBIR)».
2. Abrir `Atlas_PBA.pbip`.
3. Si los datos no están en `E:\PROVINCIA DE BUENOS AIRES ELECCIONES\03_OUTPUTS\powerbi\datos`, cambiar el parámetro **CarpetaDatos** (*Transformar datos >
   Administrar parámetros*) a la carpeta `03_OUTPUTS/powerbi/datos/` con la barra final.
4. **Actualizar** (Inicio > Actualizar). Los CSV se regeneran con `python 02_SCRIPTS/productos/p04_tablero_datos.py`
   y `p06_powerbi.py`.

## El mapa (una vez por mapa)

El mapa de municipios usa el visual **Mapa de formas** (Shape map) con un archivo propio, porque
los mapas de Bing fueron retirados. En cada uno de los tres mapas (páginas Territorio político,
Elecciones y Escenarios 2027):

*Formato > Forma del mapa > + Agregar mapa* → elegir `datos/pba_municipios.topojson` → en
*Ver tipos de mapa* asociar la clave **cod_indec**.

Si el visual no aparece, activar *Opciones > Características en versión preliminar > Objeto visual
de mapa de formas*.

## Qué tiene

| Página | Contenido |
|---|---|
| Territorio político | Filtros (municipio, sección, zona, fuerza), tarjetas (municipios, población, electores, participación), mapa por fuerza del intendente, tabla con foto, logo y enlace a Wikipedia, dona de población gobernada, columnas por sección |
| Elecciones | 17 elecciones 2007-2025: ganador, % del ganador, margen, participación; mapa del ganador por municipio; % por fuerza; evolución histórica (no se filtra por la elección elegida); tabla de municipios |
| Censo y gestión | NBI, barrios populares, universitarios, escuelas, transferencias; dispersión NBI × voto peronista; ranking con indicadores de servicios, gestión fiscal y seguridad |
| Escenarios 2027 | Motor de Atlas PBA: municipios peronistas esperados, municipios en disputa, mapa por categoría de probabilidad, tabla; botones al simulador y a la metodología |

Navegación con botones en el encabezado de cada página. Las fotos son de Wikimedia Commons (licencia
libre) y se cargan desde internet; sólo están cuando el intendente en ejercicio es el electo en 2023.

## Medidas principales (tabla Medidas)

`Votos`, `% Voto`, `% Peronismo`, `% Derecha`, `Ganador`, `% Ganador`, `Margen (pts)`, `Electores`,
`Participación`, `Municipios`, `Población`, `Hogares con NBI %`, `Hogares en barrios populares %`,
`Universitarios %`, `Transferencias por habitante`, `P(peronismo) 2027`, `Municipios peronistas
esperados`, `Municipios en disputa`. Si no hay una elección elegida, las de votación usan
Diputados nacionales 2025.

## Verificación

El reporte se validó contra los esquemas públicos de PBIR de Microsoft. El modelo TMDL no tiene
validador público: si Desktop marca un error al abrir, el mensaje indica archivo y línea en
`Atlas_PBA.SemanticModel/definition/`.
