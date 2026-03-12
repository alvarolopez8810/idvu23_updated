#!/usr/bin/env python3
"""
Verificar todos los valores de REAP en el archivo
"""

import pandas as pd

# Leer CSV línea por línea para parsear correctamente
with open('20260309.csv', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Parsear header
header = lines[0].strip().split('\t')
header = [h.strip() for h in header]

# Parsear datos
data = []
for line in lines[1:]:
    if line.strip():
        values = line.strip().split('\t')
        values = [v.strip() for v in values]
        if len(values) == len(header):
            data.append(values)

# Crear DataFrame
df = pd.DataFrame(data, columns=header)

# Convertir REAP a numérico
df['REAP'] = pd.to_numeric(df['REAP'], errors='coerce')

print("DISTRIBUCIÓN DE VALORES REAP:")
print("="*50)

# Mostrar todos los valores de REAP únicos ordenados
reap_unicos = df['REAP'].dropna().sort_values(ascending=False)
print(f"Total de jugadores: {len(df)}")
print(f"Jugadores con REAP válido: {len(reap_unicos)}")
print(f"\nValores REAP (de mayor a menor):")
print("="*50)

for i, reap in enumerate(reap_unicos.unique()):
    jugadores_con_reap = df[df['REAP'] == reap]
    print(f"REAP {reap:.2f}: {len(jugadores_con_reap)} jugadores")
    for _, row in jugadores_con_reap.iterrows():
        print(f"  - {row['Nombre']} ({row['Equipo']})")

print(f"\n{'='*50}")
print(f"JUGADORES CON REAP >= 1.29:")
print(f"{'='*50}")

df_filtrado = df[df['REAP'] >= 1.29].copy()
print(f"Total: {len(df_filtrado)} jugadores\n")

for _, row in df_filtrado.iterrows():
    print(f"{row['Nombre']} - {row['Equipo']} - REAP: {row['REAP']:.2f}")

print(f"\n{'='*50}")
print(f"JUGADORES CON REAP < 1.29:")
print(f"{'='*50}")

df_bajo = df[df['REAP'] < 1.29].copy()
print(f"Total: {len(df_bajo)} jugadores\n")

# Mostrar los 10 más altos de los que están por debajo de 1.29
df_bajo_top = df_bajo.sort_values('REAP', ascending=False).head(10)
for _, row in df_bajo_top.iterrows():
    print(f"{row['Nombre']} - {row['Equipo']} - REAP: {row['REAP']:.2f}")

print(f"\n{'='*50}")
print(f"RESUMEN:")
print(f"{'='*50}")
print(f"• REAP >= 1.29: {len(df_filtrado)} jugadores")
print(f"• REAP < 1.29: {len(df_bajo)} jugadores")
print(f"• Total jugadores con REAP válido: {len(df_filtrado) + len(df_bajo)}")
print(f"• Jugadores sin REAP: {len(df) - len(df_filtrado) - len(df_bajo)}")
