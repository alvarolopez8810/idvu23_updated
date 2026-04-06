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
import os
import platform
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH  = PROJECT_ROOT / 'config' / 'tournaments.json'


def _find_python() -> str:
    """Devuelve un ejecutable Python que funcione en subprocess.
    En Windows los comandos python/py pueden apuntar a stubs de la Store
    que no se pueden usar para lanzar subprocesos. Esta función busca
    el intérprete real en varias ubicaciones conocidas.
    """
    if platform.system() != 'Windows':
        return sys.executable

    def is_real(p: str) -> bool:
        return bool(p) and 'WindowsApps' not in p and Path(p).is_file()

    # 1. sys.executable si ya es real
    if is_real(sys.executable):
        return sys.executable

    # 2. PATH filtrando directorios WindowsApps
    for directory in os.environ.get('PATH', '').split(os.pathsep):
        if 'WindowsApps' in directory:
            continue
        for name in ('python.exe', 'python3.exe'):
            candidate = str(Path(directory) / name)
            if is_real(candidate):
                return candidate

    # 3. Ubicaciones conocidas de CPython para el usuario actual
    local_app = Path(os.environ.get('LOCALAPPDATA', r'C:\Users\Default\AppData\Local'))
    search_globs = [
        local_app / 'Python' / 'bin' / 'python.exe',           # pythoncore instalado con bin/
        *sorted((local_app / 'Python').glob('pythoncore-*/python.exe'), reverse=True),
        *sorted((local_app / 'Programs' / 'Python').glob('Python3*/python.exe'), reverse=True),
    ]
    for candidate in search_globs:
        if is_real(str(candidate)):
            return str(candidate)

    # 4. Registro de Windows
    try:
        import winreg
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for root in (
                r'SOFTWARE\Python\PythonCore',
                r'SOFTWARE\WOW6432Node\Python\PythonCore',
            ):
                try:
                    with winreg.OpenKey(hive, root) as core_key:
                        i = 0
                        while True:
                            try:
                                ver = winreg.EnumKey(core_key, i)
                                try:
                                    with winreg.OpenKey(core_key, ver + r'\InstallPath') as ip:
                                        try:
                                            exe, _ = winreg.QueryValueEx(ip, 'ExecutablePath')
                                        except FileNotFoundError:
                                            install_dir, _ = winreg.QueryValueEx(ip, '')
                                            exe = str(Path(install_dir) / 'python.exe')
                                        if is_real(exe):
                                            return exe
                                except OSError:
                                    pass
                                i += 1
                            except OSError:
                                break
                except OSError:
                    pass
    except ImportError:
        pass

    return sys.executable  # ultimo recurso


PYTHON = _find_python()


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
    parser.add_argument('--chunk-timeout', type=int, default=1800,
                        help='Segundos maximos por chunk antes de abortar (defecto: 1800 = 30 min)')
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
        print('ERROR: ningun torneo valido para procesar.')
        sys.exit(1)

    start  = date.fromisoformat(args.start)
    end    = date.fromisoformat(args.end)
    chunks = list(iter_weeks(start, end, args.week_size))

    print('=' * 70)
    print('RECONSTRUCCION HISTORICO IDV')
    print('=' * 70)
    print(f'  Python      : {PYTHON}')
    print(f'  Rango total : {start} a {end}')
    print(f'  Chunks      : {len(chunks)} x {args.week_size} dias')
    print(f'  Timeout     : {args.chunk_timeout}s por chunk')
    print(f'  Torneos     : {len(active)} cargados desde config/tournaments.json')
    for tid, cfg in active.items():
        print(f'    {tid:5} | {cfg["nombre"]:25} | season={cfg["season"]} | {cfg["strategy"]}')
    print('=' * 70)

    scraper  = str(PROJECT_ROOT / 'scripts' / '1_scraping' / 'scraper_por_fechas.py')
    failures = []

    for i, (chunk_from, chunk_to) in enumerate(chunks):
        print(f'\n[{i+1}/{len(chunks)}] {chunk_from} a {chunk_to}')

        cmd = [
            PYTHON, scraper,
            '--from', str(chunk_from),
            '--to',   str(chunk_to),
            '--tournaments', ','.join(str(t) for t in active.keys()),
        ]

        if i == 0:
            cmd.append('--reset')

        try:
            result = subprocess.run(cmd, timeout=args.chunk_timeout)
            if result.returncode != 0:
                print(f'  AVISO: chunk fallo (returncode={result.returncode})')
                failures.append((chunk_from, chunk_to))
            else:
                print(f'  OK')
        except subprocess.TimeoutExpired:
            print(f'  AVISO: chunk abortado por timeout ({args.chunk_timeout}s)')
            failures.append((chunk_from, chunk_to))

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
