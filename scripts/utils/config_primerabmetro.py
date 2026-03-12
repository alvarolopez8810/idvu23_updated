#!/usr/bin/env python3
"""
Configuración para scraping de Primera B Metro - Match Priority Score
"""

# Configuración de la liga y endpoints
LEAGUE_CONFIG = {
    "primera_b_metro": {
        "name": "Primera B Metro",
        "tournament_id": "3357",  # ID de SofaScore para Primera B Metro
        "season_id": "84541",     # Temporada 2026
        "current_round": 3,      # Jornada actual
        "endpoints": {
            "matches": "https://www.sofascore.com/api/v1/unique-tournament/3357/season/84541/events/round/3",
            "lineups": "https://www.sofascore.com/api/v1/event/{match_id}/lineups"
        }
    }
}

# Headers para requests
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
}

# Rate limiting
DELAY_BETWEEN_REQUESTS = 2.5  # segundos

# Thresholds para puntuación MPS
THRESHOLDS = {
    # PRIORIDAD 2 - JUGADORES DESTACADOS REAP
    "reap_threshold": 1.29,
    "high_reap_starters_threshold": 2,  # ≥2 jugadores con REAP ≥ 1.29 titulares
    "high_reap_squad_threshold": 3,      # ≥3 jugadores con REAP ≥ 1.29 en convocatoria
    
    # PRIORIDAD 6 - DENSIDAD U23
    "u23_birth_year": 2003,  # Nacidas en 2003 o después
    "u23_starters_threshold": 4,  # ≥4 U23 titulares
    "u23_squad_threshold": 6,      # ≥6 U23 en convocatoria
    
    # PRIORIDAD 7 - PERFORMANCE MOMENTUM
    "high_rating_threshold": 7.1,  # Rating SofaScore ≥ 7.1
    "max_high_rating_points": 6,    # Máximo +6 puntos por ratings altos
}

# Puntuación MPS
MPS_SCORES = {
    "high_reap_starters": 3,    # +3 puntos por ≥2 REAP ≥ 1.29 titulares
    "high_reap_squad": 2,        # +2 puntos por ≥3 REAP ≥ 1.29 en convocatoria
    "u23_starters": 3,          # +3 puntos por ≥4 U23 titulares
    "u23_squad": 2,              # +2 puntos por ≥6 U23 en convocatoria
    "high_rating_per_player": 2, # +2 puntos por cada jugadora con rating ≥ 7.1
}

# Flags para identificar criterios cumplidos
FLAGS = {
    "HIGH_REAP_STARTERS": "HIGH_REAP_STARTERS",
    "HIGH_REAP_SQUAD": "HIGH_REAP_SQUAD", 
    "U23_STARTERS": "U23_STARTERS",
    "U23_SQUAD": "U23_SQUAD",
    "HIGH_RATING": "HIGH_RATING",
}

# Categorías de prioridad por puntuación total
PRIORITY_CATEGORIES = {
    "must_watch": {"min_score": 8, "emoji": "🔴", "label": "MUST WATCH"},
    "high_priority": {"min_score": 5, "max_score": 7, "emoji": "🟠", "label": "HIGH PRIORITY"},
    "monitor": {"min_score": 3, "max_score": 4, "emoji": "🟡", "label": "MONITOR"},
    "low_priority": {"max_score": 2, "emoji": "⚪", "label": "LOW PRIORITY"},
}

# Archivo de jugadores U23 con REAP
REAP_DATA_FILE = "jugadores_jornada_primerabmetro_reap.json"

# Output files
OUTPUT_CSV = "mps_primera_b_metro_{date}.csv"
OUTPUT_JSON = "mps_primera_b_metro_{date}.json"
