#!/usr/bin/env python3
"""
rebuild_acumulado.py
---------------------
Reconstruye el acumulado histórico desde una fecha de inicio
iterando en chunks semanales para evitar timeouts y rate limiting.

Los torneos a procesar se leen de config/tournaments.json.
Con --tournaments puedes restringir a un subconjunto de IDs.

Uso:
  python rebuild_acumulado.py --start 2026-01-01 --end 2026-04-06
  python rebuild_acumulado.py --start 2026-01-01               # end = hoy
  python rebuild_acumulado.py --start 2026-01-01 --tournaments 382,1238

El primer chunk usa --reset para borrar el acumulado existente.
Los siguientes hacen append normal.
"""

import argparse
import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH  = PROJECT_ROOT / 'config' / 'tournaments.json'


def load_catalog(path: Path) -> dict:
    with open(path, encoding='utf-8') as f:
        raw = json.load(f)
    return {int(k): v for k, v in raw['tournaments'].items()}


def iter_weeks(start: date, end: date, week_size: int):
    """Genera tuplas (chunk_from, chunk_to) de week_size días."""
    current = start
    while current <= end:
        chunk_end = min(current + timedelta(days=week_size - 1), end)
        yield current, chunk_end
        current = chunk_end + timedelta(days=1)


def main():
    parser = argparse.ArgumentParser(description='Reconstruir acumulado histórico IDV')
    parser.add_argument('--start', required=True, help='Fecha inicio YYYY-MM-DD')
    parser.add_argument('--end', default=str(date.today()), help='Fecha fin YYYY-MM-DD')
    parser.add_argument('--week-size', type=int, default=7, help='Dias por chunk')
    parser.add_argument('--tournaments', default='',
                        help='IDs separados por coma para restringir torneos. '
                             'Omitir = todos los de config/tournaments.json')
    args = parser.parse_args()

    # Cargar catálogo completo desde config
    catalog = load_catalog(CONFIG_PATH)

    # Filtrar si se pasan IDs concretos
    if args.tournaments:
        requested = {int(x.strip()) for x in args.tournaments.split(',')}
        unknown = requested - catalog.keys()
        if unknown:
            print(f'AVISO: IDs no encontrados en config/tournaments.json: {unknown}')
        active = {tid: cfg for tid, cfg in catalog.items() if tid in requested - unknown}
    else:
        active = catalog

    if not active:
        print('ERROR: ningún torneo válido para procesar.')
        sys.exit(1)

    start  = date.fromisoformat(args.start)
    end    = date.fromisoformat(args.end)
    chunks = list(iter_weeks(start, end, args.week_size))

    print('=' * 70)
    print('RECONSTRUCCION HISTORICO IDV')
    print('=' * 70)
    print(f'  Rango total : {start} a {end}')
    print(f'  Chunks      : {len(chunks)} x {args.week_size} dias')
    print(f'  Torneos     : {len(active)} cargados desde config/tournaments.json')
    for tid, cfg in active.items():
        print(f'    {tid:5} | {cfg["nombre"]:25} | season={cfg["season"]} | {cfg["strategy"]}')
    print('=' * 70)

    scraper  = str(PROJECT_ROOT / 'scripts' / '1_scraping' / 'scraper_por_fechas.py')
    failures = []

    for i, (chunk_from, chunk_to) in enumerate(chunks):
        print(f'\n[{i+1}/{len(chunks)}] {chunk_from} a {chunk_to}')

        cmd = [
            sys.executable, scraper,
            '--from', str(chunk_from),
            '--to',   str(chunk_to),
            '--tournaments', ','.join(str(t) for t in active.keys()),
        ]

        # Solo el primer chunk resetea el acumulado
        if i == 0:
            cmd.append('--reset')

        result = subprocess.run(cmd)

        if result.returncode != 0:
            print(f'  AVISO: chunk {chunk_from}/{chunk_to} fallo (returncode={result.returncode})')
            failures.append((chunk_from, chunk_to))
        else:
            print(f'  OK')

    print('\n' + '=' * 70)
    if failures:
        print(f'Reconstruccion completada con {len(failures)} chunks fallidos:')
        for f, t in failures:
            print(f'  - {f} a {t}')
        print('Puedes re-ejecutar el workflow con esas fechas para rellenar los huecos.')
        sys.exit(1)
    else:
        print(f'Reconstruccion completada: {len(chunks)} chunks OK.')
        sys.exit(0)


if __name__ == '__main__':
    main()
