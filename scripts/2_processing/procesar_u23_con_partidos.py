#!/usr/bin/env python3
"""
Procesar jugadores U23 del archivo 20260309.csv y relacionarlos con los partidos
de Primera B Metro del 3-5 de marzo 2026
"""

import pandas as pd
from datetime import datetime

# Rutas de archivos
U23_FILE = '/Users/alvarolopezmolina/Desktop/Python/IDV_project/RONDA_02-08_03_26/20260309.csv'
OUTPUT_FILE = '/Users/alvarolopezmolina/Desktop/Python/IDV_project/RONDA_02-08_03_26/u23_primera_b_metro_marzo_3_5.csv'

# Partidos de Primera B Metro (3-5 marzo 2026)
PARTIDOS = [
    {"fecha": "03/03/2026", "local": "Deportivo Laferrere", "visitante": "Brown Adrogué", "resultado": "0-1"},
    {"fecha": "03/03/2026", "local": "Villa San Carlos", "visitante": "Sportivo Italiano", "resultado": "0-1"},
    {"fecha": "04/03/2026", "local": "Argentino Merlo", "visitante": "Flandria", "resultado": "2-0"},
    {"fecha": "04/03/2026", "local": "San Martín Burzaco", "visitante": "Ituzaingó", "resultado": "3-0"},
    {"fecha": "04/03/2026", "local": "Talleres R. Escalada", "visitante": "Dep. Armenio", "resultado": "2-1"},
    {"fecha": "04/03/2026", "local": "Arsenal de Sarandí", "visitante": "Arg. Quilmes", "resultado": "0-1"},
    {"fecha": "04/03/2026", "local": "Liniers", "visitante": "Deportivo Camioneros", "resultado": "0-2"},
    {"fecha": "04/03/2026", "local": "UAI Urquiza", "visitante": "Dock Sud", "resultado": "0-0"},
    {"fecha": "04/03/2026", "local": "Villa Dálmine", "visitante": "Comunicaciones", "resultado": "0-0"},
    {"fecha": "05/03/2026", "local": "Excursionistas", "visitante": "Def. Unidos", "resultado": "1-0"},
    {"fecha": "05/03/2026", "local": "Real Pilar", "visitante": "Deportivo Merlo", "resultado": "1-3"},
]

def normalize_team_name(name):
    """Normalizar nombres de equipos para matching"""
    if pd.isna(name):
        return ""
    
    name = str(name).strip()
    
    # Mapeo de variaciones de nombres
    mappings = {
        "Deportivo Armenio": "Dep. Armenio",
        "Defensores Unidos": "Def. Unidos",
        "Argentino Quilmes": "Arg. Quilmes",
        "Comunicaciones": "Comunicaciones ",
    }
    
    for original, normalized in mappings.items():
        if original in name:
            return normalized
    
    return name

