#!/usr/bin/env python3
"""
Descarga escudos de equipos desde SofaScore usando Selenium + Canvas
Adaptado para RONDA 02-08 MARZO 2026
"""

import pandas as pd
import os
from pathlib import Path
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import base64

# Paths
BASE_DIR = Path('/Users/alvarolopezmolina/Desktop/Python/IDV_project/RONDA_02-08_03_26')
DATA_DIR = BASE_DIR / 'data'
LOGOS_DIR = BASE_DIR / 'team_logos'

# Crear directorio de logos si no existe
LOGOS_DIR.mkdir(parents=True, exist_ok=True)


def setup_driver():
    """Configura el driver de Selenium"""
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


def descargar_escudo_canvas(driver, team_id, team_name):
    """Descarga escudo usando Canvas para convertir la imagen"""
    if pd.isna(team_id) or team_id == '' or team_id == 0:
        print(f"  ⚠️  {team_name}: Sin ID")
        return None
    
    team_id = int(float(team_id))
    logo_path = LOGOS_DIR / f"{team_id}.png"
    
    # Si ya existe, no descargar de nuevo
    if logo_path.exists():
        print(f"  ✓ {team_name} ({team_id}): Ya existe")
        return logo_path
    
    try:
        # Crear página HTML temporal con canvas
        img_url = f"https://img.sofascore.com/api/v1/team/{team_id}/image/small"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
        </head>
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
        
        # Cargar HTML en el navegador
        driver.get("data:text/html;charset=utf-8," + html_content)
        time.sleep(3)
        
        # Intentar obtener la imagen del canvas
        try:
            image_data = driver.execute_script("return window.imageData;")
            if image_data:
                # Decodificar base64 y guardar
                image_data = image_data.split(',')[1]
                with open(logo_path, 'wb') as f:
                    f.write(base64.b64decode(image_data))
                print(f"  ✓ {team_name} ({team_id}): Descargado")
                return logo_path
            else:
                print(f"  ✗ {team_name} ({team_id}): No se pudo cargar imagen")
                return None
        except:
            print(f"  ✗ {team_name} ({team_id}): Error al procesar canvas")
            return None
            
    except Exception as e:
        print(f"  ✗ {team_name} ({team_id}): {str(e)[:50]}")
        return None


def main():
    print("\n" + "="*70)
    print("DESCARGA DE ESCUDOS DE EQUIPOS - RONDA 02-08 MARZO 2026")
    print("="*70)
    
    # Leer CSV con partidos
    csv_path = DATA_DIR / 'PARTIDOS_COMPACTO_CON_MPS.csv'
    print(f"\n📂 Leyendo: {csv_path}")
    
    df = pd.read_csv(csv_path)
    print(f"   {len(df)} partidos en ranking")
    
    # Extraer todos los team_ids únicos
    home_teams = df[['home_team_id', 'partido']].copy()
    home_teams['team_name'] = home_teams['partido'].str.split(' vs ').str[0]
    home_teams = home_teams[['home_team_id', 'team_name']].rename(columns={'home_team_id': 'team_id'})
    
    away_teams = df[['away_team_id', 'partido']].copy()
    away_teams['team_name'] = away_teams['partido'].str.split(' vs ').str[1]
    away_teams = away_teams[['away_team_id', 'team_name']].rename(columns={'away_team_id': 'team_id'})
    
    all_teams = pd.concat([home_teams, away_teams]).drop_duplicates(subset=['team_id'])
    all_teams = all_teams[all_teams['team_id'] > 0]  # Filtrar IDs inválidos
    
    print(f"\n📊 {len(all_teams)} equipos únicos encontrados")
    
    # Configurar driver
    driver = setup_driver()
    
    try:
        print(f"\n🔄 Descargando escudos...")
        downloaded = 0
        skipped = 0
        failed = 0
        
        for idx, row in all_teams.iterrows():
            team_id = row['team_id']
            team_name = row['team_name']
            
            result = descargar_escudo_canvas(driver, team_id, team_name)
            
            if result:
                if result.exists():
                    downloaded += 1
                else:
                    skipped += 1
            else:
                failed += 1
            
            time.sleep(1)  # Rate limiting
        
        print(f"\n{'='*70}")
        print("RESUMEN DE DESCARGA")
        print(f"{'='*70}")
        print(f"  ✓ Descargados: {downloaded}")
        print(f"  ⊙ Ya existían: {skipped}")
        print(f"  ✗ Fallidos: {failed}")
        print(f"  📊 Total: {len(all_teams)}")
        
    finally:
        driver.quit()
    
    print(f"\n{'='*70}")
    print("✅ DESCARGA COMPLETADA")
    print(f"{'='*70}")
    print(f"\n📂 Escudos guardados en: {LOGOS_DIR}")
    print(f"\n🎯 Siguiente paso: Generar PDF con ranking")


if __name__ == '__main__':
    main()
