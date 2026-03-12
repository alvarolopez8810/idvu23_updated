#!/usr/bin/env python3
"""
Genera PDF separado con ANEXOS ACUMULADOS U23 & U21
- ANEXO I: Acumulado U23 (rating ≥ 7.1, min 2 partidos)
- ANEXO II: Acumulado U21 (rating ≥ 7.1, min 2 partidos)
- ANEXO III: TOP jugadores más jóvenes (rating > 7, ordenados de menor a mayor edad)
"""

import pandas as pd
import json
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfgen import canvas
from datetime import datetime

# Paths
BASE_DIR = Path('/Users/alvarolopezmolina/Desktop/Python/IDV_project/RONDA_02-08_03_26')
DATA_DIR = BASE_DIR / 'data'
PDF_DIR = BASE_DIR

# Colores
COLOR_NEGRO = colors.HexColor('#1a1a1a')
COLOR_GRIS = colors.HexColor('#666666')
COLOR_GRIS_CLARO = colors.HexColor('#f5f5f5')
COLOR_DORADO = colors.HexColor('#FFD700')
COLOR_DORADO_CLARO = colors.HexColor('#FFF8DC')

# Filtros
MIN_PARTIDOS = 3
MIN_PARTIDOS_JOVENES = 1
RATING_THRESHOLD_U23 = 7.1
RATING_THRESHOLD_U21 = 7.1
RATING_THRESHOLD_JOVENES = 7.0
YEAR_MIN_JOVENES = 2006
YEAR_MAX_JOVENES = 2011


