#!/usr/bin/env python3
"""
Filtrar jugadores con REAP > 1.29 del archivo 20260309.csv
"""

import pandas as pd

# Cargar CSV con manejo correcto de columnas
df = pd.read_csv('20260309.csv', sep='\t', encoding='utf-8')

# Limpiar nombres de columnas
df.columns = df.columns.str.strip()

# Convertir columnas numéricas
numeric_cols = ['Edad', 'ELO', 'Max. ELO', 'REAP', 'Potencial', 'Valor de mercado']
for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

# Filtrar jugadores con REAP > 1.29
df_filtered = df[df['REAP'] > 1.29].copy()

# Ordenar por REAP descendente
df_filtered = df_filtered.sort_values('REAP', ascending=False)

print('='*100)
print('JUGADORES U23 CON REAP > 1.29 - PRIMERA B METRO')
print('='*100)
print(f'\nTotal: {len(df_filtered)} jugadores\n')

# Crear tabla resumen
print(f"{'Nombre':<25} {'Equipo':<25} {'Pos':<6} {'REAP':<6} {'ELO':<5} {'Pot':<5} {'Min':<5}")
print('='*100)

for idx, row in df_filtered.iterrows():
    nombre = str(row['Nombre']).strip()[:24]
    equipo = str(row['Equipo']).strip()[:24]
    posicion = str(row.get('Position principal', 'N/A'))[:5]
    reap = f"{row['REAP']:.2f}"
    elo = int(row['ELO']) if pd.notna(row['ELO']) else 'N/A'
    pot = int(row['Potencial']) if pd.notna(row['Potencial']) else 'N/A'
    try:
        minutos_val = str(row['Minutos']).strip()
        minutos = int(minutos_val) if minutos_val and minutos_val != '-' else 0
    except (ValueError, AttributeError):
        minutos = 0
    
    print(f"{nombre:<25} {equipo:<25} {posicion:<6} {reap:<6} {str(elo):<5} {str(pot):<5} {minutos:<5}")

print('\n' + '='*100)
print('DETALLE COMPLETO DE JUGADORES')
print('='*100 + '\n')

for idx, row in df_filtered.iterrows():
    print(f"{'='*100}")
    print(f"👤 NOMBRE: {row['Nombre'].strip()}")
    print(f"⚽ EQUIPO: {row['Equipo'].strip()}")
    print(f"📍 POSICIÓN: {row.get('Position principal', 'N/A')}")
    print(f"🌍 PAÍS: {row['País'].strip()}")
    print(f"🎂 EDAD: {int(row['Edad'])} años (Nacido en 20{row['Año']})")
    
    if pd.notna(row['Altura']) and str(row['Altura']) != '-':
        print(f"📏 ALTURA: {row['Altura']} cm")
    
    print(f"\n📊 MÉTRICAS:")
    print(f"   • REAP: {row['REAP']:.2f}")
    print(f"   • ELO: {int(row['ELO'])} (Max: {int(row['Max. ELO'])})")
    print(f"   • Potencial: {int(row['Potencial'])}")
    
    if pd.notna(row['+/- ELO (1 año)']):
        cambio = row['+/- ELO (1 año)']
        if cambio > 0:
            print(f"   • Evolución ELO (1 año): +{int(cambio)} ⬆️")
        elif cambio < 0:
            print(f"   • Evolución ELO (1 año): {int(cambio)} ⬇️")
    
    print(f"\n⚽ TEMPORADA ACTUAL:")
    print(f"   • Partidos jugados: {int(row['PJ Temporada Actual'])}")
    print(f"   • Minutos totales: {int(row['Min Temporada Actual'])}")
    try:
        min_val = str(row['Minutos']).strip()
        min_jornada = int(min_val) if min_val and min_val != '-' else 0
    except (ValueError, AttributeError):
        min_jornada = 0
    print(f"   • Minutos última jornada: {min_jornada}")
    
    if pd.notna(row['Valor de mercado']) and row['Valor de mercado'] > 0:
        print(f"\n💰 VALOR DE MERCADO: €{row['Valor de mercado']:.3f}M")
    
    if pd.notna(row['Fin Contrato']) and str(row['Fin Contrato']) != '-':
        print(f"📝 FIN DE CONTRATO: {row['Fin Contrato']}")
    
    if pd.notna(row['Agente']) and str(row['Agente']) != '-':
        print(f"🤝 AGENTE: {row['Agente']}")
    
    print()

print('='*100)
print(f"✅ Total de jugadores destacados: {len(df_filtered)}")
print('='*100)
