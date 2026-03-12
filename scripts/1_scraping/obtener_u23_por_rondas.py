#!/usr/bin/env python3
"""
Obtener jugadores U23 acumulados mediante rondas y partidos
Método: rounds -> matches -> lineups -> filtrar U23 con ≥2-3 partidos -> ratings
"""

import pandas as pd
import json
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import random
from datetime import datetime
from collections import defaultdict

BASE_DIR = Path('/Users/alvarolopezmolina/Desktop/Python/IDV_project/RONDA_02-08_03_26')
DATA_DIR = BASE_DIR / 'data'

# Mapping de ligas a tournament_id y season_id
LIGAS_CONFIG = {
    'Paranaense': {'tournament': 382, 'season': 86658},
    'Mineiro': {'tournament': 379, 'season': 87236},
    'Carioca': {'tournament': 92, 'season': 86674},
    'Gaúcho': {'tournament': 377, 'season': 86736},
    'Baiano': {'tournament': 374, 'season': 86656},
    'Colombia 2 Div': {'tournament': 1238, 'season': 89001},
    'Paulista A1': {'tournament': 372, 'season': 86993},
    'Paulista A2': {'tournament': 1234, 'season': 87118},
}

MIN_PARTIDOS = 2  # Mínimo de partidos para considerar al jugador

