#!/usr/bin/env python3
"""
Script para corregir múltiples problemas:
1. Convertir fechas de nacimiento de timestamp a DD/MM/YYYY
2. Verificar escudos faltantes
3. Añadir REAP a jugadores de Primera B Metro
"""

import pandas as pd
import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / 'data'

def convert_timestamp_to_date(timestamp):
    """Convierte timestamp a formato DD/MM/YYYY"""
    if pd.isna(timestamp) or timestamp == '' or timestamp == 0:
        return ''
    
    try:
        timestamp = int(float(timestamp))
        date_obj = datetime.fromtimestamp(timestamp)
        return date_obj.strftime('%d/%m/%Y')
    except:
        return str(timestamp)

def main():
    print("\n" + "="*70)
    print("CORRIGIENDO PROBLEMAS DEL PDF")
    print("="*70)
    
    # 1. Cargar datos de jugadores
    jugadores_path = DATA_DIR / 'jugadores_completo_con_pbm.csv'
    print(f"\n📂 Leyendo: {jugadores_path}")
    df = pd.read_csv(jugadores_path)
    print(f"   {len(df)} registros cargados")
    
    # 2. Convertir fechas de nacimiento de timestamp
    print(f"\n🔄 Convirtiendo fechas de nacimiento...")
    
    # Verificar si hay fechas en timestamp
    if 'date_of_birth' in df.columns:
        # Intentar detectar timestamps (números grandes)
        timestamps_count = 0
        for idx, val in df['date_of_birth'].items():
            if pd.notna(val):
                try:
                    val_num = float(val)
                    if val_num > 100000:  # Es un timestamp
                        timestamps_count += 1
                        df.at[idx, 'date_of_birth'] = convert_timestamp_to_date(val_num)
                except:
                    pass
        
        print(f"   ✓ {timestamps_count} fechas convertidas de timestamp")
    
    # 3. Cargar REAP de Primera B Metro
    reap_path = BASE_DIR / 'jugadores_jornada_primerabmetro_reap.json'
    if reap_path.exists():
        print(f"\n📂 Cargando REAP de Primera B Metro...")
        with open(reap_path, 'r', encoding='utf-8') as f:
            reap_data = json.load(f)
        
        jugadores_reap = reap_data.get('jugadores_destacados', [])
        
        # Crear diccionario de REAP por nombre de jugador
        reap_dict = {}
        for j in jugadores_reap:
            nombre = j.get('nombre', '')
            reap = j.get('reap', 0)
            reap_dict[nombre] = reap
        
        # Añadir columna REAP si no existe
        if 'reap' not in df.columns:
            df['reap'] = 0.0
        
        # Asignar REAP a jugadores de Primera B Metro
        pbm_count = 0
        for idx, row in df[df['liga'] == 'Primera B Metro'].iterrows():
            player_name = row.get('player_name', '')
            if player_name in reap_dict:
                df.at[idx, 'reap'] = reap_dict[player_name]
                pbm_count += 1
        
        print(f"   ✓ REAP asignado a {pbm_count} jugadores de Primera B Metro")
    
    # 4. Guardar datos corregidos
    output_path = DATA_DIR / 'jugadores_completo_con_pbm.csv'
    df.to_csv(output_path, index=False, encoding='utf-8')
    
    print(f"\n{'='*70}")
    print("✅ DATOS CORREGIDOS")
    print(f"{'='*70}")
    print(f"  📂 Guardado en: {output_path}")
    
    # 5. Verificar escudos faltantes
    print(f"\n{'='*70}")
    print("VERIFICANDO ESCUDOS FALTANTES")
    print(f"{'='*70}")
    
    equipos_faltantes = [
        'Def. Unidos',
        'Rio Branco-ES',
        'Dep. Armenio',
        'Deportivo Laferrere',
        'EC São Bento',
        'Santa Catarina Clube',
        'Cuiabá'
    ]
    
    # Verificar en team_logos
    logos_dir = BASE_DIR / 'team_logos'
    if logos_dir.exists():
        logos_existentes = list(logos_dir.glob('*.png'))
        print(f"\n📂 {len(logos_existentes)} logos encontrados en {logos_dir}")
        
        for equipo in equipos_faltantes:
            # Buscar logo
            encontrado = False
            for logo in logos_existentes:
                if equipo.lower().replace(' ', '').replace('.', '') in logo.stem.lower().replace('_', '').replace('-', ''):
                    print(f"  ✓ {equipo}: {logo.name}")
                    encontrado = True
                    break
            
            if not encontrado:
                print(f"  ✗ {equipo}: NO ENCONTRADO")
    
    print(f"\n🎯 Siguiente paso: Regenerar PDF con datos corregidos")


if __name__ == '__main__':
    main()
