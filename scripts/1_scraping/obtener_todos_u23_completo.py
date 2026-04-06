#!/usr/bin/env python3
"""
Obtener TODOS los jugadores U23 de las ligas con sus ratings acumulados
Método: standings -> teams -> players -> ratings
Esto incluye jugadores que NO jugaron esta semana
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

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / 'data'

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

class SofaScoreCompleteU23Scraper:
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
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
    def random_delay(self, min_seconds=0.5, max_seconds=1.5):
        """Delay aleatorio"""
        time.sleep(random.uniform(min_seconds, max_seconds))
        
    def get_json_from_url(self, url, max_retries=3):
        """Obtiene JSON de una URL usando Selenium"""
        for attempt in range(max_retries):
            try:
                self.driver.get(url)
                self.random_delay(0.3, 0.8)
                
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
    
    def get_teams_from_standings(self, tournament_id, season_id):
        """Obtiene todos los equipos de una liga desde standings"""
        url = f"{self.base_url}/unique-tournament/{tournament_id}/season/{season_id}/standings/total"
        
        data = self.get_json_from_url(url)
        
        if not data or 'standings' not in data:
            return []
        
        teams = []
        for standing_group in data['standings']:
            for row in standing_group.get('rows', []):
                team = row.get('team', {})
                team_id = team.get('id')
                team_name = team.get('name', 'Unknown')
                if team_id:
                    teams.append({'team_id': team_id, 'team_name': team_name})
        
        return teams
    
    def get_team_players(self, team_id):
        """Obtiene todos los jugadores de un equipo"""
        url = f"{self.base_url}/team/{team_id}/players"
        
        data = self.get_json_from_url(url)
        
        if not data or 'players' not in data:
            return []
        
        players = []
        current_year = datetime.now().year
        
        for player_data in data['players']:
            player = player_data.get('player', {})
            player_id = player.get('id')
            player_name = player.get('name', 'Unknown')
            date_of_birth_timestamp = player.get('dateOfBirthTimestamp')
            
            if player_id and date_of_birth_timestamp:
                birth_year = datetime.fromtimestamp(date_of_birth_timestamp).year
                age = current_year - birth_year
                
                # Filtrar U23 (nacidos en 2003 o posterior)
                if birth_year >= 2003:
                    players.append({
                        'player_id': player_id,
                        'player_name': player_name,
                        'birth_year': birth_year,
                        'age': age,
                        'date_of_birth': datetime.fromtimestamp(date_of_birth_timestamp).strftime('%d/%m/%Y')
                    })
        
        return players
    
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
    print("OBTENER TODOS LOS JUGADORES U23 CON RATINGS ACUMULADOS")
    print("Método: standings -> teams -> players -> ratings")
    print("="*80)
    
    scraper = SofaScoreCompleteU23Scraper()
    
    all_players_data = []
    total_equipos = 0
    total_jugadores_u23 = 0
    total_con_rating = 0
    
    try:
        for liga_nombre, config in LIGAS_CONFIG.items():
            tournament_id = config['tournament']
            season_id = config['season']
            
            print(f"\n{'='*80}")
            print(f"📊 LIGA: {liga_nombre}")
            print(f"   Tournament: {tournament_id}, Season: {season_id}")
            print(f"{'='*80}")
            
            # 1. Obtener equipos de standings
            print(f"\n  🔍 Obteniendo equipos de standings...")
            teams = scraper.get_teams_from_standings(tournament_id, season_id)
            print(f"  ✓ {len(teams)} equipos encontrados")
            total_equipos += len(teams)
            
            # 2. Para cada equipo, obtener jugadores U23
            for idx, team in enumerate(teams, 1):
                team_id = team['team_id']
                team_name = team['team_name']
                
                print(f"\n  [{idx}/{len(teams)}] {team_name} (ID: {team_id})")
                
                # Obtener jugadores del equipo
                players = scraper.get_team_players(team_id)
                u23_players = [p for p in players if p['birth_year'] >= 2003]
                
                if u23_players:
                    print(f"    ✓ {len(u23_players)} jugadores U23 encontrados")
                    total_jugadores_u23 += len(u23_players)
                    
                    # 3. Para cada jugador U23, obtener rating acumulado
                    for player in u23_players:
                        player_id = player['player_id']
                        player_name = player['player_name']
                        
                        result = scraper.get_player_season_rating(player_id, tournament_id, season_id)
                        
                        if result['success'] and result['partidos_total'] >= 2:
                            all_players_data.append({
                                'player_id': player_id,
                                'player_name': player_name,
                                'team_name': team_name,
                                'liga': liga_nombre,
                                'birth_year': player['birth_year'],
                                'age': player['age'],
                                'date_of_birth': player['date_of_birth'],
                                'rating_promedio': result['rating_promedio'],
                                'partidos_total': result['partidos_total']
                            })
                            print(f"      ✓ {player_name}: {result['rating_promedio']:.2f} ({result['partidos_total']} partidos)")
                            total_con_rating += 1
                        else:
                            print(f"      ✗ {player_name}: Sin datos suficientes")
                        
                        scraper.random_delay(0.2, 0.5)
                else:
                    print(f"    - No hay jugadores U23")
                
                # Delay entre equipos
                scraper.random_delay(0.5, 1.0)
    
    finally:
        scraper.close()
    
    # Guardar resultados
    print(f"\n{'='*80}")
    print("💾 GUARDANDO RESULTADOS")
    print(f"{'='*80}")
    
    if all_players_data:
        # Guardar JSON
        output_json = DATA_DIR / 'todos_u23_ratings_completo.json'
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(all_players_data, f, indent=2, ensure_ascii=False)
        print(f"  ✓ JSON guardado: {output_json}")
        
        # Guardar CSV
        df = pd.DataFrame(all_players_data)
        df = df.sort_values('rating_promedio', ascending=False)
        output_csv = DATA_DIR / 'todos_u23_ratings_completo.csv'
        df.to_csv(output_csv, index=False, encoding='utf-8')
        print(f"  ✓ CSV guardado: {output_csv}")
        
        # Estadísticas
        print(f"\n{'='*80}")
        print("📊 ESTADÍSTICAS FINALES")
        print(f"{'='*80}")
        print(f"  📍 Ligas procesadas: {len(LIGAS_CONFIG)}")
        print(f"  🏟️  Equipos procesados: {total_equipos}")
        print(f"  👤 Jugadores U23 encontrados: {total_jugadores_u23}")
        print(f"  ✅ Jugadores con rating (≥2 partidos): {total_con_rating}")
        
        # Top 10
        print(f"\n{'='*80}")
        print("🏆 TOP 10 RATINGS ACUMULADOS")
        print(f"{'='*80}")
        for idx, row in df.head(10).iterrows():
            print(f"  {idx+1}. {row['player_name']} ({row['liga']}) - {row['team_name']}")
            print(f"     Rating: {row['rating_promedio']:.2f} | Partidos: {row['partidos_total']} | Edad: {row['age']}")
    else:
        print("  ⚠️  No se encontraron datos")


if __name__ == '__main__':
    main()
