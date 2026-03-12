#!/usr/bin/env python3
"""Verificar rating de Chiqueti"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import time

# Setup driver
chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--disable-blink-features=AutomationControlled')
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)
chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')

driver = webdriver.Chrome(options=chrome_options)
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

# Chiqueti - Paranaense
player_id = 1459788
tournament_id = 382
season_id = 86658

url = f'https://www.sofascore.com/api/v1/player/{player_id}/unique-tournament/{tournament_id}/season/{season_id}/ratings/overall'

print(f"\n🔍 Obteniendo datos de Chiqueti...")
print(f"   URL: {url}")

driver.get(url)
time.sleep(2)

try:
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "pre"))
    )
    
    page_source = driver.page_source
    
    if '<pre>' in page_source:
        json_text = page_source.split('<pre>')[1].split('</pre>')[0]
        data = json.loads(json_text)
        
        print(f"\n✅ Datos obtenidos:")
        print(json.dumps(data, indent=2)[:500])
        
        if 'seasonRatings' in data:
            ratings = [m['rating'] for m in data['seasonRatings'] if 'rating' in m]
            if ratings:
                avg_rating = sum(ratings) / len(ratings)
                print(f"\n{'='*60}")
                print(f"⚽ CHIQUETI (ID: {player_id})")
                print(f"{'='*60}")
                print(f"  Liga: Paranaense")
                print(f"  Rating promedio: {avg_rating:.2f}")
                print(f"  Partidos jugados: {len(ratings)}")
                print(f"  Ratings por partido: {[f'{r:.1f}' for r in ratings]}")
                print(f"{'='*60}")
            else:
                print("\n⚠️  No hay ratings en seasonRatings")
        else:
            print("\n⚠️  No se encontró 'seasonRatings' en la respuesta")
    else:
        print("\n⚠️  No se encontró <pre> en la página")
        
except Exception as e:
    print(f"\n❌ Error: {e}")

driver.quit()
