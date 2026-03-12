# IDV — Identificación De Valor
## Ronda 02–08 Marzo 2026

Pipeline automatizado de scouting para **identificar partidos prioritarios** donde juegan jugadores Sub-23 de alto rendimiento en ligas de Sudamérica y Argentina.

---

## ¿Qué hace este proyecto?

El sistema procesa datos de ~52 partidos de **Brasil, Colombia y Argentina** durante la semana del 2 al 8 de marzo de 2026, y genera un **ranking priorizado de partidos** para scouting en vivo o análisis de vídeo.

Para cada partido calcula el **MPS (Match Priority Score)**: una puntuación que combina la densidad de jugadores U23, sus ratings en SofaScore y el peso competitivo de la liga. Los partidos se ordenan por **Z-Score** y se clasifican en 5 niveles de prioridad.

El resultado final son dos PDFs:
- `desglose_detallado_IDV_ronda_02-08_mar.pdf` — Ranking completo de partidos con desglose por jugadores U23
- `ANEXOS_ACUMULADOS_U23_U21.pdf` — Acumulado de rendimiento U23/U21 en la temporada

---

## Ligas cubiertas

| Liga | País | Peso |
|---|---|---|
| Paulista A1 | Brasil | 0.90 |
| Paranaense | Brasil | 0.90 |
| Carioca | Brasil | 0.85 |
| Gaúcho | Brasil | 0.85 |
| Baiano | Brasil | 0.85 |
| Copa Brasil | Brasil | 0.75 |
| Mineiro | Brasil | 0.78 |
| Paulista A2 | Brasil | 0.65 |
| Primera B Metro | Argentina | variable |
| Colombia Segunda División | Colombia | 0.60 |

---

## Estructura del proyecto

```
RONDA_02-08_03_26/
├── data/
│   ├── 20260309.csv                          # Raw: datos brutos SofaScore
│   ├── jugadores_ronda_nueva.csv             # Todos los jugadores con minutos
│   ├── jugadores_ronda_nueva_procesado.csv   # Procesado con edades y U23 flag
│   ├── jugadores_completo_con_pbm.csv        # Integrado con Primera B Metro
│   ├── PARTIDOS_COMPACTO_CON_MPS.csv         # Ranking final de partidos (MPS + Z-Score)
│   ├── partidos_completos.json               # Detalle de partidos
│   ├── descripciones_partidos.json           # Descripciones generadas por IA
│   ├── ratings_acumulados_sofascore.csv/json # Ratings acumulados temporada
│   ├── u23_acumulado_completo.csv/json       # Acumulado U23 temporada
│   ├── u23_acumulado_por_rondas.csv/json     # U23 desglosado por rondas
│   ├── u23_ratings_por_partido.json          # Ratings U23 por partido
│   ├── jugadores_jornada_primerabmetro_reap.json  # Jugadores REAP en PBM
│   └── team_id_mapping_pbm.json             # Mapping IDs de equipos PBM
│
├── scripts/
│   ├── 1_scraping/
│   │   ├── scraper_ronda_nueva.py            # Scraper principal (Brasil + Colombia)
│   │   ├── scraper_ronda_nueva_completo.py   # Versión completa con más ligas
│   │   ├── scraper_nueva_ronda_primerabmetro.py  # Scraper Primera B Metro
│   │   ├── obtener_ratings_acumulados_sofascore.py  # Ratings acumulados vía API
│   │   ├── obtener_ratings_selenium.py       # Ratings vía Selenium (fallback)
│   │   ├── obtener_todos_u23_completo.py     # Extracción completa U23
│   │   ├── obtener_u23_playoffs.py           # U23 en playoffs
│   │   ├── obtener_u23_por_rondas.py         # U23 desglosado por rondas
│   │   └── extraer_ratings_por_partido.py    # Ratings individuales por partido
│   │
│   ├── 2_processing/
│   │   ├── calcular_mps.py                   # Cálculo de MPS y ranking de partidos
│   │   ├── recalcular_zscore_grupos.py       # Z-Score por grupos (CON/SIN rating)
│   │   ├── integrar_primera_b_metro.py       # Integración datos Primera B Metro
│   │   ├── procesar_fechas.py                # Normalización de fechas
│   │   ├── procesar_u23_con_partidos.py      # Procesamiento U23 con contexto de partido
│   │   ├── procesar_u23_partidos.py          # Procesamiento básico U23
│   │   ├── procesar_u23_primera_b_metro.py   # U23 específico de PBM
│   │   ├── generar_resumen_u23_partidos.py   # Resumen estadístico U23
│   │   └── generar_descripciones_chatgpt.py  # Generación de descripciones con IA
│   │
│   ├── 3_pdf_generation/
│   │   ├── generar_pdf_ronda_nueva.py        # PDF principal de la ronda
│   │   ├── generar_pdf_anexos_acumulados.py  # PDF de anexos U23/U21 acumulados
│   │   └── corregir_problemas_pdf.py         # Correcciones de layout PDF
│   │
│   └── utils/
│       ├── config_primerabmetro.py           # Config y umbrales para PBM
│       ├── descargar_escudos.py              # Descarga logos de equipos SofaScore
│       ├── copiar_escudos_pbm.py             # Copia logos PBM
│       ├── crear_mapping_logos.py            # Genera CSV de mapeo logos↔equipos
│       ├── corregir_team_names.py            # Normalización de nombres de equipos
│       ├── fuzzy_match_pbm.py                # Fuzzy matching jugadores PBM
│       ├── obtener_team_ids_pbm.py           # Obtiene IDs de equipos PBM
│       ├── filtrar_reap_alto.py              # Filtra jugadores con REAP ≥ 1.29
│       ├── jugadores_reap_alto.py            # Listado jugadores REAP alto
│       ├── jugadores_reap_mayor_129.py       # Jugadores REAP > 1.29
│       ├── mostrar_reap_alto.py              # Visualización REAP alto
│       ├── monitor_progreso.py               # Monitor de progreso del scraping
│       ├── verificar_chiqueti.py             # Verificación de casos específicos
│       └── verificar_reap.py                 # Verificación de valores REAP
│
├── output/
│   ├── desglose_detallado_IDV_ronda_02-08_mar.pdf  # PDF principal
│   └── ANEXOS_ACUMULADOS_U23_U21.pdf               # Anexos acumulados
│
└── team_logos/                               # Escudos de equipos (PNG por team_id)
```

