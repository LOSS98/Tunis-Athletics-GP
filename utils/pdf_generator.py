from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
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
            spaceAfter=20,
            fontName='Helvetica-Bold'
        )
        self.subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            alignment=TA_CENTER,
            spaceAfter=15,
            fontName='Helvetica-Bold'
        )
        self.date_style = ParagraphStyle(
            'DateStyle',
            parent=self.styles['Normal'],
            fontSize=11,
            alignment=TA_CENTER,
            spaceAfter=20,
            fontName='Helvetica'
        )
        self.info_style = ParagraphStyle(
            'Info',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_LEFT,
            fontName='Helvetica'
        )

    def create_header_with_logos(self, canvas, doc):
        """Créer l'en-tête avec les logos partenaires en paysage"""
        page_width = landscape(A4)[0]
        y = landscape(A4)[1] - 60

        # 3 logos alignés horizontalement (comme dans les images)
        logo_positions = [
            ("static/images/logos/wpa.png", 80),
            ("static/images/logos/tunisian.png", page_width / 2 - 30),
            ("static/images/logos/monoprix.png", page_width - 140)
        ]

        for logo_path, x_pos in logo_positions:
            if os.path.exists(logo_path):
                canvas.drawImage(logo_path, x_pos, y, width=60, height=40,
                                 preserveAspectRatio=True, mask='auto')

    def generate_results_pdf(self, game, results, include_attempts=True):
        """Générer un PDF de résultats en format paysage"""
        buffer = BytesIO()
        pagesize = landscape(A4)  # PAYSAGE obligatoire
        doc = SimpleDocTemplate(buffer, pagesize=pagesize,
                                topMargin=100, rightMargin=30, leftMargin=30, bottomMargin=50)
        story = []

        # Titre principal
        title = "RESULTS"
        story.append(Paragraph(title, self.title_style))

        # Sous-titre avec event et classes
        event_title = f"{game['gender']}'s {game['event']} {game['classes']}"
        story.append(Paragraph(event_title, self.subtitle_style))

        # Date de la compétition
        competition_date = "Tunis 5-7 March 2024"
        story.append(Paragraph(competition_date, self.date_style))

        # Informations de l'événement (gauche et droite)
        info_data = []
        left_info = f"Round: {game.get('phase', 'Final')}"
        right_info = f"Venue: Rades Athletics Stadium<br/>Date: 05/03/2024<br/>Time: {game['time']}"

        info_data.append([left_info, right_info])

        info_table = Table(info_data, colWidths=[350, 350])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 20))

        # Générer le tableau selon le type d'événement
        if game['event'] in Config.get_track_events():
            table = self._create_track_event_table(game, results)
        elif game['event'] == 'High Jump':
            table = self._create_high_jump_table(game, results)
        elif game['event'] in ['Long Jump', 'Triple Jump']:
            table = self._create_jump_table(game, results)
        elif game['event'] in ['Shot Put', 'Discus Throw', 'Javelin Throw', 'Club Throw']:
            table = self._create_throw_table(game, results)
        else:
            table = self._create_generic_field_table(game, results)

        story.append(table)

        # Ajouter page photo finish si disponible
        if game.get('photo_finish'):
            story.append(PageBreak())
            story.append(Paragraph("Photo Finish", self.title_style))
            story.append(Spacer(1, 20))

            photo_path = f"static/uploads/photo_finish/{game['photo_finish']}"
            if os.path.exists(photo_path):
                from reportlab.platypus import Image
                img = Image(photo_path, width=700, height=400)
                story.append(img)

        doc.build(story, onFirstPage=self.create_header_with_logos,
                  onLaterPages=self.create_header_with_logos)
        buffer.seek(0)
        return buffer

    def _create_throw_table(self, game, results):
        """Créer tableau pour lancers avec format correct"""
        # Headers selon le format exact des images
        headers = ['O', 'SDMS', 'Last Name', 'First Name', 'NPC', 'Gender', 'Class', 'Weight']

        # Ajouter les colonnes pour les 6 tentatives (A1, R(), A1, A2, R(), A2, etc.)
        for i in range(1, 7):
            headers.extend([f'A{i}', f'R()', f'A{i}'])

        headers.extend(['A6', 'R()', 'A6', 'Result', 'Score', 'Rank'])

        # Calculer les largeurs de colonnes pour le format paysage
        page_width = landscape(A4)[0] - 60  # Marges

        # Largeurs optimisées pour paysage
        col_widths = [
            25,  # O
            35,  # SDMS
            60,  # Last Name
            60,  # First Name
            35,  # NPC
            45,  # Gender
            35,  # Class
            45,  # Weight
        ]

        # 6 tentatives × 3 colonnes = 18 colonnes
        attempt_width = 25
        for i in range(18):
            col_widths.append(attempt_width)

        # Colonnes finales
        col_widths.extend([50, 40, 35])  # Result, Score, Rank

        data = []
        for i, result in enumerate(results):
            row = [
                str(i + 1),  # O (Order)
                str(result['athlete_sdms']),
                result['lastname'],
                result['firstname'],
                result['country'],
                result['athlete_gender'],
                result['athlete_class'],
                self._format_weight(result.get('weight')) if result.get('weight') else '-'
            ]

            # Traiter les tentatives
            attempts = result.get('attempts', [])
            for attempt_num in range(1, 7):
                attempt = next((a for a in attempts if a['attempt_number'] == attempt_num), None)
                if attempt and attempt.get('value'):
                    value = attempt['value']
                    if value.upper() in ['X', 'F']:
                        row.extend([value, '/', value])
                    else:
                        try:
                            formatted_value = f"{float(value):.2f}"
                            row.extend([formatted_value, '/', formatted_value])
                        except (ValueError, TypeError):
                            row.extend([value, '/', value])
                else:
                    row.extend(['', '', ''])

            # Résultat final, score et rang
            final_result = self._format_performance(result['value'], game['event'])
            score = str(result.get('raza_score', '')) if game.get('wpa_points') else ''
            rank = str(result.get('rank', ''))

            row.extend([final_result, score, rank])
            data.append(row)

        # Créer le tableau
        table = Table([headers] + data, colWidths=col_widths, repeatRows=1)
        table.setStyle(self._get_throw_table_style(len(headers), len(data)))
        return table

    def _create_track_event_table(self, game, results):
        """Créer tableau pour épreuves de piste"""
        headers = ['L', 'SDMS', 'Last Name', 'First Name', 'NPC', 'Gender', 'Class', 'Electronic']

        if game.get('wpa_points') and len(game['classes'].split(',')) > 1:
            headers.append('Score')

        headers.append('Rank')

        # Largeurs pour format paysage
        col_widths = [30, 40, 80, 80, 50, 60, 50, 80]
        if game.get('wpa_points'):
            col_widths.append(50)
        col_widths.append(50)

        data = []
        for i, result in enumerate(results):
            row = [
                str(i + 1),
                str(result['athlete_sdms']),
                result['lastname'],
                result['firstname'],
                result['country'],
                result['athlete_gender'],
                result['athlete_class'],
                self._format_performance(result['value'], game['event'])
            ]

            if game.get('wpa_points') and len(game['classes'].split(',')) > 1:
                row.append(str(result.get('raza_score', '')))

            row.append(str(result.get('rank', '')))
            data.append(row)

        table = Table([headers] + data, colWidths=col_widths, repeatRows=1)
        table.setStyle(self._get_official_table_style(len(headers), len(data)))
        return table

    def _create_jump_table(self, game, results):
        """Créer tableau pour sauts avec vent"""
        headers = ['O', 'SDMS', 'Last Name', 'First Name', 'NPC', 'Gender', 'Class']

        # 6 tentatives
        for i in range(1, 7):
            headers.append(f'A{i}')

        headers.extend(['Result', 'Score', 'Rank'])

        # Largeurs optimisées
        col_widths = [25, 35, 60, 60, 35, 45, 35] + [40] * 6 + [50, 40, 35]

        data = []
        for i, result in enumerate(results):
            # Ligne principale
            row1 = [
                str(i + 1),
                str(result['athlete_sdms']),
                result['lastname'],
                result['firstname'],
                result['country'],
                result['athlete_gender'],
                result['athlete_class']
            ]

            # Ligne pour les vents
            row2 = ['', '', '', '', '', '', '']

            attempts = result.get('attempts', [])
            has_wind = False

            for attempt_num in range(1, 7):
                attempt = next((a for a in attempts if a['attempt_number'] == attempt_num), None)
                if attempt and attempt.get('value'):
                    value = attempt['value']
                    wind = attempt.get('wind_velocity')

                    row1.append(value)

                    if wind is not None:
                        row2.append(f"{wind:+.1f}")
                        has_wind = True
                    else:
                        row2.append('')
                else:
                    row1.append('')
                    row2.append('')

            # Résultat final
            row1.extend([
                self._format_performance(result['value'], game['event']),
                str(result.get('raza_score', '')) if game.get('wpa_points') else '',
                str(result.get('rank', ''))
            ])
            row2.extend(['', '', ''])

            data.append(row1)
            if has_wind:
                data.append(row2)

        table = Table([headers] + data, colWidths=col_widths, repeatRows=1)
        table.setStyle(self._get_jump_table_style(len(headers), len(data)))
        return table

    def _create_high_jump_table(self, game, results):
        """Créer tableau pour saut en hauteur"""
        # Collecter toutes les hauteurs
        all_heights = set()
        for result in results:
            if result.get('attempts'):
                for attempt in result['attempts']:
                    if attempt.get('height'):
                        all_heights.add(float(attempt['height']))

        sorted_heights = sorted(all_heights)

        headers = ['O', 'SDMS', 'Last Name', 'First Name', 'NPC', 'Gender', 'Class']
        for height in sorted_heights:
            headers.append(f"{height:.2f}")
        headers.extend(['Result', 'Rank'])

        # Largeurs adaptées
        base_widths = [25, 35, 60, 60, 35, 45, 35]
        height_widths = [40] * len(sorted_heights)
        final_widths = [50, 35]
        col_widths = base_widths + height_widths + final_widths

        data = []
        for i, result in enumerate(results):
            row = [
                str(i + 1),
                str(result['athlete_sdms']),
                result['lastname'],
                result['firstname'],
                result['country'],
                result['athlete_gender'],
                result['athlete_class']
            ]

            # Traiter les hauteurs
            attempts_by_height = {}
            if result.get('attempts'):
                for attempt in result['attempts']:
                    if attempt.get('height'):
                        height = float(attempt['height'])
                        if height not in attempts_by_height:
                            attempts_by_height[height] = []
                        attempts_by_height[height].append(attempt['value'])

            for height in sorted_heights:
                if height in attempts_by_height:
                    attempts_str = ''.join(attempts_by_height[height])
                    row.append(attempts_str)
                else:
                    row.append('-')

            row.extend([
                self._format_performance(result['value'], game['event']),
                str(result.get('rank', ''))
            ])

            data.append(row)

        table = Table([headers] + data, colWidths=col_widths, repeatRows=1)
        table.setStyle(self._get_official_table_style(len(headers), len(data)))
        return table

    def _create_generic_field_table(self, game, results):
        """Tableau générique pour autres épreuves"""
        return self._create_throw_table(game, results)

    def _format_performance(self, value, event):
        """Formater la performance"""
        if value in Config.get_result_special_values():
            return value

        if event in Config.get_field_events():
            try:
                return f"{float(value):.2f}"
            except (ValueError, TypeError):
                return str(value)

        return str(value)

    def _format_weight(self, weight):
        """Formater le poids"""
        if weight:
            try:
                return f"{float(weight):.3f}kg"
            except (ValueError, TypeError):
                return str(weight)
        return '-'

    def _get_official_table_style(self, num_cols, num_rows):
        """Style de tableau officiel"""
        style = [
            # En-tête
            ('BACKGROUND', (0, 0), (-1, 0), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),

            # Corps
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('ALIGN', (0, 1), (-1, -1), 'CENTER'),

            # Bordures
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),

            # Padding réduit
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ]

        # Podiums
        if num_rows > 1:
            style.append(('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#FFD700')))  # Or
        if num_rows > 2:
            style.append(('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#C0C0C0')))  # Argent
        if num_rows > 3:
            style.append(('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#CD7F32')))  # Bronze

        return TableStyle(style)

    def _get_throw_table_style(self, num_cols, num_rows):
        """Style spécial pour les lancers"""
        style = self._get_official_table_style(num_cols, num_rows)

        # Colonnes R() en gris clair
        for col in range(8, num_cols - 3, 3):  # Colonnes R()
            style.add('BACKGROUND', (col, 0), (col, -1), colors.HexColor('#F0F0F0'))
            style.add('FONTSIZE', (col, 0), (col, -1), 6)

        return style

    def _get_jump_table_style(self, num_cols, num_rows):
        """Style pour les sauts avec lignes de vent"""
        style = self._get_official_table_style(num_cols, num_rows)

        # Lignes de vent (plus petites, italiques)
        for i in range(2, num_rows + 1, 2):
            style.add('FONTSIZE', (0, i), (-1, i), 6)
            style.add('FONTSTYLE', (0, i), (-1, i), 'Italic')
            style.add('TEXTCOLOR', (0, i), (-1, i), colors.grey)

        return style