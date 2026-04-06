#!/usr/bin/env python3
"""
Scraper de Primera B Metro - Match Priority Score (MPS)
Basado en el sistema de IDV para scouting de fútbol femenino
"""

import requests
import pandas as pd
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import sys
import os

# Importar configuración
from config_primerabmetro import *

class PrimeraBScraper:
    """Scraper para Primera B Metro con sistema de puntuación MPS"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.reap_players = self._load_reap_data()
        
    def _load_reap_data(self) -> Dict:
        """Cargar datos de jugadores con REAP desde JSON"""
        try:
            with open(REAP_DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Crear diccionario de jugadores por nombre
                reap_dict = {}
                for player in data['jugadores_destacados']:
                    reap_dict[player['nombre'].lower()] = player
                return reap_dict
        except FileNotFoundError:
            print(f"⚠️  No se encontró {REAP_DATA_FILE}")
            return {}
    
    def _make_request(self, url: str) -> Optional[Dict]:
        """Hacer request con manejo de errores y rate limiting"""
        try:
            time.sleep(DELAY_BETWEEN_REQUESTS)
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"❌ Error en request a {url}: {e}")
            return None
    
    def get_matches(self) -> List[Dict]:
        """Obtener partidos de la jornada actual (API o CSV local)"""
        print(f"📂 Obteniendo partidos de Primera B Metro - Jornada {LEAGUE_CONFIG['primera_b_metro']['current_round']}")
        
        # Intentar API primero
        matches_url = LEAGUE_CONFIG['primera_b_metro']['endpoints']['matches']
        data = self._make_request(matches_url)
        
        if data:
            matches = []
            for event in data.get('events', []):
                match_data = {
                    'match_id': event['id'],
                    'home_team': event['homeTeam']['name'],
                    'away_team': event['awayTeam']['name'],
                    'start_timestamp': event['startTimestamp'],
                    'match_date': datetime.fromtimestamp(event['startTimestamp'], tz=timezone.utc).strftime('%Y-%m-%d %H:%M'),
                    'status': event['status']['type'],
                    'league': LEAGUE_CONFIG['primera_b_metro']['name']
                }
                matches.append(match_data)
            
            print(f"✅ {len(matches)} partidos encontrados via API")
            return matches
        
        # Si API falla, usar CSV local
        print("⚠️  API falló, usando CSV local...")
        return self._get_matches_from_csv()
    
    def _get_matches_from_csv(self) -> List[Dict]:
        """Obtener partidos desde CSV local de BeSoccer"""
        csv_file = str(Path(__file__).resolve().parents[2] / 'data' / 'primera_b_metro_j3.csv')
        
        try:
            df = pd.read_csv(csv_file, encoding='utf-8')
            
            # Obtener partidos únicos del CSV
            partidos_unicos = df[['partido_id', 'equipo_local', 'equipo_visitante']].drop_duplicates()
            
            matches = []
            for _, row in partidos_unicos.iterrows():
                match_data = {
                    'match_id': row['partido_id'],
                    'home_team': row['equipo_local'],
                    'away_team': row['equipo_visitante'],
                    'start_timestamp': int(datetime.strptime('2026-03-09 15:00', '%Y-%m-%d %H:%M').timestamp()),
                    'match_date': '2026-03-09 15:00',
                    'status': 'finished',
                    'league': LEAGUE_CONFIG['primera_b_metro']['name']
                }
                matches.append(match_data)
            
            print(f"✅ {len(matches)} partidos encontrados via CSV local")
            return matches
            
        except FileNotFoundError:
            print(f"❌ No se encontró {csv_file}")
            return []
        except Exception as e:
            print(f"❌ Error leyendo CSV: {e}")
            return []
    
    def get_lineups(self, match_id: int) -> Optional[Dict]:
        """Obtener alineaciones de un partido (API o CSV local)"""
        # Intentar API primero
        lineups_url = LEAGUE_CONFIG['primera_b_metro']['endpoints']['lineups'].format(match_id=match_id)
        api_data = self._make_request(lineups_url)
        
        if api_data:
            return api_data
        
        # Si API falla, usar CSV local
        print(f"⚠️  API lineups falló para match {match_id}, usando CSV local...")
        return self._get_lineups_from_csv(match_id)
    
    def _get_lineups_from_csv(self, match_id: int) -> Optional[Dict]:
        """Obtener alineaciones desde CSV local de BeSoccer"""
        csv_file = str(Path(__file__).resolve().parents[2] / 'data' / 'primera_b_metro_j3.csv')
        
        try:
            df = pd.read_csv(csv_file, encoding='utf-8')
            
            # Filtrar jugadores de este partido
            jugadores_partido = df[df['partido_id'] == match_id]
            
            if jugadores_partido.empty:
                return None
            
            # Obtener equipos del partido
            equipos = jugadores_partido[['equipo', 'equipo_local', 'equipo_visitante']].iloc[0]
            local = equipos['equipo_local']
            visitante = equipos['equipo_visitante']
            
            # Construir estructura similar a SofaScore API
            lineups_data = {
                'homeTeam': {
                    'name': local,
                    'players': []
                },
                'awayTeam': {
                    'name': visitante,
                    'players': []
                }
            }
            
            # Procesar jugadores
            for _, row in jugadores_partido.iterrows():
                player_info = {
                    'name': row['nombre'],
                    'position': row.get('posicion', ''),
                    'jerseyNumber': row.get('dorsal', ''),
                    'country': {'name': 'Argentina'},  # Default
                    'dateOfBirthTimestamp': None,  # No disponible en CSV
                    'birth_year': row.get('año_nacimiento'),  # Para detección U23
                    'substitute': not row.get('titular', False),
                    'statistics': {
                        'rating': row.get('rating', 0)
                    }
                }
                
                # Agregar al equipo correspondiente
                if row['equipo'] == local:
                    lineups_data['homeTeam']['players'].append(player_info)
                else:
                    lineups_data['awayTeam']['players'].append(player_info)
            
            return lineups_data
            
        except Exception as e:
            print(f"❌ Error obteniendo lineups del CSV: {e}")
            return None
    
    def _is_high_reap_player(self, player_name: str) -> Tuple[bool, Optional[Dict]]:
        """Verificar si un jugador tiene REAP ≥ 1.29"""
        name_lower = player_name.lower()
        
        # Búsqueda exacta o parcial
        if name_lower in self.reap_players:
            return True, self.reap_players[name_lower]
        
        # Búsqueda por nombre parcial
        for reap_name, reap_data in self.reap_players.items():
            if reap_name in name_lower or name_lower in reap_name:
                return True, reap_data
        
        return False, None
    
    def _calculate_age_from_timestamp(self, birth_timestamp: int) -> int:
        """Calcular edad desde timestamp de nacimiento"""
        if not birth_timestamp:
            return None
        
        birth_date = datetime.fromtimestamp(birth_timestamp, tz=timezone.utc)
        current_year = datetime.now(timezone.utc).year
        return current_year - birth_date.year
    
    def _is_u23_player(self, birth_timestamp: Optional[int], birth_year: Optional[int] = None) -> bool:
        """Verificar si es jugador U23 (nacido en 2003 o después)"""
        # Primero intentar con timestamp
        if birth_timestamp:
            age = self._calculate_age_from_timestamp(birth_timestamp)
            return age is not None and age <= 23
        
        # Si no hay timestamp, usar año de nacimiento
        if birth_year:
            return birth_year >= THRESHOLDS['u23_birth_year']
        
        return False
    
    def calculate_mps_score(self, match_data: Dict, lineups_data: Optional[Dict]) -> Dict:
        """Calcular Match Priority Score para un partido"""
        
        if not lineups_data:
            return {
                'match_id': match_data['match_id'],
                'mps_total': 0,
                'flags': [],
                'high_reap_players': [],
                'u23_players': [],
                'high_rated_players': [],
                'lineup_available': False
            }
        
        # Extraer jugadores de ambos equipos
        all_players = []
        for team in ['home', 'away']:
            team_key = f"{team}Team"
            if team_key in lineups_data:
                players = lineups_data[team_key].get('players', [])
                for player in players:
                    player_info = {
                        'name': player.get('name', ''),
                        'position': player.get('position', ''),
                        'jersey_number': player.get('jerseyNumber', ''),
                        'country': player.get('country', {}).get('name', ''),
                        'birth_timestamp': player.get('dateOfBirthTimestamp'),
                        'is_substitute': player.get('substitute', False),
                        'rating': player.get('statistics', {}).get('rating', 0),
                        'team': match_data[f'{team}_team']
                    }
                    all_players.append(player_info)
        
        # Inicializar resultados
        mps_total = 0
        flags = []
        high_reap_players = []
        u23_players = []
        high_rated_players = []
        
        # Analizar jugadores
        high_reap_starters = 0
        high_reap_squad = 0
        u23_starters = 0
        u23_squad = 0
        
        for player in all_players:
            # PRIORIDAD 2 - JUGADORES DESTACADOS REAP
            is_high_reap, reap_data = self._is_high_reap_player(player['name'])
            if is_high_reap:
                player['reap'] = reap_data['reap']
                player['equipo'] = reap_data['equipo']
                high_reap_players.append(player)
                high_reap_squad += 1
                if not player['is_substitute']:
                    high_reap_starters += 1
            
            # PRIORIDAD 6 - DENSIDAD U23
            birth_year = player.get('birth_year')  # Para datos CSV
            if self._is_u23_player(player['birth_timestamp'], birth_year):
                if player['birth_timestamp']:
                    player['age'] = self._calculate_age_from_timestamp(player['birth_timestamp'])
                elif birth_year:
                    player['age'] = datetime.now(timezone.utc).year - birth_year
                u23_players.append(player)
                u23_squad += 1
                if not player['is_substitute']:
                    u23_starters += 1
            
            # PRIORIDAD 7 - PERFORMANCE MOMENTUM
            rating = player.get('rating', 0)
            if rating >= THRESHOLDS['high_rating_threshold']:
                high_rated_players.append(player)
        
        # Calcular puntuación
        if high_reap_starters >= THRESHOLDS['high_reap_starters_threshold']:
            mps_total += MPS_SCORES['high_reap_starters']
            flags.append(FLAGS['HIGH_REAP_STARTERS'])
        
        if high_reap_squad >= THRESHOLDS['high_reap_squad_threshold']:
            mps_total += MPS_SCORES['high_reap_squad']
            flags.append(FLAGS['HIGH_REAP_SQUAD'])
        
        if u23_starters >= THRESHOLDS['u23_starters_threshold']:
            mps_total += MPS_SCORES['u23_starters']
            flags.append(FLAGS['U23_STARTERS'])
        
        if u23_squad >= THRESHOLDS['u23_squad_threshold']:
            mps_total += MPS_SCORES['u23_squad']
            flags.append(FLAGS['U23_SQUAD'])
        
        # Puntos por ratings altos (máximo 6)
        rating_points = min(len(high_rated_players) * MPS_SCORES['high_rating_per_player'], 
                           THRESHOLDS['max_high_rating_points'])
        if rating_points > 0:
            mps_total += rating_points
            flags.append(FLAGS['HIGH_RATING'])
        
        return {
            'match_id': match_data['match_id'],
            'mps_total': mps_total,
            'flags': flags,
            'high_reap_players': high_reap_players,
            'u23_players': u23_players,
            'high_rated_players': high_rated_players,
            'lineup_available': True,
            'high_reap_starters': high_reap_starters,
            'high_reap_squad': high_reap_squad,
            'u23_starters': u23_starters,
            'u23_squad': u23_squad
        }
    
    def get_priority_category(self, mps_total: int) -> Dict:
        """Obtener categoría de prioridad según puntuación"""
        if mps_total >= PRIORITY_CATEGORIES['must_watch']['min_score']:
            return PRIORITY_CATEGORIES['must_watch']
        elif PRIORITY_CATEGORIES['high_priority']['min_score'] <= mps_total <= PRIORITY_CATEGORIES['high_priority']['max_score']:
            return PRIORITY_CATEGORIES['high_priority']
        elif PRIORITY_CATEGORIES['monitor']['min_score'] <= mps_total <= PRIORITY_CATEGORIES['monitor']['max_score']:
            return PRIORITY_CATEGORIES['monitor']
        else:
            return PRIORITY_CATEGORIES['low_priority']
    
    def run_scraping(self):
        """Ejecutar proceso completo de scraping y análisis"""
        print("="*80)
        print("🏆 PRIMERA B METRO - MATCH PRIORITY SCORE (MPS)")
        print("="*80)
        print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🏟️  Jornada: {LEAGUE_CONFIG['primera_b_metro']['current_round']}")
        print(f"🎯 Jugadores con REAP ≥ {THRESHOLDS['reap_threshold']}: {len(self.reap_players)}")
        print("="*80)
        
        # Paso 1: Obtener partidos
        matches = self.get_matches()
        if not matches:
            print("❌ No se encontraron partidos")
            return
        
        # Paso 2: Analizar cada partido
        results = []
        for match in matches:
            print(f"\n⚽ Analizando: {match['home_team']} vs {match['away_team']}")
            
            # Obtener alineaciones
            lineups = self.get_lineups(match['match_id'])
            
            # Calcular MPS
            mps_data = self.calculate_mps_score(match, lineups)
            
            # Combinar datos
            result = {**match, **mps_data}
            result['priority_category'] = self.get_priority_category(mps_data['mps_total'])
            
            results.append(result)
            
            # Mostrar resumen del partido
            category = result['priority_category']
            print(f"   {category['emoji']} MPS: {mps_data['mps_total']} - {category['label']}")
            
            if mps_data['flags']:
                print(f"   🏷️  Flags: {', '.join(mps_data['flags'])}")
            
            if mps_data['high_reap_players']:
                print(f"   ⭐ REAP destacados: {len(mps_data['high_reap_players'])} ({mps_data['high_reap_starters']} titulares)")
                for player in mps_data['high_reap_players'][:3]:  # Mostrar hasta 3
                    starter = "👟" if not player['is_substitute'] else "🪑"
                    print(f"      {starter} {player['name']} (REAP: {player.get('reap', 'N/A')})")
            
            if mps_data['u23_players']:
                print(f"   🎓 U23: {len(mps_data['u23_players'])} ({mps_data['u23_starters']} titulares)")
            
            if mps_data['high_rated_players']:
                print(f"   🔥 Ratings ≥7.1: {len(mps_data['high_rated_players'])}")
        
        # Paso 3: Ordenar y exportar resultados
        results.sort(key=lambda x: x['mps_total'], reverse=True)
        
        # Exportar a CSV
        date_str = datetime.now().strftime('%Y%m%d_%H%M')
        csv_file = OUTPUT_CSV.format(date=date_str)
        
        df = pd.DataFrame(results)
        df.to_csv(csv_file, index=False, encoding='utf-8')
        print(f"\n💾 CSV guardado: {csv_file}")
        
        # Exportar a JSON
        json_file = OUTPUT_JSON.format(date=date_str)
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        print(f"💾 JSON guardado: {json_file}")
        
        # Resumen final
        self._print_final_summary(results)
    
    def _print_final_summary(self, results: List[Dict]):
        """Imprimir resumen final con estadísticas"""
        print("\n" + "="*80)
        print("📊 RESUMEN FINAL - MATCH PRIORITY SCORE")
        print("="*80)
        
        # Estadísticas por categoría
        category_stats = {}
        for result in results:
            cat = result['priority_category']['label']
            if cat not in category_stats:
                category_stats[cat] = []
            category_stats[cat].append(result)
        
        for category_name, matches in category_stats.items():
            emoji = matches[0]['priority_category']['emoji']
            print(f"\n{emoji} {category_name}: {len(matches)} partidos")
            
            for match in matches:
                print(f"   {match['home_team']} vs {match['away_team']} - MPS: {match['mps_total']}")
                if match['flags']:
                    print(f"      🏷️  {', '.join(match['flags'])}")
        
        # Estadísticas generales
        total_matches = len(results)
        avg_mps = sum(r['mps_total'] for r in results) / total_matches if total_matches > 0 else 0
        
        print(f"\n📈 ESTADÍSTICAS GENERALES:")
        print(f"   • Total partidos analizados: {total_matches}")
        print(f"   • MPS promedio: {avg_mps:.1f}")
        print(f"   • MPS máximo: {max(r['mps_total'] for r in results) if results else 0}")
        print(f"   • Partidos con alineaciones: {sum(1 for r in results if r['lineup_available'])}")
        
        print("\n" + "="*80)
        print("✅ ANÁLISIS COMPLETADO")
        print("="*80)

if __name__ == "__main__":
    scraper = PrimeraBScraper()
    scraper.run_scraping()
