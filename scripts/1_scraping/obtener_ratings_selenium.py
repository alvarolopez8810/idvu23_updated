#!/usr/bin/env python3
"""
Obtener ratings acumulados de jugadores desde SofaScore usando Selenium
Para ANEXOS II y IV (Acumulado U23 y 18-21)
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
from selenium.common.exceptions import TimeoutException
import random

BASE_DIR = Path('/Users/alvarolopezmolina/Desktop/Python/IDV_project/RONDA_02-08_03_26')
DATA_DIR = BASE_DIR / 'data'

# Mapping de ligas a tournament_id y season_id
LIGA_TOURNAMENT_SEASON = {
    'Paranaense': {'tournament': 382, 'season': 86658},
    'Mineiro': {'tournament': 379, 'season': 87236},
    'Carioca': {'tournament': 92, 'season': 86674},
    'Gaúcho': {'tournament': 377, 'season': 86736},
    'Baiano': {'tournament': 374, 'season': 86656},
    'Colombia 2 Div': {'tournament': 1238, 'season': 89001},
    'Paulista A1': {'tournament': 372, 'season': 86993},
    'Paulista A2': {'tournament': 1234, 'season': 87118},
}

class SofaScoreRatingScraper:
    def __init__(self):
        self.setup_driver()
        self.base_url = "https://www.sofascore.com/api/v1"
        
    def setup_driver(self):
        """Configura el driver de Selenium con opciones para evitar detección"""
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
        
    def random_delay(self, min_seconds=1, max_seconds=3):
        """Añade un delay aleatorio para evitar detección"""
        time.sleep(random.uniform(min_seconds, max_seconds))
        
    def get_json_from_url(self, url, max_retries=3):
        """Obtiene JSON de una URL usando Selenium"""
        for attempt in range(max_retries):
            try:
                self.driver.get(url)
                self.random_delay(0.5, 1.5)
                
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
    
    def get_player_season_rating(self, player_id, tournament_id, season_id):
        """Obtiene el rating acumulado de un jugador en una temporada específica"""
        
        url = f"{self.base_url}/player/{player_id}/unique-tournament/{tournament_id}/season/{season_id}/ratings/overall"
        
        data = self.get_json_from_url(url)
        
        if data and 'seasonRatings' in data:
            season_ratings = data['seasonRatings']
            
            if len(season_ratings) > 0:
                # Calcular promedio de ratings de todos los partidos
                ratings = [match['rating'] for match in season_ratings if 'rating' in match]
                
                if ratings:
                    rating_promedio = sum(ratings) / len(ratings)
                    partidos_total = len(ratings)
                    
                    return {
                        'rating_promedio': rating_promedio,
                        'partidos_total': partidos_total,
                        'success': True
                    }
        
        return {'rating_promedio': 0, 'partidos_total': 0, 'success': False}
    
    def close(self):
        """Cierra el driver"""
        self.driver.quit()


def main():
    print("\n" + "="*70)
    print("OBTENER RATINGS ACUMULADOS DE SOFASCORE CON SELENIUM")
    print("="*70)
    
    # Cargar datos de jugadores
    jugadores_path = DATA_DIR / 'jugadores_completo_con_pbm.csv'
    print(f"\n📂 Leyendo: {jugadores_path}")
    df = pd.read_csv(jugadores_path)
    print(f"   {len(df)} registros cargados")
    
    # Filtrar jugadores U23 únicos con player_id y liga válida
    df_u23 = df[
        (df['is_u23'] == True) &
        (df['player_id'].notna()) &
        (df['liga'].isin(LIGA_TOURNAMENT_SEASON.keys()))
    ].copy()
    
    # Obtener jugadores únicos
    jugadores_unicos = df_u23.groupby('player_id').agg({
        'player_name': 'first',
        'liga': 'first',
        'date_of_birth': 'first'
    }).reset_index()
    
    print(f"\n🔄 Procesando {len(jugadores_unicos)} jugadores U23 únicos con ligas válidas...")
    
    # Inicializar scraper
    scraper = SofaScoreRatingScraper()
    
    # Crear diccionario para almacenar resultados
    ratings_acumulados = {}
    exitosos = 0
    fallidos = 0
    
    try:
        for idx, row in jugadores_unicos.iterrows():
            player_id = int(row['player_id'])
            player_name = row['player_name']
            liga = row['liga']
            
            tournament_id = LIGA_TOURNAMENT_SEASON[liga]['tournament']
            season_id = LIGA_TOURNAMENT_SEASON[liga]['season']
            
            print(f"\n  [{idx+1}/{len(jugadores_unicos)}] {player_name} ({liga})")
            print(f"    Tournament: {tournament_id}, Season: {season_id}")
            
            # Obtener rating acumulado
            result = scraper.get_player_season_rating(player_id, tournament_id, season_id)
            
            if result['success'] and result['partidos_total'] > 0:
                ratings_acumulados[player_id] = {
                    'player_name': player_name,
                    'liga': liga,
                    'rating_promedio': result['rating_promedio'],
                    'partidos_total': result['partidos_total']
                }
                print(f"    ✓ Rating: {result['rating_promedio']:.2f}, Partidos: {result['partidos_total']}")
                exitosos += 1
            else:
                print(f"    ✗ Sin datos")
                fallidos += 1
            
            # Delay más largo cada 10 jugadores
            if (idx + 1) % 10 == 0:
                print(f"\n    ⏸️  Pausa de seguridad (procesados {idx+1}/{len(jugadores_unicos)})...")
                time.sleep(3)
    
    finally:
        # Cerrar driver
        scraper.close()
    
    # Guardar resultados
    output_path = DATA_DIR / 'ratings_acumulados_sofascore.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(ratings_acumulados, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*70}")
    print("✅ PROCESO COMPLETADO")
    print(f"{'='*70}")
    print(f"  📊 Jugadores procesados: {len(jugadores_unicos)}")
    print(f"  ✓ Exitosos: {exitosos}")
    print(f"  ✗ Fallidos: {fallidos}")
    print(f"  📂 Guardado en: {output_path}")
    
    # Crear CSV para fácil revisión
    if ratings_acumulados:
        df_ratings = pd.DataFrame.from_dict(ratings_acumulados, orient='index')
        df_ratings['player_id'] = df_ratings.index
        df_ratings = df_ratings[['player_id', 'player_name', 'liga', 'rating_promedio', 'partidos_total']]
        df_ratings = df_ratings.sort_values('rating_promedio', ascending=False)
        
        csv_path = DATA_DIR / 'ratings_acumulados_sofascore.csv'
        df_ratings.to_csv(csv_path, index=False, encoding='utf-8')
        print(f"  📄 CSV guardado en: {csv_path}")
        
        # Mostrar top 10
        print(f"\n📈 TOP 10 RATINGS ACUMULADOS:")
        for idx, row in df_ratings.head(10).iterrows():
            print(f"  {idx+1}. {row['player_name']} ({row['liga']}): {row['rating_promedio']:.2f} - {row['partidos_total']} partidos")


if __name__ == '__main__':
    main()
