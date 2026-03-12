#!/usr/bin/env python3
"""
Filtrar jugadores con REAP > 1.29 del archivo 20260309.csv
"""

import pandas as pd

# Cargar CSV
df = pd.read_csv('20260309.csv', sep='\t', encoding='utf-8')
df.columns = df.columns.str.strip()

# Convertir REAP a numérico
df['REAP'] = pd.to_numeric(df['REAP'], errors='coerce')

# Filtrar jugadores con REAP > 1.29
df_filtered = df[df['REAP'] > 1.29].copy()

# Ordenar por REAP descendente
df_filtered = df_filtered.sort_values('REAP', ascending=False)

print('='*100)
print('JUGADORES CON REAP > 1.29 - PRIMERA B METRO')
print('='*100)
print(f'\nTotal: {len(df_filtered)} jugadores\n')

for idx, row in df_filtered.iterrows():
    print(f"{'='*100}")
    print(f"Nombre: {row['Nombre'].strip()}")
    print(f"Equipo: {row['Equipo'].strip()}")
    print(f"Posición: {row.get('Position principal', 'N/A')}")
    print(f"País: {row['País'].strip()}")
    print(f"Edad: {row['Edad']} años (Año: {row['Año']})")
    print(f"Altura: {row['Altura'] if pd.notna(row['Altura']) else 'N/A'} cm")
    print(f"REAP: {row['REAP']}")
    print(f"ELO: {row['ELO']} (Max: {row['Max. ELO']})")
    print(f"Potencial: {row['Potencial']}")
    print(f"+/- ELO (1 año): {row['+/- ELO (1 año)']}")
    print(f"Valor de mercado: €{row['Valor de mercado']}M")
    print(f"Fin contrato: {row['Fin Contrato'] if pd.notna(row['Fin Contrato']) else 'N/A'}")
    print(f"Agente: {row['Agente'] if pd.notna(row['Agente']) else 'N/A'}")
    print(f"PJ Temporada: {row['PJ Temporada Actual']}")
    print(f"Min Temporada: {row['Min Temporada Actual']}")
    print(f"Minutos (última jornada): {row['Minutos']}")
    print()
