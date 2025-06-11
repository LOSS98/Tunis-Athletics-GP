# utils/pdf_generator.py
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
                    self.drawImage(logo_path, x_pos, 5 * mm, width=12 * mm, height=8 * mm, preserveAspectRatio=True, mask='auto')
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

    def get_header_content(self, game):
        content = []
        content.append(Paragraph("World Para Athletics Grand Prix", self.styles['PDFMainTitle']))
        content.append(Paragraph("Rades Stadium, Tunis, Tunisia", self.styles['PDFVenue']))

        gender_title = self.format_gender_title(game['genders'])
        event_title = f"{gender_title} {game['event']} {game['classes']}"
        if game.get('phase'):
            event_title += f" - {game['phase']}"

        content.append(Paragraph(event_title, self.styles['PDFEventTitle']))
        content.append(Paragraph(f"Day {game['day']} - {game['time']}", self.styles['PDFVenue']))

        return content

    def create_track_event_table(self, results, game):
        """Create table exactly like Track events"""
        headers = ['Line', 'SDMS', 'First Name', 'Last Name', 'Gender', 'NPC', 'Class', 'Electronic']

        if game.get('wpa_points', False):
            headers.append('WPA Po')

        headers.append('Rank')

        data = [headers]

        for i, result in enumerate(results, 1):
            row = [
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

            row.append(result['rank'] or str(i))
            data.append(row)

        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.8, 0.9, 1.0)),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 7),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, 0), 4),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 4),

            # Data rows
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 6),
            ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 1), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 2),

            # NO GRID - removed all GRID styles
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        return table

    def create_field_event_table(self, game, results):
        """Create table exactly like Field events"""
        headers = ['Order', 'SDMS', 'First Name', 'Last Name', 'Gender', 'NPC']

        if game['event'] in Config.get_weight_field_events():
            headers.append('Weight')

        headers.extend(['R1/P1', 'Class', 'Performance'])

        if game.get('wpa_points', False):
            headers.append('WPA Points')

        headers.append('Rank')

        data = [headers]
        athlete_rows = []  # Track which rows are athlete rows for styling

        for i, result in enumerate(results, 1):
            # Main athlete row
            row = [
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

            # R1/P1 (final_order)
            total_finalists = len([r for r in results if r.get('final_order')])
            r1_order = f"{result['final_order']}/{total_finalists}" if result.get('final_order') else ''
            row.append(r1_order)

            row.extend([
                result.get('athlete_class', '').split(',')[0] if result.get('athlete_class') else '',
                result['value'] or ''
            ])

            if game.get('wpa_points', False):
                row.append(str(result['raza_score']) if result.get('raza_score') else '')

            row.append(result['rank'] or str(i))

            data.append(row)
            athlete_rows.append(len(data) - 1)  # Track this row as athlete row

            # Add attempts rows with REAL VALUES
            attempts = result.get('attempts', [])
            for attempt_num in range(1, 7):
                attempt = next((a for a in attempts if a['attempt_number'] == attempt_num), None)

                attempt_row = [''] * len(headers)
                attempt_row[0] = f'Attempt {attempt_num}'

                if attempt and attempt.get('value'):
                    # Real attempt value
                    attempt_row[1] = attempt['value']

                    # WPA points if available and enabled
                    if game.get('wpa_points', False) and attempt.get('raza_score'):
                        attempt_row[2] = str(attempt['raza_score'])

                    # Wind if applicable
                    if game['event'] in Config.get_wind_affected_field_events() and attempt.get('wind_velocity'):
                        wind_col = 3 if game.get('wpa_points', False) else 2
                        attempt_row[wind_col] = f"{attempt['wind_velocity']:+.2f} m/s"

                data.append(attempt_row)

        table = Table(data, repeatRows=1)

        # Build style list
        style_commands = [
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.8, 0.9, 1.0)),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 6),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, 0), 3),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 3),

            # All data rows
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 6),
            ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 1), (-1, -1), 1),  # Reduced padding
            ('BOTTOMPADDING', (0, 1), (-1, -1), 1),  # Reduced padding
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]

        # Highlight athlete rows
        for row_idx in athlete_rows:
            style_commands.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.Color(0.9, 0.95, 1.0)))
            style_commands.append(('FONTNAME', (0, row_idx), (-1, row_idx), 'Helvetica-Bold'))

        table.setStyle(TableStyle(style_commands))
        return table

    def create_high_jump_table(self, game, results):
        """Create table exactly like High Jump"""
        # Find all unique heights
        all_heights = set()
        for result in results:
            for attempt in result.get('attempts', []):
                if attempt.get('height'):
                    all_heights.add(float(attempt['height']))

        sorted_heights = sorted(all_heights)

        headers = ['Order', 'SDMS', 'First Name', 'Last Name', 'Gender', 'NPC', 'Class', 'Performance']
        if game.get('wpa_points', False):
            headers.append('WPA Po')
        headers.append('Rank')

        data = [headers]
        athlete_rows = []

        for i, result in enumerate(results, 1):
            # Main athlete row
            row = [
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

            row.append(result['rank'] or str(i))
            data.append(row)
            athlete_rows.append(len(data) - 1)

            # Group attempts by height
            attempts_by_height = {}
            for attempt in result.get('attempts', []):
                height = attempt.get('height')
                if height:
                    height_key = float(height)
                    if height_key not in attempts_by_height:
                        attempts_by_height[height_key] = []
                    attempts_by_height[height_key].append(attempt['value'])

            # Add attempt rows for each height with REAL VALUES
            for j, height in enumerate(sorted_heights, 1):
                attempt_row = [''] * len(headers)
                attempt_row[0] = f'Attempt {j}'
                attempt_row[1] = f'{height:.2f}'

                if height in attempts_by_height:
                    # Real attempt values joined together (like "XO" or "XXO")
                    attempt_row[2] = ''.join(attempts_by_height[height])

                    # WPA points if available
                    if game.get('wpa_points', False):
                        # Find WPA points for successful attempts at this height
                        for attempt in result.get('attempts', []):
                            if (attempt.get('height') == height and
                                    attempt.get('value') == 'O' and
                                    attempt.get('raza_score')):
                                attempt_row[3] = str(attempt['raza_score'])
                                break


                else:
                    attempt_row[2] = '-'

                data.append(attempt_row)

        table = Table(data, repeatRows=1)

        # Build style list
        style_commands = [
            # Header row - Pink for High Jump
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(1.0, 0.8, 0.8)),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 6),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, 0), 3),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 3),

            # All data rows
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 6),
            ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 1), (-1, -1), 1),  # Reduced padding
            ('BOTTOMPADDING', (0, 1), (-1, -1), 1),  # Reduced padding
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]

        # Highlight athlete rows
        for row_idx in athlete_rows:
            style_commands.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.Color(1.0, 0.9, 0.9)))
            style_commands.append(('FONTNAME', (0, row_idx), (-1, row_idx), 'Helvetica-Bold'))

        table.setStyle(TableStyle(style_commands))
        return table

    def generate_results_pdf(self, game, results, heat_group=None, combined_results=None):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            topMargin=35 * mm,
            bottomMargin=25 * mm,
            leftMargin=15 * mm,
            rightMargin=15 * mm
        )

        story = []

        header_content = self.get_header_content(game)
        story.extend(header_content)
        story.append(Spacer(1, 8 * mm))

        if game.get('wind_velocity') is not None and game['event'] in Config.get_track_events():
            wind_text = f"Wind: {game['wind_velocity']:+.1f} m/s"
            story.append(Paragraph(wind_text, self.styles['PDFVenue']))
            story.append(Spacer(1, 3 * mm))

        if heat_group and combined_results:
            from database.models.heat_group import HeatGroup
            from database.models.game import Game as GameModel
            from database.models.result import Result

            heat_games = HeatGroup.get_games(heat_group['id'])

            for heat_game in heat_games:
                story.append(Paragraph(f"Heat {heat_game['heat_number']} Results", self.styles['PDFEventTitle']))
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

            story.append(PageBreak())
            story.append(Paragraph("Final Combined Results", self.styles['PDFEventTitle']))
            story.append(Spacer(1, 5 * mm))

            combined_table = self.create_combined_results_table(combined_results, game)
            story.append(combined_table)

        else:
            if game['event'] == 'High Jump':
                table = self.create_high_jump_table(game, results)
            elif game['event'] in Config.get_field_events():
                table = self.create_field_event_table(game, results)
            else:
                table = self.create_track_event_table(results, game)

            story.append(table)

        doc.build(story, canvasmaker=NumberedCanvas)
        buffer.seek(0)
        return buffer

    def create_combined_results_table(self, combined_results, game):
        headers = ['Final Rank', 'Heat', 'SDMS', 'First Name', 'Last Name', 'NPC', 'Class', 'Performance']
        if game.get('wpa_points', False):
            headers.append('WPA Po')

        data = [headers]

        for result in combined_results:
            row = [
                str(result.get('final_rank', '')),
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
        """Generate start list PDF"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            topMargin=35 * mm,
            bottomMargin=25 * mm,
            leftMargin=15 * mm,
            rightMargin=15 * mm
        )

        story = []

        # Header
        header_content = self.get_header_content(game)
        story.extend(header_content)
        story.append(Spacer(1, 8 * mm))

        # Start List title
        story.append(Paragraph("Start List", self.styles['PDFEventTitle']))
        story.append(Spacer(1, 5 * mm))

        # Create start list table
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

        doc.build(story, canvasmaker=NumberedCanvas)
        buffer.seek(0)
        return buffer