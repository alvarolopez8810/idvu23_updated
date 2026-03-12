#!/usr/bin/env python3
"""Monitor de progreso del script de scraping U23"""

import time
import os
from pathlib import Path

DATA_DIR = Path('/Users/alvarolopezmolina/Desktop/Python/IDV_project/RONDA_02-08_03_26/data')

print("\n" + "="*80)
print("MONITOR DE PROGRESO - SCRAPING U23")
print("="*80)

# Verificar si el archivo de salida existe
output_csv = DATA_DIR / 'todos_u23_ratings_completo.csv'
output_json = DATA_DIR / 'todos_u23_ratings_completo.json'

if output_csv.exists():
    import pandas as pd
    df = pd.read_csv(output_csv)
    print(f"\n✅ ARCHIVO GENERADO!")
    print(f"   📊 Total jugadores procesados: {len(df)}")
    print(f"   📂 Archivo: {output_csv}")
    
    # Mostrar top 10
    print(f"\n🏆 TOP 10 RATINGS:")
    for idx, row in df.head(10).iterrows():
        print(f"   {idx+1}. {row['player_name']} ({row['liga']}) - Rating: {row['rating_promedio']:.2f} ({row['partidos_total']} partidos)")
    
    # Buscar a Chiqueti
    chiqueti = df[df['player_name'].str.contains('Chiqueti', case=False, na=False)]
    if len(chiqueti) > 0:
        print(f"\n✅ CHIQUETI ENCONTRADO:")
        for _, row in chiqueti.iterrows():
            print(f"   Nombre: {row['player_name']}")
            print(f"   Liga: {row['liga']}")
            print(f"   Rating: {row['rating_promedio']:.2f}")
            print(f"   Partidos: {row['partidos_total']}")
    else:
        print(f"\n⚠️  Chiqueti NO encontrado en el dataset")
    
    # Estadísticas por liga
    print(f"\n📊 JUGADORES POR LIGA:")
    liga_counts = df['liga'].value_counts()
    for liga, count in liga_counts.items():
        print(f"   {liga}: {count} jugadores")
    
else:
    print(f"\n⏳ PROCESO AÚN EN EJECUCIÓN...")
    print(f"   El archivo de salida aún no se ha generado")
    print(f"   Esperando: {output_csv}")
    
    # Verificar si el proceso está corriendo
    import subprocess
    result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
    if 'obtener_todos_u23_completo.py' in result.stdout:
        print(f"\n✅ Script activo (proceso Python corriendo)")
        
        # Contar procesos Chrome (indica actividad de Selenium)
        chrome_count = result.stdout.count('chrome')
        if chrome_count > 0:
            print(f"✅ Selenium activo ({chrome_count} procesos Chrome)")
        else:
            print(f"⚠️  No se detectan procesos Chrome (Selenium podría estar detenido)")
    else:
        print(f"\n❌ Script NO está corriendo")
        print(f"   Necesitas reiniciar: python3 obtener_todos_u23_completo.py")

print("\n" + "="*80)
print("Ejecuta este script cada 1-2 minutos para ver el progreso")
print("="*80 + "\n")
