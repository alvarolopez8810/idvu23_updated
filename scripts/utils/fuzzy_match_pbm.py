#!/usr/bin/env python3
"""
Fuzzy matching para equipos de Primera B Metro que no matchearon
"""

import pandas as pd
import json
from pathlib import Path
from difflib import SequenceMatcher
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import base64

# Paths
BASE_DIR = Path('/Users/alvarolopezmolina/Desktop/Python/IDV_project/RONDA_02-08_03_26')
LOGOS_DIR = BASE_DIR / 'team_logos'
STANDINGS_URL = 'https://www.sofascore.com/api/v1/tournament/7893/season/87941/standings/total'

# Equipos sin match
UNMATCHED = [
    'Arg. Quilmes',
    'Argentino Merlo',
    'Brown Adrogué',
    'Def. Unidos',
    'Dep. Armenio',
    'San Martín Burzaco',
    'Talleres R. Escalada'
]


def setup_driver():
    """Configura el driver de Selenium"""
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver


def fetch_standings(driver):
    """Obtiene datos de la tabla de posiciones"""
    driver.get(STANDINGS_URL)
    time.sleep(3)
    
    try:
        pre_element = driver.find_element(By.TAG_NAME, 'pre')
        json_text = pre_element.text
        data = json.loads(json_text)
        return data
    except Exception as e:
        return None


def extract_all_teams(standings_data):
    """Extrae TODOS los equipos de SofaScore"""
    teams = {}
    
    if not standings_data or 'standings' not in standings_data:
        return teams
    
    for standing in standings_data['standings']:
        if 'rows' in standing:
            for row in standing['rows']:
                if 'team' in row:
                    team = row['team']
                    team_id = team.get('id')
                    team_name = team.get('name', '')
                    
                    if team_id and team_name:
                        teams[team_name] = team_id
    
    return teams


def similarity(a, b):
    """Calcula similitud entre dos strings"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def fuzzy_match(csv_name, sofascore_teams, threshold=0.6):
    """Encuentra el mejor match usando fuzzy matching"""
    best_match = None
    best_score = 0
    
    for ss_name, team_id in sofascore_teams.items():
        score = similarity(csv_name, ss_name)
        
        if score > best_score:
            best_score = score
            best_match = {'sofascore_name': ss_name, 'team_id': team_id, 'score': score}
    
    if best_score >= threshold:
        return best_match
    return None


def descargar_escudo_canvas(driver, team_id, team_name):
    """Descarga escudo usando Canvas"""
    logo_path = LOGOS_DIR / f"{team_id}.png"
    
    if logo_path.exists():
        return logo_path
    
    try:
        img_url = f"https://img.sofascore.com/api/v1/team/{team_id}/image/small"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"></head>
        <body>
            <img id="teamLogo" crossorigin="anonymous" src="{img_url}" style="display:none;">
            <canvas id="canvas" width="100" height="100"></canvas>
            <script>
                var img = document.getElementById('teamLogo');
                var canvas = document.getElementById('canvas');
                var ctx = canvas.getContext('2d');
                
                img.onload = function() {{
                    ctx.drawImage(img, 0, 0, 100, 100);
                    window.imageData = canvas.toDataURL('image/png');
                }};
                
                img.onerror = function() {{
                    window.imageError = true;
                }};
            </script>
        </body>
        </html>
        """
        
        driver.get("data:text/html;charset=utf-8," + html_content)
        time.sleep(3)
        
        image_data = driver.execute_script("return window.imageData;")
        if image_data:
            image_data = image_data.split(',')[1]
            with open(logo_path, 'wb') as f:
                f.write(base64.b64decode(image_data))
            return logo_path
        return None
            
    except Exception as e:
        return None


def main():
    print("\n" + "="*70)
    print("FUZZY MATCHING - EQUIPOS PRIMERA B METRO")
    print("="*70)
    
    driver = setup_driver()
    
    try:
        # Obtener todos los equipos de SofaScore
        print(f"\n📡 Obteniendo equipos de SofaScore...")
        standings_data = fetch_standings(driver)
        
        if not standings_data:
            print("✗ No se pudieron obtener datos")
            return
        
        sofascore_teams = extract_all_teams(standings_data)
        print(f"   ✓ {len(sofascore_teams)} equipos encontrados")
        
        print(f"\n📋 Equipos en SofaScore:")
        for name in sorted(sofascore_teams.keys()):
            print(f"   • {name}")
        
        # Fuzzy matching
        print(f"\n{'='*70}")
        print("FUZZY MATCHING")
        print(f"{'='*70}")
        
        new_matches = {}
        still_unmatched = []
        
        for csv_name in UNMATCHED:
            match = fuzzy_match(csv_name, sofascore_teams, threshold=0.5)
            
            if match:
                print(f"\n✓ {csv_name}")
                print(f"  → {match['sofascore_name']} (ID: {match['team_id']})")
                print(f"  → Similitud: {match['score']:.2%}")
                new_matches[csv_name] = match
            else:
                print(f"\n✗ {csv_name}: Sin match")
                still_unmatched.append(csv_name)
        
        # Descargar escudos de nuevos matches
        if new_matches:
            print(f"\n{'='*70}")
            print("DESCARGANDO ESCUDOS")
            print(f"{'='*70}")
            
            downloaded = 0
            for csv_name, match in new_matches.items():
                result = descargar_escudo_canvas(driver, match['team_id'], csv_name)
                if result and result.exists():
                    print(f"  ✓ {csv_name} ({match['team_id']}): Descargado")
                    downloaded += 1
                else:
                    print(f"  ✗ {csv_name} ({match['team_id']}): Error")
                time.sleep(1)
            
            print(f"\n✅ {downloaded}/{len(new_matches)} escudos descargados")
        
        # Actualizar mapping
        mapping_file = BASE_DIR / 'team_id_mapping_pbm.json'
        if mapping_file.exists():
            with open(mapping_file, 'r', encoding='utf-8') as f:
                existing_mapping = json.load(f)
        else:
            existing_mapping = {}
        
        # Agregar nuevos matches
        for csv_name, match in new_matches.items():
            existing_mapping[csv_name] = {
                'sofascore_name': match['sofascore_name'],
                'team_id': match['team_id']
            }
        
        with open(mapping_file, 'w', encoding='utf-8') as f:
            json.dump(existing_mapping, f, indent=2, ensure_ascii=False)
        
        print(f"\n📂 Mapping actualizado: {mapping_file}")
        
        # Resumen final
        print(f"\n{'='*70}")
        print("RESUMEN FINAL")
        print(f"{'='*70}")
        print(f"  ✓ Nuevos matches: {len(new_matches)}")
        print(f"  ✗ Aún sin match: {len(still_unmatched)}")
        print(f"  📊 Total equipos matched: {len(existing_mapping)}/22")
        
        if still_unmatched:
            print(f"\n⚠️  Equipos que aún no tienen match:")
            for team in still_unmatched:
                print(f"    • {team}")
        
    finally:
        driver.quit()
    
    print(f"\n{'='*70}")
    print("✅ PROCESO COMPLETADO")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
