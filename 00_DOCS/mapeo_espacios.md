# Mapeo de espacios políticos · decisiones para validar

Las reglas están en [`config/reglas_mapeo.yaml`](../config/reglas_mapeo.yaml) y las aplica
`02_SCRIPTS/etl/08_mapeo_espacios.py`. El resultado, fila por fila, en
[`config/mapeo_espacios.csv`](../config/mapeo_espacios.csv): ahí se puede corregir cualquier
caso puntual completando `espacio_override`, sin tocar la regla.

**Estado: validado por Germán el 01-11-2026**, que aceptó las nueve recomendaciones (D1-D9).
Las decisiones de abajo son las que no salen de los datos; cada una trae su peso (el máximo %
que esa lista sacó en alguna categoría). Único pendiente: verificar los candidatos de
Propuesta Federal para el Cambio (D4, 2,8 % en octubre 2025).

---

## Los espacios

| Espacio | Qué es | Ejemplos |
|---|---|---|
| `PERONISMO` | El frente peronista principal y sus aliados que van aparte | FPV, Unidad Ciudadana, Frente de Todos, Unión por la Patria, Fuerza Patria |
| `TERCERA_VIA` | Peronismo no kirchnerista y sus alianzas de centro | Massa 2013-2017 (Frente Renovador, UNA, 1País), Duhalde, Rodríguez Saá, De Narváez 2013, Randazzo, Lavagna, Schiaretti, Somos |
| `PRO_JXC` | PRO y sus alianzas | Unión PRO, Cambiemos, Juntos por el Cambio, Juntos |
| `LLA` | Libertarios | Espert 2019, Avanza Libertad 2021, LLA 2023 |
| `LLA_PRO` | La alianza de 2025 | Alianza La Libertad Avanza (con el PRO adentro) |
| `CENTRO_UCR` | UCR sola, Coalición Cívica, progresismo no peronista | FAP, Frente Progresista Cívico y Social, Progresistas (Stolbizer), GEN |
| `IZQUIERDA` | FIT y la izquierda trotskista | FIT, FIT-U, MAS, PO, MST |
| `VECINAL` | Partidos de un municipio | Espacio Abierto (San Nicolás), Acción Marplatense, Nuevo Morón |
| `OTROS` | El resto | NOS, Valores, Unión con Fe, Frente Patriota |

**`TERCERA_VIA` es el espacio que en CABA no hacía falta y en PBA es indispensable.** Ganó la
provincia en 2013 (Frente Renovador, 43,5 % en Diputados provinciales) y sacó 21 % en 2015 y
11-16 % en 2017. Mezclarlo con el peronismo o con «otros» borra la elección de 2013.

---

## Decisiones abiertas

| | Caso | Peso | Propuesta | Alternativa | Recomendación |
|---|---|---|---|---|---|
| **D1** | Alianza La Libertad Avanza 2025 (provincial y nacional) | 41,5 % | `LLA_PRO`, espacio aparte | Sumarla a `LLA` | **Aparte.** El PRO está adentro y su voto no se puede separar. Para el motor 2027: si la alianza se repite, se modela LLA+PRO como un bloque con 2023 = LLA + JxC |
| **D2** | Somos Buenos Aires (sept. 2025) y Provincias Unidas (oct. 2025) | 7,0 % / 2,4 % | `TERCERA_VIA` | `CENTRO_UCR` | **Tercera vía.** Mitad UCR, mitad intendentes peronistas no K; la marca la sostienen los gobernadores de Provincias Unidas |
| **D3** | Libertarios por fuera de la alianza en 2025 (Unión y Libertad, Partido Libertario, Unión Liberal) | 1,4 % | `LLA` | `OTROS` | **LLA.** Es voto libertario que no aceptó el acuerdo con el PRO |
| **D4** | Listas 2025 sin composición verificada (Propuesta Federal para el Cambio, Potencia, Nuevos Aires, Nuevo Buenos Aires, Unión Federal, Es con Vos) | hasta 2,8 % | `OTROS` | según candidatos | **Verificar candidatos** de Propuesta Federal (2,8 %) antes de cerrar; el resto pesa menos de 1,4 % |
| **D5** | PJ y Frente Justicialista en 2005 | 14,3 % | `TERCERA_VIA` | `PERONISMO` | **Tercera vía.** Es la lista de Duhalde (Chiche) contra la de Cristina (FPV): la elección de 2005 fue una interna peronista abierta |
| **D6** | UDESO 2011 (De Narváez + Alfonsín) | 17,1 % | Por categoría: `TERCERA_VIA` en Gobernador y Legislatura, `CENTRO_UCR` en las nacionales | Todo a uno de los dos | **Por categoría**, como está: el candidato a gobernador era De Narváez y el presidencial, Alfonsín |
| **D7** | Concertación UNA 2007 (Lavagna con la UCR) | 7,6 % | `CENTRO_UCR` | `TERCERA_VIA` | **Centro/UCR.** La estructura que la sostuvo fue la UCR |
| **D8** | Nuevo Encuentro 2011 (Sabbatella) | 6,5 % | `PERONISMO` | `IZQUIERDA` | **Peronismo.** Lista propia a gobernador pero colectora de Cristina |
| **D9** | UCeDe 2005-2007 | 2,9 % | `OTROS` | `LLA`, `PRO_JXC` | **Otros.** Anterior al ciclo libertario; ponerla en LLA fabrica una continuidad que no existe |

Casos menores marcados `ambiguo` (menos de 1,5 %): Proyecto Sur, Libres del Sur, Patria Grande,
Recrear 2007, la lista «Vamos» de 2007. La lista completa con pesos sale en
`03_OUTPUTS/tablas/mapeo_ambiguos.csv` en cada corrida.

---

## La regla de los partidos locales

Una lista que no matchea ninguna regla y compite **sólo en categorías municipales**
(intendente, concejales, consejeros escolares) **o en dos municipios o menos** se clasifica
`VECINAL`. Son 1.342 filas y 1,5 % de los votos positivos de todo el inventario; en categorías
provinciales o nacionales, 0,004 %. Las colectoras de los frentes grandes en el nivel municipal
llevan el nombre del frente y caen en su espacio por regla, no por esta.

## Controles

- **Cobertura:** 0,08 % de los votos positivos queda `SIN_REGLA` (ninguna lista sin regla pasa
  de 0,4 % en su categoría).
- **Dos fuentes, el mismo resultado.** El mismo mapeo sobre el provisorio de la DINE (por mesa)
  y el definitivo de la Provincia (por municipio) da lo mismo: en Gobernador, Diputados y
  Senadores provinciales 2011-2023, la diferencia máxima por espacio es de 0,17 puntos.
  Ver `03_OUTPUTS/tablas/control_mapeo_provinciales.csv`.
