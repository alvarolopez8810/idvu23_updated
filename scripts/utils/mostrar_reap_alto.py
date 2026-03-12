#!/usr/bin/env python3
"""
Mostrar jugadores con REAP > 1.29 del archivo 20260309.csv
"""

import pandas as pd

# Cargar CSV
df = pd.read_csv('20260309.csv', sep='\t', encoding='utf-8')

# Mostrar primeras filas para debug
print("Columnas del CSV:")
print(df.columns.tolist())
print("\nPrimeras 3 filas:")
print(df.head(3))

# Las columnas correctas son:
# Nombre, País, Equipo, Categoría, Edad, Año, Altura, ELO, Max. ELO, REAP, +/- ELO (1 año), Potencial, Fin Contrato, Valor de mercado, Agente, Position principal, PJ Temporada Actual, Min Temporada Actual, Año.1, Minutos

# Convertir REAP a numérico
df['REAP'] = pd.to_numeric(df[' REAP'].str.strip(), errors='coerce')

# Filtrar REAP > 1.29
df_filtered = df[df['REAP'] > 1.29].copy()
df_filtered = df_filtered.sort_values('REAP', ascending=False)

print(f"\n{'='*120}")
print(f"JUGADORES U23 CON REAP > 1.29 - PRIMERA B METRO")
print(f"{'='*120}")
print(f"\nTotal: {len(df_filtered)} jugadores\n")

print(f"{'Nombre':<25} {'Equipo':<25} {'Pos':<8} {'REAP':<7} {'ELO':<6} {'Pot':<6} {'Min':<6}")
print('='*120)

for idx, row in df_filtered.iterrows():
    nombre = str(row['Nombre']).strip()[:24]
    equipo = str(row[' Equipo']).strip()[:24]
    posicion = str(row.get(' Position principal', 'N/A')).strip()[:7]
    reap = f"{row['REAP']:.2f}"
    
    try:
        elo = int(pd.to_numeric(str(row[' ELO']).strip(), errors='coerce'))
    except:
        elo = 'N/A'
    
    try:
        pot = int(pd.to_numeric(str(row[' Potencial']).strip(), errors='coerce'))
    except:
        pot = 'N/A'
    
    try:
        minutos_str = str(row[' Minutos']).strip()
        minutos = int(minutos_str) if minutos_str and minutos_str != '-' and minutos_str != 'nan' else 0
    except:
        minutos = 0
    
    print(f"{nombre:<25} {equipo:<25} {posicion:<8} {reap:<7} {str(elo):<6} {str(pot):<6} {minutos:<6}")

print(f"\n{'='*120}")
print("DETALLE COMPLETO DE JUGADORES")
print(f"{'='*120}\n")

for idx, row in df_filtered.iterrows():
    print(f"{'='*120}")
    print(f"👤 NOMBRE: {str(row['Nombre']).strip()}")
    print(f"⚽ EQUIPO: {str(row[' Equipo']).strip()}")
    print(f"📍 POSICIÓN: {str(row.get(' Position principal', 'N/A')).strip()}")
    print(f"🌍 PAÍS: {str(row[' País']).strip()}")
    
    try:
        edad = int(pd.to_numeric(str(row[' Edad']).strip(), errors='coerce'))
        año = str(row[' Año']).strip()
        print(f"🎂 EDAD: {edad} años (Año: 20{año})")
    except:
        print(f"🎂 EDAD: N/A")
    
    altura_val = str(row[' Altura']).strip()
    if altura_val and altura_val != '-' and altura_val != 'nan':
        print(f"📏 ALTURA: {altura_val} cm")
    
    print(f"\n📊 MÉTRICAS:")
    print(f"   • REAP: {row['REAP']:.2f}")
    
    try:
        elo = int(pd.to_numeric(str(row[' ELO']).strip(), errors='coerce'))
        max_elo = int(pd.to_numeric(str(row[' Max. ELO']).strip(), errors='coerce'))
        print(f"   • ELO: {elo} (Max: {max_elo})")
    except:
        print(f"   • ELO: N/A")
    
    try:
        pot = int(pd.to_numeric(str(row[' Potencial']).strip(), errors='coerce'))
        print(f"   • Potencial: {pot}")
    except:
        pass
    
    try:
        cambio_str = str(row[' +/- ELO (1 año)']).strip()
        if cambio_str and cambio_str != '-' and cambio_str != 'nan':
            cambio = int(float(cambio_str))
            if cambio > 0:
                print(f"   • Evolución ELO (1 año): +{cambio} ⬆️")
            elif cambio < 0:
                print(f"   • Evolución ELO (1 año): {cambio} ⬇️")
    except:
        pass
    
    print(f"\n⚽ TEMPORADA ACTUAL:")
    try:
        pj = int(pd.to_numeric(str(row[' PJ Temporada Actual']).strip(), errors='coerce'))
        print(f"   • Partidos jugados: {pj}")
    except:
        pass
    
    try:
        min_temp = int(pd.to_numeric(str(row[' Min Temporada Actual']).strip(), errors='coerce'))
        print(f"   • Minutos totales: {min_temp}")
    except:
        pass
    
    try:
        min_jor_str = str(row[' Minutos']).strip()
        if min_jor_str and min_jor_str != '-' and min_jor_str != 'nan':
            min_jor = int(float(min_jor_str))
            print(f"   • Minutos última jornada: {min_jor}")
    except:
        pass
    
    try:
        valor_str = str(row[' Valor de mercado']).strip()
        if valor_str and valor_str != '-' and valor_str != 'nan':
            valor = float(valor_str)
            if valor > 0:
                print(f"\n💰 VALOR DE MERCADO: €{valor:.3f}M")
    except:
        pass
    
    contrato = str(row.get(' Fin Contrato', '')).strip()
    if contrato and contrato != '-' and contrato != 'nan':
        print(f"📝 FIN DE CONTRATO: {contrato}")
    
    agente = str(row.get(' Agente', '')).strip()
    if agente and agente != '-' and agente != 'nan':
        print(f"🤝 AGENTE: {agente}")
    
    print()

print('='*120)
print(f"✅ Total de jugadores con REAP > 1.29: {len(df_filtered)}")
print('='*120)
