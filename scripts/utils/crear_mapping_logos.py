#!/usr/bin/env python3
"""
Crear mapping completo de nombres de equipos a logos
"""

import pandas as pd
import json
from pathlib import Path

BASE_DIR = Path('/Users/alvarolopezmolina/Desktop/Python/IDV_project/RONDA_02-08_03_26')
DATA_DIR = BASE_DIR / 'data'
LOGOS_DIR = BASE_DIR / 'team_logos'

def main():
    print("\n" + "="*70)
    print("CREAR MAPPING DE LOGOS")
    print("="*70)
    
    # Cargar partidos para obtener team_ids
    partidos_path = DATA_DIR / 'PARTIDOS_COMPACTO_CON_MPS.csv'
    df_partidos = pd.read_csv(partidos_path)
    
    # Cargar mapping de Primera B Metro
    pbm_mapping_path = BASE_DIR / 'team_id_mapping_pbm.json'
    with open(pbm_mapping_path, 'r', encoding='utf-8') as f:
        pbm_mapping = json.load(f)
    
    # Crear diccionario de team_id a nombre
    team_mapping = {}
    
    # Añadir equipos de partidos con team_id
    for _, row in df_partidos.iterrows():
        partido = row['partido']
        if ' vs ' in partido:
            equipos = partido.split(' vs ')
            home_team = equipos[0].strip()
            away_team = equipos[1].strip()
            
            home_id = row.get('home_team_id')
            away_id = row.get('away_team_id')
            
            if pd.notna(home_id):
                team_mapping[home_team] = int(home_id)
            
            if pd.notna(away_id):
                team_mapping[away_team] = int(away_id)
    
    # Añadir equipos de Primera B Metro
    for team_name, data in pbm_mapping.items():
        team_id = data.get('team_id')
        if team_id:
            team_mapping[team_name] = team_id
    
    # Crear DataFrame de mapping
    mapping_data = []
    for team_name, team_id in team_mapping.items():
        logo_path = LOGOS_DIR / f"{team_id}.png"
        if logo_path.exists():
            mapping_data.append({
                'team_name': team_name,
                'team_id': team_id,
                'logo_path': str(logo_path)
            })
    
    df_mapping = pd.DataFrame(mapping_data)
    
    # Guardar mapping
    output_path = LOGOS_DIR / 'team_logos_mapping.csv'
    df_mapping.to_csv(output_path, index=False, encoding='utf-8')
    
    print(f"\n✅ Mapping creado: {len(df_mapping)} equipos")
    print(f"📂 Guardado en: {output_path}")
    
    # Mostrar equipos sin logo
    equipos_sin_logo = set(team_mapping.keys()) - set(df_mapping['team_name'])
    if equipos_sin_logo:
        print(f"\n⚠️  Equipos sin logo ({len(equipos_sin_logo)}):")
        for equipo in sorted(equipos_sin_logo):
            team_id = team_mapping[equipo]
            print(f"  - {equipo} (ID: {team_id})")
    
    # Verificar equipos específicos
    print(f"\n{'='*70}")
    print("VERIFICACIÓN DE EQUIPOS ESPECÍFICOS")
    print(f"{'='*70}")
    
    equipos_verificar = [
        'Def. Unidos',
        'Rio Branco-ES',
        'Dep. Armenio',
        'Deportivo Laferrere',
        'EC São Bento',
        'Santa Catarina Clube',
        'Cuiabá'
    ]
    
    for equipo in equipos_verificar:
        if equipo in df_mapping['team_name'].values:
            team_id = df_mapping[df_mapping['team_name'] == equipo]['team_id'].values[0]
            print(f"  ✓ {equipo}: ID {team_id}")
        else:
            print(f"  ✗ {equipo}: NO ENCONTRADO")


if __name__ == '__main__':
    main()
