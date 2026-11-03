# Intendencias PBA 2027 · Power BI

El «Super Excel» de Intendencias PBA 2027 de Atlas Analytics llevado a Power BI, más el análisis
electoral de Atlas PBA (elecciones 2007-2025, censo, motor de escenarios 2027).

## Abrir

1. Correr una vez, en este orden (desde la raíz del repo):
   `python 02_SCRIPTS/etl/13_super_excel_intendencias.py` (lee el Excel de `E:\INTENDENTES 2027 PBA`)
   y `python 02_SCRIPTS/productos/p07_powerbi_intendencias.py`.
2. Abrir `Atlas_PBA.pbip` con Power BI Desktop (2024 o posterior; si es anterior a 2025, activar en
   *Opciones > Características en versión preliminar* «Formato de proyecto (.pbip)» y «PBIR»).
3. **Actualizar**. Si los datos están en otra carpeta: *Transformar datos > Administrar parámetros*
   → `CarpetaDatos` (03_OUTPUTS/powerbi/datos/) y `CarpetaPrivada` (03_OUTPUTS/powerbi/datos_privados/),
   las dos con barra final.

## Páginas

| Página | Qué tiene |
|---|---|
| Inicio | Menú con botones a cada página, 8 tarjetas de resumen, accesos al simulador y al tablero web |
| Dashboard | Filtros en botones (sección, espacio 2026, escenario 2027, tamaño, concejales 2025, oportunidad), tarjetas, barras, dona y tabla con colores por espacio, escenario y oportunidad |
| Mapa | Mapa de la Provincia y del Conurbano con **10 capas**: espacio 2026, escenario 2027, concejales 2025, fuerza del intendente, oportunidad, ganador de cualquier elección 2007-2025, % peronismo, motor 2027, NBI, barrios populares. Lo filtrado se apaga y el municipio elegido se resalta |
| Ficha | Página de **obtención de detalles** (clic derecho en un municipio > Obtener detalles > Ficha) o con su propio selector: foto, datos, enlaces (mapa, noticias, perfil PDF, Wikipedia), prospectos, noticias y evolución del voto |
| Prospectos | CRM de 980 personas: filtros por rol, prioridad, fuerza, estado; tarjetas y tabla |
| Noticias | 856 titulares con enlace; filtro de fechas, medios y municipios |
| Elecciones | **Dispersión animada** 2007-2025 (eje de reproducción: ▶), % por fuerza y evolución |
| Análisis 2027 | Hallazgos, margen por escenario del motor, municipios por probabilidad |
| Información emergente | Al pasar el mouse sobre un municipio en tablas y gráficos: foto y datos clave |

## Los mapas

- **Interactivos** (Mapa político, 2027, 2025, Motor 2027): visual **Mapa de formas** con el contorno
  de los 135 municipios incrustado. Clic en un municipio filtra la página; al pasar el mouse aparece
  la ficha rápida con foto. Requiere activar una vez *Archivo > Opciones y configuración > Opciones >
  Características en versión preliminar > Objeto visual de mapa de formas* y reiniciar Power BI.
- **10 capas** (imagen): la medida **Mapa Provincia** / **Mapa Conurbano** dibuja un SVG que se
  recalcula con cada filtro; no es clicable, se maneja con la capa, los filtros y la tabla.

## Privacidad

`datos_privados/` (CRM, oportunidad, noticias) no se sube a GitHub: está en `.gitignore`.

## Tablero «Voto PBA» (`Atlas_PBA_Voto.pbip`)

Proyecto aparte, sólo con datos públicos de votación (sin CRM): se puede publicar en Power BI Service.
Se genera con `python 02_SCRIPTS/productos/p08_powerbi_voto.py`.

Páginas: Inicio · Mapas (ganador, % peronismo, participación, motor 2027) · Secciones · Evolución
(animación 2007-2025) · Territorio (voto y censo) · Ficha del municipio (clic derecho > Obtener
detalles) · información emergente al pasar el mouse.

Antes de abrirlo, una sola vez: *Archivo > Opciones y configuración > Opciones > Características en
versión preliminar > «Objeto visual de mapa de formas»*, y reiniciar Power BI. Al abrirlo, *Inicio >
Actualizar* para cargar los datos.

## Tablero «ATLAS PBA 2027» (`ATLAS_PBA_2027.pbip`) · sistema de diseño ATLAS

Mismo diseño que los tableros de Brasil 2026 y CABA 2027 (barra lateral, fondo claro, tarjetas
blancas). Datos públicos en `datos_2027/`. Se genera con
`python 02_SCRIPTS/productos/p09_powerbi_pba2027.py` (usa `pbi_atlas.py`, copia de la biblioteca del
tablero de CABA).

Páginas: Inicio · Mapa completo · Resumen provincial · Mapa de municipios (13 métricas) · Conurbano ·
Secciones electorales · Mapa fino (1.146 circuitos) · Explorador · Corrimientos · Dónde se decide ·
Intendentes 2027 · Pronóstico 2027 · Simulador · Historia 2007-2025 (animada) · Metodología · Ficha del
municipio (clic derecho > Obtener detalles) · tooltip. La entrega 2 está en `p09_entrega2.py`. El mapa es una imagen SVG calculada con DAX:
no necesita activar ninguna versión preliminar y se ve igual en Power BI web.