class SofaScoreRoundsU23Scraper:
    def __init__(self):
        self.setup_driver()
        self.base_url = "https://www.sofascore.com/api/v1"
        self.player_appearances = defaultdict(lambda: {
            'count': 0,
            'player_name': '',
            'liga': '',
            'birth_year': None,
            'date_of_birth': '',
            'team_name': ''
        })
        
    def setup_driver(self):
        """Configura el driver de Selenium"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
    def random_delay(self, min_seconds=0.3, max_seconds=0.8):
        """Delay aleatorio"""
        time.sleep(random.uniform(min_seconds, max_seconds))
        
    def get_json_from_url(self, url, max_retries=3):
        """Obtiene JSON de una URL usando Selenium"""
        for attempt in range(max_retries):
            try:
                self.driver.get(url)
                self.random_delay(0.2, 0.5)
                
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "pre"))
                )
                
                page_source = self.driver.page_source
                
                if "<pre>" in page_source:
                    json_text = page_source.split("<pre>")[1].split("</pre>")[0]
                    return json.loads(json_text)
                else:
                    body = self.driver.find_element(By.TAG_NAME, "body")
                    return json.loads(body.text)
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    self.random_delay(1, 2)
                else:
                    return None
        
        return None
    
    def get_rounds_list(self, tournament_id, season_id):
        """Obtiene la lista completa de rondas desde el endpoint /rounds"""
        url = f"{self.base_url}/unique-tournament/{tournament_id}/season/{season_id}/rounds"
        
        data = self.get_json_from_url(url)
        
        if data and 'rounds' in data:
            return data['rounds']
        
        return []
    
    def get_round_events(self, tournament_id, season_id, round_info):
        """Obtiene todos los eventos (partidos) de una ronda usando round_info"""
        # Intentar con round number primero
        round_id = round_info.get('round')
        slug = round_info.get('slug', '')
        
        # Construir URL con round number y slug si existe
        if slug:
            url = f"{self.base_url}/unique-tournament/{tournament_id}/season/{season_id}/events/round/{round_id}/slug/{slug}"
        else:
            url = f"{self.base_url}/unique-tournament/{tournament_id}/season/{season_id}/events/round/{round_id}"
        
        data = self.get_json_from_url(url)
        
        if data and 'events' in data:
            return data['events']
        
        return []
    
    def get_all_rounds_events(self, tournament_id, season_id):
        """Obtiene todos los eventos de todas las rondas (incluyendo playoffs)"""
        all_rounds_data = []
        
        # Obtener lista completa de rondas
        rounds_list = self.get_rounds_list(tournament_id, season_id)
        
        if not rounds_list:
            print("    ⚠️  No se pudo obtener lista de rondas, intentando método numérico...")
            # Fallback: intentar con números de ronda
            for round_num in range(1, 30):
                events = self.get_round_events(tournament_id, season_id, {'round': round_num})
                
                if not events:
                    break
                
                all_rounds_data.append({
                    'round_number': round_num,
                    'round_name': f'Ronda {round_num}',
                    'events': events
                })
                
                self.random_delay(0.3, 0.6)
        else:
            # Procesar cada ronda de la lista
            for round_info in rounds_list:
                round_id = round_info.get('round')
                round_name = round_info.get('name', f'Round {round_id}')
                
                events = self.get_round_events(tournament_id, season_id, round_info)
                
                if events:
                    all_rounds_data.append({
                        'round_number': round_id,
                        'round_name': round_name,
                        'events': events
                    })
                
                self.random_delay(0.3, 0.6)
        
        return all_rounds_data
    
    def get_match_lineups(self, event_id):
        """Obtiene los lineups de un partido"""
        url = f"{self.base_url}/event/{event_id}/lineups"
        
        data = self.get_json_from_url(url)
        
        return data if data else None
    
    def extract_u23_from_lineups(self, lineups_data, liga_nombre):
        """Extrae jugadores U23 de los lineups"""
        current_year = datetime.now().year
        u23_players = []
        
        if not lineups_data:
            return u23_players
        
        # Procesar ambos equipos (home y away)
        for team_key in ['home', 'away']:
            if team_key not in lineups_data:
                continue
            
            team_data = lineups_data[team_key]
            team_name = team_data.get('team', {}).get('name', 'Unknown')
            
            # Procesar jugadores (players en lineup)
            all_players = team_data.get('players', [])
            
            for player_data in all_players:
                player = player_data.get('player', {})
                player_id = player.get('id')
                player_name = player.get('name', 'Unknown')
                date_of_birth_timestamp = player.get('dateOfBirthTimestamp')
                
                if player_id and date_of_birth_timestamp:
                    birth_year = datetime.fromtimestamp(date_of_birth_timestamp).year
                    
                    # Filtrar U23 (nacidos en 2003 o posterior)
                    if birth_year >= 2003:
                        u23_players.append({
                            'player_id': player_id,
                            'player_name': player_name,
                            'birth_year': birth_year,
                            'date_of_birth': datetime.fromtimestamp(date_of_birth_timestamp).strftime('%d/%m/%Y'),
                            'team_name': team_name,
                            'liga': liga_nombre
                        })
        
        return u23_players
    
    def get_player_season_rating(self, player_id, tournament_id, season_id):
        """Obtiene el rating acumulado de un jugador"""
        url = f"{self.base_url}/player/{player_id}/unique-tournament/{tournament_id}/season/{season_id}/ratings/overall"
        
        data = self.get_json_from_url(url)
        
        if data and 'seasonRatings' in data:
            season_ratings = data['seasonRatings']
            
            if len(season_ratings) > 0:
                ratings = [match['rating'] for match in season_ratings if 'rating' in match]
                
                if ratings:
                    return {
                        'rating_promedio': sum(ratings) / len(ratings),
                        'partidos_total': len(ratings),
                        'success': True
                    }
        
        return {'rating_promedio': 0, 'partidos_total': 0, 'success': False}
    
    def close(self):
        """Cierra el driver"""
        self.driver.quit()


def main():
    print("\n" + "="*80)
    print("OBTENER JUGADORES U23 ACUMULADOS - MÉTODO RONDAS")
    print("Proceso: rounds -> matches -> lineups -> U23 filter -> ratings")
    print("="*80)
    
    scraper = SofaScoreRoundsU23Scraper()
    
    total_ligas = len(LIGAS_CONFIG)
    total_rondas_procesadas = 0
    total_partidos_procesados = 0
    
    try:
        for idx_liga, (liga_nombre, config) in enumerate(LIGAS_CONFIG.items(), 1):
            tournament_id = config['tournament']
            season_id = config['season']
            
            print(f"\n{'='*80}")
            print(f"📊 LIGA {idx_liga}/{total_ligas}: {liga_nombre}")
            print(f"   Tournament: {tournament_id}, Season: {season_id}")
            print(f"{'='*80}")
            
            # 1. Obtener todas las rondas iterando por números
            print(f"\n  🔍 Obteniendo rondas (iterando números de ronda)...")
            all_rounds = scraper.get_all_rounds_events(tournament_id, season_id, max_rounds=30)
            print(f"  ✓ {len(all_rounds)} rondas encontradas")
            
            # 2. Para cada ronda, procesar partidos
            for idx_round, round_data in enumerate(all_rounds, 1):
                round_number = round_data['round_number']
                events = round_data['events']
                
                print(f"\n  [{idx_round}/{len(all_rounds)}] Ronda {round_number}")
                print(f"    ✓ {len(events)} partidos encontrados")
                total_rondas_procesadas += 1
                
                # 3. Para cada partido, obtener lineups
                for idx_event, event in enumerate(events, 1):
                    event_id = event.get('id')
                    home_team = event.get('homeTeam', {}).get('name', 'Home')
                    away_team = event.get('awayTeam', {}).get('name', 'Away')
                    
                    print(f"      [{idx_event}/{len(events)}] {home_team} vs {away_team} (ID: {event_id})", end='')
                    
                    # Obtener lineups
                    lineups = scraper.get_match_lineups(event_id)
                    
                    if not lineups:
                        print(" - Sin lineups")
                        continue
                    
                    # 4. Extraer jugadores U23
                    u23_players = scraper.extract_u23_from_lineups(lineups, liga_nombre)
                    
                    if u23_players:
                        print(f" - {len(u23_players)} U23")
                        
                        # Registrar apariciones
                        for player in u23_players:
                            player_id = player['player_id']
                            scraper.player_appearances[player_id]['count'] += 1
                            scraper.player_appearances[player_id]['player_name'] = player['player_name']
                            scraper.player_appearances[player_id]['liga'] = player['liga']
                            scraper.player_appearances[player_id]['birth_year'] = player['birth_year']
                            scraper.player_appearances[player_id]['date_of_birth'] = player['date_of_birth']
                            scraper.player_appearances[player_id]['team_name'] = player['team_name']
                    else:
                        print(" - 0 U23")
                    
                    total_partidos_procesados += 1
                    scraper.random_delay(0.2, 0.4)
                
                # Delay entre rondas
                scraper.random_delay(0.5, 1.0)
        
        # 5. Filtrar jugadores con >= MIN_PARTIDOS
        print(f"\n{'='*80}")
        print(f"📊 FILTRADO DE JUGADORES")
        print(f"{'='*80}")
        
        filtered_players = {
            pid: data for pid, data in scraper.player_appearances.items()
            if data['count'] >= MIN_PARTIDOS
        }
        
        print(f"  Total jugadores U23 únicos: {len(scraper.player_appearances)}")
        print(f"  Jugadores con >= {MIN_PARTIDOS} partidos: {len(filtered_players)}")
        
        # 6. Obtener ratings acumulados
        print(f"\n{'='*80}")
        print(f"📊 OBTENIENDO RATINGS ACUMULADOS")
        print(f"{'='*80}")
        
        all_players_data = []
        
        for idx, (player_id, player_info) in enumerate(filtered_players.items(), 1):
            player_name = player_info['player_name']
            liga = player_info['liga']
            partidos_jugados = player_info['count']
            
            # Obtener config de la liga
            liga_config = LIGAS_CONFIG.get(liga)
            if not liga_config:
                continue
            
            tournament_id = liga_config['tournament']
            season_id = liga_config['season']
            
            print(f"  [{idx}/{len(filtered_players)}] {player_name} ({liga}) - {partidos_jugados} partidos", end='')
            
            # Obtener rating
            rating_result = scraper.get_player_season_rating(player_id, tournament_id, season_id)
            
            if rating_result['success']:
                all_players_data.append({
                    'player_id': player_id,
                    'player_name': player_name,
                    'team_name': player_info['team_name'],
                    'liga': liga,
                    'birth_year': player_info['birth_year'],
                    'date_of_birth': player_info['date_of_birth'],
                    'rating_promedio': rating_result['rating_promedio'],
                    'partidos_total': rating_result['partidos_total']
                })
                print(f" → Rating: {rating_result['rating_promedio']:.2f} ({rating_result['partidos_total']} partidos)")
            else:
                print(f" → Sin rating")
            
            scraper.random_delay(0.2, 0.5)
    
    finally:
        scraper.close()
    
    # Guardar resultados
    print(f"\n{'='*80}")
    print("💾 GUARDANDO RESULTADOS")
    print(f"{'='*80}")
    
    if all_players_data:
        # Guardar JSON
        output_json = DATA_DIR / 'u23_acumulado_por_rondas.json'
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(all_players_data, f, indent=2, ensure_ascii=False)
        print(f"  ✓ JSON guardado: {output_json}")
        
        # Guardar CSV
        df = pd.DataFrame(all_players_data)
        df = df.sort_values('rating_promedio', ascending=False)
        output_csv = DATA_DIR / 'u23_acumulado_por_rondas.csv'
        df.to_csv(output_csv, index=False, encoding='utf-8')
        print(f"  ✓ CSV guardado: {output_csv}")
        
        # Estadísticas finales
        print(f"\n{'='*80}")
        print("📊 ESTADÍSTICAS FINALES")
        print(f"{'='*80}")
        print(f"  📍 Ligas procesadas: {total_ligas}")
        print(f"  🔄 Rondas procesadas: {total_rondas_procesadas}")
        print(f"  ⚽ Partidos procesados: {total_partidos_procesados}")
        print(f"  👤 Jugadores U23 únicos: {len(scraper.player_appearances)}")
        print(f"  ✅ Jugadores con rating (≥{MIN_PARTIDOS} partidos): {len(all_players_data)}")
        
        # Top 10
        print(f"\n{'='*80}")
        print("🏆 TOP 10 RATINGS ACUMULADOS")
        print(f"{'='*80}")
        for idx, row in df.head(10).iterrows():
            print(f"  {idx+1}. {row['player_name']} ({row['liga']}) - {row['team_name']}")
            print(f"     Rating: {row['rating_promedio']:.2f} | Partidos: {row['partidos_total']}")
        
        # Buscar a Chiqueti
        chiqueti = df[df['player_name'].str.contains('Chiqueti', case=False, na=False)]
        if len(chiqueti) > 0:
            print(f"\n{'='*80}")
            print("✅ CHIQUETI ENCONTRADO")
            print(f"{'='*80}")
            for _, row in chiqueti.iterrows():
                print(f"  Nombre: {row['player_name']}")
                print(f"  Equipo: {row['team_name']}")
                print(f"  Liga: {row['liga']}")
                print(f"  Rating: {row['rating_promedio']:.2f}")
                print(f"  Partidos: {row['partidos_total']}")
    else:
        print("  ⚠️  No se encontraron datos")


if __name__ == '__main__':
    main()
