"""
Generador de PDF Final IDV - Personalizado
Con portada IDV, header, estrellas para ratings ≥7.0, resultado/fecha/ronda
Colores: Negro, Gris, Dorado
"""

import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from datetime import datetime
import os

# Colores personalizados
COLOR_NEGRO = colors.HexColor('#000000')
COLOR_GRIS_OSCURO = colors.HexColor('#2c2c2c')
COLOR_GRIS = colors.HexColor('#666666')
COLOR_GRIS_CLARO = colors.HexColor('#cccccc')
COLOR_DORADO = colors.HexColor('#D4AF37')
COLOR_DORADO_CLARO = colors.HexColor('#F4E4B7')

class PDFGeneratorIDV:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.width, self.height = A4
        
        # Estilos personalizados con colores IDV
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=20,
            textColor=COLOR_NEGRO,
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        self.subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=COLOR_GRIS_OSCURO,
            spaceAfter=15,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold'
        )
        
        self.match_title_style = ParagraphStyle(
            'MatchTitle',
            parent=self.styles['Heading3'],
            fontSize=13,
            textColor=COLOR_NEGRO,
            spaceAfter=10,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold'
        )
        
        self.normal_style = ParagraphStyle(
            'CustomNormal',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=COLOR_GRIS_OSCURO,
            spaceAfter=6,
            fontName='Helvetica'
        )
    
    def add_header_footer(self, canvas, doc):
        """Añade header personalizado y pie de página (excepto en portada e índice)"""
        canvas.saveState()
        
        # No añadir header/footer en páginas 1 (portada) y 2 (índice)
        if doc.page <= 2:
            canvas.restoreState()
            return
        
        # Header: Logo a la izquierda y TEMPORADA 2026 a la derecha
        if os.path.exists('independientedelvalle.png'):
            try:
                canvas.drawImage('independientedelvalle.png', 0.75*inch, self.height - 0.55*inch, 
                                width=0.5*inch, height=0.5*inch, 
                                preserveAspectRatio=True, mask='auto')
            except:
                pass
        
        # Texto TEMPORADA 2026 a la derecha
        canvas.setFont('Helvetica-Bold', 10)
        canvas.setFillColor(COLOR_NEGRO)
        canvas.drawRightString(self.width - 0.75*inch, self.height - 0.5*inch, "TEMPORADA 2026")
        
        # Línea separadora debajo del header
        canvas.setStrokeColor(COLOR_DORADO)
        canvas.setLineWidth(1.5)
        canvas.line(0.75*inch, self.height - 0.7*inch, 
                   self.width - 0.75*inch, self.height - 0.7*inch)
        
        # Pie de página
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(COLOR_GRIS)
        canvas.drawString(inch, 0.5 * inch, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        canvas.drawRightString(self.width - inch, 0.5 * inch, f"Pág. {doc.page}")
        
        canvas.restoreState()
    
    def create_portada_from_pdf(self, story, tipo_pdf="detallado"):
        """Crea portada usando imagen de PDF existente
        
        Args:
            tipo_pdf: 'resumen' o 'detallado'
        """
        # Nota: ReportLab no puede insertar PDFs directamente en platypus
        # Usaremos la portada generada manualmente
        self.create_portada_manual(story, tipo_pdf)
    
    def create_portada_manual(self, story, tipo_pdf="detallado"):
        """Crea la portada visual y persuasiva IDV"""
        # Header de portada con logo y temporada
        header_data = []
        
        # Logo IDV a la izquierda (más grande en portada)
        if os.path.exists('independientedelvalle.png'):
            try:
                logo_idv = Image('independientedelvalle.png', width=1.5*inch, height=1.5*inch, mask='auto')
                temporada_style = ParagraphStyle(
                    'TemporadaPortada',
                    parent=self.subtitle_style,
                    fontSize=16,
                    textColor=COLOR_NEGRO,
                    alignment=TA_RIGHT,
                    fontName='Helvetica-Bold'
                )
                header_data.append([logo_idv, Paragraph("<b>TEMPORADA 2026</b>", temporada_style)])
            except:
                header_data.append([Paragraph("", self.normal_style), Paragraph("<b>TEMPORADA 2026</b>", self.subtitle_style)])
        else:
            header_data.append([Paragraph("", self.normal_style), Paragraph("<b>TEMPORADA 2026</b>", self.subtitle_style)])
        
        header_table = Table(header_data, colWidths=[3*inch, 3*inch])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 0.15*inch))
        
        # Línea separadora dorada horizontal
        from reportlab.platypus import HRFlowable
        story.append(HRFlowable(width="100%", thickness=2, color=COLOR_DORADO, spaceBefore=0, spaceAfter=0))
        
        story.append(Spacer(1, 0.8*inch))
        
        # INDEPENDIENTE DEL VALLE - Principal (destacado, en negrita)
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
        
        # DEPARTAMENTO DE SCOUTING - Secundario (más pequeño, estilo normal)
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
        
        # Línea decorativa dorada (más gruesa y visible)
        story.append(HRFlowable(width="50%", thickness=3, color=COLOR_DORADO, spaceBefore=10, spaceAfter=10))
        
        story.append(Spacer(1, 0.6*inch))
        
        # Título según tipo de PDF
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
        
        # Cambiar texto según tipo de PDF
        if tipo_pdf == "resumen":
            # Para resumen: PLANIFICACIÓN DE PARTIDOS + RESUMEN EJECUTIVO
            story.append(Paragraph("<b>PLANIFICACIÓN DE PARTIDOS</b>", titulo_campeonato))
            story.append(Spacer(1, 0.1*inch))
            
            titulo_resumen = ParagraphStyle(
                'TituloResumen',
                parent=self.title_style,
                fontSize=18,
                textColor=COLOR_NEGRO,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold',
                spaceAfter=15
            )
            story.append(Paragraph("<b>RESUMEN EJECUTIVO</b>", titulo_resumen))
        else:
            # Para detallado: DESGLOSE DETALLADO DE U23
            story.append(Paragraph("<b>DESGLOSE DETALLADO DE U23</b>", titulo_campeonato))
        
        # SEMANA 04-02 - 09-02 de 2026 - Pequeño (estilo normal)
        subtitulo_rondas = ParagraphStyle(
            'SubtituloRondas',
            parent=self.normal_style,
            fontSize=14,
            textColor=COLOR_GRIS_OSCURO,
            alignment=TA_CENTER,
            fontName='Helvetica',
            spaceAfter=40
        )
        story.append(Paragraph("SEMANA 04-02-2026 - 09-02-2026", subtitulo_rondas))
        
        story.append(Spacer(1, 0.4*inch))
        
        # Logos inferiores - solo Álvaro y SDC (más pequeños y con ancho limitado)
        logos_row = []
        
        # Logo Álvaro - con ancho máximo limitado
        if os.path.exists('Logo_Alvaro_resized.png'):
            try:
                logos_row.append(Image('Logo_Alvaro_resized.png', width=1.5*inch, height=0.6*inch, mask='auto'))
            except Exception as e:
                print(f"⚠️  Error cargando Logo_Alvaro_resized.png: {e}")
        
        # Logo SDC - con ancho máximo limitado
        if os.path.exists('sdc_resized.png'):
            try:
                logos_row.append(Image('sdc_resized.png', width=1.2*inch, height=0.5*inch, mask='auto'))
            except Exception as e:
                print(f"⚠️  Error cargando sdc_resized.png: {e}")
        
        if len(logos_row) >= 2:
            # Crear tabla con logos centrados - anchos automáticos para acomodar proporciones
            logos_table = Table([logos_row])
            logos_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ]))
            
            # Centrar la tabla de logos
            logos_container = Table([[logos_table]], colWidths=[6*inch])
            logos_container.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ]))
            story.append(logos_container)
        
        story.append(PageBreak())
    
    def create_indice(self, story, categorias_count, df_partidos=None):
        """Crea índice del documento con lista detallada de partidos"""
        import pandas as pd
        
        # Título del índice
        indice_title = ParagraphStyle(
            'IndiceTitulo',
            parent=self.title_style,
            fontSize=20,
            textColor=COLOR_NEGRO,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            spaceAfter=20
        )
        
        story.append(Paragraph("<b>ÍNDICE</b>", indice_title))
        story.append(Spacer(1, 0.5*inch))
        
        # Línea separadora
        line_table = Table([['_' * 100]], colWidths=[6*inch])
        line_table.setStyle(TableStyle([
            ('TEXTCOLOR', (0, 0), (-1, -1), COLOR_DORADO),
            ('FONTSIZE', (0, 0), (-1, -1), 1),
            ('LINEABOVE', (0, 0), (-1, -1), 2, COLOR_DORADO),
        ]))
        story.append(line_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Estilos para el índice
        indice_style = ParagraphStyle('Indice', parent=self.normal_style, fontSize=10, leading=14)
        indice_item_bold_style = ParagraphStyle('IndiceItemBold', parent=indice_style, fontName='Helvetica-Bold', fontSize=11)
        indice_partido_style = ParagraphStyle('IndicePartido', parent=indice_style, fontSize=9, leftIndent=20, leading=13)
        
        # Secciones principales - SOLO categorías, sin lista de partidos
        story.append(Paragraph(f"<b>Resumen Ejecutivo</b> .................... pág. 3-4", indice_item_bold_style))
        story.append(Spacer(1, 0.1*inch))
        
        # Categorías principales
        prioridad_top = categorias_count.get('PRIORIDAD TOP', 0)
        story.append(Paragraph(f"<b>🔴 Prioridad TOP</b> ({prioridad_top} partidos) .................... pág. 5", indice_item_bold_style))
        
        prioridad_muy_alta = categorias_count.get('PRIORIDAD MUY ALTA', 0)
        story.append(Paragraph(f"<b>🟠 Prioridad MUY ALTA</b> ({prioridad_muy_alta} partidos) .................... pág. 13", indice_item_bold_style))
        
        prioridad_alta = categorias_count.get('PRIORIDAD ALTA', 0)
        story.append(Paragraph(f"<b>🟡 Prioridad ALTA</b> ({prioridad_alta} partidos) .................... pág. 17", indice_item_bold_style))
        
        prioridad_media = categorias_count.get('PRIORIDAD MEDIA', 0)
        story.append(Paragraph(f"<b>🟢 Prioridad MEDIA</b> ({prioridad_media} partidos) .................... pág. 29", indice_item_bold_style))
        
        story.append(Paragraph(f"<b>📋 ANEXOS</b> (2 partidos) .................... pág. 33", indice_item_bold_style))
        
        story.append(Spacer(1, 0.5*inch))
        story.append(PageBreak())
    
    def create_resumen(self, story, categorias_count, partidos_reporte=[]):
        """Crea página de resumen"""
        story.append(Paragraph("RESUMEN EJECUTIVO", self.title_style))
        story.append(Spacer(1, 0.3*inch))
        
        # Tabla de resumen con colores IDV
        resumen_data = [['Categoría', 'Partidos', 'Descripción']]
        
        categorias_info = [
            ('🔴 PRIORIDAD TOP', categorias_count.get('PRIORIDAD TOP', 0), 'Z-Score ≥ 1.5 - Partido obligatorio'),
            ('🟠 PRIORIDAD MUY ALTA', categorias_count.get('PRIORIDAD MUY ALTA', 0), 'Z-Score 1.0-1.5 - Alto valor'),
            ('🟡 PRIORIDAD ALTA', categorias_count.get('PRIORIDAD ALTA', 0), 'Z-Score 0.5-1.0 - Seguimiento'),
            ('🟢 PRIORIDAD MEDIA', categorias_count.get('PRIORIDAD MEDIA', 0), 'Z-Score 0-0.5 - Contextual'),
            ('📋 ANEXOS', 2, 'Partidos adicionales con Z-Score positivo')
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
        
        # Explicación del sistema
        explicacion = """
        <b>Sistema de Scoring:</b><br/>
        • <b>Factor A</b> (Densidad U23): Número de jugadores U23 en el partido<br/>
        • <b>Factor B</b> (Minutos): Minutos promedio jugados por U23<br/>
        • <b>Factor C</b> (Contexto): Importancia del partido según liga y posiciones<br/>
        • <b>Multiplicador Ratings</b>: Bonus basado en calidad individual de jugadores<br/>
        • <b>Z-Score</b>: Medida estadística que indica cuánto se desvía un partido de la media<br/>
        <br/>
        <b>Ligas analizadas:</b> 🇧🇷 Brasil (Paulista A1, Paulista A2, Carioca, Paranaense, Gaúcho, Baiano) + 🇨🇴 Colombia 2 Div + 🇦🇷 Copa Argentina
        """
        
        story.append(Paragraph(explicacion, self.normal_style))
        story.append(Spacer(1, 0.3*inch))
        
        # Tabla resumen de todos los partidos
        if partidos_reporte:
            titulo_tabla_style = ParagraphStyle(
                'TituloTabla',
                parent=self.normal_style,
                fontSize=12,
                textColor=COLOR_NEGRO,
                fontName='Helvetica-Bold',
                spaceAfter=6
            )
            story.append(Paragraph("<b>TABLA RESUMEN DE PARTIDOS</b>", titulo_tabla_style))
            story.append(Spacer(1, 0.1*inch))
            
            # Preparar datos para la tabla
            tabla_data = [['', '#', 'Equipo Local', 'Equipo Visitante', 'Fecha', 'U23', 'Liga', 'Prioridad']]
            
            # Ordenar partidos por z_score y tomar los seleccionados
            partidos_ordenados = sorted(partidos_reporte, key=lambda x: x['z_score'], reverse=True)
            
            for i, partido in enumerate(partidos_ordenados, 1):
                # Determinar prioridad
                z = partido['z_score']
                if z >= 1.5:
                    prioridad = 'TOP'
                    icono_path = 'advert.avif'
                elif z >= 1.0:
                    prioridad = 'MUY ALTA'
                    icono_path = 'estrella.png'
                elif z >= 0.5:
                    prioridad = 'ALTA'
                    icono_path = 'lupa.png'
                else:
                    prioridad = 'MEDIA'
                    icono_path = 'ok.jpg'
                
                # Cargar icono
                icono = ''
                if os.path.exists(icono_path):
                    try:
                        icono = Image(icono_path, width=0.15*inch, height=0.15*inch)
                    except:
                        icono = ''
                
                # Acortar nombres si son muy largos
                local = partido['equipo_local'][:18]
                visitante = partido['equipo_visitante'][:18]
                liga = partido['liga'][:12]
                
                # Fecha del partido
                fecha = partido.get('match_date', partido.get('fecha', ''))
                if pd.isna(fecha) or fecha == '' or fecha is None:
                    fecha = ''
                else:
                    fecha = str(fecha)[:10]
                
                tabla_data.append([
                    icono,
                    str(i),
                    local,
                    visitante,
                    fecha,
                    str(int(partido['num_u23'])),
                    liga,
                    prioridad
                ])
            
            # Crear tabla
            tabla_resumen = Table(tabla_data, colWidths=[0.25*inch, 0.25*inch, 1.15*inch, 1.15*inch, 0.6*inch, 0.3*inch, 0.85*inch, 0.7*inch])
            tabla_resumen.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), COLOR_NEGRO),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 7),
                ('FONTSIZE', (0, 1), (-1, -1), 6),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GRIS),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_GRIS_CLARO]),
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            
            story.append(tabla_resumen)
        
        story.append(Spacer(1, 0.3*inch))
    
    def create_contraportada(self, story, categorias_count):
        """Crea contraportada con iconos grandes y centrados - todo en una página"""
        story.append(Spacer(1, 0.8*inch))
        
        for i, (cat_name, count) in enumerate([('MUST WATCH', categorias_count['MUST WATCH']), 
                                                ('RECOMMEND', categorias_count['RECOMMEND']), 
                                                ('DESERVES A LOOK', categorias_count['DESERVES A LOOK'])]):
            # Icono muy grande y centrado
            icono_path = self.get_icono_categoria(cat_name)
            if icono_path:
                try:
                    icono_img = Image(icono_path, width=1.8*inch, height=1.8*inch)
                    icono_table = Table([[icono_img]], colWidths=[6*inch])
                    icono_table.setStyle(TableStyle([
                        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                        ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
                    ]))
                    story.append(icono_table)
                except:
                    pass
            
            story.append(Spacer(1, 0.15*inch))
            
            # Título más grande y centrado
            titulo_style = ParagraphStyle(
                'ContraportadaTitulo',
                parent=self.title_style,
                fontSize=28,
                textColor=COLOR_NEGRO,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )
            story.append(Paragraph(f"<b>{cat_name}</b>", titulo_style))
            story.append(Spacer(1, 0.08*inch))
            
            # Número de partidos centrado
            count_style = ParagraphStyle(
                'ContraportadaCount',
                parent=self.subtitle_style,
                fontSize=20,
                textColor=COLOR_DORADO,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )
            story.append(Paragraph(f"{count} {'partido' if count == 1 else 'partidos'}", count_style))
            
            # Espaciado entre categorías (menos en la última)
            if i < 2:
                story.append(Spacer(1, 0.6*inch))
        
        story.append(PageBreak())
    
    def get_logo_path(self, team_name, logos_df):
        """Obtiene la ruta del logo de un equipo"""
        import glob
        
        # Primero intentar desde el CSV de logos
        logo_row = logos_df[logos_df['team_name'] == team_name]
        if not logo_row.empty:
            logo_path = logo_row.iloc[0]['logo_path']
            # Verificar que logo_path sea un string válido y no NaN
            if pd.notna(logo_path) and isinstance(logo_path, str) and logo_path and os.path.exists(logo_path):
                return logo_path
        
        # Intentar búsqueda directa con nombre exacto
        direct_path = f"logos_equipos/{team_name}.png"
        if os.path.exists(direct_path):
            return direct_path
        
        # Normalizar nombre del equipo para búsqueda
        team_normalized = team_name.replace(' ', '_')
        
        # Buscar en carpeta logos_equipos (Brasil) - buscar por nombre parcial
        brasil_logos = glob.glob(f"logos_equipos/*{team_normalized}*.png")
        if brasil_logos:
            return brasil_logos[0]
        
        # Buscar en carpeta logos_equipos sin espacios
        brasil_logos = glob.glob(f"logos_equipos/{team_normalized}_*.png")
        if brasil_logos:
            return brasil_logos[0]
        
        # Buscar en carpeta Colombia por nombre
        colombia_logos = glob.glob(f"imagenes_colombia/equipos/*{team_normalized}*.png")
        if colombia_logos:
            return colombia_logos[0]
        
        # Buscar en todas las carpetas por coincidencia parcial
        all_logos = glob.glob("logos_equipos/*.png") + glob.glob("imagenes_colombia/equipos/*.png")
        for logo in all_logos:
            logo_lower = logo.lower()
            team_lower = team_name.lower().replace(' ', '_')
            if team_lower in logo_lower or team_name.lower().replace(' ', '') in logo_lower:
                return logo
        
        return None
    
    def get_foto_jugador(self, player_id, fotos_df):
        """Obtiene la foto de un jugador"""
        import glob
        
        # Primero intentar desde el CSV de fotos
        foto_row = fotos_df[fotos_df['player_id'] == player_id]
        if not foto_row.empty and os.path.exists(foto_row.iloc[0]['foto_path']):
            return foto_row.iloc[0]['foto_path']
        
        # Convertir player_id a string
        player_id_str = str(player_id)
        
        # Buscar en carpeta fotos_jugadores (Brasil) - por ID exacto
        foto_path = f"fotos_jugadores/{player_id_str}.png"
        if os.path.exists(foto_path):
            return foto_path
        
        # Buscar en carpeta fotos_jugadores (Brasil) - por ID con nombre
        brasil_fotos = glob.glob(f"fotos_jugadores/{player_id_str}_*.png")
        if brasil_fotos:
            return brasil_fotos[0]
        
        # Buscar en carpeta Colombia
        colombia_fotos = glob.glob(f"imagenes_colombia/jugadores/{player_id_str}_*.png")
        if colombia_fotos:
            return colombia_fotos[0]
        
        # Buscar en todas las carpetas por coincidencia de ID
        all_fotos = glob.glob("fotos_jugadores/*.png") + glob.glob("imagenes_colombia/jugadores/*.png")
        for foto in all_fotos:
            if player_id_str in foto:
                return foto
        
        return None
    
    def get_icono_categoria(self, categoria):
        """Obtiene el icono de la categoría"""
        iconos = {
            'MUST WATCH': 'advert.avif',
            'RECOMMEND': 'lupa.png',
            'DESERVES A LOOK': 'ok.jpg'
        }
        icono_path = iconos.get(categoria)
        if icono_path and os.path.exists(icono_path):
            return icono_path
        return None
    
    def generar_insight(self, partido, jugadores_u23):
        """Genera un comentario conciso (5-6 líneas) explicando por qué ver este partido"""
        
        # DATOS DEL PARTIDO
        equipo_local = partido['equipo_local']
        equipo_visitante = partido['equipo_visitante']
        nombre_liga = partido['liga']
        
        # Determinar contexto del partido
        round_num = partido.get('round', 0)
        if 'Quarterfinals' in str(round_num) or 'Cuartos' in str(round_num):
            contexto_partido = "cuartos de final"
        elif 'Semifinals' in str(round_num) or 'Semifinales' in str(round_num):
            contexto_partido = "semifinales"
        elif 'Final' in str(round_num):
            contexto_partido = "final"
        elif round_num >= 10:
            contexto_partido = f"jornada {round_num}"
        else:
            contexto_partido = f"fecha {round_num}"
        
        # DATOS U23
        total_u23 = len(jugadores_u23)
        jugadores_60min = len(jugadores_u23[jugadores_u23['minutes_played'] >= 60])
        minutos_promedio = int(jugadores_u23['minutes_played'].mean())
        
        # RENDIMIENTO
        jugadores_rating_8 = 0
        jugadores_rating_7 = 0
        nombres_rating_7 = []
        
        for _, j in jugadores_u23.iterrows():
            if pd.notna(j['rating']) and j['rating'] != '':
                try:
                    rating = float(j['rating'])
                    if rating >= 8.0:
                        jugadores_rating_8 += 1
                    elif rating >= 7.0:
                        jugadores_rating_7 += 1
                        nombres_rating_7.append(f"{j['player_name']} {rating:.1f}")
                except:
                    pass
        
        nombres_rating_7_str = ", ".join(nombres_rating_7[:2])
        
        # PERFIL EDAD U18
        total_u18 = 0
        nombres_u18_destacados = []
        
        for _, j in jugadores_u23.iterrows():
            if pd.notna(j.get('date_of_birth')):
                dob_str = str(j['date_of_birth'])
                try:
                    if '/' in dob_str:
                        year = int(dob_str.split('/')[-1])
                    elif '-' in dob_str:
                        year = int(dob_str.split('-')[0])
                    else:
                        continue
                    
                    if year >= 2006:
                        total_u18 += 1
                        if pd.notna(j['rating']) and j['rating'] != '':
                            try:
                                rating = float(j['rating'])
                                if rating >= 6.8:
                                    nombres_u18_destacados.append(f"{j['player_name']} ({year})")
                            except:
                                pass
                except:
                    pass
        
        porcentaje_u18 = int((total_u18 / total_u23 * 100)) if total_u23 > 0 else 0
        nombres_u18_destacados_str = ", ".join(nombres_u18_destacados[:2])
        
        # GENERAR COMENTARIO
        frase1 = f"Este encuentro de {contexto_partido} del {nombre_liga} destaca por su <b>alta densidad de jugadores jóvenes ({total_u23} U23)</b> con participación significativa: {jugadores_60min} jugadores superan los 60 minutos."
        
        if 'final' in contexto_partido.lower() or 'cuartos' in contexto_partido.lower():
            frase2 = "El contexto eliminatorio eleva la intensidad competitiva."
        else:
            frase2 = f"El contexto de {nombre_liga} ofrece un nivel competitivo adecuado para evaluación."
        
        if jugadores_rating_8 > 0:
            frase3 = f"Sobresalen <b>{jugadores_rating_8} jugadores con rating 8.0+</b> de alto rendimiento."
        elif jugadores_rating_7 > 0:
            if nombres_rating_7_str:
                frase3 = f"Sobresalen <b>{jugadores_rating_7} jugadores con rating 7.0+</b> ({nombres_rating_7_str})."
            else:
                frase3 = f"Sobresalen <b>{jugadores_rating_7} jugadores con rating 7.0+</b> de buen nivel."
        else:
            frase3 = f"Los jugadores muestran rendimiento sólido con minutos promedio de {minutos_promedio}'."
        
        if total_u18 > 0 and porcentaje_u18 >= 30:
            if nombres_u18_destacados_str:
                frase4 = f"El partido incluye <b>{total_u18} jugadores U18</b> ({porcentaje_u18}% del total), destacando {nombres_u18_destacados_str}, ofreciendo buena observación de perfiles con proyección en un escenario de alta exigencia."
            else:
                frase4 = f"El partido incluye <b>{total_u18} jugadores U18</b> ({porcentaje_u18}% del total), ofreciendo buena observación de perfiles con proyección en un escenario de alta exigencia."
        else:
            frase4 = f"La combinación de densidad ({total_u23} U23), tiempo de juego ({jugadores_60min} con 60+') y calidad individual lo convierte en un partido valioso para scouting."
        
        return f"{frase1} {frase2} {frase3} {frase4}"
    
    def create_partido_section(self, story, partido, jugadores_u23, logos_df, fotos_df, match_info, ranking, categoria):
        """Crea sección detallada de un partido"""
        
        elements = []
        
        # Título del partido sin icono
        # Título con Liga y Prioridad (sin número de U23)
        titulo = f"#{ranking}. {partido['partido']} - {partido['liga']} - {categoria}"
        elements.append(Paragraph(f"<b>{titulo}</b>", self.match_title_style))
        elements.append(Spacer(1, 0.08*inch))
        
        # Título de sección de jugadores (más compacto)
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
            # Crear título del equipo con logo sin background
            logo_path = self.get_logo_path(equipo, logos_df)
            if logo_path and os.path.exists(logo_path):
                try:
                    # Logo pequeño + nombre del equipo (sin background)
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
                        ('BACKGROUND', (0, 0), (-1, -1), colors.white),  # Fondo blanco explícito
                    ]))
                    elements.append(equipo_title_table)
                except:
                    elements.append(Paragraph(f"<b>{equipo}</b>", self.match_title_style))
            else:
                elements.append(Paragraph(f"<b>{equipo}</b>", self.match_title_style))
            
            # Línea separadora negra debajo del nombre del equipo
            from reportlab.platypus import HRFlowable
            elements.append(HRFlowable(width="100%", thickness=1, color=COLOR_NEGRO, spaceBefore=3, spaceAfter=5))
            
            # Tabla de jugadores con dorsal
            jugadores_data = [['Dorsal', 'Nombre', 'Pos', 'Min', 'Rating', 'Fecha Nac.']]
            
            df_equipo_sorted = df_equipo.sort_values('minutes_played', ascending=False)
            
            for _, jugador in df_equipo_sorted.iterrows():
                # Dorsal/Jersey number
                dorsal = str(int(jugador['shirt_number'])) if pd.notna(jugador.get('shirt_number')) else 'N/A'
                
                # Nombre sin estrella
                nombre_jugador = jugador['player_name'][:25]
                nombre_cell = Paragraph(nombre_jugador, self.normal_style)
                
                # Verificar si tiene estrella (rating >= 7.0)
                rating_val = None
                tiene_estrella = False
                if pd.notna(jugador['rating']) and jugador['rating'] != '':
                    try:
                        rating_val = float(jugador['rating'])
                        if rating_val >= 7.0:
                            tiene_estrella = True
                    except:
                        pass
                
                # Convertir posición: G→POR, D→DEF, M→MED, F→DEL
                pos_original = jugador['position'] if pd.notna(jugador['position']) else 'N/A'
                pos_map = {'G': 'POR', 'D': 'DEF', 'M': 'MED', 'F': 'DEL'}
                pos = pos_map.get(pos_original, pos_original)
                
                minutos = str(int(jugador['minutes_played']))
                
                # Rating con estrella si rating >= 7.0
                if pd.notna(jugador['rating']) and jugador['rating'] != '':
                    rating_str = f"{jugador['rating']:.1f}"
                    if tiene_estrella and os.path.exists('estrella.png'):
                        try:
                            estrella_img = Image('estrella.png', width=0.1*inch, height=0.1*inch)
                            rating_cell = Table([[Paragraph(rating_str, self.normal_style), estrella_img]], 
                                              colWidths=[0.3*inch, 0.12*inch])
                            rating_cell.setStyle(TableStyle([
                                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                                ('TOPPADDING', (0, 0), (-1, -1), 0),
                                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                            ]))
                        except:
                            rating_cell = Paragraph(rating_str, self.normal_style)
                    else:
                        rating_cell = Paragraph(rating_str, self.normal_style)
                else:
                    rating_cell = Paragraph('N/A', self.normal_style)
                
                # DOB - Para Primera B Metro mostrar solo año, para otros mostrar fecha completa
                fecha_nac = 'N/A'
                liga = partido.get('liga', '')
                
                # Para Primera B Metro, mostrar solo año de nacimiento
                if 'Primera B Met' in liga:
                    if 'birth_year' in jugador and pd.notna(jugador['birth_year']):
                        fecha_nac = str(int(jugador['birth_year']))
                    elif 'date_of_birth' in jugador and pd.notna(jugador['date_of_birth']):
                        dob_str = str(jugador['date_of_birth'])
                        # Extraer año de la fecha
                        if '/' in dob_str:
                            fecha_nac = dob_str.split('/')[-1]  # Último elemento es el año
                        elif '-' in dob_str:
                            fecha_nac = dob_str.split('-')[0]  # Primer elemento es el año
                else:
                    # Para otras ligas, mostrar fecha completa
                    if 'date_of_birth' in jugador and pd.notna(jugador['date_of_birth']):
                        dob_str = str(jugador['date_of_birth'])
                        # Si es formato DD/MM/YYYY o YYYY-MM-DD, usar directamente
                        if '/' in dob_str or '-' in dob_str:
                            fecha_nac = dob_str
                        # Si es timestamp, convertir
                        elif dob_str.isdigit():
                            try:
                                from datetime import datetime
                                fecha_nac = datetime.fromtimestamp(int(dob_str)).strftime('%d/%m/%Y')
                            except:
                                fecha_nac = 'N/A'
                    elif 'fecha_nacimiento' in jugador and pd.notna(jugador['fecha_nacimiento']):
                        fecha_nac = str(jugador['fecha_nacimiento'])
                
                jugadores_data.append([dorsal, nombre_cell, pos, minutos, rating_cell, fecha_nac])
            
            jugadores_table = Table(jugadores_data, colWidths=[0.4*inch, 1.8*inch, 0.4*inch, 0.35*inch, 0.45*inch, 0.75*inch])
            
            # Estilo con colores IDV - más compacto
            table_style = [
                ('BACKGROUND', (0, 0), (-1, 0), COLOR_DORADO),
                ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_NEGRO),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 6),
                ('FONTSIZE', (0, 1), (-1, -1), 5),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GRIS),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 1),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                ('LEFTPADDING', (0, 0), (-1, -1), 2),
                ('RIGHTPADDING', (0, 0), (-1, -1), 2),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.white])  # Todo blanco
            ]
            
            # NO resaltar filas con rating >= 7.0 para mantener fondo blanco
            # La estrella ya indica el rating destacado
            
            jugadores_table.setStyle(TableStyle(table_style))
            
            elements.append(jugadores_table)
            elements.append(Spacer(1, 0.03*inch))  # Espaciado reducido entre equipos
        
        elements.append(Spacer(1, 0.05*inch))
        
        # Añadir insight/comentario explicativo (más compacto)
        insight_text = self.generar_insight(partido, jugadores_u23)
        insight_style = ParagraphStyle(
            'InsightStyle',
            parent=self.normal_style,
            fontSize=8,
            textColor=COLOR_GRIS_OSCURO,
            leftIndent=0.2*inch,
            rightIndent=0.2*inch,
            spaceAfter=10,
            spaceBefore=5,
            backColor=COLOR_DORADO_CLARO,
            borderPadding=8,
            borderWidth=1,
            borderColor=COLOR_DORADO
        )
        
        insight_para = Paragraph(f"💡 <b>¿Por qué ver este partido?</b><br/>{insight_text}", insight_style)
        elements.append(insight_para)
        elements.append(Spacer(1, 0.1*inch))
        
        # Usar KeepTogether para mantener cada partido en una página
        from reportlab.platypus import KeepTogether
        try:
            story.append(KeepTogether(elements))
        except:
            # Si no cabe en una página, añadir normalmente
            for element in elements:
                story.append(element)
    
    def generate_pdf_detallado(self, output_filename="desglose_detallado_IDV.pdf"):
        """Genera el PDF detallado con todos los partidos"""
        print("\n" + "="*70)
        print("GENERANDO PDF DESGLOSE DETALLADO IDV - BRASIL + COLOMBIA")
        print("="*70)
        
        # Cargar datos
        print("\n📂 Cargando datos...")
        df_partidos = pd.read_csv('partidos_brasil_colombia_combinados.csv')
        df_lineups_brasil = pd.read_csv('todas_ligas_completo.csv', sep=';')
        df_lineups_colombia = pd.read_csv('primera_b_colombia_2025_round1.csv')
        
        # Intentar cargar logos y fotos (opcional)
        try:
            df_logos = pd.read_csv('equipos_logos.csv')
        except:
            df_logos = pd.DataFrame(columns=['team_name', 'logo_path'])
        
        try:
            df_fotos = pd.read_csv('jugadores_fotos.csv')
        except:
            df_fotos = pd.DataFrame(columns=['player_id', 'foto_path'])
        
        # Crear info de partidos (resultado, fecha, round)
        df_info = pd.DataFrame()
        for _, partido in df_partidos.iterrows():
            df_info = pd.concat([df_info, pd.DataFrame([{
                'match_id': partido['match_id'],
                'resultado': 'N/A',
                'fecha': 'Enero 2026',
                'round': int(partido['round'])
            }])], ignore_index=True)
        
        print(f"✓ {len(df_partidos)} partidos totales")
        print(f"✓ {len(df_lineups_brasil)} jugadores Brasil")
        print(f"✓ {len(df_lineups_colombia)} jugadores Colombia")
        
        # Categorizar con 4 prioridades
        categorias = {
            'PRIORIDAD TOP': [],
            'PRIORIDAD MUY ALTA': [],
            'PRIORIDAD ALTA': [],
            'PRIORIDAD MEDIA': []
        }
        
        for _, partido in df_partidos.iterrows():
            z = partido['z_score']
            if z >= 1.5:
                categorias['PRIORIDAD TOP'].append(partido)
            elif z >= 1.0:
                categorias['PRIORIDAD MUY ALTA'].append(partido)
            elif z >= 0.5:
                categorias['PRIORIDAD ALTA'].append(partido)
            elif z >= 0:
                categorias['PRIORIDAD MEDIA'].append(partido)
        
        # Ordenar partidos por categoría (sin límite para mostrar todos)
        for cat_name in categorias:
            categorias[cat_name] = sorted(categorias[cat_name], key=lambda x: x['z_score'], reverse=True)
        
        # Partidos para ANEXOS (excluir los que ya están en otras prioridades)
        partidos_anexos = df_partidos[(df_partidos['z_score'] < 0.5) & (df_partidos['num_u23'] > 9)].copy()
        
        # Obtener match_ids de partidos ya incluidos en prioridades
        match_ids_incluidos = set()
        for cat_partidos in categorias.values():
            for partido in cat_partidos:
                match_ids_incluidos.add(partido['match_id'])
        
        # Filtrar anexos para excluir partidos ya incluidos
        partidos_anexos = partidos_anexos[~partidos_anexos['match_id'].isin(match_ids_incluidos)]
        partidos_anexos = partidos_anexos.sort_values('num_u23', ascending=False)
        
        categorias_count = {k: len(v) for k, v in categorias.items()}
        categorias_count['ANEXOS'] = len(partidos_anexos)
        
        print(f"✓ {sum(categorias_count.values())} partidos en reporte")
        
        # Crear PDF
        doc = SimpleDocTemplate(output_filename, pagesize=A4,
                                rightMargin=0.75*inch, leftMargin=0.75*inch,
                                topMargin=inch, bottomMargin=0.75*inch)
        
        story = []
        
        # Portada
        print("📄 Generando portada IDV...")
        self.create_portada_from_pdf(story, tipo_pdf="detallado")
        
        # Índice
        print("📄 Generando índice...")
        self.create_indice(story, categorias_count)
        
        # NO incluir resumen ejecutivo en PDF detallado - ir directo al contenido
        print("📄 Saltando resumen ejecutivo (solo en PDF detallado)...")
        
        # Partidos por categoría
        ranking_global = 1
        
        for categoria, partidos_cat in categorias.items():
            if not partidos_cat:
                continue
            
            print(f"\n📄 Generando {categoria}...")
            
            # Título de categoría
            story.append(Paragraph(f"<b>{categoria}</b>", self.title_style))
            story.append(Spacer(1, 0.15*inch))
            
            for partido in partidos_cat:
                match_id = partido['match_id']
                liga = partido['liga']
                
                # Obtener info del partido
                match_info = df_info[df_info['match_id'] == match_id].iloc[0]
                
                # Obtener jugadores U23 según la liga
                if 'Colombia' in liga:
                    jugadores_u23 = df_lineups_colombia[
                        (df_lineups_colombia['match_id'] == match_id) & 
                        (df_lineups_colombia['is_u23'] == True) & 
                        (df_lineups_colombia['minutes_played'] > 0)
                    ].copy()
                else:
                    jugadores_u23 = df_lineups_brasil[
                        (df_lineups_brasil['match_id'] == match_id) & 
                        (df_lineups_brasil['is_u23'] == True) & 
                        (df_lineups_brasil['minutes_played'] > 0)
                    ].copy()
                
                if len(jugadores_u23) > 0:
                    self.create_partido_section(story, partido, jugadores_u23, df_logos, df_fotos, match_info, ranking_global, categoria)
                    ranking_global += 1
            
            story.append(PageBreak())
        
        # ANEXOS
        if len(partidos_anexos) > 0:
            print("\n📄 Generando ANEXOS...")
            story.append(Paragraph("<b>📋 ANEXOS</b>", self.title_style))
            story.append(Spacer(1, 0.1*inch))
            
            anexos_style = ParagraphStyle('Anexos', parent=self.normal_style, fontSize=10)
            story.append(Paragraph(
                "<b>Partidos con alto número de jugadores U23 pero Z-Score bajo</b><br/>"
                "Estos partidos destacan por tener más de 9 jugadores U23. El Z-Score bajo se debe principalmente "
                "a que los minutos promedio fueron reducidos (Factor B bajo), indicando que muchos jóvenes entraron "
                "como suplentes o jugaron poco tiempo. Sin embargo, la alta cantidad de U23 los hace interesantes para monitoreo.",
                anexos_style
            ))
            story.append(Spacer(1, 0.2*inch))
            
            for _, partido in partidos_anexos.iterrows():
                match_id = partido['match_id']
                liga = partido['liga']
                
                match_info = df_info[df_info['match_id'] == match_id].iloc[0]
                
                if 'Colombia' in liga:
                    jugadores_u23 = df_lineups_colombia[
                        (df_lineups_colombia['match_id'] == match_id) & 
                        (df_lineups_colombia['is_u23'] == True) & 
                        (df_lineups_colombia['minutes_played'] > 0)
                    ].copy()
                else:
                    jugadores_u23 = df_lineups_brasil[
                        (df_lineups_brasil['match_id'] == match_id) & 
                        (df_lineups_brasil['is_u23'] == True) & 
                        (df_lineups_brasil['minutes_played'] > 0)
                    ].copy()
                
                if len(jugadores_u23) > 0:
                    self.create_partido_section(story, partido, jugadores_u23, df_logos, df_fotos, match_info, ranking_global, 'ANEXOS')
                    
                    # Explicación específica
                    explicacion = f"<b>¿Por qué Z-Score bajo?</b> Aunque tiene {int(partido['num_u23'])} jugadores U23, "
                    explicacion += f"el promedio de minutos es solo {partido['minutos_promedio']:.0f}' (Factor B = {partido['factor_b']:.1f})."
                    story.append(Paragraph(explicacion, anexos_style))
                    story.append(Spacer(1, 0.2*inch))
                    ranking_global += 1
        
        # Sección ANEXOS (título antes del partido 15)
        # Verificar si hay partidos 15-16 (ANEXOS reales - sin el 19)
        partidos_positivos_todos = df_partidos[df_partidos['z_score'] >= 0].sort_values('z_score', ascending=False)
        hay_anexos = len(partidos_positivos_todos) > 14
        
        if hay_anexos:
            story.append(PageBreak())
            
            # Título ANEXOS grande y visible
            titulo_anexos_style = ParagraphStyle(
                'TituloAnexos',
                parent=self.title_style,
                fontSize=28,
                textColor=COLOR_NEGRO,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold',
                spaceAfter=20,
                spaceBefore=10
            )
            story.append(Paragraph("<b>ANEXOS</b>", titulo_anexos_style))
            story.append(Spacer(1, 0.3*inch))
            
            # Explicación
            explicacion_anexos = """
            <b>Partidos con Z-Score positivo que complementan el análisis principal.</b><br/>
            Estos partidos no alcanzaron el TOP 14 pero presentan características valiosas para seguimiento.
            """
            story.append(Paragraph(explicacion_anexos, self.normal_style))
            story.append(Spacer(1, 0.2*inch))
            
            # Tabla de partidos ANEXOS (tomar partidos 15, 16, 19)
            partidos_positivos_todos = df_partidos[df_partidos['z_score'] >= 0].sort_values('z_score', ascending=False)
            # Tomar partidos 15, 16, 19 (excluir 17 y 18)
            partidos_anexos_detalle = pd.concat([
                partidos_positivos_todos.iloc[14:16],  # 15-16
                partidos_positivos_todos.iloc[18:19]   # 19
            ])
            
            # Reiniciar ranking_global a 15 para ANEXOS
            ranking_global = 15
            
            for idx, anexo_partido in partidos_anexos_detalle.iterrows():
                match_id = anexo_partido['match_id']
                liga = anexo_partido['liga']
                
                # Obtener info del partido
                match_info = df_info[df_info['match_id'] == match_id].iloc[0]
                
                # Obtener jugadores U23
                if 'Colombia' in liga:
                    jugadores_u23 = df_lineups_colombia[
                        (df_lineups_colombia['match_id'] == match_id) & 
                        (df_lineups_colombia['is_u23'] == True) & 
                        (df_lineups_colombia['minutes_played'] > 0)
                    ].copy()
                else:
                    jugadores_u23 = df_lineups_brasil[
                        (df_lineups_brasil['match_id'] == match_id) & 
                        (df_lineups_brasil['is_u23'] == True) & 
                        (df_lineups_brasil['minutes_played'] > 0)
                    ].copy()
                
                # Crear sección del partido ANEXO
                self.create_partido_section(story, anexo_partido, jugadores_u23, df_logos, df_fotos, 
                                           match_info, ranking_global, 'ANEXO')
                ranking_global += 1
        
        # Construir PDF
        print("\n📝 Construyendo PDF...")
        doc.build(story, onFirstPage=self.add_header_footer, onLaterPages=self.add_header_footer)
        
        print(f"\n{'='*70}")
        print(f"✅ PDF IDV generado: {output_filename}")
        print(f"{'='*70}\n")
        
        return output_filename


if __name__ == "__main__":
    generator = PDFGeneratorIDV()
    
    # Generar PDF Detallado
    print("\n🔹 Generando PDF Detallado...")
    pdf_detallado = generator.generate_pdf_detallado()
    
    # Generar PDF Resumen Ejecutivo
    print("\n🔹 Generando PDF Resumen Ejecutivo...")
    from generar_pdf_resumen import PDFResumenEjecutivo
    generator_resumen = PDFResumenEjecutivo()
    pdf_resumen = generator_resumen.generate_pdf_resumen()
    
    print("\n" + "="*70)
    print("✅ AMBOS PDFs GENERADOS")
    print("="*70)
    print(f"📄 Resumen Ejecutivo: {pdf_resumen}")
    print(f"📄 Desglose Detallado: {pdf_detallado}")
    print("="*70 + "\n")