def main():
    print("="*80)
    print("PROCESAMIENTO DE JUGADORES U23 - PRIMERA B METRO")
    print("Partidos del 3-5 de marzo 2026")
    print("="*80)
    
    # Cargar archivo de jugadores U23
    print(f"\n📂 Cargando jugadores U23 desde: {U23_FILE}")
    df_u23 = pd.read_csv(U23_FILE, sep='\t', encoding='utf-8')
    df_u23.columns = df_u23.columns.str.strip()
    
    print(f"   ✅ {len(df_u23)} jugadores U23 cargados")
    
    # Crear lista de resultados
    resultados = []
    
    # Procesar cada partido
    print(f"\n⚽ Procesando {len(PARTIDOS)} partidos...")
    
    for partido in PARTIDOS:
        fecha = partido['fecha']
        local = partido['local']
        visitante = partido['visitante']
        resultado = partido['resultado']
        
        print(f"\n📅 {fecha}: {local} vs {visitante} ({resultado})")
        
        # Normalizar nombres de equipos (quitar espacios extra)
        local_norm = local.strip()
        visitante_norm = visitante.strip()
        
        # Buscar jugadores U23 del equipo local
        jugadores_local = df_u23[df_u23['Equipo'].str.strip() == local_norm]
        
        # Buscar jugadores U23 del equipo visitante
        jugadores_visitante = df_u23[df_u23['Equipo'].str.strip() == visitante_norm]
        
        # Debug: mostrar equipos si no hay matches
        if len(jugadores_local) == 0 and len(jugadores_visitante) == 0:
            equipos_disponibles = df_u23['Equipo'].str.strip().unique()
            if local_norm not in equipos_disponibles and visitante_norm not in equipos_disponibles:
                print(f"   ⚠️  Equipos no encontrados en CSV U23")
        
        # Procesar jugadores locales
        for _, jugador in jugadores_local.iterrows():
            nombre = jugador['Nombre'].strip()
            posicion = str(jugador.get('Position principal', '')).strip() if pd.notna(jugador.get('Position principal')) else ''
            año = jugador['Año']
            minutos = jugador['Minutos'] if pd.notna(jugador['Minutos']) else 0
            
            resultado_jugador = {
                'player_name': nombre,
                'shirt_number': '',
                'position': posicion,
                'date_of_birth': '',
                'team': local,
                'opponent': visitante,
                'team_id': '',
                'opponent_id': '',
                'match_id': f"{fecha.replace('/', '')}_{local.replace(' ', '_')}_{visitante.replace(' ', '_')}",
                'match_date': fecha,
                'liga': 'Primera B Metro',
                'peso_liga': 0.9,
                'minutes_played': int(minutos) if pd.notna(minutos) and str(minutos).replace('.', '').isdigit() else 0
            }
            resultados.append(resultado_jugador)
            print(f"   🏠 {nombre} ({posicion}) - {int(minutos) if pd.notna(minutos) else 0} min")
        
        # Procesar jugadores visitantes
        for _, jugador in jugadores_visitante.iterrows():
            nombre = jugador['Nombre'].strip()
            posicion = str(jugador.get('Position principal', '')).strip() if pd.notna(jugador.get('Position principal')) else ''
            año = jugador['Año']
            minutos = jugador['Minutos'] if pd.notna(jugador['Minutos']) else 0
            
            resultado_jugador = {
                'player_name': nombre,
                'shirt_number': '',
                'position': posicion,
                'date_of_birth': '',
                'team': visitante,
                'opponent': local,
                'team_id': '',
                'opponent_id': '',
                'match_id': f"{fecha.replace('/', '')}_{local.replace(' ', '_')}_{visitante.replace(' ', '_')}",
                'match_date': fecha,
                'liga': 'Primera B Metro',
                'peso_liga': 0.9,
                'minutes_played': int(minutos) if pd.notna(minutos) and str(minutos).replace('.', '').isdigit() else 0
            }
            resultados.append(resultado_jugador)
            print(f"   ✈️  {nombre} ({posicion}) - {int(minutos) if pd.notna(minutos) else 0} min")
        
        total_u23 = len(jugadores_local) + len(jugadores_visitante)
        print(f"   📊 Total U23 en este partido: {total_u23}")
    
    # Crear DataFrame de resultados
    df_resultado = pd.DataFrame(resultados)
    
    if len(df_resultado) == 0:
        print(f"\n⚠️  No se encontraron jugadores U23 en los partidos especificados")
        print(f"\nEquipos en CSV U23:")
        for equipo in sorted(df_u23['Equipo'].str.strip().unique()):
            print(f"   - {equipo}")
        return
    
    # Ordenar por fecha y equipo
    df_resultado = df_resultado.sort_values(['match_date', 'team', 'player_name'])
    
    # Guardar resultado
    df_resultado.to_csv(OUTPUT_FILE, index=False, encoding='utf-8')
    
    print(f"\n{'='*80}")
    print(f"✅ PROCESAMIENTO COMPLETADO")
    print(f"{'='*80}")
    print(f"   📊 Total de registros: {len(df_resultado)}")
    print(f"   👥 Jugadores únicos: {df_resultado['player_name'].nunique()}")
    print(f"   ⚽ Partidos procesados: {len(PARTIDOS)}")
    print(f"\n💾 Archivo guardado: {OUTPUT_FILE}")
    
    # Resumen por partido
    print(f"\n📈 RESUMEN POR PARTIDO:")
    print("="*80)
    
    for partido in PARTIDOS:
        fecha = partido['fecha']
        local = partido['local']
        visitante = partido['visitante']
        resultado = partido['resultado']
        
        match_id = f"{fecha.replace('/', '')}_{local.replace(' ', '_')}_{visitante.replace(' ', '_')}"
        jugadores_partido = df_resultado[df_resultado['match_id'] == match_id]
        
        jugadores_local = jugadores_partido[jugadores_partido['team'] == local]
        jugadores_visitante = jugadores_partido[jugadores_partido['team'] == visitante]
        
        print(f"\n{fecha} - {local} {resultado} {visitante}")
        print(f"  U23 {local}: {len(jugadores_local)} jugadores")
        for _, jug in jugadores_local.iterrows():
            print(f"    • {jug['player_name']} ({jug['position']}) - {jug['minutes_played']} min")
        
        print(f"  U23 {visitante}: {len(jugadores_visitante)} jugadores")
        for _, jug in jugadores_visitante.iterrows():
            print(f"    • {jug['player_name']} ({jug['position']}) - {jug['minutes_played']} min")

if __name__ == '__main__':
    main()
