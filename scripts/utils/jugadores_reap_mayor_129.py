#!/usr/bin/env python3
"""
Jugadores U23 con REAP > 1.29 - Primera B Metro
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

# Convertir columnas numéricas
df['REAP'] = pd.to_numeric(df['REAP'], errors='coerce')
df['ELO'] = pd.to_numeric(df['ELO'], errors='coerce')
df['Max. ELO'] = pd.to_numeric(df['Max. ELO'], errors='coerce')
df['Potencial'] = pd.to_numeric(df['Potencial'], errors='coerce')
df['Edad'] = pd.to_numeric(df['Edad'], errors='coerce')
df['+/- ELO (1 año)'] = pd.to_numeric(df['+/- ELO (1 año)'], errors='coerce')
df['Valor de mercado'] = pd.to_numeric(df['Valor de mercado'], errors='coerce')
df['PJ Temporada Actual'] = pd.to_numeric(df['PJ Temporada Actual'], errors='coerce')
df['Min Temporada Actual'] = pd.to_numeric(df['Min Temporada Actual'], errors='coerce')
df['Minutos'] = pd.to_numeric(df['Minutos'], errors='coerce')

# Filtrar REAP >= 1.29
df_filtered = df[df['REAP'] >= 1.29].copy()
df_filtered = df_filtered.sort_values('REAP', ascending=False)

print('='*120)
print('JUGADORES U23 CON REAP > 1.29 - PRIMERA B METRO')
print('='*120)
print(f'\nTotal: {len(df_filtered)} jugadores\n')

# Tabla resumen
print(f"{'Nombre':<25} {'Equipo':<25} {'Pos':<8} {'REAP':<7} {'ELO':<6} {'Pot':<6} {'Min Jor':<8}")
print('='*120)

for idx, row in df_filtered.iterrows():
    nombre = str(row['Nombre'])[:24]
    equipo = str(row['Equipo'])[:24]
    posicion = str(row.get('Position principal', 'N/A'))[:7]
    reap = f"{row['REAP']:.2f}"
    elo = int(row['ELO']) if pd.notna(row['ELO']) else 'N/A'
    pot = int(row['Potencial']) if pd.notna(row['Potencial']) else 'N/A'
    minutos = int(row['Minutos']) if pd.notna(row['Minutos']) else 0
    
    print(f"{nombre:<25} {equipo:<25} {posicion:<8} {reap:<7} {str(elo):<6} {str(pot):<6} {minutos:<8}")

print(f"\n{'='*120}")
print("DETALLE COMPLETO DE JUGADORES")
print(f"{'='*120}\n")

for idx, row in df_filtered.iterrows():
    print(f"{'='*120}")
    print(f"👤 NOMBRE: {row['Nombre']}")
    print(f"⚽ EQUIPO: {row['Equipo']}")
    print(f"📍 POSICIÓN: {row.get('Position principal', 'N/A')}")
    print(f"🌍 PAÍS: {row['País']}")
    
    if pd.notna(row['Edad']):
        año = row['Año']
        print(f"🎂 EDAD: {int(row['Edad'])} años (Nacido en 20{año})")
    
    if pd.notna(row['Altura']) and str(row['Altura']) != '-':
        print(f"📏 ALTURA: {row['Altura']} cm")
    
    print(f"\n📊 MÉTRICAS:")
    print(f"   • REAP: {row['REAP']:.2f}")
    
    if pd.notna(row['ELO']):
        elo = int(row['ELO'])
        max_elo = int(row['Max. ELO']) if pd.notna(row['Max. ELO']) else 'N/A'
        print(f"   • ELO: {elo} (Max: {max_elo})")
    
    if pd.notna(row['Potencial']):
        print(f"   • Potencial: {int(row['Potencial'])}")
    
    if pd.notna(row['+/- ELO (1 año)']):
        cambio = int(row['+/- ELO (1 año)'])
        if cambio > 0:
            print(f"   • Evolución ELO (1 año): +{cambio} ⬆️")
        elif cambio < 0:
            print(f"   • Evolución ELO (1 año): {cambio} ⬇️")
    
    print(f"\n⚽ TEMPORADA ACTUAL:")
    if pd.notna(row['PJ Temporada Actual']):
        print(f"   • Partidos jugados: {int(row['PJ Temporada Actual'])}")
    if pd.notna(row['Min Temporada Actual']):
        print(f"   • Minutos totales: {int(row['Min Temporada Actual'])}")
    if pd.notna(row['Minutos']):
        print(f"   • Minutos última jornada: {int(row['Minutos'])}")
    
    if pd.notna(row['Valor de mercado']) and row['Valor de mercado'] > 0:
        print(f"\n💰 VALOR DE MERCADO: €{row['Valor de mercado']:.3f}M")
    
    if pd.notna(row['Fin Contrato']) and str(row['Fin Contrato']) != '-':
        print(f"📝 FIN DE CONTRATO: {row['Fin Contrato']}")
    
    if pd.notna(row['Agente']) and str(row['Agente']) != '-':
        print(f"🤝 AGENTE: {row['Agente']}")
    
    print()

print('='*120)
print(f"✅ Total de jugadores destacados con REAP > 1.29: {len(df_filtered)}")
print('='*120)
