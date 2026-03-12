#!/usr/bin/env python3
"""
Generar descripciones de partidos usando ChatGPT API
"""

import pandas as pd
import json
from pathlib import Path
from openai import OpenAI

# Paths
BASE_DIR = Path('/Users/alvarolopezmolina/Desktop/Python/IDV_project/RONDA_02-08_03_26')
DATA_DIR = BASE_DIR / 'data'

# API Key
API_KEY = "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"

SYSTEM_PROMPT = """Eres un analista de scouting especializado en priorización de partidos para fútbol profesional.
Tu tarea es explicar de forma breve, clara y útil por qué un partido merece ser visto, basándote EXCLUSIVAMENTE en los datos de entrada.

REGLAS OBLIGATORIAS:
1. No inventes contexto.
2. No uses frases genéricas como "rendimiento sólido", "alta calidad individual" o "nivel competitivo adecuado" salvo que estén respaldadas por variables explícitas.
3. No menciones cosas que no estén en los datos.
4. El texto debe sonar ejecutivo, natural y aplicado a scouting real.
5. Debes explicar el valor del partido en función de:
   - densidad de jugadores U23
   - cantidad de U23 con minutos significativos
   - minutos promedio de los U23
   - peso competitivo de la liga
   - rating del partido, si existe
6. Si falta el rating, adapta el análisis al modelo SIN Rating.
7. Nunca repitas números sin interpretarlos.
8. Máximo 70-90 palabras.
9. Tono: profesional, directo, scouting-oriented.
10. Salida en español.

LÓGICA DEL MODELO:
- CON Rating: MPS = (Densidad_U23 × 5) + (Rating_Normalizado × 3) + (Peso_Liga × 2)
- SIN Rating: MPS = (Densidad_U23 × 7) + (Peso_Liga × 3)

INTERPRETACIÓN ESPERADA:
- Densidad_U23 alta = partido interesante para detectar talento joven en volumen
- Muchos U23 con 60+ minutos = contexto más fiable para evaluación real
- Minutos promedio altos = confianza competitiva y muestra más estable
- Peso_Liga alto = entorno más exigente y transferibilidad mayor
- Rating_Normalizado alto = mejor calidad relativa del partido dentro de la muestra

ESTRUCTURA DE SALIDA:
Devuelve SOLO el texto de 2-4 frases, sin título, sin bullets, sin fórmulas.

IMPORTANTE:
Prioriza la INTERPRETACIÓN de los inputs, no su reformulación. 
No digas: 'hay 7 U23 y 7 superan los 60 minutos'.
Di: 'el partido concentra una muestra amplia de talento joven con exposición competitiva suficiente para una evaluación más fiable'.

No uses estas expresiones salvo evidencia explícita:
- rendimiento sólido
- alta calidad individual
- partido valioso
- nivel competitivo adecuado
- contexto ideal

Sustitúyelas por interpretaciones derivadas de los datos disponibles."""


