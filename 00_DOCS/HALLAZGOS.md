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
