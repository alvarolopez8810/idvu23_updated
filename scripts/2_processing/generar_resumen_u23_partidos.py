#!/usr/bin/env python3
"""
Generar resumen de jugadores U23 por partido usando datos de BeSoccer
Primera B Metro - Jornada 3 (9 marzo 2026)
"""

import pandas as pd

# Archivos
from pathlib import Path
_DATA = Path(__file__).resolve().parents[2] / 'data'
PARTIDOS_FILE = str(_DATA / 'primera_b_metro_j3.csv')
OUTPUT_FILE = str(_DATA / 'u23_primera_b_metro_resumen.csv')

def main():
    print("="*80)
    print("RESUMEN JUGADORES U23 - PRIMERA B METRO - JORNADA 3")
    print("Fecha: 9 de marzo 2026")
    print("="*80)
    
    # Cargar datos de partidos
    print(f"\n📂 Cargando datos de partidos...")
    df = pd.read_csv(PARTIDOS_FILE, encoding='utf-8')
    
    print(f"   ✅ {len(df)} registros cargados")
    
    # Filtrar solo jugadores U23 (nacidos en 2003 o después) que jugaron
    df_u23 = df[
        (df['año_nacimiento'] >= 2003) & 
        (df['minutos_jugados'] > 0)
    ].copy()
    
    print(f"   🔍 Filtrado U23 con minutos: {len(df_u23)} jugadores")
    
    # Crear dataset con las columnas requeridas
    resultados = []
    
    for _, row in df_u23.iterrows():
        # Determinar oponente
        if row['equipo'] == row['equipo_local']:
            opponent = row['equipo_visitante']
        else:
            opponent = row['equipo_local']
        
        resultado = {
            'player_name': row['nombre'],
            'shirt_number': int(row['dorsal']) if pd.notna(row['dorsal']) else '',
            'position': row['posicion'],
            'date_of_birth': row['fecha_nacimiento'],
            'team': row['equipo'],
            'opponent': opponent,
            'team_id': '',  # No disponible en BeSoccer
            'opponent_id': '',  # No disponible en BeSoccer
            'match_id': row['partido_id'],
            'match_date': '09/03/2026',  # Jornada 3
            'liga': 'Primera B Metro',
            'peso_liga': 0.9,
            'minutes_played': int(row['minutos_jugados'])
        }
        resultados.append(resultado)
    
    # Crear DataFrame
    df_resultado = pd.DataFrame(resultados)
    
    # Ordenar por equipo y jugador
    df_resultado = df_resultado.sort_values(['team', 'player_name'])
    
    # Guardar
    df_resultado.to_csv(OUTPUT_FILE, index=False, encoding='utf-8')
    
    print(f"\n{'='*80}")
    print(f"✅ PROCESAMIENTO COMPLETADO")
    print(f"{'='*80}")
    print(f"   📊 Total jugadores U23: {len(df_resultado)}")
    print(f"   👥 Jugadores únicos: {df_resultado['player_name'].nunique()}")
    print(f"   ⚽ Partidos: {df_resultado['match_id'].nunique()}")
    print(f"\n💾 Archivo guardado: {OUTPUT_FILE}")
    
    # Resumen por partido
    print(f"\n📈 RESUMEN POR PARTIDO:")
    print("="*80)
    
    partidos = df_resultado.groupby(['match_id', 'team', 'opponent']).agg({
        'player_name': 'count',
        'minutes_played': 'sum'
    }).rename(columns={
        'player_name': 'jugadores_u23',
        'minutes_played': 'minutos_totales'
    }).reset_index()
    
    # Agrupar por partido completo
    for match_id in partidos['match_id'].unique():
        partidos_match = partidos[partidos['match_id'] == match_id]
        
        if len(partidos_match) >= 2:
            local = partidos_match.iloc[0]
            visitante = partidos_match.iloc[1]
            
            print(f"\n{local['team']} vs {visitante['team']}")
            print(f"  {local['team']}: {local['jugadores_u23']} jugadores U23 ({local['minutos_totales']} min)")
            
            # Mostrar jugadores del equipo local
            jugadores_local = df_resultado[
                (df_resultado['match_id'] == match_id) & 
                (df_resultado['team'] == local['team'])
            ]
            for _, jug in jugadores_local.iterrows():
                print(f"    • {jug['player_name']} (#{jug['shirt_number']}) - {jug['position']} - {jug['minutes_played']} min")
            
            print(f"  {visitante['team']}: {visitante['jugadores_u23']} jugadores U23 ({visitante['minutos_totales']} min)")
            
            # Mostrar jugadores del equipo visitante
            jugadores_visitante = df_resultado[
                (df_resultado['match_id'] == match_id) & 
                (df_resultado['team'] == visitante['team'])
            ]
            for _, jug in jugadores_visitante.iterrows():
                print(f"    • {jug['player_name']} (#{jug['shirt_number']}) - {jug['position']} - {jug['minutes_played']} min")
        else:
            # Solo un equipo con U23
            equipo = partidos_match.iloc[0]
            print(f"\n{equipo['team']} vs {equipo['opponent']}")
            print(f"  {equipo['team']}: {equipo['jugadores_u23']} jugadores U23 ({equipo['minutos_totales']} min)")
            
            jugadores = df_resultado[
                (df_resultado['match_id'] == match_id) & 
                (df_resultado['team'] == equipo['team'])
            ]
            for _, jug in jugadores.iterrows():
                print(f"    • {jug['player_name']} (#{jug['shirt_number']}) - {jug['position']} - {jug['minutes_played']} min")
            
            print(f"  {equipo['opponent']}: 0 jugadores U23")
    
    print(f"\n{'='*80}")

if __name__ == '__main__':
    main()
