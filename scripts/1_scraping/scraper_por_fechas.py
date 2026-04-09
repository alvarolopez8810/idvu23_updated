#!/usr/bin/env python3
"""
Scraper IDV por rango de fechas
--------------------------------
Sustituye al scraper por número de ronda. Usa dos estrategias según el torneo:

  A) scheduled-events  — Para torneos que aparecen en el endpoint global:
       GET /api/v1/sport/football/scheduled-events/{YYYY-MM-DD}
       (Colombia 2 Div, Carioca, Gaucho, Mineiro)

  B) tournament/last   — Para torneos que NO aparecen en scheduled-events:
       GET /api/v1/unique-tournament/{id}/season/{sid}/events/last/{page}
       Pagina hasta cubrir el rango de fechas.
       (Paranaense, Paulista A1/A2, Copa Brasil, Baiano)

En ambos casos filtra por status == 'finished' para no incluir partidos aún
en juego o aplazados.

Uso:
  python scraper_por_fechas.py --from 2026-03-02 --to 2026-03-08
  python scraper_por_fechas.py --from 2026-03-02 --to 2026-03-08 --tournaments 382,372

Variables de entorno equivalentes (para GitHub Actions):
  DATE_FROM=2026-03-02
  DATE_TO=2026-03-08
  TOURNAMENT_IDS=382,372        # opcional, coma-separado; omitir = todos
  CHROMEDRIVER_PATH=/path/to/chromedriver  # opcional
"""

import argparse
import json
import os
import time
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

# ---------------------------------------------------------------------------
# Rutas relativas al repo
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / 'data'
DATA_DIR.mkdir(parents=True, exist_ok=True)

SOFASCORE_BASE = 'https://www.sofascore.com/api/v1'

# ---------------------------------------------------------------------------
# Catálogo de torneos — cargado desde config/tournaments.json
#   strategy: 'scheduled'  -> aparece en /scheduled-events/{date}
#             'tournament' -> hay que paginar /events/last/{page}
# ---------------------------------------------------------------------------
_CONFIG_PATH = PROJECT_ROOT / 'config' / 'tournaments.json'

def _load_catalog(path: Path) -> dict:
    with open(path, encoding='utf-8') as f:
        raw = json.load(f)
    return {int(k): v for k, v in raw['tournaments'].items()}

TOURNAMENT_CATALOG = _load_catalog(_CONFIG_PATH)


# ---------------------------------------------------------------------------
# Selenium helpers
# ---------------------------------------------------------------------------