---

## Fórmula MPS (Match Priority Score)

El MPS pondera la densidad de jugadores U23, su rendimiento (rating) y el nivel competitivo de la liga:

**Partidos CON rating SofaScore:**
```
MPS = (Densidad_U23 × 5) + (Rating_Normalizado × 3) + (Peso_Liga × 2)
```

**Partidos SIN rating (Primera B Metro, Copa Brasil temprana):**
```
MPS = (Densidad_U23 × 7) + (Peso_Liga × 3)
```

Donde:
- `Densidad_U23 = n_U23_con_>60min / max_U23_global_ronda`
- `Rating_Normalizado = rating_promedio_U23 / 10`
- `Peso_Liga` = coeficiente de calidad de la liga (0.60 – 0.90)

### Z-Score por grupos

El ranking final aplica **Z-Score por grupos separados** para evitar comparaciones injustas entre partidos con y sin rating:

| Grupo | Descripción |
|---|---|
| `Resto CON rating` | Ligas brasileñas con ratings SofaScore disponibles |
| `Colombia CON rating` | Colombia 2ª División (normalizado por separado) |
| `SIN rating` | Primera B Metro + Copa Brasil (sin ratings individuales) |

### Niveles de prioridad

| Prioridad | Percentil Z-Score |
|---|---|
| **TOP** | ≥ 90 |
| **MUY ALTA** | 75 – 89 |
| **ALTA** | 60 – 74 |
| **MEDIA** | 40 – 59 |
| **BAJA** | < 40 |

---

## REAP (Rendimiento Esperado Ajustado por Partido)

El umbral REAP se usa en la integración con Primera B Metro para identificar jugadores de alto impacto:

- **REAP ≥ 1.29** → jugador de alto rendimiento
- Se calcula a partir del histórico acumulado de la temporada y se usa para puntuar partidos de la PBM con el sistema **MPS** (ver `config_primerabmetro.py`)

---

## Pipeline de ejecución

```bash
# PASO 1 — Scraping
python scripts/1_scraping/scraper_ronda_nueva_completo.py
python scripts/1_scraping/scraper_nueva_ronda_primerabmetro.py
python scripts/1_scraping/obtener_ratings_acumulados_sofascore.py

# PASO 2 — Procesamiento
python scripts/2_processing/integrar_primera_b_metro.py
python scripts/2_processing/calcular_mps.py
python scripts/2_processing/recalcular_zscore_grupos.py
python scripts/2_processing/generar_resumen_u23_partidos.py
python scripts/2_processing/generar_descripciones_chatgpt.py  # Requiere API key OpenAI

# PASO 3 — Descarga de escudos
python scripts/utils/descargar_escudos.py

# PASO 4 — Generación de PDFs
python scripts/3_pdf_generation/generar_pdf_ronda_nueva.py
python scripts/3_pdf_generation/generar_pdf_anexos_acumulados.py
```

---

## Requisitos

```bash
pip install requests pandas numpy scipy reportlab selenium beautifulsoup4 rapidfuzz openai
```

Para el scraping con Selenium también necesitas **ChromeDriver**:

```bash
brew install chromedriver   # macOS
```

---

## Dependencias del proyecto padre

Este módulo forma parte del proyecto **IDV_project** y depende del generador de PDF base:

```python
from generar_pdf_final_idv import PDFGeneratorIDV  # en IDV_project/
```

Asegúrate de tener el directorio raíz `IDV_project/` en el path al ejecutar los scripts de generación de PDF.

---

## Datos de la ronda

| Campo | Valor |
|---|---|
| **Período** | 02 – 08 Marzo 2026 |
| **Partidos procesados** | ~52 |
| **Ligas** | 10 (Brasil, Colombia, Argentina) |
| **Umbral U23** | Nacidos en 2003 o posterior |
| **Mínimo de minutos** | 60 min para contar en densidad U23 |

---

*Generado: Marzo 2026*
