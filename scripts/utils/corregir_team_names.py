#!/usr/bin/env python3
"""
Corrige los team_names en el CSV que aparecen como 'Unknown'
Vuelve a scrapear solo los nombres de equipo desde SofaScore
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

BASE_DIR = Path('/Users/alvarolopezmolina/Desktop/Python/IDV_project/RONDA_02-08_03_26')
DATA_DIR = BASE_DIR / 'data'

class TeamNameFixer:
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
    
    def get_player_team(self, player_id):
        """Obtiene el equipo actual del jugador"""
        url = f"{self.base_url}/player/{player_id}"
        
        data = self.get_json_from_url(url)
        
        if data and 'player' in data:
            team = data['player'].get('team', {})
            return team.get('name', 'Unknown')
        
        return 'Unknown'
    
    def close(self):
        """Cierra el driver"""
        self.driver.quit()


def main():
    print("\n" + "="*80)
    print("CORRIGIENDO TEAM NAMES EN CSV")
    print("="*80)
    
    # Cargar CSV
    csv_file = DATA_DIR / 'u23_acumulado_completo.csv'
    
    if not csv_file.exists():
        print(f"❌ Error: No se encontró {csv_file}")
        return
    
    print(f"\n📂 Cargando datos: {csv_file}")
    df = pd.read_csv(csv_file)
    print(f"  ✓ {len(df)} jugadores cargados")
    
    # Contar cuántos tienen Unknown
    unknown_count = len(df[df['team_name'] == 'Unknown'])
    print(f"  ⚠️  {unknown_count} jugadores con team_name = 'Unknown'")
    
    if unknown_count == 0:
        print("\n✅ No hay jugadores con team_name Unknown. No se requiere corrección.")
        return
    
    # Corregir team names
    fixer = TeamNameFixer()
    
    try:
        print(f"\n🔧 Corrigiendo team names...")
        
        for idx, row in df.iterrows():
            if row['team_name'] == 'Unknown':
                player_id = row['player_id']
                player_name = row['player_name']
                
                print(f"  [{idx+1}/{len(df)}] {player_name} (ID: {player_id})", end='')
                
                team_name = fixer.get_player_team(player_id)
                df.at[idx, 'team_name'] = team_name
                
                print(f" → {team_name}")
                
                fixer.random_delay(0.3, 0.6)
    
    finally:
        fixer.close()
    
    # Guardar CSV corregido
    print(f"\n💾 Guardando CSV corregido...")
    df.to_csv(csv_file, index=False, encoding='utf-8')
    print(f"  ✓ CSV guardado: {csv_file}")
    
    # Guardar JSON también
    json_file = DATA_DIR / 'u23_acumulado_completo.json'
    df.to_json(json_file, orient='records', indent=2, force_ascii=False)
    print(f"  ✓ JSON guardado: {json_file}")
    
    # Verificar corrección
    unknown_after = len(df[df['team_name'] == 'Unknown'])
    print(f"\n📊 Resultado:")
    print(f"  • Antes: {unknown_count} jugadores con Unknown")
    print(f"  • Después: {unknown_after} jugadores con Unknown")
    print(f"  • Corregidos: {unknown_count - unknown_after}")
    print()


if __name__ == '__main__':
    main()
