#!/usr/bin/env python3
"""
Copiar escudos de Primera B Metro desde directorio de escudos existente
"""

import os
import pandas as pd
import shutil
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOGOS_DIR = PROJECT_ROOT / 'team_logos'
ESCUDOS_SOURCE = Path(os.getenv('ESCUDOS_SOURCE_DIR', str(PROJECT_ROOT / 'escudos')))

# Crear directorio si no existe
LOGOS_DIR.mkdir(parents=True, exist_ok=True)

def normalize_name(name):
    """Normaliza nombre de equipo para buscar archivo"""
    # Remover espacios, puntos, acentos
    name = name.replace(' ', '').replace('.', '').replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
    return name

def main():
    print("\n" + "="*70)
    print("COPIAR ESCUDOS PRIMERA B METRO")
    print("="*70)
    
    # Leer CSV de Primera B Metro
    pbm_file = PROJECT_ROOT / 'data' / 'u23_primera_b_metro_resumen.csv'
    df = pd.read_csv(pbm_file)
    
    # Obtener equipos únicos
    equipos = set(df['team'].unique()) | set(df['opponent'].unique())
    equipos = sorted(equipos)
    
    print(f"\n📊 {len(equipos)} equipos de Primera B Metro")
    print(f"📂 Buscando escudos en: {ESCUDOS_SOURCE}")
    
    # Listar archivos disponibles en escudos
    if not ESCUDOS_SOURCE.exists():
        print(f"\n✗ Directorio de escudos no existe: {ESCUDOS_SOURCE}")
        return
    
    escudos_disponibles = list(ESCUDOS_SOURCE.glob('*.png'))
    print(f"📂 {len(escudos_disponibles)} escudos disponibles")
    
    # Intentar copiar escudos
    copiados = 0
    no_encontrados = []
    
    for equipo in equipos:
        # Buscar archivo con nombre del equipo
        archivo_encontrado = None
        
        # Buscar por nombre exacto
        for escudo in escudos_disponibles:
            if equipo in escudo.stem or normalize_name(equipo) in normalize_name(escudo.stem):
                archivo_encontrado = escudo
                break
        
        if archivo_encontrado:
            # Copiar a directorio de logos con nombre del equipo
            destino = LOGOS_DIR / f"{equipo}.png"
            shutil.copy2(archivo_encontrado, destino)
            print(f"  ✓ {equipo}: Copiado desde {archivo_encontrado.name}")
            copiados += 1
        else:
            print(f"  ✗ {equipo}: No encontrado")
            no_encontrados.append(equipo)
    
    print(f"\n{'='*70}")
    print("RESUMEN")
    print(f"{'='*70}")
    print(f"  ✓ Copiados: {copiados}/{len(equipos)}")
    print(f"  ✗ No encontrados: {len(no_encontrados)}")
    
    if no_encontrados:
        print(f"\n⚠️  Equipos sin escudo:")
        for equipo in no_encontrados:
            print(f"    • {equipo}")
    
    print(f"\n{'='*70}")
    print("✅ PROCESO COMPLETADO")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
