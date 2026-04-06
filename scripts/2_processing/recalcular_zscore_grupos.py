#!/usr/bin/env python3
"""
Recalcular z-score por grupos separados:
1. Colombia 2 Div CON rating
2. Partidos SIN rating (Primera B Metro + Copa Brasil)
3. Resto de partidos CON rating
"""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats

# Paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / 'data'

def calcular_zscore_por_grupos(df):
    """Calcula z-score por grupos separados"""
    
    # Crear columna para z-score
    df['z_score_grupo'] = 0.0
    df['grupo_zscore'] = ''
    
    # Grupo 1: Colombia 2 Div CON rating
    grupo1 = df[(df['liga'] == 'Colombia 2 Div') & (df['tiene_rating'] == True)].copy()
    if len(grupo1) > 1:
        grupo1['z_score_grupo'] = stats.zscore(grupo1['mps'])
        df.loc[grupo1.index, 'z_score_grupo'] = grupo1['z_score_grupo']
        df.loc[grupo1.index, 'grupo_zscore'] = 'Colombia CON rating'
    elif len(grupo1) == 1:
        df.loc[grupo1.index, 'z_score_grupo'] = 0
        df.loc[grupo1.index, 'grupo_zscore'] = 'Colombia CON rating'
    
    # Grupo 2: Partidos SIN rating (Primera B Metro + Copa Brasil)
    grupo2 = df[(df['tiene_rating'] == False)].copy()
    if len(grupo2) > 1:
        grupo2['z_score_grupo'] = stats.zscore(grupo2['mps'])
        df.loc[grupo2.index, 'z_score_grupo'] = grupo2['z_score_grupo']
        df.loc[grupo2.index, 'grupo_zscore'] = 'SIN rating'
    elif len(grupo2) == 1:
        df.loc[grupo2.index, 'z_score_grupo'] = 0
        df.loc[grupo2.index, 'grupo_zscore'] = 'SIN rating'
    
    # Grupo 3: Resto CON rating (excluye Colombia 2 Div)
    grupo3 = df[(df['liga'] != 'Colombia 2 Div') & (df['tiene_rating'] == True)].copy()
    if len(grupo3) > 1:
        grupo3['z_score_grupo'] = stats.zscore(grupo3['mps'])
        df.loc[grupo3.index, 'z_score_grupo'] = grupo3['z_score_grupo']
        df.loc[grupo3.index, 'grupo_zscore'] = 'Resto CON rating'
    elif len(grupo3) == 1:
        df.loc[grupo3.index, 'z_score_grupo'] = 0
        df.loc[grupo3.index, 'grupo_zscore'] = 'Resto CON rating'
    
    return df


def main():
    print("\n" + "="*70)
    print("RECALCULAR Z-SCORE POR GRUPOS")
    print("="*70)
    
    # Leer ranking actual
    ranking_path = DATA_DIR / 'PARTIDOS_COMPACTO_CON_MPS.csv'
    print(f"\n📂 Leyendo: {ranking_path}")
    df = pd.read_csv(ranking_path)
    print(f"   {len(df)} partidos cargados")
    
    # Calcular z-score por grupos
    print(f"\n🔄 Calculando z-score por grupos...")
    df = calcular_zscore_por_grupos(df)
    
    # Ordenar por z-score de grupo (descendente)
    df = df.sort_values('z_score_grupo', ascending=False).reset_index(drop=True)
    
    # Recalcular percentiles basados en el nuevo orden
    df['percentil_zscore_grupo'] = (df.index / (len(df) - 1) * 100).round(1)
    df['percentil_zscore_grupo'] = 100 - df['percentil_zscore_grupo']  # Invertir para que mayor sea mejor
    
    # Recalcular prioridad basada en percentil
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
    
    df['prioridad'] = df['percentil_zscore_grupo'].apply(asignar_prioridad)
    
    # Guardar ranking actualizado
    output_path = DATA_DIR / 'PARTIDOS_COMPACTO_CON_MPS.csv'
    df.to_csv(output_path, index=False, encoding='utf-8')
    
    print(f"\n{'='*70}")
    print("RESUMEN POR GRUPO")
    print(f"{'='*70}")
    
    for grupo in ['Colombia CON rating', 'SIN rating', 'Resto CON rating']:
        grupo_data = df[df['grupo_zscore'] == grupo]
        if len(grupo_data) > 0:
            print(f"\n{grupo}:")
            print(f"  Partidos: {len(grupo_data)}")
            print(f"  MPS promedio: {grupo_data['mps'].mean():.2f}")
            print(f"  Z-score rango: {grupo_data['z_score_grupo'].min():.2f} a {grupo_data['z_score_grupo'].max():.2f}")
    
    print(f"\n{'='*70}")
    print("RESUMEN POR PRIORIDAD (NUEVO RANKING)")
    print(f"{'='*70}")
    
    for prioridad in ['TOP', 'MUY ALTA', 'ALTA', 'MEDIA', 'BAJA']:
        count = len(df[df['prioridad'] == prioridad])
        print(f"  {prioridad:12s} {count:3d} partidos")
    
    print(f"\n{'='*70}")
    print("TOP 15 PARTIDOS (NUEVO RANKING POR Z-SCORE GRUPO)")
    print(f"{'='*70}\n")
    
    top15 = df.head(15)
    print(f"{'#':<4} {'Partido':<45} {'Liga':<18} {'U23':<4} {'MPS':<6} {'Z-Sc':<6} {'Grupo':<20} {'Prior':<10}")
    print("-" * 120)
    
    for idx, row in top15.iterrows():
        print(f"{idx+1:<4} {row['partido'][:44]:<45} {row['liga'][:17]:<18} {row['n_u23']:<4} "
              f"{row['mps']:<6.2f} {row['z_score_grupo']:<6.2f} {row['grupo_zscore'][:19]:<20} {row['prioridad']:<10}")
    
    print(f"\n✅ Ranking actualizado guardado: {output_path}")
    print(f"\n🎯 Siguiente paso: Regenerar PDF con nuevo ranking")


if __name__ == '__main__':
    main()
