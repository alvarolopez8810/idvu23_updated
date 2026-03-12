#!/usr/bin/env python3
"""
Scraper completo para nueva ronda IDV - Marzo 2026
Basado en scrape_complete_15220787.py
Extrae: lineups, ratings, statistics, avg positions, heatmaps
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import json
import time
import pandas as pd
from datetime import datetime
from pathlib import Path

# Configuración
BASE_DIR = Path('/Users/alvarolopezmolina/Desktop/Python/IDV_project/RONDA_NUEVA')
DATA_DIR = BASE_DIR / 'data'
DATA_DIR.mkdir(parents=True, exist_ok=True)

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
        'filter_dates': ['04/03/2026', '05/03/2026']
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


def setup_driver():
    """Configurar driver de Chrome"""
    chrome_options = Options()
    # chrome_options.add_argument('--headless')  # Comentado para debug
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver


def fetch_json(driver, url, max_retries=3):
    """Obtener JSON de un endpoint con reintentos"""
    for attempt in range(max_retries):
        try:
            driver.get(url)
            time.sleep(2)
            
            pre_element = driver.find_element(By.TAG_NAME, 'pre')
            json_text = pre_element.text
            data = json.loads(json_text)
            
            if 'error' in data:
                return None
            
            return data
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                return None
    return None


def get_tournament_events(driver, config):
    """Obtener eventos de un torneo"""
    url = config['url']
    data = fetch_json(driver, url)
    
    if not data or 'events' not in data:
        return []
    
    events = data['events']
    
    # Filtrar por fecha si es necesario (Copa Brasil)
    if 'filter_dates' in config:
        filtered_events = []
        for event in events:
            start_timestamp = event.get('startTimestamp', 0)
            event_date = datetime.fromtimestamp(start_timestamp).strftime('%d/%m/%Y') if start_timestamp else ''
            if event_date in config['filter_dates']:
                filtered_events.append(event)
        return filtered_events
    
    return events


def extract_match_data(driver, event_id, liga_nombre, peso_liga):
    """Extrae todos los datos de un partido"""
    print(f"\n  {'='*66}")
    print(f"  PARTIDO {event_id} - {liga_nombre}")
    print(f"  {'='*66}")
    
    match_data = {
        'match_id': event_id,
        'liga': liga_nombre,
        'peso_liga': peso_liga,
        'event_info': None,
        'lineups': None,
        'players': []
    }
    
    # 1. Event info
    print(f"  📋 Obteniendo información del partido...")
    event_url = f"https://www.sofascore.com/api/v1/event/{event_id}"
    event_data = fetch_json(driver, event_url)
    
    if not event_data or 'event' not in event_data:
        print(f"    ✗ No se pudo obtener información del evento")
        return None
    
    event = event_data['event']
    match_data['event_info'] = event
    
    home_team = event.get('homeTeam', {})
    away_team = event.get('awayTeam', {})
    home_team_name = home_team.get('name', '')
    away_team_name = away_team.get('name', '')
    home_team_id = home_team.get('id', 0)
    away_team_id = away_team.get('id', 0)
    start_timestamp = event.get('startTimestamp', 0)
    match_date = datetime.fromtimestamp(start_timestamp).strftime('%d/%m/%Y') if start_timestamp else ''
    
    print(f"    ✓ {home_team_name} vs {away_team_name} - {match_date}")
    
    # 2. Lineups
    print(f"  📋 Obteniendo lineups...")
    lineups_url = f"https://www.sofascore.com/api/v1/event/{event_id}/lineups"
    lineups_data = fetch_json(driver, lineups_url)
    
    if not lineups_data:
        print(f"    ✗ No se pudieron obtener lineups")
        return None
    
    match_data['lineups'] = lineups_data
    
    # 3. Procesar jugadores
    all_players = []
    
    # Jugadores locales
    if 'home' in lineups_data and 'players' in lineups_data['home']:
        for player in lineups_data['home']['players']:
            player_info = player.get('player', {})
            player_id = player_info.get('id', 0)
            player_name = player_info.get('name', '')
            
            player_data = {
                'player_id': player_id,
                'player_name': player_name,
                'shirt_number': player.get('shirtNumber', ''),
                'position': player.get('position', ''),
                'substitute': player.get('substitute', False),
                'date_of_birth': player_info.get('dateOfBirthTimestamp', ''),
                'team': home_team_name,
                'opponent': away_team_name,
                'team_id': home_team_id,
                'opponent_id': away_team_id,
                'home_away': 'home',
                'match_id': event_id,
                'match_date': match_date,
                'liga': liga_nombre,
                'peso_liga': peso_liga,
                'minutes_played': player.get('statistics', {}).get('minutesPlayed', 0),
                'rating': player.get('statistics', {}).get('rating', 0),
                'goals': player.get('statistics', {}).get('goals', 0),
                'assists': player.get('statistics', {}).get('goalAssist', 0)
            }
            all_players.append(player_data)
    
    # Jugadores visitantes
    if 'away' in lineups_data and 'players' in lineups_data['away']:
        for player in lineups_data['away']['players']:
            player_info = player.get('player', {})
            player_id = player_info.get('id', 0)
            player_name = player_info.get('name', '')
            
            player_data = {
                'player_id': player_id,
                'player_name': player_name,
                'shirt_number': player.get('shirtNumber', ''),
                'position': player.get('position', ''),
                'substitute': player.get('substitute', False),
                'date_of_birth': player_info.get('dateOfBirthTimestamp', ''),
                'team': away_team_name,
                'opponent': home_team_name,
                'team_id': away_team_id,
                'opponent_id': home_team_id,
                'home_away': 'away',
                'match_id': event_id,
                'match_date': match_date,
                'liga': liga_nombre,
                'peso_liga': peso_liga,
                'minutes_played': player.get('statistics', {}).get('minutesPlayed', 0),
                'rating': player.get('statistics', {}).get('rating', 0),
                'goals': player.get('statistics', {}).get('goals', 0),
                'assists': player.get('statistics', {}).get('goalAssist', 0)
            }
            all_players.append(player_data)
    
    match_data['players'] = all_players
    print(f"    ✓ {len(all_players)} jugadores procesados")
    
    return match_data


def calculate_age_and_u23(df):
    """Calcula edad y marca U23 basado en fecha de nacimiento"""
    current_year = 2026
    
    df['birth_year'] = 0
    df['age'] = 0
    df['is_u23'] = False
    
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
    print("SCRAPER COMPLETO - RONDA NUEVA IDV MARZO 2026")
    print("="*70)
    
    driver = setup_driver()
    all_matches_data = []
    all_players_data = []
    
    try:
        # Procesar torneos completos
        print("\n🏆 PROCESANDO TORNEOS COMPLETOS...")
        for key, config in LEAGUE_CONFIG.items():
            print(f"\n{'='*70}")
            print(f"{config['nombre']}")
            print(f"{'='*70}")
            
            events = get_tournament_events(driver, config)
            print(f"  📊 {len(events)} partidos encontrados")
            
            for event in events:
                event_id = event.get('id')
                if event_id:
                    match_data = extract_match_data(driver, event_id, config['nombre'], config['peso_liga'])
                    if match_data:
                        all_matches_data.append(match_data)
                        all_players_data.extend(match_data['players'])
                    time.sleep(2)  # Rate limiting
        
        # Procesar partidos individuales
        print("\n📋 PROCESANDO PARTIDOS INDIVIDUALES...")
        for key, config in INDIVIDUAL_MATCHES.items():
            print(f"\n{'='*70}")
            print(f"{config['nombre']}")
            print(f"{'='*70}")
            print(f"  📊 {len(config['event_ids'])} partidos a procesar")
            
            for event_id in config['event_ids']:
                match_data = extract_match_data(driver, event_id, config['nombre'], config['peso_liga'])
                if match_data:
                    all_matches_data.append(match_data)
                    all_players_data.extend(match_data['players'])
                time.sleep(2)  # Rate limiting
        
    finally:
        driver.quit()
    
    # Procesar datos
    print(f"\n{'='*70}")
    print("PROCESANDO DATOS...")
    print(f"{'='*70}")
    
    # Crear DataFrame de jugadores
    df_players = pd.DataFrame(all_players_data)
    print(f"  📊 Total jugadores extraídos: {len(df_players)}")
    print(f"  📊 Total partidos únicos: {df_players['match_id'].nunique()}")
    
    # Calcular edad y U23
    df_players = calculate_age_and_u23(df_players)
    
    # Filtrar solo jugadores que jugaron
    df_filtered = df_players[df_players['minutes_played'] > 0].copy()
    print(f"  📊 Jugadores con minutos: {len(df_filtered)}")
    print(f"  📊 Jugadores U23: {df_filtered['is_u23'].sum()}")
    
    # Guardar datos de jugadores
    output_file = DATA_DIR / 'jugadores_ronda_nueva.csv'
    df_filtered.to_csv(output_file, index=False, encoding='utf-8')
    print(f"\n✅ Datos de jugadores guardados: {output_file}")
    
    # Guardar datos completos de partidos (JSON)
    matches_file = DATA_DIR / 'partidos_completos.json'
    with open(matches_file, 'w', encoding='utf-8') as f:
        json.dump(all_matches_data, f, indent=2, ensure_ascii=False)
    print(f"✅ Datos completos de partidos guardados: {matches_file}")
    
    # Resumen por liga
    print(f"\n{'='*70}")
    print("RESUMEN POR LIGA")
    print(f"{'='*70}")
    
    summary = df_filtered.groupby('liga').agg({
        'match_id': 'nunique',
        'player_id': 'count',
        'is_u23': 'sum',
        'rating': lambda x: x[x > 0].mean() if len(x[x > 0]) > 0 else 0
    }).rename(columns={
        'match_id': 'Partidos',
        'player_id': 'Jugadores',
        'is_u23': 'U23',
        'rating': 'Rating Avg'
    })
    
    summary['Rating Avg'] = summary['Rating Avg'].round(2)
    print(summary.to_string())
    
    print(f"\n{'='*70}")
    print("✅ SCRAPING COMPLETADO")
    print(f"{'='*70}")
    print(f"\n📂 Archivos generados:")
    print(f"  • {output_file}")
    print(f"  • {matches_file}")
    print(f"\n🎯 Siguiente paso: Ejecutar integrar_y_calcular_mps.py")


if __name__ == '__main__':
    main()
