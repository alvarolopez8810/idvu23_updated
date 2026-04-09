"""
Generador de PDF — RONDA NUEVA (02-08 Mar 2026)
52 partidos: Brasil, Colombia, Argentina
Fórmula MPS con densidad U23 normalizada globalmente
"""

import pandas as pd
import numpy as np
import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Paths — relativos al repo
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _semana_label() -> str:
    """Construye 'SEMANA DD-MM-YYYY - DD-MM-YYYY' desde env vars DATE_FROM/DATE_TO."""
    def fmt(iso: str) -> str:
        try:
            return datetime.strptime(iso, '%Y-%m-%d').strftime('%d-%m-%Y')
        except Exception:
            return iso
    d_from = os.getenv('DATE_FROM', '')
    d_to   = os.getenv('DATE_TO', '')
    if d_from and d_to:
        return f'SEMANA {fmt(d_from)} - {fmt(d_to)}'
    return 'SEMANA'
DATA_DIR = str(PROJECT_ROOT / 'data')
LOGOS_DIR = str(PROJECT_ROOT / 'team_logos')
PDF_DIR = str(PROJECT_ROOT / 'output')

# Añadir directorio actual al path para importar generar_pdf_final_idv
sys.path.insert(0, str(Path(__file__).resolve().parent))

from generar_pdf_final_idv import PDFGeneratorIDV, COLOR_NEGRO, COLOR_GRIS, COLOR_GRIS_OSCURO, COLOR_DORADO, COLOR_GRIS_CLARO, COLOR_DORADO_CLARO
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, Image, SimpleDocTemplate
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus.flowables import HRFlowable
import pandas as pd
import numpy as np
from datetime import datetime

# Funciones auxiliares
def parse_birth_year(dob_str):
    if pd.isna(dob_str) or dob_str == '':
        return None
    try:
        if isinstance(dob_str, str) and '/' in dob_str:
            parts = dob_str.split('/')
            if len(parts) == 3:
                return int(parts[2])
    except:
        pass
    return None

def normalize_besoccer(df_bs):
    df_norm = df_bs.copy()
    rename_map = {
        'nombre': 'player_name',
        'dorsal': 'shirt_number',
        'posicion': 'position',
        'minutos_jugados': 'minutes_played',
        'goles': 'goals',
        'asistencias': 'assists',
        'partido_id': 'match_id',
        'año_nacimiento': 'birth_year'
    }
    for old_col, new_col in rename_map.items():
        if old_col in df_norm.columns:
            df_norm[new_col] = df_norm[old_col]
    if 'birth_year' in df_norm.columns:
        df_norm['is_u23'] = df_norm['birth_year'] >= 2003
    return df_norm

LEAGUE_WEIGHTS = {
    'Colombia 2 Div': 0.60,
    'Copa Brasil': 0.75,
    'Primera B Metro': 0.90,
    'Paulista A2': 0.65,
    'Paulista A1': 0.90,
    'Carioca': 0.85,
    'Mineiro': 0.78,
    'Baiano': 0.85,
    'Gaúcho': 0.85,
    'Paranaense': 0.90
}


