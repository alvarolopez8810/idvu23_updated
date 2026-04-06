#!/usr/bin/env python3
"""
Obtener ratings acumulados de jugadores desde SofaScore API
usando tournament/season específicos por liga
"""

import pandas as pd
import requests
import time
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / 'data'

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

def get_player_season_rating(player_id, tournament_id, season_id):
    """Obtiene el rating acumulado de un jugador en una temporada específica"""
    
    url = f"https://www.sofascore.com/api/v1/player/{player_id}/unique-tournament/{tournament_id}/season/{season_id}/ratings/overall"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'application/json',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extraer rating promedio y número de partidos
            rating = data.get('rating', 0)
            appearances = data.get('appearances', 0)
            
            return {
                'rating_promedio': rating,
                'partidos_total': appearances,
                'success': True
            }
        else:
            return {'rating_promedio': 0, 'partidos_total': 0, 'success': False}
    
    except Exception as e:
        print(f"    ✗ Error: {str(e)[:50]}")
        return {'rating_promedio': 0, 'partidos_total': 0, 'success': False}


def main():
    print("\n" + "="*70)
    print("OBTENER RATINGS ACUMULADOS DE SOFASCORE")
    print("="*70)
    
    # Cargar datos de jugadores
    jugadores_path = DATA_DIR / 'jugadores_completo_con_pbm.csv'
    print(f"\n📂 Leyendo: {jugadores_path}")
    df = pd.read_csv(jugadores_path)
    print(f"   {len(df)} registros cargados")
    
    # Filtrar jugadores U23 únicos con player_id
    df_u23 = df[
        (df['is_u23'] == True) &
        (df['player_id'].notna())
    ].copy()
    
    # Obtener jugadores únicos
    jugadores_unicos = df_u23.groupby('player_id').agg({
        'player_name': 'first',
        'liga': 'first',
        'date_of_birth': 'first'
    }).reset_index()
    
    print(f"\n🔄 Procesando {len(jugadores_unicos)} jugadores U23 únicos...")
    
    # Crear diccionario para almacenar resultados
    ratings_acumulados = {}
    
    for idx, row in jugadores_unicos.iterrows():
        player_id = int(row['player_id'])
        player_name = row['player_name']
        liga = row['liga']
        
        # Verificar si la liga tiene mapping
        if liga not in LIGA_TOURNAMENT_SEASON:
            print(f"  ⚠️  {player_name} ({liga}): Liga sin mapping")
            continue
        
        tournament_id = LIGA_TOURNAMENT_SEASON[liga]['tournament']
        season_id = LIGA_TOURNAMENT_SEASON[liga]['season']
        
        print(f"\n  {idx+1}/{len(jugadores_unicos)}: {player_name} ({liga})")
        print(f"    Tournament: {tournament_id}, Season: {season_id}")
        
        # Obtener rating acumulado
        result = get_player_season_rating(player_id, tournament_id, season_id)
        
        if result['success']:
            ratings_acumulados[player_id] = {
                'player_name': player_name,
                'liga': liga,
                'rating_promedio': result['rating_promedio'],
                'partidos_total': result['partidos_total']
            }
            print(f"    ✓ Rating: {result['rating_promedio']:.2f}, Partidos: {result['partidos_total']}")
        else:
            print(f"    ✗ No se pudo obtener rating")
        
        # Delay para no saturar la API
        time.sleep(0.5)
    
    # Guardar resultados
    output_path = DATA_DIR / 'ratings_acumulados_sofascore.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(ratings_acumulados, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*70}")
    print("✅ RATINGS ACUMULADOS OBTENIDOS")
    print(f"{'='*70}")
    print(f"  📊 {len(ratings_acumulados)} jugadores procesados exitosamente")
    print(f"  📂 Guardado en: {output_path}")
    
    # Estadísticas
    total_con_rating = sum(1 for r in ratings_acumulados.values() if r['rating_promedio'] > 0)
    print(f"\n📈 Estadísticas:")
    print(f"  • Jugadores con rating: {total_con_rating}")
    print(f"  • Jugadores sin rating: {len(ratings_acumulados) - total_con_rating}")


if __name__ == '__main__':
    main()
