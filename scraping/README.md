# scraping — Framework de extracción de datos (ScoresWay)

Módulo de scraping modular para extraer datos de partidos, plantillas, fixtures y estadísticas desde la API de ScoresWay. Soporta almacenamiento local y en AWS S3 de forma transparente.

---

## Estructura

```
scraping/
├── scraper_base.py          # Clase base: sesión HTTP, headers, delays, logging
├── storage_manager.py       # Abstracción local / AWS S3
├── utils.py                 # Utilidades compartidas
├── memory_logger.py         # Logger de ejecuciones
│
├── scraper_competitions.py  # Metadatos de ligas y competiciones
├── scraper_seasons.py       # Información de temporadas y torneos
├── scraper_squads.py        # Plantillas de equipos
├── scraper_fixture.py       # Detalles de fixtures (partidos programados)
├── scraper_match_stats.py   # Estadísticas detalladas de partidos
├── processor_fixtures.py    # Post-procesado de fixtures
│
├── run_scraper_orchestrator.ipynb  # Notebook principal de ejecución
├── run_scraper_by_dates.ipynb      # Scraping por rango de fechas
│
├── data/                    # JSONs descargados (organizados por liga/temporada)
├── schema/                  # Esquemas de validación JSON
└── logs/                    # Logs de ejecución
```

---

## Scrapers disponibles

| Clase | Archivo | Descripción |
|---|---|---|
| `BaseScraper` | `scraper_base.py` | Clase base con HTTP, headers, delays aleatorios |
| `ScrapeCompetitions` | `scraper_competitions.py` | Ligas y competiciones disponibles |
| `ScrapeSeasons` | `scraper_seasons.py` | Temporadas y fases de torneo |
| `ScrapeSquads` | `scraper_squads.py` | Plantillas y datos de jugadores por equipo |
| `ScrapeFixture` | `scraper_fixture.py` | Fixtures de partidos |
| `ScrapeMatchStats` | `scraper_match_stats.py` | Estadísticas completas de partido |

---

## Ejecución

Usar los notebooks de Jupyter como punto de entrada:

```bash
cd U23-data/scraping
jupyter notebook run_scraper_orchestrator.ipynb   # flujo principal
jupyter notebook run_scraper_by_dates.ipynb       # scraping por fechas
```

---

## Almacenamiento

`StorageManager` abstrae el backend de forma transparente:

```python
from storage_manager import StorageManager

# Local
sm = StorageManager(storage_type="local")

# AWS S3
sm = StorageManager(storage_type="s3", s3_bucket="mi-bucket")
```

El tipo de almacenamiento se puede configurar también mediante la variable de entorno `STORAGE_TYPE`.

---

## Configuración de delays

Los scrapers incluyen delays aleatorios entre peticiones para evitar bloqueos:

```python
scraper = ScrapeMatchStats()
scraper.set_delay_range(min_delay=1.5, max_delay=4.0)  # valores en segundos
```

Por defecto: 1.0–3.0 s. Transfermarkt usa 3.0–6.0 s.

---

## Salida de datos

Los JSONs se guardan organizados por competición y temporada:

```
data/
└── south_america/
    └── {pais}/
        └── {competicion}/
            └── {temporada}/
                └── {match_id}.json
```

---

## Dependencias

```
requests
pandas
boto3        # solo para S3
python-dotenv
```
