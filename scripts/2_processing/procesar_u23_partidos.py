#!/usr/bin/env python3
"""
Procesar jugadores U23 del archivo 20260309.csv y relacionarlos con sus partidos
de la carpeta RONDA_02-08_03_26
"""

import pandas as pd
from datetime import datetime

# Rutas de archivos
U23_FILE = '/Users/alvarolopezmolina/Desktop/Python/IDV_project/RONDA_02-08_03_26/20260309.csv'
MATCHES_FILE = '/Users/alvarolopezmolina/Desktop/Python/IDV_project/RONDA_02-08_03_26/data/jugadores_ronda_nueva.csv'
OUTPUT_FILE = '/Users/alvarolopezmolina/Desktop/Python/IDV_project/RONDA_02-08_03_26/u23_partidos_primera_b.csv'

def main():
    print("="*80)
    print("PROCESAMIENTO DE JUGADORES U23 - PRIMERA B METRO")
    print("="*80)
    
    # Cargar archivo de jugadores U23
    print(f"\n📂 Cargando jugadores U23 desde: {U23_FILE}")
    df_u23 = pd.read_csv(U23_FILE, sep='\t', encoding='utf-8')
    
    # Limpiar espacios en nombres de columnas
    df_u23.columns = df_u23.columns.str.strip()
    
    print(f"   ✅ {len(df_u23)} jugadores U23 cargados")
    print(f"   Columnas: {list(df_u23.columns)}")
    
    # Cargar archivo de partidos
    print(f"\n📂 Cargando datos de partidos desde: {MATCHES_FILE}")
    df_matches = pd.read_csv(MATCHES_FILE, encoding='utf-8')
    
    print(f"   ✅ {len(df_matches)} registros de jugadores en partidos")
    print(f"   Columnas: {list(df_matches.columns)}")
    
    # Filtrar solo Primera B Metro
    df_primera_b = df_matches[df_matches['liga'] == 'Primera B Metro'].copy()
    print(f"\n🔍 Filtrado Primera B Metro: {len(df_primera_b)} registros")
    
    # Obtener lista de equipos de Primera B del archivo U23
    equipos_primera_b = set(df_u23['Equipo'].str.strip().unique())
    print(f"\n📋 Equipos en Primera B Metro ({len(equipos_primera_b)}):")
    for equipo in sorted(equipos_primera_b):
        print(f"   - {equipo}")
    
    # Crear lista de resultados
    resultados = []
    
    # Procesar cada jugador U23
    print(f"\n⚙️  Procesando jugadores U23...")
    
    for idx, row in df_u23.iterrows():
        nombre = row['Nombre'].strip()
        equipo = row['Equipo'].strip()
        año_nacimiento = row['Año']
        posicion = row.get('Position principal', '').strip() if pd.notna(row.get('Position principal')) else ''
        
        # Buscar partidos de este jugador en Primera B Metro
        # Intentar match por nombre del jugador
        partidos_jugador = df_primera_b[
            (df_primera_b['player_name'].str.contains(nombre.split()[0], case=False, na=False)) |
            (df_primera_b['player_name'].str.lower() == nombre.lower())
        ]
        
        # Si no encontramos por nombre, intentar por equipo y año de nacimiento
        if len(partidos_jugador) == 0:
            partidos_jugador = df_primera_b[
                (df_primera_b['team'] == equipo) &
                (df_primera_b['birth_year'] == año_nacimiento)
            ]
        
        # Agregar cada partido del jugador
        for _, partido in partidos_jugador.iterrows():
            resultado = {
                'player_name': nombre,
                'shirt_number': partido.get('shirt_number', ''),
                'position': posicion if posicion else partido.get('position', ''),
                'date_of_birth': partido.get('date_of_birth', ''),
                'team': partido['team'],
                'opponent': partido['opponent'],
                'team_id': partido['team_id'],
                'opponent_id': partido['opponent_id'],
                'match_id': partido['match_id'],
                'match_date': partido['match_date'],
                'liga': 'Primera B Metro',
                'peso_liga': 0.9,
                'minutes_played': partido['minutes_played']
            }
            resultados.append(resultado)
    
    # Crear DataFrame de resultados
    df_resultado = pd.DataFrame(resultados)
    
    # Eliminar duplicados
    df_resultado = df_resultado.drop_duplicates(subset=['player_name', 'match_id'])
    
    # Ordenar por jugador y fecha
    df_resultado = df_resultado.sort_values(['player_name', 'match_date'])
    
    # Guardar resultado
    df_resultado.to_csv(OUTPUT_FILE, index=False, encoding='utf-8')
    
    print(f"\n✅ Procesamiento completado")
    print(f"   📊 Total de registros: {len(df_resultado)}")
    print(f"   👥 Jugadores únicos: {df_resultado['player_name'].nunique()}")
    print(f"   ⚽ Partidos únicos: {df_resultado['match_id'].nunique()}")
    print(f"\n💾 Archivo guardado: {OUTPUT_FILE}")
    
    # Resumen por jugador
    print(f"\n📈 RESUMEN POR JUGADOR:")
    print("="*80)
    
    resumen = df_resultado.groupby('player_name').agg({
        'match_id': 'count',
        'minutes_played': 'sum',
        'team': 'first',
        'opponent': lambda x: ', '.join(x.unique()[:3])
    }).rename(columns={
        'match_id': 'partidos',
        'minutes_played': 'minutos_totales',
        'team': 'equipo',
        'opponent': 'rivales'
    }).sort_values('partidos', ascending=False)
    
    print(resumen.to_string())
    
    print(f"\n{'='*80}")
    print(f"✅ PROCESO COMPLETADO")
    print(f"{'='*80}")

if __name__ == '__main__':
    main()