def generar_descripcion_partido(client, partido_data):
    """Genera descripción usando ChatGPT"""
    
    # Preparar datos
    tiene_rating = partido_data.get('rating_promedio_u23', 0) > 0
    modelo = "CON rating" if tiene_rating else "SIN rating"
    
    user_prompt = f"""Analiza este partido y redacta el texto final siguiendo las reglas anteriores.

DATOS:
- Competición: {partido_data.get('liga', 'N/A')}
- Equipo local: {partido_data.get('equipo_local', 'N/A')}
- Equipo visitante: {partido_data.get('equipo_visitante', 'N/A')}
- Densidad_U23: {partido_data.get('densidad_u23', 0):.2f}
- U23 con 60+ minutos: {partido_data.get('n_u23', 0)}
- Minutos promedio U23: {partido_data.get('minutos_promedio_u23', 0):.0f}
- Peso_Liga: {partido_data.get('peso_liga', 0):.2f}
- Rating_Normalizado: {partido_data.get('rating_normalizado', 0):.2f}
- MPS: {partido_data.get('mps', 0):.2f}
- Modelo usado: {modelo}

INSTRUCCIONES ADICIONALES:
- Si Densidad_U23 es la principal palanca del MPS, enfatiza volumen de talento joven.
- Si Peso_Liga es alto, enfatiza exigencia competitiva.
- Si hay muchos U23 con 60+ minutos, enfatiza fiabilidad de observación.
- Si el rating existe y es alto, enfatiza calidad relativa del partido.
- Evita adjetivos vacíos.
- Escribe como si el texto fuese a leerlo un Head of Scouting."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=200
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        print(f"  ✗ Error generando descripción: {str(e)[:100]}")
        return "Partido con presencia significativa de talento U23 en contexto competitivo."


def main():
    print("\n" + "="*70)
    print("GENERAR DESCRIPCIONES DE PARTIDOS CON CHATGPT")
    print("="*70)
    
    # Inicializar cliente OpenAI
    client = OpenAI(api_key=API_KEY)
    
    # Leer ranking
    ranking_path = DATA_DIR / 'PARTIDOS_COMPACTO_CON_MPS.csv'
    print(f"\n📂 Leyendo: {ranking_path}")
    df = pd.read_csv(ranking_path)
    print(f"   {len(df)} partidos cargados")
    
    # Leer datos de jugadores para calcular estadísticas adicionales
    jugadores_path = DATA_DIR / 'jugadores_completo_con_pbm.csv'
    df_jugadores = pd.read_csv(jugadores_path)
    
    # Calcular estadísticas por partido
    print(f"\n🔄 Calculando estadísticas adicionales...")
    
    for idx, row in df.iterrows():
        match_id = row['match_id']
        
        # Filtrar jugadores U23 de este partido con 60+ minutos
        jugadores_partido = df_jugadores[
            (df_jugadores['match_id'] == match_id) &
            (df_jugadores['is_u23'] == True) &
            (df_jugadores['minutes_played'] >= 60)
        ]
        
        # Calcular minutos promedio
        if len(jugadores_partido) > 0:
            minutos_promedio = jugadores_partido['minutes_played'].mean()
        else:
            minutos_promedio = 0
        
        df.at[idx, 'minutos_promedio_u23'] = minutos_promedio
        
        # Calcular rating normalizado
        rating = row.get('rating_promedio_u23', 0)
        df.at[idx, 'rating_normalizado'] = rating / 10 if rating > 0 else 0
        
        # Extraer equipos del partido
        partido = row['partido']
        if ' vs ' in partido:
            equipos = partido.split(' vs ')
            df.at[idx, 'equipo_local'] = equipos[0].strip()
            df.at[idx, 'equipo_visitante'] = equipos[1].strip()
        else:
            df.at[idx, 'equipo_local'] = partido
            df.at[idx, 'equipo_visitante'] = ''
    
    # Generar descripciones solo para TOP y MUY ALTA
    print(f"\n🤖 Generando descripciones con ChatGPT...")
    
    partidos_prioritarios = df[df['prioridad'].isin(['TOP', 'MUY ALTA'])].copy()
    print(f"   {len(partidos_prioritarios)} partidos prioritarios")
    
    descripciones = {}
    
    for idx, row in partidos_prioritarios.iterrows():
        match_id = row['match_id']
        partido = row['partido']
        
        print(f"\n  {idx+1}/{len(partidos_prioritarios)}: {partido[:50]}...")
        
        partido_data = {
            'liga': row['liga'],
            'equipo_local': row.get('equipo_local', ''),
            'equipo_visitante': row.get('equipo_visitante', ''),
            'densidad_u23': row['densidad_u23'],
            'n_u23': row['n_u23'],
            'minutos_promedio_u23': row.get('minutos_promedio_u23', 0),
            'peso_liga': row['peso_liga'],
            'rating_normalizado': row.get('rating_normalizado', 0),
            'rating_promedio_u23': row.get('rating_promedio_u23', 0),
            'mps': row['mps']
        }
        
        descripcion = generar_descripcion_partido(client, partido_data)
        descripciones[match_id] = descripcion
        
        print(f"  ✓ Descripción generada ({len(descripcion)} caracteres)")
    
    # Guardar descripciones
    output_path = DATA_DIR / 'descripciones_partidos.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(descripciones, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*70}")
    print("✅ DESCRIPCIONES GENERADAS")
    print(f"{'='*70}")
    print(f"  📊 {len(descripciones)} descripciones generadas")
    print(f"  📂 Guardadas en: {output_path}")
    print(f"\n🎯 Siguiente paso: Regenerar PDF con descripciones")


if __name__ == '__main__':
    main()
