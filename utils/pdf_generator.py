from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from io import BytesIO
import os
from config import Config

class PDFGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            alignment=TA_CENTER,
            spaceAfter=30,
            fontName='Helvetica-Bold'
        )
        self.subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            alignment=TA_CENTER,
            spaceAfter=20,
            fontName='Helvetica-Bold'
        )
        self.header_style = ParagraphStyle(
            'Header',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_CENTER,
            fontName='Helvetica'
        )

    def create_header_with_logos(self, canvas, doc):
        """Créer l'en-tête avec les logos partenaires (fond blanc, logos PNG transparents)"""
        y = landscape(A4)[1] - 80  # Position verticale pour landscape(A4)
        # Logo principal
        logo_path = "static/images/logos/wpa.png"
        if os.path.exists(logo_path):
            canvas.drawImage(logo_path, 50, y, width=60, height=40, preserveAspectRatio=True, mask='auto')

        # Titre principal
        canvas.setFont('Helvetica-Bold', 16)
        canvas.drawCentredString(landscape(A4)[0] / 2, y + 40, "WORLD PARA ATHLETICS")
        canvas.setFont('Helvetica', 12)
        canvas.drawCentredString(landscape(A4)[0] / 2, y + 25, "GRAND PRIX - TUNIS 2025")

        # Logos partenaires (alignés à droite)
        partner_logos = [
            ("static/images/logos/npc.png", landscape(A4)[0] - 170),
            ("static/images/logos/monoprix.png", landscape(A4)[0] - 120),
            ("static/images/logos/basar.png", landscape(A4)[0] - 70)
        ]
        for logo_path, x_pos in partner_logos:
            if os.path.exists(logo_path):
                canvas.drawImage(logo_path, x_pos, y, width=40, height=40, preserveAspectRatio=True, mask='auto')

    def generate_results_pdf(self, game, results, include_attempts=True):
        """Générer un PDF de résultats pour un événement"""
        buffer = BytesIO()
        pagesize = landscape(A4)  # Toujours paysage
        doc = SimpleDocTemplate(buffer, pagesize=pagesize, topMargin=100, rightMargin=24, leftMargin=24)
        story = []

        # En-tête
        title = f"Results - {game['event']} {game['gender']}"
        story.append(Paragraph(title, self.title_style))

        subtitle = f"{game['classes']} - Tunis 5-7 March 2024"
        story.append(Paragraph(subtitle, self.subtitle_style))

        # Informations de l'événement
        event_info = f"Round: {game.get('phase', 'Final')}"
        event_info += f" | Venue: Rades Athletics Stadium | Date: 05/03/2024 | Time: {game['time']}"
        story.append(Paragraph(event_info, self.header_style))
        story.append(Spacer(1, 20))

        # Vent si applicable
        if game.get('wind_velocity') and game['wind_velocity'] != 0:
            wind_text = f"WIND: {Config.format_wind(game['wind_velocity'])} m/s"
            story.append(Paragraph(wind_text, self.header_style))
            story.append(Spacer(1, 10))

        # Préparer les données du tableau
        if game['event'] in Config.get_field_events() and include_attempts:
            headers, data = self._prepare_field_event_data(game, results)
        else:
            headers, data = self._prepare_track_event_data(game, results)

        # Créer le tableau
        table = Table([headers] + data, repeatRows=1)

        # Style de tableau PRO
        table_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#102447')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor('#e9eef6')]),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]
        # Podiums gold/silver/bronze
        for i, result in enumerate(results):
            if result.get('rank') == '1':
                table_style.append(('BACKGROUND', (0, i + 1), (-1, i + 1), colors.HexColor('#ffd700')))  # Gold
            elif result.get('rank') == '2':
                table_style.append(('BACKGROUND', (0, i + 1), (-1, i + 1), colors.HexColor('#c0c0c0')))  # Silver
            elif result.get('rank') == '3':
                table_style.append(('BACKGROUND', (0, i + 1), (-1, i + 1), colors.HexColor('#cd7f32')))  # Bronze

        table.setStyle(TableStyle(table_style))
        story.append(table)

        # Footer avec infos RAZA si applicable
        if game.get('wpa_points') and len(game['classes'].split(',')) > 1:
            story.append(Spacer(1, 20))
            raza_info = "RAZA Score calculations based on official IPC data for fair multi-class competition"
            story.append(Paragraph(raza_info, self.header_style))

        doc.build(story, onFirstPage=self.create_header_with_logos, onLaterPages=self.create_header_with_logos)
        buffer.seek(0)
        return buffer

    def _prepare_track_event_data(self, game, results):
        """Préparer les données pour les épreuves de piste"""
        headers = ['L', 'BIB', 'Last Name', 'First Name', 'NPC', 'Gender', 'Class', 'Electronic', 'Score', 'Rank']

        if game.get('wpa_points') and len(game['classes'].split(',')) > 1:
            headers.insert(-1, 'RAZA')

        data = []
        for i, result in enumerate(results):
            row = [
                str(i + 1),  # Lane/Order
                str(result['athlete_bib']),
                result['lastname'],
                result['firstname'],
                result['country'],
                result['athlete_gender'],
                result['athlete_class'],
                Config.format_time(result['value']) if result['value'] not in Config.get_result_special_values() else
                result['value'],
                str(result.get('raza_score', '-')) if game.get('wpa_points') else '-',
                str(result.get('rank', '-'))
            ]

            if not (game.get('wpa_points') and len(game['classes'].split(',')) > 1):
                row.pop(-2)  # Enlever le score RAZA si pas applicable

            data.append(row)

        return headers, data

    def _prepare_field_event_data(self, game, results):
        """Préparer les données pour les épreuves de terrain avec tentatives"""
        headers = ['O', 'BIB', 'Last Name', 'First Name', 'NPC', 'Gender', 'Class', 'Weight']

        # Ajouter les colonnes pour les tentatives
        max_attempts = 6
        for i in range(1, max_attempts + 1):
            headers.extend([f'A{i}', f'A{i}', f'A{i}'])  # Value, Wind, Height si applicable

        headers.extend(['Result', 'Score', 'Rank'])

        data = []
        for i, result in enumerate(results):
            row = [
                str(i + 1),  # Order
                str(result['athlete_bib']),
                result['lastname'],
                result['firstname'],
                result['country'],
                result['athlete_gender'],
                result['athlete_class'],
                Config.format_weight(result.get('weight', '')) if result.get('weight') else '-'
            ]

            # Ajouter les tentatives
            attempts = result.get('attempts', [])
            for attempt_num in range(1, max_attempts + 1):
                attempt = next((a for a in attempts if a['attempt_number'] == attempt_num), None)
                if attempt:
                    row.extend([
                        attempt.get('value', ''),
                        Config.format_wind(attempt.get('wind_velocity', '')) if attempt.get('wind_velocity') else '',
                        str(attempt.get('height', '')) if attempt.get('height') else ''
                    ])
                else:
                    row.extend(['', '', ''])

            # Résultat final
            performance = result['value']
            if performance not in Config.get_result_special_values():
                performance = Config.format_distance(performance) + " m"

            row.extend([
                performance,
                str(result.get('raza_score', '-')),
                str(result.get('rank', '-'))
            ])

            data.append(row)

        return headers, data