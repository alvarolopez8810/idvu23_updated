#!/usr/bin/env python3
"""
Calcular MPS para nueva ronda - Marzo 2026
Basado en integrar_round3_y_recalcular.py

Fórmula MPS:
- CON Rating: MPS = (Densidad_U23 × 5) + (Rating_Normalizado × 3) + (Peso_Liga × 2)
- SIN Rating: MPS = (Densidad_U23 × 7) + (Peso_Liga × 3)

Densidad_U23 = n_u23_partido / max_u23_global
Rating_Normalizado = rating_promedio / 10
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / 'data'

MIN_MINUTOS = 60  # Filtro de minutos mínimos


def calcular_mps_filtrado(df, min_minutos=60):
    """
    Calcula MPS con filtro:
    - Partido se incluye si al menos 1 U23 jugó >min_minutos
    - Densidad = (n_u23_partido / max_u23_global) normalizada
    """
    
    print(f"\n{'='*70}")
    print(f"CÁLCULO DE MPS - DENSIDAD NORMALIZADA GLOBAL")
    print(f"{'='*70}")
    
    # PASO 1: Encontrar el máximo de U23 con >=min_minutos en todos los partidos
    max_u23_global = 0
    partidos_temp = []
    
    for match_id, grupo in df.groupby('match_id'):
        u23_filtrado = grupo[(grupo['is_u23'] == True) & (grupo['minutes_played'] >= min_minutos)].copy()
        if len(u23_filtrado) > 0:
            partidos_temp.append({
                'match_id': match_id,
                'n_u23': len(u23_filtrado),
                'grupo': grupo,
                'u23_filtrado': u23_filtrado
            })
            if len(u23_filtrado) > max_u23_global:
                max_u23_global = len(u23_filtrado)
    
    print(f"\n📊 Máximo de U23 con >{min_minutos} min en un partido: {max_u23_global}")
    print(f"   Total partidos a procesar: {len(partidos_temp)}")
    
    # PASO 2: Calcular MPS con densidad normalizada
    partidos = []
    
    for p_temp in partidos_temp:
        match_id = p_temp['match_id']
        grupo = p_temp['grupo']
        u23_filtrado = p_temp['u23_filtrado']
        
        # Datos del partido
        partido_info = {
            'match_id': match_id,
            'partido': f"{grupo.iloc[0]['team']} vs {grupo.iloc[0]['opponent']}",
            'liga': grupo.iloc[0]['liga'],
            'peso_liga': grupo.iloc[0]['peso_liga'],
            'match_date': grupo.iloc[0]['match_date'],
            'home_team_id': grupo.iloc[0].get('team_id', 0),
            'away_team_id': grupo.iloc[0].get('opponent_id', 0)
        }
        
        # Calcular métricas U23 FILTRADO
        total_u23_filtrado = len(u23_filtrado)
        
        # DENSIDAD U23 NORMALIZADA: n_u23_partido / max_u23_global
        densidad_u23_normalizada = total_u23_filtrado / max_u23_global if max_u23_global > 0 else 0
        
        # Rating promedio (solo si hay ratings)
        ratings_validos = u23_filtrado['rating'].dropna()
        ratings_validos = ratings_validos[ratings_validos > 0]
        rating_promedio = ratings_validos.mean() if len(ratings_validos) > 0 else 0
        tiene_rating = len(ratings_validos) > 0
        
        # Peso de liga
        peso_liga = grupo.iloc[0]['peso_liga']
        
        # CALCULAR MPS
        if tiene_rating:
            # FÓRMULA 1: Partidos CON rating
            # MPS = (Densidad × 5) + (Rating_Normalizado × 3) + (Peso_Liga × 2)
            rating_normalizado = rating_promedio / 10
            mps = (densidad_u23_normalizada * 5) + (rating_normalizado * 3) + (peso_liga * 2)
            formula_usada = "CON_RATING"
        else:
            # FÓRMULA 2: Partidos SIN rating
            # MPS = (Densidad × 7) + (Peso_Liga × 3)
            mps = (densidad_u23_normalizada * 7) + (peso_liga * 3)
            formula_usada = "SIN_RATING"
        
        partido_info.update({
            'n_u23': total_u23_filtrado,
            'densidad_u23': round(densidad_u23_normalizada, 3),
            'minutos_u23': int(u23_filtrado['minutes_played'].sum()),
            'rating_promedio_u23': round(rating_promedio, 2) if rating_promedio > 0 else 0,
            'tiene_rating': tiene_rating,
            'mps': round(mps, 2),
            'formula_usada': formula_usada
        })
        
        partidos.append(partido_info)
    
    # Crear DataFrame de partidos
    df_partidos = pd.DataFrame(partidos)
    
    # Calcular Z-SCORE por separado para cada grupo (CON rating y SIN rating)
    df_con_rating = df_partidos[df_partidos['formula_usada'] == 'CON_RATING'].copy()
    df_sin_rating = df_partidos[df_partidos['formula_usada'] == 'SIN_RATING'].copy()
    
    # Z-Score para partidos CON rating
    if len(df_con_rating) > 0:
        mean_con = df_con_rating['mps'].mean()
        std_con = df_con_rating['mps'].std()
        df_con_rating['z_score'] = (df_con_rating['mps'] - mean_con) / std_con if std_con > 0 else 0
    
    # Z-Score para partidos SIN rating
    if len(df_sin_rating) > 0:
        mean_sin = df_sin_rating['mps'].mean()
        std_sin = df_sin_rating['mps'].std()
        df_sin_rating['z_score'] = (df_sin_rating['mps'] - mean_sin) / std_sin if std_sin > 0 else 0
    
    # Combinar ambos DataFrames
    df_partidos = pd.concat([df_con_rating, df_sin_rating], ignore_index=True)
    
    # Calcular PERCENTILES GLOBALES del Z-Score
    df_partidos['percentil_zscore'] = df_partidos['z_score'].rank(pct=True) * 100
    
    # Asignar PRIORIDAD basada en percentiles del Z-Score
    def asignar_prioridad(percentil):
        if percentil >= 90:
            return 'TOP'
        elif percentil >= 75:
            return 'MUY ALTA'
        elif percentil >= 60:
            return 'ALTA'
        elif percentil >= 40:
            return 'MEDIA'
        else:
            return 'BAJA'
    
    df_partidos['prioridad'] = df_partidos['percentil_zscore'].apply(asignar_prioridad)
    
    # Ordenar por Z-Score descendente
    df_partidos = df_partidos.sort_values('z_score', ascending=False).reset_index(drop=True)
    
    return df_partidos


def main():
    print("\n" + "="*70)
    print("CÁLCULO MPS - RONDA 02-08 MARZO 2026")
    print("="*70)
    
    # Leer datos procesados (con Primera B Metro)
    input_file = DATA_DIR / 'jugadores_completo_con_pbm.csv'
    print(f"\n📂 Leyendo: {input_file}")
    
    df = pd.read_csv(input_file)
    print(f"   {len(df)} jugadores cargados")
    print(f"   {df['match_id'].nunique()} partidos únicos")
    
    # Calcular MPS
    df_partidos = calcular_mps_filtrado(df, min_minutos=MIN_MINUTOS)
    
    # Guardar ranking
    output_file = DATA_DIR / 'PARTIDOS_COMPACTO_CON_MPS.csv'
    df_partidos.to_csv(output_file, index=False, encoding='utf-8')
    print(f"\n✅ Ranking guardado: {output_file}")
    
    # Resumen por prioridad
    print(f"\n{'='*70}")
    print("RESUMEN POR PRIORIDAD")
    print(f"{'='*70}")
    
    prioridad_counts = df_partidos['prioridad'].value_counts()
    for prioridad in ['TOP', 'MUY ALTA', 'ALTA', 'MEDIA', 'BAJA']:
        count = prioridad_counts.get(prioridad, 0)
        print(f"  {prioridad:12} {count:3d} partidos")
    
    # TOP 15 partidos
    print(f"\n{'='*70}")
    print("TOP 15 PARTIDOS PRIORITARIOS")
    print(f"{'='*70}")
    
    top15 = df_partidos.head(15)
    
    print(f"\n{'#':<3} {'Partido':<45} {'Liga':<15} {'U23':<4} {'MPS':<6} {'Z-Score':<7} {'%ile':<6} {'Prior':<10}")
    print("-" * 110)
    
    for idx, row in top15.iterrows():
        print(f"{idx+1:<3} {row['partido']:<45} {row['liga']:<15} {row['n_u23']:<4} "
              f"{row['mps']:<6.2f} {row['z_score']:<7.2f} {row['percentil_zscore']:<6.1f} {row['prioridad']:<10}")
    
    # Resumen por liga
    print(f"\n{'='*70}")
    print("RESUMEN POR LIGA")
    print(f"{'='*70}")
    
    summary = df_partidos.groupby('liga').agg({
        'match_id': 'count',
        'n_u23': 'sum',
        'mps': 'mean',
        'rating_promedio_u23': lambda x: x[x > 0].mean() if len(x[x > 0]) > 0 else 0
    }).rename(columns={
        'match_id': 'Partidos',
        'n_u23': 'Total U23',
        'mps': 'MPS Avg',
        'rating_promedio_u23': 'Rating Avg'
    })
    
    summary['MPS Avg'] = summary['MPS Avg'].round(2)
    summary['Rating Avg'] = summary['Rating Avg'].round(2)
    print(summary.to_string())
    
    print(f"\n{'='*70}")
    print("✅ CÁLCULO MPS COMPLETADO")
    print(f"{'='*70}")
    print(f"\n📂 Archivo generado: {output_file}")
    print(f"\n🎯 Siguiente paso: Descargar escudos de equipos")


if __name__ == '__main__':
    main()
