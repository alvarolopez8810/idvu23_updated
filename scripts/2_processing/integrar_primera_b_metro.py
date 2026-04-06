#!/usr/bin/env python3
"""
Integrar Primera B Metro con datos existentes y recalcular MPS
"""

import pandas as pd
from datetime import datetime
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / 'data'

def convert_date_to_timestamp(date_str):
    """Convierte fecha YYYY-MM-DD a timestamp"""
    if pd.isna(date_str) or date_str == '':
        return ''
    try:
        dt = datetime.strptime(str(date_str), '%Y-%m-%d')
        return int(dt.timestamp())
    except:
        return ''

def calculate_age_and_u23(birth_date_str):
    """Calcula edad y si es U23 desde fecha YYYY-MM-DD"""
    if pd.isna(birth_date_str) or birth_date_str == '':
        return 0, 0, False
    
    try:
        birth_date = datetime.strptime(str(birth_date_str), '%Y-%m-%d')
        birth_year = birth_date.year
        age = 2026 - birth_year
        is_u23 = birth_year >= 2003
        return birth_year, age, is_u23
    except:
        return 0, 0, False

def format_date_dd_mm_yyyy(date_str):
    """Convierte YYYY-MM-DD a DD/MM/YYYY"""
    if pd.isna(date_str) or date_str == '':
        return ''
    try:
        dt = datetime.strptime(str(date_str), '%Y-%m-%d')
        return dt.strftime('%d/%m/%Y')
    except:
        return ''

def main():
    print("\n" + "="*70)
    print("INTEGRACIÓN PRIMERA B METRO")
    print("="*70)
    
    # Leer Primera B Metro
    pbm_file = DATA_DIR / 'u23_primera_b_metro_resumen.csv'
    print(f"\n📂 Leyendo Primera B Metro: {pbm_file}")
    df_pbm = pd.read_csv(pbm_file)
    print(f"   {len(df_pbm)} jugadores U23 cargados")
    print(f"   {df_pbm['match_id'].nunique()} partidos únicos")
    
    # Procesar fechas y calcular edad/U23
    print(f"\n🔄 Procesando fechas de nacimiento...")
    df_pbm['birth_year'] = 0
    df_pbm['age'] = 0
    df_pbm['is_u23'] = False
    df_pbm['date_of_birth_formatted'] = ''
    
    for idx, row in df_pbm.iterrows():
        birth_year, age, is_u23 = calculate_age_and_u23(row['date_of_birth'])
        df_pbm.at[idx, 'birth_year'] = birth_year
        df_pbm.at[idx, 'age'] = age
        df_pbm.at[idx, 'is_u23'] = is_u23
        df_pbm.at[idx, 'date_of_birth_formatted'] = format_date_dd_mm_yyyy(row['date_of_birth'])
    
    # Convertir date_of_birth a timestamp para compatibilidad
    df_pbm['date_of_birth'] = df_pbm['date_of_birth'].apply(convert_date_to_timestamp)
    
    # Agregar columnas faltantes para compatibilidad
    df_pbm['rating'] = 0
    df_pbm['goals'] = 0
    df_pbm['assists'] = 0
    df_pbm['home_away'] = df_pbm.apply(lambda x: 'home' if pd.notna(x['team']) else 'away', axis=1)
    
    # Generar player_id único (usando hash del nombre)
    df_pbm['player_id'] = df_pbm['player_name'].apply(lambda x: abs(hash(x)) % 10000000)
    
    print(f"   ✓ {df_pbm['is_u23'].sum()} jugadores U23 confirmados")
    
    # Leer datos existentes
    existing_file = DATA_DIR / 'jugadores_ronda_nueva_procesado.csv'
    print(f"\n📂 Leyendo datos existentes: {existing_file}")
    df_existing = pd.read_csv(existing_file)
    print(f"   {len(df_existing)} jugadores existentes")
    print(f"   {df_existing['match_id'].nunique()} partidos existentes")
    
    # Reordenar columnas de Primera B Metro para que coincidan
    columns_order = df_existing.columns.tolist()
    
    # Asegurar que todas las columnas existen
    for col in columns_order:
        if col not in df_pbm.columns:
            df_pbm[col] = '' if df_pbm.dtypes.get(col, 'object') == 'object' else 0
    
    df_pbm = df_pbm[columns_order]
    
    # Combinar datasets
    print(f"\n🔄 Combinando datasets...")
    df_combined = pd.concat([df_existing, df_pbm], ignore_index=True)
    
    print(f"   ✓ Total jugadores: {len(df_combined)}")
    print(f"   ✓ Total partidos: {df_combined['match_id'].nunique()}")
    print(f"   ✓ Total U23: {df_combined['is_u23'].sum()}")
    
    # Guardar dataset combinado
    output_file = DATA_DIR / 'jugadores_completo_con_pbm.csv'
    df_combined.to_csv(output_file, index=False, encoding='utf-8')
    print(f"\n✅ Dataset combinado guardado: {output_file}")
    
    # Resumen por liga
    print(f"\n{'='*70}")
    print("RESUMEN POR LIGA")
    print(f"{'='*70}")
    
    summary = df_combined.groupby('liga').agg({
        'match_id': 'nunique',
        'player_id': 'count',
        'is_u23': 'sum',
        'rating': lambda x: x[x > 0].mean() if len(x[x > 0]) > 0 else 0
    }).rename(columns={
        'match_id': 'Partidos',
        'player_id': 'Jugadores',
        'is_u23': 'U23',
        'rating': 'Rating Avg'
    })
    
    summary['Rating Avg'] = summary['Rating Avg'].round(2)
    print(summary.to_string())
    
    print(f"\n{'='*70}")
    print("✅ INTEGRACIÓN COMPLETADA")
    print(f"{'='*70}")
    print(f"\n🎯 Siguiente paso: Recalcular MPS con Primera B Metro incluida")


if __name__ == '__main__':
    main()