class PDFGeneratorRonda17(PDFGeneratorIDV):
    """Generador PDF para Ronda 17 — 01 MAR 2026"""

    def create_portada_manual(self, story, tipo_pdf="detallado"):
        """Portada con fecha SEMANA 02-03-2026 - 08-03-2026"""
        header_data = []

        logo_path = str(PROJECT_ROOT / 'independientedelvalle.png')
        if os.path.exists(logo_path):
            try:
                logo_idv = Image(logo_path, width=1.5*inch, height=1.5*inch, mask='auto')
                temporada_style = ParagraphStyle(
                    'TemporadaPortada',
                    parent=self.subtitle_style,
                    fontSize=16,
                    textColor=COLOR_NEGRO,
                    alignment=TA_RIGHT,
                    fontName='Helvetica-Bold'
                )
                header_data.append([logo_idv, Paragraph("<b>FOOTBALL INTELLIGENCE DEPARTMENT</b>", temporada_style)])
            except:
                header_data.append([Paragraph("", self.normal_style), Paragraph("<b>FOOTBALL INTELLIGENCE DEPARTMENT</b>", self.subtitle_style)])
        else:
            header_data.append([Paragraph("", self.normal_style), Paragraph("<b>FOOTBALL INTELLIGENCE DEPARTMENT</b>", self.subtitle_style)])

        header_table = Table(header_data, colWidths=[3*inch, 3*inch])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 0.15*inch))

        story.append(HRFlowable(width="100%", thickness=2, color=COLOR_DORADO, spaceBefore=0, spaceAfter=0))
        story.append(Spacer(1, 0.8*inch))

        titulo_principal = ParagraphStyle(
            'TituloPrincipal', parent=self.title_style,
            fontSize=40, textColor=COLOR_NEGRO, alignment=TA_CENTER,
            fontName='Helvetica-Bold', spaceAfter=10, leading=48
        )
        story.append(Paragraph("<b>INDEPENDIENTE DEL VALLE</b>", titulo_principal))

        subtitulo_depto = ParagraphStyle(
            'SubtituloDepto', parent=self.subtitle_style,
            fontSize=16, textColor=COLOR_GRIS, alignment=TA_CENTER,
            fontName='Helvetica', spaceAfter=40
        )
        story.append(Paragraph("DEPARTAMENTO DE SCOUTING", subtitulo_depto))

        story.append(HRFlowable(width="50%", thickness=3, color=COLOR_DORADO, spaceBefore=10, spaceAfter=10))
        story.append(Spacer(1, 0.6*inch))

        titulo_campeonato = ParagraphStyle(
            'TituloCampeonato', parent=self.title_style,
            fontSize=22, textColor=COLOR_NEGRO, alignment=TA_CENTER,
            fontName='Helvetica-Bold', spaceAfter=10, leading=26
        )
        story.append(Paragraph("<b>DESGLOSE DETALLADO DE U23</b>", titulo_campeonato))

        subtitulo_rondas = ParagraphStyle(
            'SubtituloRondas', parent=self.normal_style,
            fontSize=14, textColor=COLOR_GRIS_OSCURO, alignment=TA_CENTER,
            fontName='Helvetica', spaceAfter=40
        )
        story.append(Paragraph(_semana_label(), subtitulo_rondas))

        story.append(Spacer(1, 0.4*inch))

        # Solo logo de Álvaro
        logo_alvaro = str(PROJECT_ROOT / 'Logo_Alvaro_resized.png')
        if os.path.exists(logo_alvaro):
            try:
                logo_img = Image(logo_alvaro, width=1.5*inch, height=0.6*inch, mask='auto')
                logos_container = Table([[logo_img]], colWidths=[6*inch])
                logos_container.setStyle(TableStyle([('ALIGN', (0, 0), (0, 0), 'CENTER')]))
                story.append(logos_container)
            except:
                pass

        story.append(PageBreak())

    def add_header_footer(self, canvas, doc):
        """Header/footer personalizado"""
        canvas.saveState()

        if doc.page <= 2:
            canvas.restoreState()
            return

        logo_path = str(PROJECT_ROOT / 'independientedelvalle.png')
        if os.path.exists(logo_path):
            try:
                canvas.drawImage(logo_path, 0.75*inch, self.height - 0.55*inch,
                                width=0.5*inch, height=0.5*inch,
                                preserveAspectRatio=True, mask='auto')
            except:
                pass

        canvas.setFont('Helvetica-Bold', 10)
        canvas.setFillColor(COLOR_NEGRO)
        canvas.drawRightString(self.width - 0.75*inch, self.height - 0.5*inch, "FOOTBALL INTELLIGENCE DEPARTMENT")

        canvas.setStrokeColor(COLOR_DORADO)
        canvas.setLineWidth(1.5)
        canvas.line(0.75*inch, self.height - 0.7*inch,
                   self.width - 0.75*inch, self.height - 0.7*inch)

        from datetime import datetime
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(COLOR_GRIS)
        canvas.drawString(inch, 0.5 * inch, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        canvas.drawRightString(self.width - inch, 0.5 * inch, f"Pág. {doc.page}")

        canvas.restoreState()

    def create_resumen_ejecutivo(self, story, ranking_df, categorias_count):
        """Resumen ejecutivo con tabla MPS + Z-Score"""

        story.append(Paragraph("RESUMEN EJECUTIVO", self.title_style))
        story.append(Spacer(1, 0.3*inch))

        # Tabla de categorías - SIEMPRE mostrar todas las prioridades aunque sean 0
        resumen_data = [['Categoría', 'Partidos', 'Descripción']]
        categorias_info = [
            ('🔴 PRIORIDAD TOP', categorias_count.get('PRIORIDAD TOP', 0), 'Z-Score >= 1.5 - Partido obligatorio'),
            ('🟠 PRIORIDAD MUY ALTA', categorias_count.get('PRIORIDAD MUY ALTA', 0), 'Z-Score 1.0-1.5 - Alto valor'),
            ('🟡 PRIORIDAD ALTA', categorias_count.get('PRIORIDAD ALTA', 0), 'Z-Score 0.5-1.0 - Seguimiento'),
            ('🟢 PRIORIDAD MEDIA', categorias_count.get('PRIORIDAD MEDIA', 0), 'Z-Score 0-0.5 - Contextual')
        ]

        for cat_name, count, desc in categorias_info:
            cat_cell = Paragraph(f"{cat_name}", self.normal_style)
            resumen_data.append([cat_cell, str(count), desc])

        resumen_table = Table(resumen_data, colWidths=[1.5*inch, 1*inch, 3.5*inch])
        resumen_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_NEGRO),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, COLOR_GRIS_CLARO),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_DORADO_CLARO])
        ]))

        story.append(resumen_table)
        story.append(Spacer(1, 0.3*inch))

        # Explicación del sistema MPS
        explicacion = """
        <b>Sistema de Scoring MPS (Match Priority Score):</b><br/>
        Índice propio que prioriza partidos según: <b>cantidad de U23</b>, <b>minutos reales jugados</b>, <b>titularidad</b>, <b>rating individual</b>, <b>edad</b> (bonus sub-20) y <b>peso de liga</b>. Se estandariza con Z-Score para clasificar por prioridad.<br/>
        <br/>
        <b>Ligas:</b> 🇧🇷 Paulista A1/A2, Carioca QF, Paranaense SF, Mineiro, Gaúcho SF, Baiano · 🇨🇴 Colombia 2 Div · 🇦🇷 Copa Argentina, Primera B, Primera B Met
        """
        story.append(Paragraph(explicacion, self.normal_style))
        story.append(Spacer(1, 0.2*inch))

        # Tabla: Filtrar por z-score (TOP > 1.5, MUY ALTA 0.5-1.5)
        # Ordenar por z_score_grupo descendente
        partidos_tabla = ranking_df[
            (ranking_df['z_score_grupo'] >= 0.5)
        ].sort_values('z_score_grupo', ascending=False).copy()
        
        num_partidos = len(partidos_tabla)
        
        titulo_tabla_style = ParagraphStyle(
            'TituloTabla', parent=self.normal_style,
            fontSize=11, textColor=COLOR_NEGRO, fontName='Helvetica-Bold', spaceAfter=8
        )
        story.append(Paragraph(f"<b>PARTIDOS PRIORIZADOS (TOP + MUY ALTA) - {num_partidos} PARTIDOS</b>", titulo_tabla_style))
        story.append(Spacer(1, 0.08*inch))

        tabla_data = [['#', 'Equipo Local', 'Equipo Visitante', 'U23', 'Liga', 'Z-Score', 'Prioridad']]

        for i, (_, row) in enumerate(partidos_tabla.iterrows(), 1):
            z_score = row['z_score_grupo']
            if z_score > 1.5:
                prioridad = 'TOP'
            elif z_score >= 0.5:
                prioridad = 'MUY ALTA'
            else:
                prioridad = 'ALTA'

            tabla_data.append([
                str(i),
                str(row['partido']).split(' vs ')[0][:15],
                str(row['partido']).split(' vs ')[1][:15] if ' vs ' in str(row['partido']) else '',
                str(int(row['n_u23'])),
                str(row['liga'])[:12],
                f"{z_score:.2f}",
                prioridad
            ])

        tabla_top10 = Table(tabla_data, colWidths=[0.3*inch, 1.2*inch, 1.2*inch, 0.35*inch, 1.0*inch, 0.6*inch, 0.8*inch])
        tabla_top10.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_NEGRO),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 7),
            ('FONTSIZE', (0, 1), (-1, -1), 6.5),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GRIS),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_GRIS_CLARO]),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))

        story.append(tabla_top10)
        story.append(Spacer(1, 0.2*inch))
        story.append(PageBreak())

    @staticmethod
    def _gradient_color(value, val_min, val_max):
        """Gradiente 5 paradas: rojo(0) → naranja(p25) → amarillo(p50) → azul(p75) → verde(max)."""
        if val_max == val_min:
            t = 1.0
        else:
            t = max(0.0, min(1.0, (value - val_min) / (val_max - val_min)))

        # 5 stops: 0.0=rojo, 0.25=naranja, 0.5=amarillo, 0.75=azul, 1.0=verde
        stops = [
            (0.00, (220, 50, 50)),    # rojo
            (0.25, (240, 160, 50)),   # naranja
            (0.50, (240, 220, 60)),   # amarillo
            (0.75, (70, 130, 200)),   # azul
            (1.00, (34, 139, 34)),    # verde
        ]

        # Encontrar segmento
        for i in range(len(stops) - 1):
            t0, c0 = stops[i]
            t1, c1 = stops[i + 1]
            if t <= t1:
                seg = (t - t0) / (t1 - t0) if t1 != t0 else 1.0
                r = int(c0[0] + seg * (c1[0] - c0[0]))
                g = int(c0[1] + seg * (c1[1] - c0[1]))
                b = int(c0[2] + seg * (c1[2] - c0[2]))
                return colors.HexColor(f'#{r:02x}{g:02x}{b:02x}')

        # Fallback: verde
        return colors.HexColor('#228b22')

    def create_anexo_u23_destacados(self, story, df_all):
        """ANEXO I: Jugadores U23 destacados — agrupados por equipo, gradiente en rating"""

        story.append(PageBreak())
        story.append(Paragraph("<b>ANEXO I: JUGADORES U23 DESTACADOS</b>", self.title_style))
        story.append(Spacer(1, 0.3*inch))

        explicacion_style = ParagraphStyle('Explicacion', parent=self.normal_style, fontSize=10, spaceAfter=15)
        story.append(Paragraph(
            "<b>Todos los jugadores U23 (nacidos en 2003 o después) con rating ≥ 7.5.</b><br/>"
            "Agrupados por equipo. Color en rating: 🟢 verde (alto) → 🟡 amarillo (máximo).",
            explicacion_style
        ))
        story.append(Spacer(1, 0.2*inch))

        # Filter U23 with rating >= 7.5
        df_u23 = df_all[(df_all['is_u23'] == True) & (df_all['minutes_played'] > 0)].copy()
        df_u23['rating_num'] = pd.to_numeric(df_u23['rating'], errors='coerce')
        df_u23 = df_u23[df_u23['rating_num'] >= 7.5].sort_values('rating_num', ascending=False)

        if len(df_u23) == 0:
            story.append(Paragraph("<i>No se encontraron jugadores con rating >= 7.5</i>", self.normal_style))
            return

        # Agrupar por equipo, ordenar equipos por mejor rating de su mejor jugador
        equipos_order = df_u23.groupby('team')['rating_num'].max().sort_values(ascending=False).index.tolist()

        tabla_data = [['Nombre', 'Equipo', 'Liga', 'Rating', 'Fecha Nac.', 'Min.']]
        rating_values = []  # track rating per data row for gradient

        for equipo in equipos_order:
            df_equipo = df_u23[df_u23['team'] == equipo].sort_values('rating_num', ascending=False)
            for _, jugador in df_equipo.iterrows():
                dob = jugador.get('date_of_birth', '')
                if pd.isna(dob):
                    dob = ''
                tabla_data.append([
                    str(jugador['player_name'])[:25],
                    str(jugador['team'])[:18],
                    str(jugador['liga'])[:12],
                    f"{jugador['rating_num']:.1f}",
                    str(dob)[:10],
                    str(int(jugador['minutes_played']))
                ])
                rating_values.append(jugador['rating_num'])

        tabla = Table(tabla_data, colWidths=[1.5*inch, 1.2*inch, 0.9*inch, 0.5*inch, 0.8*inch, 0.4*inch])

        base_style = [
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_NEGRO),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (3, 0), (5, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GRIS),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]

        # Gradiente rating ANEXO I: 7.5=naranja, p25=amarillo, p50=azul, p75=verde, 10=amarillo(negro)
        rating_stops = [
            (0.00, (240, 160, 50)),   # 7.5 = naranja
            (0.25, (240, 220, 60)),   # p25 = amarillo
            (0.50, (70, 130, 200)),   # p50 = azul
            (0.75, (34, 139, 34)),    # p75 = verde
            (1.00, (255, 220, 40)),   # 10 = amarillo dorado
        ]
        for i, rv in enumerate(rating_values):
            row_idx = i + 1
            t = (rv - 7.5) / (10.0 - 7.5) if 10.0 != 7.5 else 1.0
            t = max(0.0, min(1.0, t))
            # Interpolar entre stops
            bg_color = None
            for s in range(len(rating_stops) - 1):
                t0, c0 = rating_stops[s]
                t1, c1 = rating_stops[s + 1]
                if t <= t1:
                    seg = (t - t0) / (t1 - t0) if t1 != t0 else 1.0
                    r = int(c0[0] + seg * (c1[0] - c0[0]))
                    g = int(c0[1] + seg * (c1[1] - c0[1]))
                    b = int(c0[2] + seg * (c1[2] - c0[2]))
                    bg_color = colors.HexColor(f'#{r:02x}{g:02x}{b:02x}')
                    break
            if bg_color is None:
                bg_color = colors.HexColor('#ffdc28')
            base_style.append(('BACKGROUND', (3, row_idx), (3, row_idx), bg_color))
            # Texto blanco en zona azul/verde (p50-p75), negro en amarillo (max)
            if 0.4 <= t <= 0.85:
                base_style.append(('TEXTCOLOR', (3, row_idx), (3, row_idx), colors.white))
            else:
                base_style.append(('TEXTCOLOR', (3, row_idx), (3, row_idx), colors.black))

        # Alternar fondo gris/blanco entre equipos (excepto columna rating)
        GRIS_EQUIPO = colors.HexColor('#E8E8E8')
        current_row = 1
        equipo_idx = 0
        non_rating_cols = [(0, 2), (4, 5)]  # cols 0-2 y 4-5 (excluir col 3 = rating)
        for equipo in equipos_order:
            count = len(df_u23[df_u23['team'] == equipo])
            if equipo_idx % 2 == 0:
                # Fondo gris para equipos pares
                for col_start, col_end in non_rating_cols:
                    base_style.append(('BACKGROUND', (col_start, current_row), (col_end, current_row + count - 1), GRIS_EQUIPO))
            # else: blanco (default)
            current_row += count
            equipo_idx += 1

        tabla.setStyle(TableStyle(base_style))
        story.append(tabla)
        story.append(Spacer(1, 0.3*inch))

    def create_anexo_acumulado_u23(self, story, df_all):
        """ANEXO II: Acumulado jugadores U23 — merge histórico + ronda actual"""

        story.append(PageBreak())
        story.append(Paragraph("<b>ANEXO II: ACUMULADO JUGADORES U23</b>", self.title_style))
        story.append(Spacer(1, 0.3*inch))

        explicacion_style = ParagraphStyle('ExplicacionAcum', parent=self.normal_style, fontSize=10, spaceAfter=15)
        story.append(Paragraph(
            "<b>Criterios de selección:</b><br/>"
            "• Jugadores nacidos en 2003 o posterior (U23)<br/>"
            "• Rating promedio superior a 7.29<br/>"
            "• Mínimo 2 partidos jugados<br/>"
            "• Datos acumulados de todas las rondas analizadas",
            explicacion_style
        ))
        story.append(Spacer(1, 0.2*inch))
        
        explicacion = """
        <b>Jugadores U23 con mejor rating promedio acumulado en la temporada (SofaScore)</b><br/>
        Mínimo 2 partidos jugados y rating promedio ≥ 7.0. Datos obtenidos directamente de SofaScore API.
        """
        story.append(Paragraph(explicacion, self.normal_style))
        story.append(Spacer(1, 0.2*inch))

        # Cargar ratings acumulados de SofaScore
        ratings_path = os.path.join(DATA_DIR, 'ratings_acumulados_sofascore.json')
        if not os.path.exists(ratings_path):
            story.append(Paragraph("<i>No se encontraron datos de ratings acumulados de SofaScore</i>", self.normal_style))
            return
        
        with open(ratings_path, 'r', encoding='utf-8') as f:
            ratings_data = json.load(f)
        
        # Convertir a DataFrame
        ratings_list = []
        for player_id, data in ratings_data.items():
            ratings_list.append({
                'player_id': int(player_id),
                'player_name': data['player_name'],
                'liga': data['liga'],
                'rating_promedio': data['rating_promedio'],
                'partidos_total': data['partidos_total']
            })
        
        df_ratings = pd.DataFrame(ratings_list)
        
        # Obtener información adicional de jugadores (equipo, fecha nacimiento)
        df_players = df_all[df_all['is_u23'] == True][['player_id', 'player_name', 'team', 'date_of_birth']].drop_duplicates('player_id')
        
        # Merge ratings con info de jugadores
        df = pd.merge(df_ratings, df_players, on='player_id', how='left', suffixes=('', '_extra'))
        df['team_name'] = df['team'].fillna('N/A')
        df['fecha_nacimiento'] = df['date_of_birth'].fillna('N/A')
        
        # Filtrar: rating >= 7.0 y mínimo 2 partidos
        df = df[
            (df['rating_promedio'] >= 7.0) & (df['partidos_total'] >= 2)
        ].sort_values('rating_promedio', ascending=False).reset_index(drop=True)

        if len(df) == 0:
            story.append(Paragraph("<i>No hay jugadores que cumplan los criterios</i>", self.normal_style))
            return

        tabla_data = [['Nombre', 'Fecha Nac.', 'Equipo', 'Liga', 'Rating', 'Partidos']]

        for _, row in df.iterrows():
            tabla_data.append([
                row['player_name'],
                str(row['fecha_nacimiento'])[:10],
                row['team_name'],
                str(row['liga'])[:12],
                f"{row['rating_promedio']:.2f}",
                str(int(row['partidos_total']))
            ])

        tabla = Table(tabla_data, colWidths=[2.0*inch, 0.9*inch, 1.5*inch, 1.1*inch, 0.6*inch, 0.7*inch])
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_DORADO),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (2, 1), (2, -1), 'LEFT'),
            ('ALIGN', (3, 1), (3, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GRIS),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ]))

        # Resaltar TOP 3
        for i in range(1, min(4, len(tabla_data))):
            tabla.setStyle(TableStyle([
                ('BACKGROUND', (0, i), (-1, i), COLOR_DORADO_CLARO),
            ]))

        story.append(tabla)
        story.append(Spacer(1, 0.3*inch))

    def create_anexo_partidos_u23(self, story, df_all):
        """ANEXO II: Partidos con más U23 — gradiente vertical por columna de año"""

        story.append(PageBreak())
        story.append(Paragraph("<b>ANEXO II: PARTIDOS CON MÁS JUGADORES U23</b>", self.title_style))
        story.append(Spacer(1, 0.3*inch))

        explicacion_style = ParagraphStyle('Explicacion', parent=self.normal_style, fontSize=10, spaceAfter=15)
        story.append(Paragraph(
            "<b>Partidos ordenados por cantidad de jugadores U23 que jugaron minutos.</b><br/>"
            "Desglosado por año de nacimiento. Mínimo 10 jugadores U23.<br/>"
            "Color por columna: verde = máximo de esa columna, naranja = mínimo.",
            explicacion_style
        ))
        story.append(Spacer(1, 0.2*inch))

        partidos_u23 = []
        for match_id in df_all['match_id'].unique():
            df_match = df_all[(df_all['match_id'] == match_id) & (df_all['minutes_played'] > 0)].copy()
            df_match['birth_year'] = df_match['birth_year_direct'].apply(
                lambda x: int(x) if pd.notna(x) else None
            )
            df_u23 = df_match[df_match['is_u23'] == True]

            if len(df_u23) == 0:
                continue

            total = len(df_u23)
            by_counts = df_u23['birth_year'].dropna().astype(int)

            equipos = df_match['team'].unique()
            partido_nombre = f"{equipos[0]} vs {equipos[1]}" if len(equipos) >= 2 else "N/A"
            liga = df_match['liga'].iloc[0]

            partidos_u23.append({
                'partido': partido_nombre,
                'liga': liga,
                'total': total,
                '2003': len(by_counts[by_counts == 2003]),
                '2004': len(by_counts[by_counts == 2004]),
                '2005': len(by_counts[by_counts == 2005]),
                '2006': len(by_counts[by_counts == 2006]),
                '2007': len(by_counts[by_counts == 2007]),
                '2008+': len(by_counts[by_counts >= 2008]),
            })

        partidos_u23 = [p for p in partidos_u23 if p['total'] >= 10]
        partidos_u23 = sorted(partidos_u23, key=lambda x: x['total'], reverse=True)

        if not partidos_u23:
            story.append(Paragraph("<i>No hay partidos con ≥ 10 U23</i>", self.normal_style))
            return

        year_cols = ['2003', '2004', '2005', '2006', '2007', '2008+']

        tabla_data = [['Partido', 'Liga', '2003', '2004', '2005', '2006', '2007', '2008+', 'Total']]
        for p in partidos_u23:
            tabla_data.append([
                p['partido'][:30], p['liga'][:10],
                str(p['2003']), str(p['2004']), str(p['2005']),
                str(p['2006']), str(p['2007']), str(p['2008+']),
                str(p['total'])
            ])

        tabla = Table(tabla_data, colWidths=[1.6*inch, 0.8*inch, 0.4*inch, 0.4*inch, 0.4*inch, 0.4*inch, 0.4*inch, 0.5*inch, 0.6*inch])

        base_style = [
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_NEGRO),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GRIS),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]

        # Gradiente vertical por cada columna de año
        for col_offset, year_key in enumerate(year_cols):
            col_idx = col_offset + 2  # columnas 2-7
            col_values = [p[year_key] for p in partidos_u23]
            col_max = max(col_values) if col_values else 0
            col_min = min(col_values) if col_values else 0

            if col_max == 0:
                continue  # no colorear si toda la columna es 0

            for row_offset, val in enumerate(col_values):
                row_idx = row_offset + 1  # +1 por header
                # Gradiente: 0 = rojo, max = verde (siempre colorear)
                bg = self._gradient_color(val, 0, col_max)
                base_style.append(('BACKGROUND', (col_idx, row_idx), (col_idx, row_idx), bg))
                if val >= col_max * 0.8 and col_max > 2:
                    base_style.append(('TEXTCOLOR', (col_idx, row_idx), (col_idx, row_idx), colors.white))

        tabla.setStyle(TableStyle(base_style))
        story.append(tabla)
        story.append(Spacer(1, 0.3*inch))

    def create_anexo_mejores_18_21(self, story, df_all):
        """ANEXO II: Mejores jugadores 18-21 años de la jornada (nacidos 2005-2008)"""
        
        story.append(PageBreak())
        story.append(Paragraph("<b>ANEXO II: MEJORES JUGADORES 18-21 AÑOS DE LA JORNADA</b>", self.title_style))
        story.append(Spacer(1, 0.3*inch))
        
        explicacion_style = ParagraphStyle('Explicacion', parent=self.normal_style, fontSize=10, spaceAfter=15)
        story.append(Paragraph(
            "<b>Criterios de selección:</b><br/>"
            "• Jugadores nacidos entre 2005 y 2008 (18-21 años)<br/>"
            "• Rating ≥ 7.5 en la jornada<br/>"
            "• Jugaron minutos en al menos un partido<br/>"
            "• Ordenados por rating descendente",
            explicacion_style
        ))
        story.append(Spacer(1, 0.2*inch))
        
        # Filtrar jugadores 18-21 años con rating >= 7.5
        df_18_21 = df_all[
            (df_all['birth_year_direct'] >= 2005) & 
            (df_all['birth_year_direct'] <= 2008) &
            (df_all['minutes_played'] > 0)
        ].copy()
        
        df_18_21['rating_num'] = pd.to_numeric(df_18_21['rating'], errors='coerce')
        df_18_21 = df_18_21[df_18_21['rating_num'] >= 7.5]
        
        if len(df_18_21) == 0:
            story.append(Paragraph("<i>No hay jugadores 18-21 años con rating ≥ 7.5 en esta jornada</i>", self.normal_style))
            return
        
        # Ordenar por rating DESCENDENTE (mayor a menor)
        df_18_21 = df_18_21.sort_values('rating_num', ascending=False).reset_index(drop=True)
        
        # Crear tabla sin agrupar, directamente ordenado por rating
        tabla_data = [['Equipo', 'Nombre', 'Pos', 'Min', 'Rating', 'Año Nac.', 'Liga']]
        
        for _, row in df_18_21.iterrows():
            tabla_data.append([
                row['team'][:15],
                row['player_name'][:20],
                str(row.get('position', ''))[:3],
                str(int(row['minutes_played'])),
                f"{row['rating_num']:.1f}",
                str(int(row['birth_year_direct'])),
                str(row['liga'])[:12]
            ])
        
        tabla = Table(tabla_data, colWidths=[1.3*inch, 1.5*inch, 0.4*inch, 0.4*inch, 0.5*inch, 0.7*inch, 1.0*inch])
        
        # Aplicar gradiente a columna de rating
        base_style = [
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_DORADO),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GRIS),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]
        
        # Gradiente en columna rating (índice 4)
        # 7.5 = naranja, medio = verde, máximo = verde claro con texto negro
        ratings = [float(tabla_data[i][4]) for i in range(1, len(tabla_data))]
        if ratings:
            min_r, max_r = min(ratings), max(ratings)
            for i, r in enumerate(ratings, start=1):
                # Normalizar entre 0 y 1
                if max_r > min_r:
                    norm = (r - min_r) / (max_r - min_r)
                else:
                    norm = 1.0
                
                # Gradiente: 0 (min/7.5) = naranja, 0.5 (medio) = verde, 1.0 (max) = verde claro
                if norm < 0.5:
                    # De naranja a verde
                    factor = norm * 2  # 0 a 1
                    red = int(255 - (255 - 34) * factor)
                    green = int(165 + (139 - 165) * factor)
                    blue = int(0 + (34 - 0) * factor)
                else:
                    # De verde a verde claro
                    factor = (norm - 0.5) * 2  # 0 a 1
                    red = int(34 + (144 - 34) * factor)
                    green = int(139 + (238 - 139) * factor)
                    blue = int(34 + (144 - 34) * factor)
                
                bg = colors.HexColor(f'#{red:02x}{green:02x}{blue:02x}')
                base_style.append(('BACKGROUND', (4, i), (4, i), bg))
                
                # Texto negro solo para los valores más altos (verde claro)
                if norm >= 0.75:
                    base_style.append(('TEXTCOLOR', (4, i), (4, i), colors.black))
                else:
                    base_style.append(('TEXTCOLOR', (4, i), (4, i), colors.white))
        
        tabla.setStyle(TableStyle(base_style))
        story.append(tabla)
        story.append(Spacer(1, 0.3*inch))
    
    def create_anexo_acumulado_18_21(self, story, df_all):
        """ANEXO IV: Acumulado jugadores 18-21 años (nacidos 2005-2008)"""
        
        story.append(PageBreak())
        story.append(Paragraph("<b>ANEXO IV: ACUMULADO JUGADORES 18-21 AÑOS</b>", self.title_style))
        story.append(Spacer(1, 0.3*inch))
        
        explicacion_style = ParagraphStyle('Explicacion', parent=self.normal_style, fontSize=10, spaceAfter=15)
        story.append(Paragraph(
            "<b>Criterios de selección:</b><br/>"
            "• Jugadores nacidos entre 2005 y 2008 (18-21 años)<br/>"
            "• Rating promedio ≥ 7.0 (SofaScore)<br/>"
            "• Mínimo 2 partidos jugados<br/>"
            "• Datos obtenidos directamente de SofaScore API",
            explicacion_style
        ))
        story.append(Spacer(1, 0.2*inch))
        
        # Cargar ratings acumulados de SofaScore
        ratings_path = os.path.join(DATA_DIR, 'ratings_acumulados_sofascore.json')
        if not os.path.exists(ratings_path):
            story.append(Paragraph("<i>No se encontraron datos de ratings acumulados de SofaScore</i>", self.normal_style))
            return
        
        with open(ratings_path, 'r', encoding='utf-8') as f:
            ratings_data = json.load(f)
        
        # Convertir a DataFrame
        ratings_list = []
        for player_id, data in ratings_data.items():
            ratings_list.append({
                'player_id': int(player_id),
                'player_name': data['player_name'],
                'liga': data['liga'],
                'rating_promedio': data['rating_promedio'],
                'partidos_total': data['partidos_total']
            })
        
        df_ratings = pd.DataFrame(ratings_list)
        
        # Obtener información adicional de jugadores (equipo, fecha nacimiento, birth_year)
        df_players = df_all[['player_id', 'player_name', 'team', 'date_of_birth', 'birth_year_direct']].drop_duplicates('player_id')
        
        # Merge ratings con info de jugadores
        df = pd.merge(df_ratings, df_players, on='player_id', how='left', suffixes=('', '_extra'))
        df['team_name'] = df['team'].fillna('N/A')
        df['fecha_nacimiento'] = df['date_of_birth'].fillna('N/A')
        
        # Filtrar solo jugadores 18-21 años (nacidos 2005-2008)
        df = df[(df['birth_year_direct'] >= 2005) & (df['birth_year_direct'] <= 2008)]
        
        # Filtrar: rating >= 7.0 y mínimo 2 partidos
        df = df[
            (df['rating_promedio'] >= 7.0) & (df['partidos_total'] >= 2)
        ].sort_values('rating_promedio', ascending=False).reset_index(drop=True)
        
        if len(df) == 0:
            story.append(Paragraph("<i>No hay jugadores 18-21 años que cumplan los criterios</i>", self.normal_style))
            return
        
        tabla_data = [['Nombre', 'Fecha Nac.', 'Equipo', 'Liga', 'Rating', 'Partidos']]
        
        for _, row in df.iterrows():
            tabla_data.append([
                row['player_name'],
                str(row['fecha_nacimiento'])[:10],
                row['team_name'],
                str(row['liga'])[:12],
                f"{row['rating_promedio']:.2f}",
                str(int(row['partidos_total']))
            ])
        
        tabla = Table(tabla_data, colWidths=[2.0*inch, 0.9*inch, 1.5*inch, 1.1*inch, 0.6*inch, 0.7*inch])
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_DORADO),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (2, 1), (2, -1), 'LEFT'),
            ('ALIGN', (3, 1), (3, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GRIS),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ]))
        
        # Resaltar TOP 3
        for i in range(1, min(4, len(tabla_data))):
            tabla.setStyle(TableStyle([
                ('BACKGROUND', (0, i), (-1, i), COLOR_DORADO_CLARO),
            ]))
        
        story.append(tabla)
        story.append(Spacer(1, 0.3*inch))

    def create_anexo_reap_primera_b_metro(self, story):
        """ANEXO III: Jugadores con mayor REAP - Primera B Metro"""
        
        story.append(PageBreak())
        story.append(Paragraph("<b>ANEXO III: JUGADORES CON MAYOR REAP - PRIMERA B METRO</b>", self.title_style))
        story.append(Spacer(1, 0.3*inch))
        
        explicacion_style = ParagraphStyle('Explicacion', parent=self.normal_style, fontSize=10, spaceAfter=15)
        story.append(Paragraph(
            "<b>Criterios de selección:</b><br/>"
            "• Jugadores U23 de Primera B Metro<br/>"
            "• REAP (Rendimiento Esperado Ajustado por Potencial) ≥ 1.29<br/>"
            "• Jornada 3 - 09/03/2026<br/>"
            "• Ordenados por REAP descendente",
            explicacion_style
        ))
        story.append(Spacer(1, 0.2*inch))
        
        # Cargar datos JSON
        json_path = os.path.join(DATA_DIR, 'jugadores_jornada_primerabmetro_reap.json')
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            story.append(Paragraph(f"<i>Error al cargar datos: {str(e)}</i>", self.normal_style))
            return
        
        jugadores = data.get('jugadores_destacados', [])
        
        if len(jugadores) == 0:
            story.append(Paragraph("<i>No hay jugadores que cumplan los criterios</i>", self.normal_style))
            return
        
        # Crear tabla
        tabla_data = [['#', 'Nombre', 'Equipo', 'Pos', 'Edad', 'REAP', 'ELO', 'Pot', 'VM (M€)', 'Contrato']]
        
        for idx, j in enumerate(jugadores, 1):
            # Formatear valor de mercado
            vm = j.get('valor_mercado_millones', 0)
            vm_str = f"{vm:.3f}" if vm else "-"
            
            # Formatear contrato
            contrato = j.get('fin_contrato', '')
            if contrato and contrato != 'null':
                try:
                    contrato_str = contrato.split('-')[0]  # Solo año
                except:
                    contrato_str = "-"
            else:
                contrato_str = "-"
            
            tabla_data.append([
                str(idx),
                j.get('nombre', ''),
                j.get('equipo', ''),
                j.get('posicion', ''),
                str(j.get('edad', '')),
                f"{j.get('reap', 0):.2f}",
                str(j.get('elo', '')),
                str(j.get('potencial', '')),
                vm_str,
                contrato_str
            ])
        
        # Crear tabla con estilo
        tabla = Table(tabla_data, colWidths=[
            0.3*inch,  # #
            1.5*inch,  # Nombre
            1.3*inch,  # Equipo
            0.5*inch,  # Pos
            0.5*inch,  # Edad
            0.6*inch,  # REAP
            0.5*inch,  # ELO
            0.5*inch,  # Pot
            0.7*inch,  # VM
            0.7*inch   # Contrato
        ])
        
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_DORADO),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GRIS),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_GRIS_CLARO]),
        ]))
        
        # Resaltar TOP 3
        for i in range(1, min(4, len(tabla_data))):
            tabla.setStyle(TableStyle([
                ('BACKGROUND', (0, i), (-1, i), COLOR_DORADO_CLARO),
            ]))
        
        story.append(tabla)
        story.append(Spacer(1, 0.3*inch))
        
        # Añadir estadísticas
        stats = data.get('estadisticas', {})
        if stats:
            stats_style = ParagraphStyle('Stats', parent=self.normal_style, fontSize=9, textColor=COLOR_GRIS_OSCURO)
            story.append(Paragraph(
                f"<b>Estadísticas:</b> REAP promedio: {stats.get('reap_promedio', 0):.2f} | "
                f"ELO promedio: {stats.get('elo_promedio', 0):.0f} | "
                f"Potencial promedio: {stats.get('potencial_promedio', 0):.0f} | "
                f"Edad promedio: {stats.get('edad_promedio', 0):.1f} años",
                stats_style
            ))

    def generar_insight(self, partido, jugadores_u23):
        """Override para usar descripción de ChatGPT si existe, sino usar la automática"""
        
        # Intentar obtener descripción de ChatGPT del partido
        match_id = partido.get('match_id')
        
        # Cargar descripciones de ChatGPT si no están cargadas
        if not hasattr(self, '_descripciones_chatgpt'):
            descripciones_path = os.path.join(DATA_DIR, 'descripciones_partidos.json')
            if os.path.exists(descripciones_path):
                with open(descripciones_path, 'r', encoding='utf-8') as f:
                    self._descripciones_chatgpt = json.load(f)
            else:
                self._descripciones_chatgpt = {}
        
        # Si existe descripción de ChatGPT, usarla
        descripcion_chatgpt = self._descripciones_chatgpt.get(str(match_id), '')
        if descripcion_chatgpt:
            return descripcion_chatgpt
        
        # Si no, usar la función automática del padre
        return super().generar_insight(partido, jugadores_u23)
    
    def create_partido_section(self, story, partido, jugadores_u23, logos_df, fotos_df, match_info, ranking, categoria):
        """Override para mostrar REAP en vez de rating para Primera B Metro"""
        
        elements = []
        liga = partido.get('liga', '')
        es_primera_b_metro = 'Primera B Met' in liga
        
        # Si es Primera B Metro, copiar y modificar DataFrame
        if es_primera_b_metro:
            jugadores_u23 = jugadores_u23.copy()
            if 'reap' in jugadores_u23.columns:
                jugadores_u23['rating'] = jugadores_u23['reap']
        
        # Título del partido
        titulo = f"#{ranking}. {partido['partido']} - {partido['liga']} - {categoria}"
        elements.append(Paragraph(f"<b>{titulo}</b>", self.match_title_style))
        elements.append(Spacer(1, 0.08*inch))
        
        # Insight del partido
        insight_text = self.generar_insight(partido, jugadores_u23)
        insight_style = ParagraphStyle(
            'Insight',
            parent=self.normal_style,
            fontSize=9,
            leftIndent=0.2*inch,
            rightIndent=0.2*inch,
            spaceBefore=5,
            spaceAfter=10,
            leading=12,
            borderPadding=8,
            borderColor=COLOR_DORADO
        )
        insight_para = Paragraph(f"💡 <b>¿Por qué ver este partido?</b><br/>{insight_text}", insight_style)
        elements.append(insight_para)
        elements.append(Spacer(1, 0.1*inch))
        
        # Título de sección de jugadores
        titulo_jugadores = ParagraphStyle(
            'TituloJugadores',
            parent=self.normal_style,
            fontSize=9,
            fontName='Helvetica-Bold',
            textColor=COLOR_NEGRO,
            spaceAfter=3
        )
        elements.append(Paragraph(f"<b>JUGADORES U23 ({len(jugadores_u23)} jugadores)</b>", titulo_jugadores))
        elements.append(Spacer(1, 0.03*inch))
        
        # Agrupar por equipo
        equipos_u23 = jugadores_u23.groupby('team')
        
        for equipo, df_equipo in equipos_u23:
            # Logo del equipo
            logo_path = self.get_logo_path(equipo, logos_df)
            if logo_path and os.path.exists(logo_path):
                try:
                    logo_img = Image(logo_path, width=0.3*inch, height=0.3*inch, mask='auto')
                    equipo_title_data = [[logo_img, Paragraph(f"<b>{equipo}</b>", self.match_title_style)]]
                    equipo_title_table = Table(equipo_title_data, colWidths=[0.4*inch, 5*inch])
                    equipo_title_table.setStyle(TableStyle([
                        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                        ('ALIGN', (1, 0), (1, 0), 'LEFT'),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('LEFTPADDING', (0, 0), (-1, -1), 0),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                        ('TOPPADDING', (0, 0), (-1, -1), 0),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
                    ]))
                    elements.append(equipo_title_table)
                except:
                    elements.append(Paragraph(f"<b>{equipo}</b>", self.match_title_style))
            else:
                elements.append(Paragraph(f"<b>{equipo}</b>", self.match_title_style))
            
            elements.append(HRFlowable(width="100%", thickness=1, color=COLOR_NEGRO, spaceBefore=3, spaceAfter=5))
            
            # Tabla de jugadores - CAMBIAR ENCABEZADO SEGÚN LIGA
            if es_primera_b_metro:
                jugadores_data = [['Dorsal', 'Nombre', 'Pos', 'Min', 'REAP', 'Año Nac.']]
            else:
                jugadores_data = [['Dorsal', 'Nombre', 'Pos', 'Min', 'Rating', 'Fecha Nac.']]
            
            df_equipo_sorted = df_equipo.sort_values('minutes_played', ascending=False)
            
            for _, jugador in df_equipo_sorted.iterrows():
                dorsal = str(int(jugador['shirt_number'])) if pd.notna(jugador.get('shirt_number')) else 'N/A'
                nombre_jugador = jugador['player_name'][:25]
                nombre_cell = Paragraph(nombre_jugador, self.normal_style)
                
                pos_original = jugador['position'] if pd.notna(jugador['position']) else 'N/A'
                pos_map = {'G': 'POR', 'D': 'DEF', 'M': 'MED', 'F': 'DEL'}
                pos = pos_map.get(pos_original, pos_original)
                
                minutos = str(int(jugador['minutes_played']))
                
                # Rating/REAP
                if pd.notna(jugador['rating']) and jugador['rating'] != '':
                    rating_str = f"{jugador['rating']:.2f}" if es_primera_b_metro else f"{jugador['rating']:.1f}"
                    rating_cell = Paragraph(rating_str, self.normal_style)
                else:
                    rating_cell = Paragraph('N/A', self.normal_style)
                
                # Fecha de nacimiento
                if es_primera_b_metro:
                    # Solo año para Primera B Metro
                    fecha_nac = 'N/A'
                    if 'birth_year' in jugador and pd.notna(jugador['birth_year']):
                        fecha_nac = str(int(jugador['birth_year']))
                    elif 'date_of_birth' in jugador and pd.notna(jugador['date_of_birth']):
                        dob_str = str(jugador['date_of_birth'])
                        if '/' in dob_str:
                            fecha_nac = dob_str.split('/')[-1]
                        elif '-' in dob_str:
                            fecha_nac = dob_str.split('-')[0]
                else:
                    # Fecha completa para otras ligas
                    fecha_nac = 'N/A'
                    if 'date_of_birth' in jugador and pd.notna(jugador['date_of_birth']):
                        fecha_nac = str(jugador['date_of_birth'])
                
                jugadores_data.append([dorsal, nombre_cell, pos, minutos, rating_cell, fecha_nac])
            
            jugadores_table = Table(jugadores_data, colWidths=[0.4*inch, 1.8*inch, 0.4*inch, 0.35*inch, 0.45*inch, 0.75*inch])
            
            table_style = [
                ('BACKGROUND', (0, 0), (-1, 0), COLOR_DORADO),
                ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_NEGRO),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 7),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GRIS),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_GRIS_CLARO]),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ]
            
            jugadores_table.setStyle(TableStyle(table_style))
            elements.append(jugadores_table)
            elements.append(Spacer(1, 0.15*inch))
        
        # Añadir todo al story
        for element in elements:
            story.append(element)
        
        story.append(Spacer(1, 0.2*inch))

    def _build_partido_dict(self, ranking_row):
        """Convierte una fila del ranking a dict compatible con create_partido_section"""
        partido_str = str(ranking_row['partido'])
        parts = partido_str.split(' vs ')
        return {
            'match_id': ranking_row['match_id'],
            'equipo_local': parts[0] if len(parts) >= 2 else partido_str,
            'equipo_visitante': parts[1] if len(parts) >= 2 else '',
            'partido': partido_str,
            'liga': ranking_row['liga'],
            'round': ranking_row.get('round', 1),
            'num_u23': ranking_row['n_u23'],
            'z_score': ranking_row.get('z_score', 0),
            'score': ranking_row['mps'],
        }

    def generate_pdf(self, output_filename=None, use_brasil_data=False):
        """Genera el PDF completo de Ronda 17"""

        if output_filename is None:
            output_filename = os.path.join(PDF_DIR, 'desglose_detallado_IDV_ronda18.pdf')

        print("\n" + "="*70)
        if use_brasil_data:
            print("GENERANDO PDF — BRASIL + COLOMBIA + ARGENTINA")
        else:
            print("GENERANDO PDF — RONDA 18 (02 MAR - 08 MAR 2026)")
        print("="*70)

        # ── Cargar ranking MPS ──
        if use_brasil_data:
            # Usar datos de RONDA_02-08_03_26
            ranking_path = os.path.join(DATA_DIR, 'PARTIDOS_COMPACTO_CON_MPS.csv')
            jugadores_path = os.path.join(DATA_DIR, 'jugadores_completo_con_pbm.csv')
            LOGOS_DIR_ACT = LOGOS_DIR
        else:
            ranking_path = os.path.join(DATA_DIR, 'PARTIDOS_COMPACTO_CON_MPS.csv')
            jugadores_path = os.path.join(DATA_DIR, 'jugadores_completo_con_pbm.csv')
            LOGOS_DIR_ACT = LOGOS_DIR
            
        print(f"\n📂 Cargando ranking: {ranking_path}")
        ranking = pd.read_csv(ranking_path)
        
        if use_brasil_data:
            # Usar percentil_zscore si existe, si no usar percentil_mps (compatibilidad)
            if 'percentil_zscore' in ranking.columns:
                ranking['percentil'] = ranking['percentil_zscore']
            elif 'percentil_mps' in ranking.columns:
                ranking['percentil'] = ranking['percentil_mps']
            # No filtrar por formula_usada - todos los partidos compiten juntos
            
        print(f"   {len(ranking)} partidos en ranking")

        # ── Cargar datos de jugadores (ambas fuentes) ──
        print("\n📂 Cargando datos de jugadores...")

        if use_brasil_data:
            # Cargar datos de Brasil + Colombia + Argentina
            df_all = pd.read_csv(jugadores_path)
            df_all['birth_year_direct'] = df_all['birth_year']
            # Mantener date_of_birth del CSV (ya viene en formato dd/mm/yyyy)
            
            # Asegurar columnas necesarias
            if 'equipo_local' not in df_all.columns:
                df_all['equipo_local'] = ''
            if 'equipo_visitante' not in df_all.columns:
                df_all['equipo_visitante'] = ''
            if 'round' not in df_all.columns:
                df_all['round'] = 1
            if 'shirt_number' not in df_all.columns:
                df_all['shirt_number'] = np.nan
            if 'home_away' not in df_all.columns:
                df_all['home_away'] = ''
            if 'opponent' not in df_all.columns:
                df_all['opponent'] = ''
            if 'is_substitute' not in df_all.columns:
                df_all['is_substitute'] = False
                
            print(f"   Brasil data: {len(df_all)} registros, {df_all['match_id'].nunique()} partidos")
        else:
            # Fuente 1: SofaScore
            df_f1 = pd.read_csv(os.path.join(EXTRACCION_DIR, 'ronda18_completo.csv'))
            df_f1['birth_year_direct'] = df_f1['date_of_birth'].apply(parse_birth_year)
            df_f1['equipo_local'] = df_f1.apply(
                lambda r: r['team'] if r.get('home_away') == 'home' else r.get('opponent', ''), axis=1
            )
            df_f1['equipo_visitante'] = df_f1.apply(
                lambda r: r['team'] if r.get('home_away') == 'away' else r.get('opponent', ''), axis=1
            )
            print(f"   Fuente 1 (SofaScore): {len(df_f1)} registros, {df_f1['match_id'].nunique()} partidos")

            # Fuente 2: BeSoccer
            besoccer_path = os.path.join(EXTRACCION_DIR, 'primera_b_met_jornada2.csv')
            if os.path.exists(besoccer_path):
                df_bs = pd.read_csv(besoccer_path)
                df_f2 = normalize_besoccer(df_bs, 'Primera B Met')
                print(f"   Fuente 2 (BeSoccer): {len(df_f2)} registros, {df_f2['match_id'].nunique()} partidos")
            else:
                df_f2 = pd.DataFrame()
                print("   ⚠️ Fuente 2 no encontrada")

            # Unificar
            unified_cols = ['match_id', 'player_name', 'position', 'is_substitute', 'date_of_birth',
                            'birth_year_direct', 'is_u23', 'team', 'opponent', 'home_away',
                            'minutes_played', 'rating', 'liga', 'round',
                            'equipo_local', 'equipo_visitante']

            for col in unified_cols:
                if col not in df_f1.columns:
                    df_f1[col] = np.nan

            dfs = [df_f1[unified_cols]]
            if not df_f2.empty:
                dfs.append(df_f2)
            df_all = pd.concat(dfs, ignore_index=True)

            # Add shirt_number if missing (needed by base class)
            if 'shirt_number' not in df_all.columns:
                # Try to get from original F1
                if 'shirt_number' in df_f1.columns:
                    df_all = df_all.merge(
                        df_f1[['match_id', 'player_name', 'team', 'shirt_number']].drop_duplicates(),
                        on=['match_id', 'player_name', 'team'], how='left', suffixes=('', '_orig')
                    )
                else:
                    df_all['shirt_number'] = np.nan

            # For BeSoccer, try to get dorsal
            if not df_f2.empty and 'dorsal' in df_bs.columns:
                bs_dorsal = df_bs[['partido_id', 'nombre', 'equipo', 'dorsal']].copy()
                bs_dorsal.columns = ['match_id', 'player_name', 'team', 'shirt_number_bs']
                df_all = df_all.merge(bs_dorsal, on=['match_id', 'player_name', 'team'], how='left')
                mask = df_all['shirt_number'].isna() & df_all['shirt_number_bs'].notna()
                df_all.loc[mask, 'shirt_number'] = df_all.loc[mask, 'shirt_number_bs']
                df_all.drop(columns=['shirt_number_bs'], inplace=True, errors='ignore')

            print(f"\n📊 Dataset combinado: {len(df_all)} registros, {df_all['match_id'].nunique()} partidos")

        # ── Selección de partidos ──
        # Asegurar que existe columna percentil
        if 'percentil' not in ranking.columns:
            ranking['percentil'] = ranking['z_score'].rank(pct=True) * 100
        
        # Filtrar partidos por z-score: TOP (> 1.5) y MUY ALTA (0.5-1.5)
        partidos_prioritarios = ranking[ranking['z_score_grupo'] >= 0.5].copy()
        
        # NO HAY ANEXOS - todos los partidos compiten en el mismo ranking
        anexos_alta = pd.DataFrame()
        anexos_extra = pd.DataFrame()

        # Contar TODOS los partidos por prioridad del ranking completo
        categorias_count = {
            'PRIORIDAD TOP': len(ranking[ranking['z_score_grupo'] > 1.5]),
            'PRIORIDAD MUY ALTA': len(ranking[(ranking['z_score_grupo'] >= 0.5) & (ranking['z_score_grupo'] <= 1.5)]),
            'PRIORIDAD ALTA': len(ranking[(ranking['z_score_grupo'] >= 0.0) & (ranking['z_score_grupo'] < 0.5)]),
            'PRIORIDAD MEDIA': len(ranking[ranking['z_score_grupo'] < 0.0])
        }
        
        # Categorizar partidos para mostrar en PDF (solo TOP y MUY ALTA)
        categorias = {
            'PRIORIDAD TOP': [],
            'PRIORIDAD MUY ALTA': [],
            'PRIORIDAD ALTA': [],
            'PRIORIDAD MEDIA': []
        }

        for _, row in partidos_prioritarios.iterrows():
            z_score = row['z_score_grupo']
            p = self._build_partido_dict(row)
            if z_score > 1.5:
                categorias['PRIORIDAD TOP'].append(p)
            elif z_score >= 0.5:
                categorias['PRIORIDAD MUY ALTA'].append(p)

        total_sel = sum(categorias_count.values())
        print(f"\n📊 Selección final ({total_sel} partidos):")
        for cat, count in categorias_count.items():
            print(f"  • {cat}: {count}")

        # ── Crear PDF ──
        doc = SimpleDocTemplate(output_filename, pagesize=A4,
                                rightMargin=0.75*inch, leftMargin=0.75*inch,
                                topMargin=inch, bottomMargin=0.75*inch)

        story = []

        # Portada
        print("\n📄 Generando portada...")
        self.create_portada_manual(story)

        # Índice
        print("📄 Generando índice...")
        self.create_indice(story, categorias_count)

        # Resumen ejecutivo
        print("📄 Generando resumen ejecutivo...")
        self.create_resumen_ejecutivo(story, ranking, categorias_count)

        # Cargar descripciones de ChatGPT
        descripciones_path = os.path.join(DATA_DIR, 'descripciones_partidos.json')
        descripciones_chatgpt = {}
        if os.path.exists(descripciones_path):
            with open(descripciones_path, 'r', encoding='utf-8') as f:
                descripciones_chatgpt = json.load(f)
            print(f"\n📂 Descripciones ChatGPT cargadas: {len(descripciones_chatgpt)} partidos")
        else:
            print("\n⚠️  No se encontraron descripciones de ChatGPT")
        
        # Cargar logos
        if use_brasil_data:
            logos_mapping_path = os.path.join(LOGOS_DIR_ACT, 'team_logos_mapping.csv')
            if os.path.exists(logos_mapping_path):
                df_logos = pd.read_csv(logos_mapping_path)
                print(f"📂 Logos cargados: {len(df_logos)} equipos")
            else:
                df_logos = pd.DataFrame(columns=['team_name', 'logo_path'])
                print("⚠️  No se encontró mapping de logos")
        else:
            df_logos = pd.DataFrame(columns=['team_name', 'logo_path'])
        
        df_fotos = pd.DataFrame(columns=['player_id', 'foto_path'])

        # Partidos principales por categoría
        ranking_global = 1

        for categoria, partidos_cat in categorias.items():
            if not partidos_cat:
                continue

            print(f"\n📄 Generando {categoria} ({len(partidos_cat)} partidos)...")

            for partido in partidos_cat:
                match_id = partido['match_id']

                jugadores_u23 = df_all[
                    (df_all['match_id'] == match_id) &
                    (df_all['is_u23'] == True) &
                    (df_all['minutes_played'] > 60)
                ].copy()

                # Obtener descripción de ChatGPT si existe
                descripcion_chatgpt = descripciones_chatgpt.get(str(match_id), '')

                match_info = pd.Series({
                    'match_id': match_id,
                    'resultado': 'N/A',
                    'fecha': 'Febrero 2026',
                    'round': int(partido['round']),
                    'descripcion_chatgpt': descripcion_chatgpt
                })

                if len(jugadores_u23) > 0:
                    self.create_partido_section(story, partido, jugadores_u23, df_logos, df_fotos, match_info, ranking_global, categoria)
                    ranking_global += 1

        # ANEXOS DE PARTIDOS - ELIMINADO
        # Ya no hay sección separada de ANEXOS de partidos
        # Todos los partidos se clasifican como TOP, MUY ALTA, ALTA, MEDIA o BAJA
        # (Código comentado - se mantienen solo los anexos de jugadores)

        # ANEXO I: Jugadores U23 destacados
        print("\n📄 Generando ANEXO I: Jugadores U23 destacados...")
        self.create_anexo_u23_destacados(story, df_all)

        # ANEXO II: Mejores jugadores 18-21 años de la jornada
        print("\n📄 Generando ANEXO II: Mejores jugadores 18-21 años...")
        self.create_anexo_mejores_18_21(story, df_all)

        # ANEXO III: Jugadores con mayor REAP - Primera B Metro
        print("\n📄 Generando ANEXO III: Jugadores con mayor REAP - Primera B Metro...")
        self.create_anexo_reap_primera_b_metro(story)
        
        # ANEXOS ACUMULADOS ELIMINADOS (jugadores de equipos U20 no disponibles en SofaScore)
        # - ANEXO Acumulado U23 (eliminado)
        # - ANEXO Acumulado 18-21 (eliminado)

        # Construir PDF
        print("\n📝 Construyendo PDF...")
        doc.build(story, onFirstPage=self.add_header_footer, onLaterPages=self.add_header_footer)

        print(f"\n{'='*70}")
        print(f"✅ PDF generado: {output_filename}")
        print(f"{'='*70}\n")

        return output_filename


if __name__ == "__main__":
    # Change to project dir for logo/image resolution
    os.chdir(str(PROJECT_ROOT))

    generator = PDFGeneratorRonda17()
    
    # Generar PDF de Brasil + Colombia + Argentina
    pdf_file = generator.generate_pdf(
        output_filename=os.path.join(PDF_DIR, 'desglose_detallado_IDV_ronda_02-08_mar.pdf'),
        use_brasil_data=True
    )

    print(f"\n📄 Archivo: {pdf_file}")
    print(f"📊 Contenido:")
    print(f"  • 52 partidos analizados (Brasil, Colombia, Argentina)")
    print(f"  • 6 TOP + 8 MUY ALTA partidos principales")
    print(f"  • 96 escudos de equipos")
    print(f"  • ANEXO I: Jugadores U23 destacados (rating ≥ 7.5)")
    print(f"  • ANEXO II: Mejores jugadores 18-21 años")
    print(f"  • ANEXO III: Jugadores con mayor REAP - Primera B Metro")
