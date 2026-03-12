#!/usr/bin/env python3
"""
Extrae ratings individuales por partido de jugadores U23
Para crear ANEXO IV: Puntuaciones más altas - Record por jornada
"""

import pandas as pd
import json
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
from datetime import datetime

BASE_DIR = Path('/Users/alvarolopezmolina/Desktop/Python/IDV_project/RONDA_02-08_03_26')
DATA_DIR = BASE_DIR / 'data'

# Mapping de ligas
LIGAS_CONFIG = {
    'Paranaense': {'tournament': 382, 'season': 86658},
    'Mineiro': {'tournament': 379, 'season': 87236},
    'Carioca': {'tournament': 92, 'season': 86674},
    'Gaúcho': {'tournament': 377, 'season': 86736},
    'Baiano': {'tournament': 374, 'season': 86656},
    'Paulista A1': {'tournament': 372, 'season': 86993},
    'Paulista A2': {'tournament': 1234, 'season': 87118},
}


class RatingsExtractor:
    def __init__(self):
        self.setup_driver()
        self.base_url = "https://www.sofascore.com/api/v1"
        
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
    
    def get_player_season_ratings(self, player_id, tournament_id, season_id):
        """Obtiene todos los ratings de un jugador en una temporada"""
        url = f"{self.base_url}/player/{player_id}/unique-tournament/{tournament_id}/season/{season_id}/ratings/overall"
        
        data = self.get_json_from_url(url)
        
        if data and 'seasonRatings' in data:
            return data['seasonRatings']
        
        return []
    
    def close(self):
        """Cierra el driver"""
        self.driver.quit()


def main():
    print("\n" + "="*80)
    print("EXTRAYENDO RATINGS POR PARTIDO - JUGADORES U23")
    print("="*80)
    
    # Cargar datos de jugadores U23
    players_file = DATA_DIR / 'u23_acumulado_completo.csv'
    
    if not players_file.exists():
        print(f"❌ Error: No se encontró {players_file}")
        return
    
    print(f"\n📂 Cargando jugadores U23: {players_file}")
    df = pd.read_csv(players_file)
    print(f"  ✓ {len(df)} jugadores cargados")
    
    # Filtrar solo U23 (nacidos 2003+)
    df_u23 = df[df['birth_year'] >= 2003].copy()
    print(f"  ✓ {len(df_u23)} jugadores U23 (nacidos 2003+)")
    
    extractor = RatingsExtractor()
    all_ratings = []
    
    try:
        print(f"\n🔍 Extrayendo ratings por partido...")
        
        for idx, row in df_u23.iterrows():
            player_id = row['player_id']
            player_name = row['player_name']
            liga = row['liga']
            birth_year = row['birth_year']
            date_of_birth = row['date_of_birth']
            team_name = row['team_name']
            
            # Obtener config de la liga
            liga_config = LIGAS_CONFIG.get(liga)
            if not liga_config:
                continue
            
            tournament_id = liga_config['tournament']
            season_id = liga_config['season']
            
            print(f"  [{idx+1}/{len(df_u23)}] {player_name} ({liga})", end='')
            
            # Obtener ratings por partido
            season_ratings = extractor.get_player_season_ratings(player_id, tournament_id, season_id)
            
            if season_ratings:
                print(f" → {len(season_ratings)} partidos")
                
                # Procesar cada partido
                for match_rating in season_ratings:
                    rating = match_rating.get('rating')
                    
                    if rating:
                        # Obtener info del partido
                        event = match_rating.get('event', {})
                        home_team = event.get('homeTeam', {}).get('name', '')
                        away_team = event.get('awayTeam', {}).get('name', '')
                        match_info = f"{home_team} vs {away_team}"
                        
                        all_ratings.append({
                            'player_id': player_id,
                            'player_name': player_name,
                            'team_name': team_name,
                            'liga': liga,
                            'birth_year': birth_year,
                            'date_of_birth': date_of_birth,
                            'rating': rating,
                            'match': match_info,
                            'event_id': event.get('id')
                        })
            else:
                print(" → Sin ratings")
            
            extractor.random_delay(0.2, 0.5)
    
    finally:
        extractor.close()
    
    # Guardar resultados
    print(f"\n💾 Guardando resultados...")
    
    output_file = DATA_DIR / 'u23_ratings_por_partido.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_ratings, f, indent=2, ensure_ascii=False)
    
    print(f"  ✓ JSON guardado: {output_file}")
    print(f"  ✓ Total registros: {len(all_ratings)}")
    
    # Estadísticas
    if all_ratings:
        all_ratings_sorted = sorted(all_ratings, key=lambda x: x['rating'], reverse=True)
        
        print(f"\n📊 TOP 10 RATINGS INDIVIDUALES:")
        for idx, record in enumerate(all_ratings_sorted[:10], 1):
            print(f"  {idx}. {record['rating']:.2f} - {record['player_name']} ({record['team_name']})")
            print(f"      {record['match']}")
    
    print()


if __name__ == '__main__':
    main()
