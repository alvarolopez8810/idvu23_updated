#!/usr/bin/env python3
"""
Procesar jugadores U23 del archivo 20260309.csv y relacionarlos con sus partidos
de Primera B Metro - Jornada 3
"""

import pandas as pd
from datetime import datetime

# Rutas de archivos
from pathlib import Path
_DATA = Path(__file__).resolve().parents[2] / 'data'
U23_FILE = str(_DATA / '20260309.csv')
PARTIDOS_FILE = str(_DATA / 'primera_b_metro_j3.csv')
OUTPUT_FILE = str(_DATA / 'u23_primera_b_metro_jornada3.csv')

def normalize_name(name):
    """Normalizar nombres para comparación"""
    if pd.isna(name):
        return ""
    return str(name).strip().lower()

def main():
    print("="*80)
    print("PROCESAMIENTO DE JUGADORES U23 - PRIMERA B METRO - JORNADA 3")
    print("="*80)
    
    # Cargar archivo de jugadores U23
    print(f"\n📂 Cargando jugadores U23 desde: {U23_FILE}")
    df_u23 = pd.read_csv(U23_FILE, sep='\t', encoding='utf-8')
    df_u23.columns = df_u23.columns.str.strip()
    
    print(f"   ✅ {len(df_u23)} jugadores U23 cargados")
    
    # Cargar archivo de partidos Primera B Metro
    print(f"\n📂 Cargando partidos Primera B Metro desde: {PARTIDOS_FILE}")
    df_partidos = pd.read_csv(PARTIDOS_FILE, encoding='utf-8')
    
    print(f"   ✅ {len(df_partidos)} registros de jugadores en partidos")
    
    # Filtrar solo jugadores que jugaron (minutos > 0)
    df_partidos = df_partidos[df_partidos['minutos_jugados'] > 0].copy()
    print(f"   🔍 Filtrado jugadores con minutos: {len(df_partidos)} registros")
    
    # Crear lista de resultados
    resultados = []
    
    # Procesar cada jugador U23
    print(f"\n⚙️  Procesando jugadores U23...")
    
    jugadores_encontrados = 0
    jugadores_no_encontrados = []
    
    for idx, row in df_u23.iterrows():
        nombre_u23 = row['Nombre'].strip()
        equipo_u23 = row['Equipo'].strip()
        
        # Manejar año de nacimiento con valores inválidos
        try:
            año_str = str(row['Año']).strip()
            año_nacimiento = int(año_str) if año_str and año_str != '-' and año_str.isdigit() else None
        except (ValueError, AttributeError):
            año_nacimiento = None
        
        posicion = str(row.get('Position principal', '')).strip() if pd.notna(row.get('Position principal')) else ''
        
        # Normalizar nombre para búsqueda
        nombre_norm = normalize_name(nombre_u23)
        
        # Buscar en partidos por nombre y equipo
        partido_encontrado = False
        
        for _, partido in df_partidos.iterrows():
            nombre_partido_norm = normalize_name(partido['nombre'])
            equipo_partido = partido['equipo']
            
            # Match por nombre (contiene o es igual)
            if (nombre_norm in nombre_partido_norm or 
                nombre_partido_norm in nombre_norm or
                nombre_norm.split()[0] in nombre_partido_norm):
                
                # Verificar que el equipo coincida
                if equipo_u23 == equipo_partido:
                    # Verificar año de nacimiento si está disponible
                    if año_nacimiento and pd.notna(partido['año_nacimiento']):
                        if int(partido['año_nacimiento']) != año_nacimiento:
                            continue
                    
                    partido_encontrado = True
                    jugadores_encontrados += 1
                    
                    resultado = {
                        'player_name': nombre_u23,
                        'shirt_number': int(partido['dorsal']) if pd.notna(partido['dorsal']) else '',
                        'position': posicion if posicion else partido.get('posicion', ''),
                        'date_of_birth': partido.get('fecha_nacimiento', ''),
                        'team': partido['equipo'],
                        'opponent': partido['equipo_visitante'] if partido['equipo'] == partido['equipo_local'] else partido['equipo_local'],
                        'team_id': '',  # No disponible en BeSoccer
                        'opponent_id': '',  # No disponible en BeSoccer
                        'match_id': partido['partido_id'],
                        'match_date': '09/03/2026',  # Jornada 3
                        'liga': 'Primera B Metro',
                        'peso_liga': 0.9,
                        'minutes_played': int(partido['minutos_jugados'])
                    }
                    resultados.append(resultado)
                    break
        
        if not partido_encontrado:
            jugadores_no_encontrados.append(f"{nombre_u23} ({equipo_u23})")
    
    # Crear DataFrame de resultados
    df_resultado = pd.DataFrame(resultados)
    
    # Eliminar duplicados
    df_resultado = df_resultado.drop_duplicates(subset=['player_name', 'match_id'])
    
    # Ordenar por equipo y jugador
    df_resultado = df_resultado.sort_values(['team', 'player_name'])
    
    # Guardar resultado
    df_resultado.to_csv(OUTPUT_FILE, index=False, encoding='utf-8')
    
    print(f"\n✅ Procesamiento completado")
    print(f"   📊 Total de registros: {len(df_resultado)}")
    print(f"   👥 Jugadores encontrados: {jugadores_encontrados}")
    print(f"   ❌ Jugadores no encontrados: {len(jugadores_no_encontrados)}")
    print(f"\n💾 Archivo guardado: {OUTPUT_FILE}")
    
    # Mostrar jugadores no encontrados
    if jugadores_no_encontrados:
        print(f"\n⚠️  JUGADORES U23 NO ENCONTRADOS EN JORNADA 3:")
        print("="*80)
        for jugador in jugadores_no_encontrados[:10]:
            print(f"   - {jugador}")
        if len(jugadores_no_encontrados) > 10:
            print(f"   ... y {len(jugadores_no_encontrados) - 10} más")
    
    # Resumen por equipo
    print(f"\n📈 RESUMEN POR EQUIPO:")
    print("="*80)
    
    resumen = df_resultado.groupby('team').agg({
        'player_name': 'count',
        'minutes_played': 'sum',
        'opponent': 'first'
    }).rename(columns={
        'player_name': 'jugadores_u23',
        'minutes_played': 'minutos_totales',
        'opponent': 'rival'
    }).sort_values('jugadores_u23', ascending=False)
    
    print(resumen.to_string())
    
    # Detalle de jugadores
    print(f"\n📋 DETALLE DE JUGADORES U23:")
    print("="*80)
    
    for equipo in df_resultado['team'].unique():
        jugadores_equipo = df_resultado[df_resultado['team'] == equipo]
        rival = jugadores_equipo.iloc[0]['opponent']
        print(f"\n{equipo} vs {rival}")
        print(f"  Jugadores U23: {len(jugadores_equipo)}")
        for _, jug in jugadores_equipo.iterrows():
            print(f"    - {jug['player_name']} (#{jug['shirt_number']}) - {jug['position']} - {jug['minutes_played']} min")
    
    print(f"\n{'='*80}")
    print(f"✅ PROCESO COMPLETADO")
    print(f"{'='*80}")

if __name__ == '__main__':
    main()
