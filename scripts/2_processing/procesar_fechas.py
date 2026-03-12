#!/usr/bin/env python3
"""
Procesar fechas de nacimiento de timestamp a formato DD/MM/YYYY
"""

import pandas as pd
from datetime import datetime
from pathlib import Path

# Paths
BASE_DIR = Path('/Users/alvarolopezmolina/Desktop/Python/IDV_project/RONDA_02-08_03_26')
DATA_DIR = BASE_DIR / 'data'

def convert_timestamp_to_date(timestamp):
    """Convierte timestamp a formato DD/MM/YYYY"""
    if pd.isna(timestamp) or timestamp == '' or timestamp == 0:
        return ''
    
    try:
        timestamp = int(float(timestamp))
        date_obj = datetime.fromtimestamp(timestamp)
        return date_obj.strftime('%d/%m/%Y')
    except:
        return ''


def main():
    print("\n" + "="*70)
    print("PROCESANDO FECHAS DE NACIMIENTO")
    print("="*70)
    
    # Leer CSV
    input_file = DATA_DIR / 'jugadores_ronda_nueva.csv'
    print(f"\n📂 Leyendo: {input_file}")
    
    df = pd.read_csv(input_file)
    print(f"   {len(df)} jugadores cargados")
    
    # Convertir timestamps a fechas
    print(f"\n🔄 Convirtiendo timestamps a DD/MM/YYYY...")
    df['date_of_birth_formatted'] = df['date_of_birth'].apply(convert_timestamp_to_date)
    
    # Contar conversiones exitosas
    converted = df['date_of_birth_formatted'].apply(lambda x: x != '').sum()
    print(f"   ✓ {converted}/{len(df)} fechas convertidas")
    
    # Reordenar columnas para que date_of_birth_formatted esté después de date_of_birth
    cols = df.columns.tolist()
    # Insertar date_of_birth_formatted después de date_of_birth
    dob_idx = cols.index('date_of_birth')
    cols.insert(dob_idx + 1, cols.pop(cols.index('date_of_birth_formatted')))
    df = df[cols]
    
    # Guardar CSV actualizado
    output_file = DATA_DIR / 'jugadores_ronda_nueva_procesado.csv'
    df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"\n✅ Archivo guardado: {output_file}")
    
    # Mostrar ejemplos
    print(f"\n{'='*70}")
    print("EJEMPLOS DE CONVERSIÓN")
    print(f"{'='*70}")
    
    sample = df[df['date_of_birth_formatted'] != ''].head(10)
    for _, row in sample.iterrows():
        print(f"  {row['player_name']:30} | {row['date_of_birth']} → {row['date_of_birth_formatted']} | Edad: {row['age']}")
    
    # Resumen por liga
    print(f"\n{'='*70}")
    print("RESUMEN POR LIGA")
    print(f"{'='*70}")
    
    summary = df.groupby('liga').agg({
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
    print("✅ PROCESAMIENTO COMPLETADO")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