class PDFAnexosAcumulados:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_styles()
        
    def setup_styles(self):
        """Configura estilos personalizados"""
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=COLOR_NEGRO,
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        self.subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=12,
            textColor=COLOR_GRIS,
            spaceAfter=15,
            alignment=TA_CENTER,
            fontName='Helvetica'
        )
        
        self.normal_style = ParagraphStyle(
            'CustomNormal',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=COLOR_NEGRO,
            spaceAfter=10,
            fontName='Helvetica'
        )
    
    def add_header_footer(self, canvas, doc):
        """Añade header y footer a cada página"""
        canvas.saveState()
        
        # Header
        canvas.setFont('Helvetica-Bold', 10)
        canvas.setFillColor(COLOR_NEGRO)
        canvas.drawString(inch, A4[1] - 0.5*inch, "ANEXOS ACUMULADOS U23 & U21")
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(COLOR_GRIS)
        canvas.drawString(inch, A4[1] - 0.65*inch, "Semana 02-03-2026 a 08-03-2026")
        
        # Footer
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(COLOR_GRIS)
        page_num = canvas.getPageNumber()
        canvas.drawRightString(A4[0] - inch, 0.5*inch, f"Página {page_num}")
        
        canvas.restoreState()
    
    def create_portada(self, story):
        """Crea la portada del documento con estilo profesional"""
        from reportlab.platypus.flowables import HRFlowable
        from reportlab.platypus import Image, Table
        
        # Header con logo IDV
        header_data = []
        logo_path = Path('/Users/alvarolopezmolina/Desktop/Python/IDV_project/independientedelvalle.png')
        
        if logo_path.exists():
            try:
                logo_idv = Image(str(logo_path), width=1.5*inch, height=1.5*inch, mask='auto')
                temporada_style = ParagraphStyle(
                    'TemporadaPortada',
                    parent=self.subtitle_style,
                    fontSize=16,
                    textColor=COLOR_NEGRO,
                    alignment=TA_CENTER,
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
        
        # Título principal
        titulo_principal = ParagraphStyle(
            'TituloPrincipal',
            parent=self.title_style,
            fontSize=40,
            textColor=COLOR_NEGRO,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            spaceAfter=10,
            leading=48
        )
        story.append(Paragraph("<b>INDEPENDIENTE DEL VALLE</b>", titulo_principal))
        
        subtitulo_depto = ParagraphStyle(
            'SubtituloDepto',
            parent=self.subtitle_style,
            fontSize=16,
            textColor=COLOR_GRIS,
            alignment=TA_CENTER,
            fontName='Helvetica',
            spaceAfter=40
        )
        story.append(Paragraph("DEPARTAMENTO DE SCOUTING", subtitulo_depto))
        
        story.append(HRFlowable(width="50%", thickness=3, color=COLOR_DORADO, spaceBefore=10, spaceAfter=10))
        story.append(Spacer(1, 0.6*inch))
        
        # Título del documento
        titulo_campeonato = ParagraphStyle(
            'TituloCampeonato',
            parent=self.title_style,
            fontSize=22,
            textColor=COLOR_NEGRO,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            spaceAfter=10,
            leading=26
        )
        story.append(Paragraph("<b>ANEXOS ACUMULADOS U23 & U21</b>", titulo_campeonato))
        
        subtitulo_rondas = ParagraphStyle(
            'SubtituloRondas',
            parent=self.normal_style,
            fontSize=14,
            textColor=COLOR_GRIS,
            alignment=TA_CENTER,
            fontName='Helvetica',
            spaceAfter=40
        )
        story.append(Paragraph("SEMANA 02-03-2026 - 08-03-2026", subtitulo_rondas))
        
        story.append(Spacer(1, 0.4*inch))
        
        # Logo Álvaro
        logo_alvaro = Path('/Users/alvarolopezmolina/Desktop/Python/IDV_project/Logo_Alvaro_resized.png')
        if logo_alvaro.exists():
            try:
                logo_img = Image(str(logo_alvaro), width=1.5*inch, height=0.6*inch, mask='auto')
                logos_container = Table([[logo_img]], colWidths=[6*inch])
                logos_container.setStyle(TableStyle([('ALIGN', (0, 0), (0, 0), 'CENTER')]))
                story.append(logos_container)
            except:
                pass
        
        story.append(PageBreak())
    
    def create_anexo_u23(self, story, df):
        """ANEXO I: Acumulado U23 (rating ≥ 7.1)"""
        story.append(Paragraph("<b>ANEXO I: ACUMULADO JUGADORES U23</b>", self.title_style))
        story.append(Spacer(1, 0.3*inch))
        
        # Filtrar U23 (nacidos 2003 o posterior) con rating >= 7.1 y min 3 partidos
        df_u23 = df[
            (df['birth_year'] >= 2003) & 
            (df['rating_promedio'] >= RATING_THRESHOLD_U23) &
            (df['partidos_total'] >= MIN_PARTIDOS)
        ].copy()
        
        df_u23 = df_u23.sort_values('rating_promedio', ascending=False)
        
        # Explicación
        explicacion_style = ParagraphStyle('Explicacion', parent=self.normal_style, fontSize=10, spaceAfter=15)
        story.append(Paragraph(
            f"<b>Criterios de selección:</b><br/>"
            f"• Jugadores nacidos en 2003 o posterior (U23)<br/>"
            f"• Rating acumulado ≥ {RATING_THRESHOLD_U23}<br/>"
            f"• Mínimo {MIN_PARTIDOS} partidos jugados<br/>"
            f"• Ordenados por rating descendente<br/>"
            f"<b>Total: {len(df_u23)} jugadores</b>",
            explicacion_style
        ))
        story.append(Spacer(1, 0.2*inch))
        
        # Tabla
        tabla_data = [['#', 'Jugador', 'Equipo', 'Liga', 'Año Nac.', 'Rating', 'Partidos']]
        
        for idx, (_, row) in enumerate(df_u23.iterrows(), 1):
            tabla_data.append([
                str(idx),
                str(row['player_name'])[:25],
                str(row['team_name'])[:20],
                str(row['liga'])[:15],
                str(row['birth_year']),
                f"{row['rating_promedio']:.2f}",
                str(row['partidos_total'])
            ])
        
        tabla = Table(tabla_data, colWidths=[0.4*inch, 1.8*inch, 1.5*inch, 1.2*inch, 0.7*inch, 0.6*inch, 0.7*inch])
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_NEGRO),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GRIS),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_GRIS_CLARO]),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        # Resaltar TOP 3
        if len(df_u23) >= 3:
            tabla.setStyle(TableStyle([
                ('BACKGROUND', (0, 1), (-1, 3), COLOR_DORADO_CLARO),
            ]))
        
        story.append(tabla)
        story.append(Spacer(1, 0.3*inch))
        story.append(PageBreak())
    
    def create_anexo_u21(self, story, df):
        """ANEXO II: Acumulado U21 (rating ≥ 7.1)"""
        story.append(Paragraph("<b>ANEXO II: ACUMULADO JUGADORES U21</b>", self.title_style))
        story.append(Spacer(1, 0.3*inch))
        
        # Filtrar U21 (nacidos 2005 o posterior) con rating >= 7.1 y min 3 partidos
        df_u21 = df[
            (df['birth_year'] >= 2005) & 
            (df['rating_promedio'] >= RATING_THRESHOLD_U21) &
            (df['partidos_total'] >= MIN_PARTIDOS)
        ].copy()
        
        df_u21 = df_u21.sort_values('rating_promedio', ascending=False)
        
        # Explicación
        explicacion_style = ParagraphStyle('Explicacion', parent=self.normal_style, fontSize=10, spaceAfter=15)
        story.append(Paragraph(
            f"<b>Criterios de selección:</b><br/>"
            f"• Jugadores nacidos en 2005 o posterior (U21)<br/>"
            f"• Rating acumulado ≥ {RATING_THRESHOLD_U21}<br/>"
            f"• Mínimo {MIN_PARTIDOS} partidos jugados<br/>"
            f"• Ordenados por rating descendente<br/>"
            f"<b>Total: {len(df_u21)} jugadores</b>",
            explicacion_style
        ))
        story.append(Spacer(1, 0.2*inch))
        
        # Tabla
        tabla_data = [['#', 'Jugador', 'Equipo', 'Liga', 'Año Nac.', 'Rating', 'Partidos']]
        
        for idx, (_, row) in enumerate(df_u21.iterrows(), 1):
            tabla_data.append([
                str(idx),
                str(row['player_name'])[:25],
                str(row['team_name'])[:20],
                str(row['liga'])[:15],
                str(row['birth_year']),
                f"{row['rating_promedio']:.2f}",
                str(row['partidos_total'])
            ])
        
        tabla = Table(tabla_data, colWidths=[0.4*inch, 1.8*inch, 1.5*inch, 1.2*inch, 0.7*inch, 0.6*inch, 0.7*inch])
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_NEGRO),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GRIS),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_GRIS_CLARO]),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        # Resaltar TOP 3
        if len(df_u21) >= 3:
            tabla.setStyle(TableStyle([
                ('BACKGROUND', (0, 1), (-1, 3), COLOR_DORADO_CLARO),
            ]))
        
        story.append(tabla)
        story.append(Spacer(1, 0.3*inch))
        story.append(PageBreak())
    
    def create_anexo_jovenes(self, story, df):
        """ANEXO III: TOP jugadores más jóvenes (rating > 7, nacidos 2006-2011, min 1 partido)"""
        story.append(Paragraph("<b>ANEXO III: TOP JUGADORES MÁS JÓVENES</b>", self.title_style))
        story.append(Spacer(1, 0.3*inch))
        
        # Filtrar jugadores nacidos 2006-2011 con rating > 7 y min 1 partido
        df_jovenes = df[
            (df['birth_year'] >= YEAR_MIN_JOVENES) &
            (df['birth_year'] <= YEAR_MAX_JOVENES) &
            (df['rating_promedio'] > RATING_THRESHOLD_JOVENES) &
            (df['partidos_total'] >= MIN_PARTIDOS_JOVENES)
        ].copy()
        
        # Ordenar de MENOR a MAYOR edad (año de nacimiento descendente = más jóvenes primero)
        df_jovenes = df_jovenes.sort_values(['birth_year', 'rating_promedio'], ascending=[False, False])
        
        # Calcular edad
        current_year = 2026
        df_jovenes['edad'] = current_year - df_jovenes['birth_year']
        
        # Explicación
        explicacion_style = ParagraphStyle('Explicacion', parent=self.normal_style, fontSize=10, spaceAfter=15)
        story.append(Paragraph(
            f"<b>Criterios de selección:</b><br/>"
            f"• Jugadores nacidos entre {YEAR_MIN_JOVENES} y {YEAR_MAX_JOVENES}<br/>"
            f"• Rating acumulado > {RATING_THRESHOLD_JOVENES}<br/>"
            f"• Mínimo {MIN_PARTIDOS_JOVENES} partido jugado<br/>"
            f"• Ordenados de MENOR a MAYOR edad<br/>"
            f"<b>Total: {len(df_jovenes)} jugadores</b>",
            explicacion_style
        ))
        story.append(Spacer(1, 0.2*inch))
        
        # Tabla
        tabla_data = [['#', 'Jugador', 'Equipo', 'Liga', 'Edad', 'Año Nac.', 'Rating', 'Partidos']]
        
        for idx, (_, row) in enumerate(df_jovenes.iterrows(), 1):
            tabla_data.append([
                str(idx),
                str(row['player_name'])[:25],
                str(row['team_name'])[:18],
                str(row['liga'])[:12],
                str(int(row['edad'])),
                str(row['birth_year']),
                f"{row['rating_promedio']:.2f}",
                str(row['partidos_total'])
            ])
        
        tabla = Table(tabla_data, colWidths=[0.4*inch, 1.6*inch, 1.4*inch, 1.0*inch, 0.5*inch, 0.7*inch, 0.6*inch, 0.7*inch])
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_NEGRO),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GRIS),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_GRIS_CLARO]),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        # Resaltar TOP 5 más jóvenes
        if len(df_jovenes) >= 5:
            tabla.setStyle(TableStyle([
                ('BACKGROUND', (0, 1), (-1, 5), COLOR_DORADO_CLARO),
            ]))
        
        story.append(tabla)
        story.append(Spacer(1, 0.3*inch))
        story.append(PageBreak())
    
    def create_anexo_puntuaciones_altas(self, story, ratings_file):
        """ANEXO IV: Puntuaciones más altas - Record por jornada U23"""
        story.append(Paragraph("<b>ANEXO IV: PUNTUACIONES MÁS ALTAS - RECORD POR JORNADA</b>", self.title_style))
        story.append(Spacer(1, 0.3*inch))
        
        # Cargar datos de ratings por partido
        import json
        
        if not ratings_file.exists():
            story.append(Paragraph("No se encontraron datos de ratings por partido.", self.normal_style))
            return
        
        with open(ratings_file, 'r', encoding='utf-8') as f:
            all_ratings = json.load(f)
        
        # Filtrar solo U23 y ordenar por rating descendente
        u23_ratings = [r for r in all_ratings if r.get('birth_year', 0) >= 2003]
        u23_ratings.sort(key=lambda x: x.get('rating', 0), reverse=True)
        
        # Tomar top 50
        top_ratings = u23_ratings[:50]
        
        # Explicación
        explicacion_style = ParagraphStyle('Explicacion', parent=self.normal_style, fontSize=10, spaceAfter=15)
        story.append(Paragraph(
            f"<b>Criterios de selección:</b><br/>"
            f"• Jugadores U23 (nacidos 2003 o posterior)<br/>"
            f"• TOP 50 puntuaciones individuales más altas de la jornada<br/>"
            f"• Ordenados por rating descendente<br/>"
            f"<b>Total: {len(top_ratings)} registros</b>",
            explicacion_style
        ))
        story.append(Spacer(1, 0.2*inch))
        
        # Tabla
        tabla_data = [['#', 'Rating', 'Partido', 'Jugador', 'Fecha Nac.', 'Equipo']]
        
        for idx, record in enumerate(top_ratings, 1):
            rating = record.get('rating', 0)
            match_info = record.get('match', 'N/A')
            player_name = record.get('player_name', 'N/A')[:25]
            birth_date = record.get('date_of_birth', 'N/A')
            team_name = record.get('team_name', 'N/A')[:20]
            
            tabla_data.append([
                str(idx),
                f"{rating:.2f}" if isinstance(rating, (int, float)) else str(rating),
                str(match_info)[:30],
                player_name,
                birth_date,
                team_name
            ])
        
        tabla = Table(tabla_data, colWidths=[0.3*inch, 0.6*inch, 2.0*inch, 1.5*inch, 0.9*inch, 1.5*inch])
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_NEGRO),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GRIS),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_GRIS_CLARO]),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        # Resaltar TOP 10
        if len(top_ratings) >= 10:
            tabla.setStyle(TableStyle([
                ('BACKGROUND', (0, 1), (-1, 10), COLOR_DORADO_CLARO),
            ]))
        
        story.append(tabla)
        story.append(Spacer(1, 0.3*inch))
    
    def generar_pdf(self, df, output_filename, ratings_file=None):
        """Genera el PDF completo"""
        doc = SimpleDocTemplate(
            output_filename,
            pagesize=A4,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=inch,
            bottomMargin=0.75*inch
        )
        
        story = []
        
        # Portada
        print("\n📄 Generando portada...")
        self.create_portada(story)
        
        # ANEXO I: U23
        print("📄 Generando ANEXO I: Acumulado U23...")
        self.create_anexo_u23(story, df)
        
        # ANEXO II: U21
        print("📄 Generando ANEXO II: Acumulado U21...")
        self.create_anexo_u21(story, df)
        
        # ANEXO III: Más jóvenes
        print("📄 Generando ANEXO III: TOP Jugadores Más Jóvenes...")
        self.create_anexo_jovenes(story, df)
        
        # ANEXO IV: Puntuaciones más altas
        if ratings_file and ratings_file.exists():
            print("📄 Generando ANEXO IV: Puntuaciones Más Altas - Record por Jornada...")
            self.create_anexo_puntuaciones_altas(story, ratings_file)
        else:
            print("⚠️  Saltando ANEXO IV: No se encontró archivo de ratings por partido")
        
        # Construir PDF
        print("\n📝 Construyendo PDF...")
        doc.build(story, onFirstPage=self.add_header_footer, onLaterPages=self.add_header_footer)
        
        print(f"\n{'='*70}")
        print(f"✅ PDF generado: {output_filename}")
        print(f"{'='*70}\n")
        
        return output_filename


