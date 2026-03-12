#!/usr/bin/env python3
"""
Scraper para nueva ronda de datos IDV - Marzo 2026
Extrae datos de SofaScore para múltiples ligas brasileñas, colombianas y Copa Brasil
"""

import requests
import json
import time
import pandas as pd
from datetime import datetime
from pathlib import Path

# Configuración
BASE_DIR = Path('/Users/alvarolopezmolina/Desktop/Python/IDV_project/RONDA_NUEVA')
DATA_DIR = BASE_DIR / 'data'
DATA_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json',
    'Referer': 'https://www.sofascore.com/'
}

# Configuración de ligas y pesos
LEAGUE_CONFIG = {
    'PAULISTA_A1': {
        'url': 'https://www.sofascore.com/api/v1/unique-tournament/372/season/86993/events/round/29/slug/final',
        'peso_liga': 0.9,
        'nombre': 'Paulista A1'
    },
    'PAULISTA_A2': {
        'url': 'https://www.sofascore.com/api/v1/unique-tournament/1234/season/87118/events/round/15',
        'peso_liga': 0.65,
        'nombre': 'Paulista A2'
    },
    'COLOMBIA_2_DIV': {
        'url': 'https://www.sofascore.com/api/v1/unique-tournament/1238/season/89001/events/round/8',
        'peso_liga': 0.6,
        'nombre': 'Colombia 2 Div'
    },
    'COPA_BRASIL': {
        'url': 'https://www.sofascore.com/api/v1/unique-tournament/373/season/89353/events/round/2/slug/round-2',
        'peso_liga': 0.75,
        'nombre': 'Copa Brasil',
        'filter_dates': ['04/03/2026', '05/03/2026']  # Solo estos días
    }
}

# Partidos individuales
INDIVIDUAL_MATCHES = {
    'CARIOCA': {
        'peso_liga': 0.85,
        'nombre': 'Carioca',
        'event_ids': [15651378, 15512222, 15566225, 15512233, 15512228, 15648858]
    },
    'MINEIRO': {
        'peso_liga': 0.78,
        'nombre': 'Mineiro',
        'event_ids': [15643392, 15643465, 15643468]
    },
    'GAUCHO': {
        'peso_liga': 0.85,
        'nombre': 'Gaúcho',
        'event_ids': [15608566, 15607733]
    },
    'BAIANO': {
        'peso_liga': 0.85,
        'nombre': 'Baiano',
        'event_ids': [15643353]
    },
    'PARANAENSE': {
        'peso_liga': 0.9,
        'nombre': 'Paranaense',
        'event_ids': [15600632]
    }
}


