#!/usr/bin/env python3
"""
Obtener team_ids de Primera B Metro desde SofaScore API
y descargar escudos
"""

import pandas as pd
import json
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import base64

# Paths
BASE_DIR = Path('/Users/alvarolopezmolina/Desktop/Python/IDV_project/RONDA_02-08_03_26')
LOGOS_DIR = BASE_DIR / 'team_logos'
LOGOS_DIR.mkdir(parents=True, exist_ok=True)

# API URL
STANDINGS_URL = 'https://www.sofascore.com/api/v1/tournament/7893/season/87941/standings/total'


def setup_driver():
    """Configura el driver de Selenium"""
    chrome_options = Options()
    # chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver


def fetch_standings(driver):
    """Obtiene datos de la tabla de posiciones"""
    print(f"\n📡 Obteniendo datos de SofaScore...")
    print(f"   URL: {STANDINGS_URL}")
    
    driver.get(STANDINGS_URL)
    time.sleep(3)
    
    try:
        pre_element = driver.find_element(By.TAG_NAME, 'pre')
        json_text = pre_element.text
        data = json.loads(json_text)
        return data
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return None


def extract_teams(standings_data):
    """Extrae team_id y nombres de equipos"""
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


def normalize_name(name):
    """Normaliza nombre para matching"""
    # Remover acentos y caracteres especiales
    replacements = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
        '.': '', ' ': ''
    }
    
    normalized = name.lower()
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)
    
    return normalized


def match_teams(csv_teams, sofascore_teams):
    """Matchea equipos del CSV con SofaScore"""
    matches = {}
    unmatched = []
    
    for csv_team in csv_teams:
        matched = False
        csv_normalized = normalize_name(csv_team)
        
        # Buscar match exacto o parcial
        for ss_team, team_id in sofascore_teams.items():
            ss_normalized = normalize_name(ss_team)
            
            # Match exacto
            if csv_normalized == ss_normalized:
                matches[csv_team] = {'sofascore_name': ss_team, 'team_id': team_id}
                matched = True
                break
            
            # Match parcial (contiene)
            if csv_normalized in ss_normalized or ss_normalized in csv_normalized:
                matches[csv_team] = {'sofascore_name': ss_team, 'team_id': team_id}
                matched = True
                break
        
        if not matched:
            unmatched.append(csv_team)
    
    return matches, unmatched


def descargar_escudo_canvas(driver, team_id, team_name):
    """Descarga escudo usando Canvas"""
    logo_path = LOGOS_DIR / f"{team_id}.png"
    
    if logo_path.exists():
        print(f"  ✓ {team_name} ({team_id}): Ya existe")
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
            print(f"  ✓ {team_name} ({team_id}): Descargado")
            return logo_path
        else:
            print(f"  ✗ {team_name} ({team_id}): No se pudo cargar")
            return None
            
    except Exception as e:
        print(f"  ✗ {team_name} ({team_id}): {str(e)[:50]}")
        return None


def main():
    print("\n" + "="*70)
    print("OBTENER TEAM IDS Y ESCUDOS - PRIMERA B METRO")
    print("="*70)
    
    # Leer equipos del CSV
    pbm_file = BASE_DIR / 'u23_primera_b_metro_resumen.csv'
    df = pd.read_csv(pbm_file)
    csv_teams = sorted(set(df['team'].unique()) | set(df['opponent'].unique()))
    
    print(f"\n📊 {len(csv_teams)} equipos en CSV")
    
    # Setup driver
    driver = setup_driver()
    
    try:
        # Obtener datos de SofaScore
        standings_data = fetch_standings(driver)
        
        if not standings_data:
            print("\n✗ No se pudieron obtener datos de SofaScore")
            return
        
        # Extraer equipos
        sofascore_teams = extract_teams(standings_data)
        print(f"\n📊 {len(sofascore_teams)} equipos encontrados en SofaScore")
        
        # Matchear equipos
        print(f"\n🔄 Matcheando equipos...")
        matches, unmatched = match_teams(csv_teams, sofascore_teams)
        
        print(f"\n{'='*70}")
        print("RESULTADOS DEL MATCHING")
        print(f"{'='*70}")
        print(f"  ✓ Matched: {len(matches)}/{len(csv_teams)}")
        print(f"  ✗ Unmatched: {len(unmatched)}")
        
        if matches:
            print(f"\n✓ Equipos matched:")
            for csv_name, info in matches.items():
                print(f"  • {csv_name} → {info['sofascore_name']} (ID: {info['team_id']})")
        
        if unmatched:
            print(f"\n✗ Equipos sin match:")
            for team in unmatched:
                print(f"  • {team}")
        
        # Descargar escudos
        if matches:
            print(f"\n{'='*70}")
            print("DESCARGANDO ESCUDOS")
            print(f"{'='*70}")
            
            downloaded = 0
            for csv_name, info in matches.items():
                result = descargar_escudo_canvas(driver, info['team_id'], csv_name)
                if result and result.exists():
                    downloaded += 1
                time.sleep(1)
            
            print(f"\n✅ {downloaded}/{len(matches)} escudos descargados")
        
        # Guardar mapping para referencia
        mapping_file = BASE_DIR / 'team_id_mapping_pbm.json'
        with open(mapping_file, 'w', encoding='utf-8') as f:
            json.dump(matches, f, indent=2, ensure_ascii=False)
        
        print(f"\n📂 Mapping guardado: {mapping_file}")
        
    finally:
        driver.quit()
    
    print(f"\n{'='*70}")
    print("✅ PROCESO COMPLETADO")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