def main():
    print("\n" + "="*70)
    print("GENERANDO PDF - ANEXOS ACUMULADOS U23 & U21")
    print("="*70)
    
    # Cargar datos
    data_file = DATA_DIR / 'u23_acumulado_completo.csv'
    
    if not data_file.exists():
        print(f"❌ Error: No se encontró el archivo {data_file}")
        return
    
    print(f"\n📂 Cargando datos: {data_file}")
    df = pd.read_csv(data_file)
    print(f"  ✓ {len(df)} jugadores cargados")
    
    # Buscar archivo de ratings por partido
    ratings_file = DATA_DIR / 'u23_ratings_por_partido.json'
    
    # Generar PDF
    pdf_generator = PDFAnexosAcumulados()
    output_file = PDF_DIR / 'ANEXOS_ACUMULADOS_U23_U21.pdf'
    
    pdf_generator.generar_pdf(df, str(output_file), ratings_file)
    
    # Estadísticas
    df_u23 = df[(df['birth_year'] >= 2003) & (df['rating_promedio'] >= RATING_THRESHOLD_U23) & (df['partidos_total'] >= MIN_PARTIDOS)]
    df_u21 = df[(df['birth_year'] >= 2005) & (df['rating_promedio'] >= RATING_THRESHOLD_U21) & (df['partidos_total'] >= MIN_PARTIDOS)]
    df_jovenes = df[(df['rating_promedio'] > RATING_THRESHOLD_JOVENES) & (df['partidos_total'] >= MIN_PARTIDOS)]
    
    print(f"\n📊 Contenido:")
    print(f"  • ANEXO I: {len(df_u23)} jugadores U23 (rating ≥ {RATING_THRESHOLD_U23}, min {MIN_PARTIDOS} partidos)")
    print(f"  • ANEXO II: {len(df_u21)} jugadores U21 (rating ≥ {RATING_THRESHOLD_U21}, min {MIN_PARTIDOS} partidos)")
    print(f"  • ANEXO III: {len(df_jovenes)} jugadores más jóvenes (rating > {RATING_THRESHOLD_JOVENES})")
    
    if ratings_file.exists():
        with open(ratings_file, 'r', encoding='utf-8') as f:
            all_ratings = json.load(f)
        u23_ratings = [r for r in all_ratings if r.get('birth_year', 0) >= 2003]
        print(f"  • ANEXO IV: TOP 50 puntuaciones más altas ({len(u23_ratings)} registros U23 totales)")
    else:
        print(f"  • ANEXO IV: No disponible (falta archivo de ratings por partido)")
    
    print()


if __name__ == '__main__':
    main()
