import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from config import Config
import os


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        # Extraire game_title s'il est passé
        self.game_title = kwargs.pop('game_title', '')
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []
        self.page_num = 0

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()
        self.page_num += 1

    def save(self):
        num_pages = len(self._saved_page_states)
        for (page_num, state) in enumerate(self._saved_page_states):
            self.__dict__.update(state)
            self.draw_page_number(page_num + 1, num_pages)
            self.draw_header_footer()
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_num, total_pages):
        self.setFont("Helvetica", 8)
        self.drawRightString(A4[0] - 15 * mm, 15 * mm, f"Page {page_num} / {total_pages}")

    def draw_header_footer(self):
        # Header logos
        try:
            # Logo left
            logo_path = os.path.join('static', 'images', 'logo.png')
            if os.path.exists(logo_path):
                self.drawImage(logo_path, 15 * mm, A4[1] - 25 * mm, width=25 * mm, height=15 * mm,
                               preserveAspectRatio=True, mask='auto')

            # Logo right
            pa_logo_path = os.path.join('static', 'images', 'logos', 'wpa.png')
            if os.path.exists(pa_logo_path):
                self.drawImage(pa_logo_path, A4[0] - 40 * mm, A4[1] - 25 * mm, width=25 * mm, height=15 * mm,
                               preserveAspectRatio=True, mask='auto')
        except:
            pass

        # Titre centré entre les logos
        if hasattr(self, 'game_title') and self.game_title:
            self.setFont("Helvetica-Bold", 12)
            title_y = A4[1] - 17.5 * mm

            left_logo_end = 15 * mm + 25 * mm
            right_logo_start = A4[0] - 40 * mm
            available_width = right_logo_start - left_logo_end
            center_x = left_logo_end + (available_width / 2)

            text_width = self.stringWidth(self.game_title, "Helvetica-Bold", 12)
            self.drawString(center_x - text_width / 2, title_y, self.game_title)
        # Footer logos
        try:
            footer_logos = ['basar.png', 'ministere.png', 'monoprix.png', 'nextstep.png', 'npc.png', 'wpa.png']
            logo_width = 15 * mm
            total_width = len(footer_logos) * logo_width
            start_x = (A4[0] - total_width) / 2

            for i, logo_file in enumerate(footer_logos):
                logo_path = os.path.join('static', 'images', 'logos', logo_file)
                if os.path.exists(logo_path):
                    x_pos = start_x + (i * logo_width)
                    self.drawImage(logo_path, x_pos, 5 * mm, width=12 * mm, height=8 * mm, preserveAspectRatio=True,
                                   mask='auto')
        except:
            pass

        # Generation date
        generation_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.setFont("Helvetica", 6)
        self.drawString(15 * mm, 15 * mm, f"Generated on {generation_date}")


class PDFGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_styles()

    def setup_styles(self):
        self.styles.add(ParagraphStyle(
            name='PDFMainTitle',
            parent=self.styles['Normal'],
            fontSize=12,
            spaceAfter=4,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))

        self.styles.add(ParagraphStyle(
            name='PDFVenue',
            parent=self.styles['Normal'],
            fontSize=8,
            spaceAfter=3,
            alignment=TA_CENTER,
            fontName='Helvetica'
        ))

        self.styles.add(ParagraphStyle(
            name='PDFEventTitle',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=3,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))

    def format_gender_title(self, gender):
        if gender == 'Male':
            return "Men's"
        elif gender == 'Female':
            return "Women's"
        return gender

    def create_track_event_table(self, results, game):
        headers = ['Rank', 'lane', 'SDMS', 'First Name', 'Last Name', 'Gender', 'NPC', 'Class', 'Electronic']

        if game.get('wpa_points', False):
            headers.append('WPA Points')

        data = [headers]

        for i, result in enumerate(results, 1):
            row = [
                result['rank'] or str(i),
                str(i),
                str(result['athlete_sdms']),
                result['firstname'] or '',
                result['lastname'] or '',
                result['athlete_gender'] or '',
                result['npc'] or '',
                result.get('athlete_class', '').split(',')[0] if result.get('athlete_class') else '',
                result['value'] or ''
            ]

            if game.get('wpa_points', False):
                row.append(str(result['raza_score']) if result.get('raza_score') else '')

            data.append(row)

        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.8, 0.9, 1.0)),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 7),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, 0), 4),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 4),

            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 6),
            ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 1), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 2),

            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        return table

    def create_field_event_table(self, game, results):
        headers = ['Rank', 'Order', 'SDMS', 'First Name', 'Last Name', 'Gender', 'NPC']

        if game['event'] in Config.get_weight_field_events():
            headers.append('Weight')

        headers.extend(['R1/P1', 'Class', 'Performance'])

        if game.get('wpa_points', False):
            headers.append('WPA Points')

        data = [headers]
        athlete_rows = []

        for i, result in enumerate(results, 1):
            row = [
                result['rank'] or str(i),
                str(i),
                str(result['athlete_sdms']),
                result['firstname'] or '',
                result['lastname'] or '',
                result['athlete_gender'] or '',
                result['npc'] or ''
            ]

            if game['event'] in Config.get_weight_field_events():
                weight_val = f"{result['weight']:.3f} kg" if result.get('weight') else '3.000 kg'
                row.append(weight_val)

            total_finalists = len([r for r in results if r.get('final_order')])
            r1_order = f"{result['final_order']}/{total_finalists}" if result.get('final_order') else ''
            row.append(r1_order)

            row.extend([
                result.get('athlete_class', '').split(',')[0] if result.get('athlete_class') else '',
                result['value'] or ''
            ])

            if game.get('wpa_points', False):
                row.append(str(result['raza_score']) if result.get('raza_score') else '')

            data.append(row)
            athlete_rows.append(len(data) - 1)

            attempts = result.get('attempts', [])
            for attempt_num in range(1, 7):
                attempt = next((a for a in attempts if a['attempt_number'] == attempt_num), None)

                attempt_row = [''] * len(headers)
                attempt_row[1] = f'Attempt {attempt_num}'

                if attempt and attempt.get('value'):
                    attempt_row[2] = attempt['value']

                    if game.get('wpa_points', False) and attempt.get('raza_score'):
                        attempt_row[3] = str(attempt['raza_score'])

                    if game['event'] in Config.get_wind_affected_field_events() and attempt.get('wind_velocity'):
                        wind_col = 4 if game.get('wpa_points', False) else 3
                        attempt_row[wind_col] = f"{attempt['wind_velocity']:+.2f} m/s"

                data.append(attempt_row)

        table = Table(data, repeatRows=1)

        style_commands = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.8, 0.9, 1.0)),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 6),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, 0), 3),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 3),

            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 6),
            ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 1), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 1),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]

        for row_idx in athlete_rows:
            style_commands.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.Color(0.9, 0.95, 1.0)))
            style_commands.append(('FONTNAME', (0, row_idx), (-1, row_idx), 'Helvetica-Bold'))

        table.setStyle(TableStyle(style_commands))
        return table

    def create_high_jump_table(self, game, results):
        all_heights = set()
        for result in results:
            for attempt in result.get('attempts', []):
                if attempt.get('height'):
                    all_heights.add(float(attempt['height']))

        sorted_heights = sorted(all_heights)

        headers = ['Rank', 'Order', 'SDMS', 'First Name', 'Last Name', 'Gender', 'NPC', 'Class', 'Performance']
        if game.get('wpa_points', False):
            headers.append('WPA Points')

        data = [headers]
        athlete_rows = []

        for i, result in enumerate(results, 1):
            row = [
                result['rank'] or str(i),
                str(i),
                str(result['athlete_sdms']),
                result['firstname'] or '',
                result['lastname'] or '',
                result['athlete_gender'] or '',
                result['npc'] or '',
                result.get('athlete_class', '').split(',')[0] if result.get('athlete_class') else '',
                result['value'] or ''
            ]

            if game.get('wpa_points', False):
                row.append(str(result['raza_score']) if result.get('raza_score') else '')

            data.append(row)
            athlete_rows.append(len(data) - 1)

            attempts_by_height = {}
            for attempt in result.get('attempts', []):
                height = attempt.get('height')
                if height:
                    height_key = float(height)
                    if height_key not in attempts_by_height:
                        attempts_by_height[height_key] = []
                    attempts_by_height[height_key].append(attempt['value'])

            for j, height in enumerate(sorted_heights, 1):
                attempt_row = [''] * len(headers)
                attempt_row[1] = f'Attempt {j}'
                attempt_row[2] = f'{height:.2f}'

                if height in attempts_by_height:
                    attempt_row[3] = ''.join(attempts_by_height[height])

                    if game.get('wpa_points', False):
                        for attempt in result.get('attempts', []):
                            if (attempt.get('height') == height and
                                    attempt.get('value') == 'O' and
                                    attempt.get('raza_score')):
                                attempt_row[4] = str(attempt['raza_score'])
                                break

                else:
                    attempt_row[3] = '-'

                data.append(attempt_row)

        table = Table(data, repeatRows=1)

        style_commands = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(1.0, 0.8, 0.8)),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 6),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, 0), 3),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 3),

            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 6),
            ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 1), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 1),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]

        for row_idx in athlete_rows:
            style_commands.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.Color(1.0, 0.9, 0.9)))
            style_commands.append(('FONTNAME', (0, row_idx), (-1, row_idx), 'Helvetica-Bold'))

        table.setStyle(TableStyle(style_commands))
        return table

    def generate_results_pdf(self, game, results, heat_group=None, combined_results=None):
        buffer = io.BytesIO()

        # Créer le titre pour le header
        gender_title = self.format_gender_title(game['genders'])
        game_title = f"{gender_title} {game['event']} {game['classes']}"
        if game.get('phase'):
            game_title += f" - {game['phase']}"
        game_title += " - Results"

        # Créer le canvas maker avec le titre
        def make_canvas(*args, **kwargs):
            kwargs['game_title'] = game_title
            return NumberedCanvas(*args, **kwargs)

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            topMargin=35 * mm,
            bottomMargin=25 * mm,
            leftMargin=10 * mm,
            rightMargin=10 * mm
        )

        story = []

        # Ajouter les infos de base
        story.append(Paragraph("World Para Athletics Grand Prix", self.styles['PDFMainTitle']))
        story.append(Paragraph("Rades Stadium, Tunis, Tunisia", self.styles['PDFVenue']))
        story.append(Paragraph(f"Day {game['day']} - {game['time']}", self.styles['PDFVenue']))
        story.append(Spacer(1, 8 * mm))

        game_heat_group_id = game.get('heat_group_id')
        if game_heat_group_id or heat_group:
            from database.models.heat_group import HeatGroup
            from database.models.result import Result

            heat_group_id = heat_group['id'] if heat_group else game_heat_group_id

            all_heat_games = HeatGroup.get_games(heat_group_id)
            all_heat_games = sorted(all_heat_games, key=lambda x: x.get('heat_number', 0))

            for heat_game in all_heat_games:
                story.append(
                    Paragraph(f"Heat {heat_game.get('heat_number', '?')} Results", self.styles['PDFEventTitle']))
                story.append(Spacer(1, 3 * mm))

                # Ajouter la vitesse du vent pour ce heat spécifique
                if heat_game.get('wind_velocity') is not None and heat_game['event'] in Config.get_track_events():
                    wind_text = f"Wind: {heat_game['wind_velocity']:+.1f} m/s"
                    story.append(Paragraph(wind_text, self.styles['PDFVenue']))
                    story.append(Spacer(1, 3 * mm))

                heat_results = Result.get_all(game_id=heat_game['id'])

                if heat_results:
                    if heat_game['event'] == 'High Jump':
                        table = self.create_high_jump_table(heat_game, heat_results)
                    elif heat_game['event'] in Config.get_field_events():
                        table = self.create_field_event_table(heat_game, heat_results)
                    else:
                        table = self.create_track_event_table(heat_results, heat_game)

                    story.append(table)
                    story.append(Spacer(1, 8 * mm))

            if combined_results:
                story.append(PageBreak())
                story.append(Paragraph("Final Combined Results", self.styles['PDFEventTitle']))
                story.append(Spacer(1, 5 * mm))

                combined_table = self.create_combined_results_table(combined_results, game)
                story.append(combined_table)
            else:
                story.append(PageBreak())
                story.append(Paragraph("Final Combined Results", self.styles['PDFEventTitle']))
                story.append(Spacer(1, 5 * mm))

                auto_combined_results = HeatGroup.get_combined_results(heat_group_id)
                if auto_combined_results:
                    combined_table = self.create_combined_results_table(auto_combined_results, game)
                    story.append(combined_table)

        else:
            # Game individuel - afficher le vent du game principal
            if game.get('wind_velocity') is not None and game['event'] in Config.get_track_events():
                wind_text = f"Wind: {game['wind_velocity']:+.1f} m/s"
                story.append(Paragraph(wind_text, self.styles['PDFVenue']))
                story.append(Spacer(1, 3 * mm))

            if game['event'] == 'High Jump':
                table = self.create_high_jump_table(game, results)
            elif game['event'] in Config.get_field_events():
                table = self.create_field_event_table(game, results)
            else:
                table = self.create_track_event_table(results, game)

            story.append(table)

        doc.build(story, canvasmaker=make_canvas)
        buffer.seek(0)
        return buffer

    def create_combined_results_table(self, combined_results, game):
        headers = ['Rank', 'Heat', 'SDMS', 'First Name', 'Last Name', 'NPC', 'Class', 'Performance']
        if game.get('wpa_points', False):
            headers.append('WPA Points')

        data = [headers]

        for result in combined_results:
            row = [
                str(result.get('rank', '')),
                f"Heat {result.get('heat_number', '')}",
                str(result['athlete_sdms']),
                result['firstname'] or '',
                result['lastname'] or '',
                result['npc'] or '',
                result.get('athlete_class', '').split(',')[0] if result.get('athlete_class') else '',
                result['value'] or ''
            ]

            if game.get('wpa_points', False):
                row.append(str(result['raza_score']) if result.get('raza_score') else '')

            data.append(row)

        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.8, 0.9, 1.0)),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 7),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, 0), 4),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 4),

            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 6),
            ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 1), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 2),

            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        return table

    def generate_startlist_pdf(self, game, startlist):
        buffer = io.BytesIO()

        # Créer le titre pour le header
        gender_title = self.format_gender_title(game['genders'])
        game_title = f"{gender_title} {game['event']} {game['classes']}"
        if game.get('phase'):
            game_title += f" - {game['phase']}"

        # Créer le canvas maker avec le titre
        def make_canvas(*args, **kwargs):
            kwargs['game_title'] = game_title
            return NumberedCanvas(*args, **kwargs)

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            topMargin=35 * mm,
            bottomMargin=25 * mm,
            leftMargin=10 * mm,
            rightMargin=10 * mm
        )

        story = []

        # Ajouter les infos de base
        story.append(Paragraph("World Para Athletics Grand Prix", self.styles['PDFMainTitle']))
        story.append(Paragraph("Rades Stadium, Tunis, Tunisia", self.styles['PDFVenue']))
        story.append(Paragraph(f"Day {game['day']} - {game['time']}", self.styles['PDFVenue']))
        story.append(Spacer(1, 8 * mm))

        story.append(Paragraph("Start List", self.styles['PDFEventTitle']))
        story.append(Spacer(1, 5 * mm))

        headers = ['Lane', 'SDMS', 'First Name', 'Last Name', 'NPC', 'Class', 'Gender']

        data = [headers]
        for entry in startlist:
            row = [
                str(entry['lane_order']) if entry.get('lane_order') else '',
                str(entry['athlete_sdms']),
                entry['firstname'] or '',
                entry['lastname'] or '',
                entry['npc'] or '',
                entry['class'] or '',
                entry['gender'] or ''
            ]
            data.append(row)
            data.append([''] * len(headers))

        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.8, 0.9, 1.0)),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 7),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, 0), 4),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 4),

            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 6),
            ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 1), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 2),

            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        story.append(table)

        doc.build(story, canvasmaker=make_canvas)
        buffer.seek(0)
        return buffer