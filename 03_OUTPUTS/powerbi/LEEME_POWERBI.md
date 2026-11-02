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

## El mapa

No usa el visual de mapa de formas (en versión preliminar, por eso no aparecía): lo dibuja la
medida **Mapa Provincia** (y **Mapa Conurbano**) como una imagen SVG que se recalcula con cada
filtro. Se muestra en una tabla de una celda; si se ve chico, *Formato > Cuadrícula > Alto de la
imagen*.

## Privacidad

`datos_privados/` (CRM, oportunidad, noticias) no se sube a GitHub: está en `.gitignore`.