def fetch_json(url, max_retries=3):
    """Fetch JSON from URL with retries"""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            time.sleep(1)  # Rate limiting
            return response.json()
        except Exception as e:
            print(f"  ⚠️  Intento {attempt + 1}/{max_retries} falló: {str(e)[:50]}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                return None
    return None


def extract_player_data(player, team_name, opponent_name, team_id, opponent_id, match_id, match_date, liga, peso_liga, home_away):
    """Extrae datos de un jugador"""
    return {
        'player_id': player.get('player', {}).get('id', 0),
        'player_name': player.get('player', {}).get('name', ''),
        'shirt_number': player.get('shirtNumber', ''),
        'position': player.get('position', ''),
        'date_of_birth': player.get('player', {}).get('dateOfBirthTimestamp', ''),
        'birth_year': 0,  # Se calculará después
        'age': 0,  # Se calculará después
        'is_u23': False,  # Se calculará después
        'team': team_name,
        'opponent': opponent_name,
        'team_id': team_id,
        'opponent_id': opponent_id,
        'home_away': home_away,
        'minutes_played': player.get('statistics', {}).get('minutesPlayed', 0),
        'rating': player.get('statistics', {}).get('rating', 0),
        'goals': player.get('statistics', {}).get('goals', 0),
        'assists': player.get('statistics', {}).get('goalAssist', 0),
        'match_id': match_id,
        'match_date': match_date,
        'liga': liga,
        'peso_liga': peso_liga,
        'substitute': player.get('substitute', False)
    }


def process_match_lineups(event_id, liga_nombre, peso_liga):
    """Procesa lineups de un partido individual"""
    print(f"\n  📋 Procesando partido {event_id} ({liga_nombre})...")
    
    # Obtener información del evento
    event_url = f"https://www.sofascore.com/api/v1/event/{event_id}"
    event_data = fetch_json(event_url)
    
    if not event_data or 'event' not in event_data:
        print(f"    ✗ No se pudo obtener datos del evento")
        return []
    
    event = event_data['event']
    
    # Extraer información del partido
    home_team = event.get('homeTeam', {})
    away_team = event.get('awayTeam', {})
    home_team_name = home_team.get('name', '')
    away_team_name = away_team.get('name', '')
    home_team_id = home_team.get('id', 0)
    away_team_id = away_team.get('id', 0)
    
    # Fecha del partido
    start_timestamp = event.get('startTimestamp', 0)
    match_date = datetime.fromtimestamp(start_timestamp).strftime('%d/%m/%Y') if start_timestamp else ''
    
    print(f"    {home_team_name} vs {away_team_name} - {match_date}")
    
    # Obtener lineups
    lineups_url = f"https://www.sofascore.com/api/v1/event/{event_id}/lineups"
    lineups_data = fetch_json(lineups_url)
    
    if not lineups_data:
        print(f"    ✗ No se pudieron obtener lineups")
        return []
    
    players_data = []
    
    # Procesar jugadores del equipo local
    if 'home' in lineups_data and 'players' in lineups_data['home']:
        for player in lineups_data['home']['players']:
            player_data = extract_player_data(
                player, home_team_name, away_team_name, home_team_id, away_team_id,
                event_id, match_date, liga_nombre, peso_liga, 'home'
            )
            players_data.append(player_data)
    
    # Procesar jugadores del equipo visitante
    if 'away' in lineups_data and 'players' in lineups_data['away']:
        for player in lineups_data['away']['players']:
            player_data = extract_player_data(
                player, away_team_name, home_team_name, away_team_id, home_team_id,
                event_id, match_date, liga_nombre, peso_liga, 'away'
            )
            players_data.append(player_data)
    
    print(f"    ✓ {len(players_data)} jugadores extraídos")
    return players_data


def process_tournament_round(config_key, config):
    """Procesa una ronda completa de un torneo"""
    print(f"\n{'='*70}")
    print(f"PROCESANDO: {config['nombre']}")
    print(f"{'='*70}")
    
    url = config['url']
    peso_liga = config['peso_liga']
    liga_nombre = config['nombre']
    
    # Obtener eventos de la ronda
    round_data = fetch_json(url)
    
    if not round_data or 'events' not in round_data:
        print(f"  ✗ No se pudieron obtener eventos")
        return []
    
    events = round_data['events']
    print(f"  📊 {len(events)} partidos encontrados")
    
    # Filtrar por fecha si es necesario (Copa Brasil)
    if 'filter_dates' in config:
        filtered_events = []
        for event in events:
            start_timestamp = event.get('startTimestamp', 0)
            event_date = datetime.fromtimestamp(start_timestamp).strftime('%d/%m/%Y') if start_timestamp else ''
            if event_date in config['filter_dates']:
                filtered_events.append(event)
        events = filtered_events
        print(f"  🔍 Filtrado a {len(events)} partidos ({', '.join(config['filter_dates'])})")
    
    all_players = []
    
    for event in events:
        event_id = event.get('id')
        if event_id:
            players = process_match_lineups(event_id, liga_nombre, peso_liga)
            all_players.extend(players)
            time.sleep(1)  # Rate limiting
    
    return all_players


def process_individual_matches(league_key, league_config):
    """Procesa partidos individuales de una liga"""
    print(f"\n{'='*70}")
    print(f"PROCESANDO: {league_config['nombre']} (Partidos individuales)")
    print(f"{'='*70}")
    
    peso_liga = league_config['peso_liga']
    liga_nombre = league_config['nombre']
    event_ids = league_config['event_ids']
    
    print(f"  📊 {len(event_ids)} partidos a procesar")
    
    all_players = []
    
    for event_id in event_ids:
        players = process_match_lineups(event_id, liga_nombre, peso_liga)
        all_players.extend(players)
        time.sleep(1)  # Rate limiting
    
    return all_players


def calculate_age_and_u23(df):
    """Calcula edad y marca U23 basado en fecha de nacimiento"""
    current_year = 2026
    
    for idx, row in df.iterrows():
        dob_timestamp = row['date_of_birth']
        
        if dob_timestamp and dob_timestamp != '':
            try:
                birth_date = datetime.fromtimestamp(int(dob_timestamp))
                birth_year = birth_date.year
                age = current_year - birth_year
                
                df.at[idx, 'birth_year'] = birth_year
                df.at[idx, 'age'] = age
                df.at[idx, 'is_u23'] = birth_year >= 2003
            except:
                pass
    
    return df


def main():
    print("\n" + "="*70)
    print("SCRAPER RONDA NUEVA - IDV MARZO 2026")
    print("="*70)
    
    all_players_data = []
    
    # Procesar torneos completos
    print("\n🏆 PROCESANDO TORNEOS COMPLETOS...")
    for key, config in LEAGUE_CONFIG.items():
        players = process_tournament_round(key, config)
        all_players_data.extend(players)
    
    # Procesar partidos individuales
    print("\n📋 PROCESANDO PARTIDOS INDIVIDUALES...")
    for key, config in INDIVIDUAL_MATCHES.items():
        players = process_individual_matches(key, config)
        all_players_data.extend(players)
    
    # Crear DataFrame
    print(f"\n{'='*70}")
    print("PROCESANDO DATOS...")
    print(f"{'='*70}")
    
    df = pd.DataFrame(all_players_data)
    print(f"  📊 Total jugadores extraídos: {len(df)}")
    print(f"  📊 Total partidos únicos: {df['match_id'].nunique()}")
    
    # Calcular edad y U23
    df = calculate_age_and_u23(df)
    
    # Filtrar solo jugadores que jugaron
    df_filtered = df[df['minutes_played'] > 0].copy()
    print(f"  📊 Jugadores con minutos: {len(df_filtered)}")
    
    # Guardar datos
    output_file = DATA_DIR / 'jugadores_ronda_nueva.csv'
    df_filtered.to_csv(output_file, index=False, encoding='utf-8')
    print(f"\n✅ Datos guardados: {output_file}")
    
    # Resumen por liga
    print(f"\n{'='*70}")
    print("RESUMEN POR LIGA")
    print(f"{'='*70}")
    
    summary = df_filtered.groupby('liga').agg({
        'match_id': 'nunique',
        'player_id': 'count',
        'is_u23': 'sum'
    }).rename(columns={
        'match_id': 'Partidos',
        'player_id': 'Jugadores',
        'is_u23': 'U23'
    })
    
    print(summary.to_string())
    
    # Guardar también en JSON para backup
    json_file = DATA_DIR / 'jugadores_ronda_nueva.json'
    df_filtered.to_json(json_file, orient='records', indent=2, force_ascii=False)
    print(f"\n✅ Backup JSON guardado: {json_file}")
    
    print(f"\n{'='*70}")
    print("✅ SCRAPING COMPLETADO")
    print(f"{'='*70}")
    print(f"\n📂 Archivos generados:")
    print(f"  • {output_file}")
    print(f"  • {json_file}")
    print(f"\n🎯 Siguiente paso: Ejecutar integrar_y_calcular_mps.py")


if __name__ == '__main__':
    main()