def build_driver(chromedriver_path: str | None = None) -> webdriver.Chrome:
    opts = Options()
    opts.add_argument('--headless')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('--disable-blink-features=AutomationControlled')
    opts.add_argument(
        'user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    opts.add_experimental_option('excludeSwitches', ['enable-automation'])

    service = Service(executable_path=chromedriver_path) if chromedriver_path else Service()
    driver = webdriver.Chrome(service=service, options=opts)
    driver.set_page_load_timeout(30)   # máx 30s por página; evita colgar en rate-limit
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver


def fetch_json(driver: webdriver.Chrome, url: str, retries: int = 3) -> dict | None:
    for attempt in range(retries):
        try:
            driver.get(url)
            time.sleep(2)
            pre = driver.find_element(By.TAG_NAME, 'pre')
            data = json.loads(pre.text)
            if 'error' in data:
                print(f'    API error {url}: {data["error"]}')
                return None
            return data
        except TimeoutException:
            print(f'    Timeout cargando {url} (intento {attempt + 1}/{retries})')
            if attempt < retries - 1:
                time.sleep(3)
        except Exception as exc:
            if attempt < retries - 1:
                time.sleep(3)
            else:
                print(f'    fetch_json falló ({url}): {exc}')
    return None


# ---------------------------------------------------------------------------
# Estrategia A: scheduled-events (un request por día, varios torneos)
# ---------------------------------------------------------------------------

def collect_via_scheduled(
    driver: webdriver.Chrome,
    date_from: date,
    date_to: date,
    target_ids: set[int],
) -> list[dict]:
    """Recoge eventos finished de torneos que aparecen en scheduled-events."""
    collected: list[dict] = []
    seen: set[int] = set()

    ts_from = int(datetime.combine(date_from, datetime.min.time()).timestamp())
    ts_to   = int(datetime.combine(date_to,   datetime.max.time()).timestamp())

    day = date_from
    while day <= date_to:
        url = f'{SOFASCORE_BASE}/sport/football/scheduled-events/{day.isoformat()}'
        data = fetch_json(driver, url)
        if data:
            for event in data.get('events', []):
                tid    = event.get('tournament', {}).get('uniqueTournament', {}).get('id')
                status = event.get('status', {}).get('type', '')
                eid    = event.get('id')
                ts     = event.get('startTimestamp', 0)
                if (tid in target_ids and status == 'finished'
                        and ts_from <= ts <= ts_to and eid not in seen):
                    seen.add(eid)
                    collected.append(event)
        day += timedelta(days=1)
        time.sleep(1)

    return collected


# ---------------------------------------------------------------------------
# Estrategia B: /events/last/{page} por torneo
# ---------------------------------------------------------------------------

def collect_via_tournament(
    driver: webdriver.Chrome,
    date_from: date,
    date_to: date,
    tid: int,
    cfg: dict,
) -> list[dict]:
    """Recoge eventos finished de un torneo paginando /events/last/."""
    sid = cfg['season']
    collected: list[dict] = []
    seen: set[int] = set()

    ts_from = int(datetime.combine(date_from, datetime.min.time()).timestamp())
    ts_to   = int(datetime.combine(date_to,   datetime.max.time()).timestamp())

    page = 0
    while True:
        url = f'{SOFASCORE_BASE}/unique-tournament/{tid}/season/{sid}/events/last/{page}'
        data = fetch_json(driver, url)
        if not data:
            break

        events = data.get('events', [])
        if not events:
            break

        # /events/last devuelve orden cronológico inverso: más recientes primero
        # Cuando el más reciente de la página ya es anterior a date_from, paramos
        oldest_ts = events[-1].get('startTimestamp', 0)
        if oldest_ts < ts_from:
            # Puede haber eventos en esta página dentro del rango; añadimos los válidos y paramos
            for event in events:
                ts = event.get('startTimestamp', 0)
                status = event.get('status', {}).get('type', '')
                eid = event.get('id')
                if ts_from <= ts <= ts_to and status == 'finished' and eid not in seen:
                    seen.add(eid)
                    collected.append(event)
            break

        for event in events:
            ts = event.get('startTimestamp', 0)
            status = event.get('status', {}).get('type', '')
            eid = event.get('id')
            if ts_from <= ts <= ts_to and status == 'finished' and eid not in seen:
                seen.add(eid)
                collected.append(event)

        page += 1
        time.sleep(1)

    return collected


# ---------------------------------------------------------------------------
# Extracción de jugadores a partir de un evento
# ---------------------------------------------------------------------------

def extract_players(driver: webdriver.Chrome, event: dict, catalog: dict) -> list[dict]:
    event_id = event['id']
    tid = event.get('tournament', {}).get('uniqueTournament', {}).get('id')
    cfg = catalog[tid]

    home_team = event.get('homeTeam', {})
    away_team = event.get('awayTeam', {})
    home_name = home_team.get('name', '')
    away_name = away_team.get('name', '')
    home_id   = home_team.get('id', 0)
    away_id   = away_team.get('id', 0)

    ts = event.get('startTimestamp', 0)
    match_date = datetime.fromtimestamp(ts).strftime('%d/%m/%Y') if ts else ''

    print(f'    [{cfg["nombre"]}] {home_name} vs {away_name} ({match_date})')

    lineups_url = f'{SOFASCORE_BASE}/event/{event_id}/lineups'
    lineups = fetch_json(driver, lineups_url)
    if not lineups:
        print(f'      ✗ Sin lineups')
        return []

    players = []
    for side, team, opponent, team_id, opp_id in [
        ('home', home_name, away_name, home_id, away_id),
        ('away', away_name, home_name, away_id, home_id),
    ]:
        for p in lineups.get(side, {}).get('players', []):
            pi    = p.get('player', {})
            stats = p.get('statistics', {})
            players.append({
                'player_id':      pi.get('id', 0),
                'player_name':    pi.get('name', ''),
                'shirt_number':   p.get('shirtNumber', ''),
                'position':       p.get('position', ''),
                'substitute':     p.get('substitute', False),
                'date_of_birth':  pi.get('dateOfBirthTimestamp', ''),
                'team':           team,
                'opponent':       opponent,
                'team_id':        team_id,
                'opponent_id':    opp_id,
                'home_away':      side,
                'match_id':       event_id,
                'match_date':     match_date,
                'liga':           cfg['nombre'],
                'peso_liga':      cfg['peso_liga'],
                'minutes_played': stats.get('minutesPlayed', 0),
                'rating':         stats.get('rating', 0),
                'goals':          stats.get('goals', 0),
                'assists':        stats.get('goalAssist', 0),
            })

    print(f'      + {len(players)} jugadores')
    return players


def enrich_ages(df: pd.DataFrame) -> pd.DataFrame:
    current_year = date.today().year
    birth_years, ages, u23_flags = [], [], []
    for dob in df['date_of_birth']:
        try:
            bd = datetime.fromtimestamp(int(dob))
            by = bd.year
            birth_years.append(by)
            ages.append(current_year - by)
            u23_flags.append(by >= 2003)
        except Exception:
            birth_years.append(0)
            ages.append(0)
            u23_flags.append(False)
    df['birth_year'] = birth_years
    df['age']        = ages
    df['is_u23']     = u23_flags
    return df


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Scraper IDV por rango de fechas')
    parser.add_argument('--from', dest='date_from', default=os.getenv('DATE_FROM'),
                        help='Fecha inicio YYYY-MM-DD (o env DATE_FROM)')
    parser.add_argument('--to', dest='date_to', default=os.getenv('DATE_TO'),
                        help='Fecha fin YYYY-MM-DD (o env DATE_TO)')
    parser.add_argument('--tournaments', default=os.getenv('TOURNAMENT_IDS'),
                        help='IDs separados por coma (o env TOURNAMENT_IDS). '
                             'Omitir = todos los del catálogo.')
    parser.add_argument('--chromedriver', default=os.getenv('CHROMEDRIVER_PATH'),
                        help='Ruta al chromedriver (o env CHROMEDRIVER_PATH)')
    parser.add_argument('--output', default=str(DATA_DIR / 'jugadores_ronda_nueva.csv'),
                        help='Ruta del CSV de salida')
    parser.add_argument('--reset', action='store_true',
                        help='Borra el acumulado histórico antes de empezar (para reconstrucción)')
    return parser.parse_args()


def main():
    args = parse_args()

    if not args.date_from or not args.date_to:
        print('ERROR: Debes indicar --from y --to (o DATE_FROM / DATE_TO)')
        sys.exit(1)

    date_from = date.fromisoformat(args.date_from)
    date_to   = date.fromisoformat(args.date_to)

    if args.tournaments:
        target_ids = {int(x.strip()) for x in args.tournaments.split(',')}
        unknown = target_ids - TOURNAMENT_CATALOG.keys()
        if unknown:
            print(f'AVISO: tournament_ids desconocidos (se ignoran): {unknown}')
            target_ids -= unknown
    else:
        target_ids = set(TOURNAMENT_CATALOG.keys())

    catalog = {tid: TOURNAMENT_CATALOG[tid] for tid in target_ids}

    scheduled_ids  = {tid for tid, cfg in catalog.items() if cfg['strategy'] == 'scheduled'}
    tournament_ids = {tid for tid, cfg in catalog.items() if cfg['strategy'] == 'tournament'}

    print('\n' + '=' * 70)
    print('SCRAPER IDV - POR RANGO DE FECHAS')
    print('=' * 70)
    print(f'  Rango   : {date_from} a {date_to}')
    print(f'  Ligas   : {", ".join(v["nombre"] for v in catalog.values())}')
    print(f'  Output  : {args.output}')
    print('=' * 70)

    driver = build_driver(args.chromedriver)
    all_events: list[dict] = []

    try:
        # Estrategia A: scheduled-events (un ciclo diario para todos)
        if scheduled_ids:
            nombres = [catalog[t]['nombre'] for t in scheduled_ids]
            print(f'\n[Estrategia A] scheduled-events: {", ".join(nombres)}')
            events_a = collect_via_scheduled(driver, date_from, date_to, scheduled_ids)
            print(f'  -> {len(events_a)} partido(s) encontrado(s)')
            all_events.extend(events_a)

        # Estrategia B: /events/last por torneo
        if tournament_ids:
            print(f'\n[Estrategia B] tournament/last:')
            for tid in tournament_ids:
                cfg = catalog[tid]
                print(f'  {cfg["nombre"]} (id={tid}, season={cfg["season"]})')
                events_b = collect_via_tournament(driver, date_from, date_to, tid, cfg)
                print(f'  -> {len(events_b)} partido(s)')
                all_events.extend(events_b)

        # Extracción de lineups
        print(f'\n[Lineups] {len(all_events)} partido(s) a procesar...')
        all_players: list[dict] = []
        for event in all_events:
            players = extract_players(driver, event, catalog)
            all_players.extend(players)
            time.sleep(1)

    finally:
        try:
            driver.quit()
        except Exception:
            pass
        try:
            driver.service.stop()
        except Exception:
            pass

    if not all_players:
        print('\nSin datos. Revisa el rango de fechas o los tournament_ids.')
        sys.exit(0)

    df = pd.DataFrame(all_players)
    df = enrich_ages(df)
    df = df[df['minutes_played'] > 0].copy()

    cols = [
        'player_id', 'player_name', 'shirt_number', 'position', 'substitute',
        'date_of_birth', 'team', 'opponent', 'team_id', 'opponent_id',
        'home_away', 'match_id', 'match_date', 'liga', 'peso_liga',
        'minutes_played', 'rating', 'goals', 'assists',
        'birth_year', 'age', 'is_u23',
    ]
    df = df[cols]

    # --- Guardar semana actual ---
    df.to_csv(args.output, index=False, encoding='utf-8')

    # --- Actualizar acumulado histórico ---
    acumulado_path = DATA_DIR / 'jugadores_acumulado.csv'
    if args.reset and acumulado_path.exists():
        acumulado_path.unlink()
        print('Acumulado reseteado.')
    if acumulado_path.exists():
        df_acum = pd.read_csv(acumulado_path, encoding='utf-8')
        # Deduplicar: match_id + player_id + home_away identifica una fila única
        df_combined = pd.concat([df_acum, df], ignore_index=True)
        df_combined = df_combined.drop_duplicates(
            subset=['match_id', 'player_id', 'home_away'], keep='last'
        )
        partidos_nuevos = df_combined['match_id'].nunique() - df_acum['match_id'].nunique()
    else:
        df_combined = df.copy()
        partidos_nuevos = df_combined['match_id'].nunique()

    df_combined = df_combined[cols]
    df_combined.to_csv(acumulado_path, index=False, encoding='utf-8')

    print('\n' + '=' * 70)
    print('RESUMEN')
    print('=' * 70)
    summary = df.groupby('liga').agg(
        Partidos=('match_id', 'nunique'),
        Jugadores=('player_id', 'count'),
        U23=('is_u23', 'sum'),
    )
    print(summary.to_string())
    print(f'\nTotal semana  : {len(df)} jugadores | {df["match_id"].nunique()} partidos')
    print(f'Partidos nuevos al acumulado: {partidos_nuevos}')
    print(f'Total acumulado: {len(df_combined)} jugadores | {df_combined["match_id"].nunique()} partidos')
    print(f'\nGuardado en    : {args.output}')
    print(f'Acumulado en   : {acumulado_path}')


if __name__ == '__main__':
    main()
