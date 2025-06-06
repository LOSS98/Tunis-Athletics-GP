# utils/pdf_generator.py - Complete rewrite
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
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
            fontSize=20,
            alignment=TA_CENTER,
            spaceAfter=15,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#1a365d')
        )
        self.subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            alignment=TA_CENTER,
            spaceAfter=12,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#2d3748')
        )
        self.info_style = ParagraphStyle(
            'Info',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_LEFT,
            fontName='Helvetica'
        )

    def create_header(self, canvas, doc):
        page_width = doc.pagesize[0]
        page_height = doc.pagesize[1]

        # Main logo top left
        logo_path = "static/images/logos/logo.png"
        if os.path.exists(logo_path):
            canvas.drawImage(logo_path, 30, page_height - 80, width=80, height=50,
                             preserveAspectRatio=True, mask='auto')

        # WPA logo top right
        wpa_logo_path = "static/images/logos/wpa.png"
        if os.path.exists(wpa_logo_path):
            canvas.drawImage(wpa_logo_path, page_width - 110, page_height - 80, width=80, height=50,
                             preserveAspectRatio=True, mask='auto')

    def create_footer(self, canvas, doc):
        page_width = doc.pagesize[0]

        # Partner logos in footer
        footer_logos = [
            ("static/images/logos/tunisian.png", 150),
            ("static/images/logos/monoprix.png", page_width / 2 - 30),
            ("static/images/logos/partner3.png", page_width - 180)
        ]

        for logo_path, x_pos in footer_logos:
            if os.path.exists(logo_path):
                canvas.drawImage(logo_path, x_pos, 20, width=60, height=30,
                                 preserveAspectRatio=True, mask='auto')

    def generate_results_pdf(self, game, results, include_attempts=True):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                topMargin=100, rightMargin=30, leftMargin=30, bottomMargin=70)
        story = []

        # Title
        story.append(Paragraph("RESULTS", self.title_style))

        # Event details
        genders = game['gender'].split(',') if ',' in game['gender'] else [game['gender']]
        gender_text = ' & '.join(genders)
        event_title = f"{gender_text} {game['event']} {game['classes']}"
        story.append(Paragraph(event_title, self.subtitle_style))

        # Competition info
        story.append(Paragraph("Tunis Grand Prix 2025", self.info_style))
        story.append(Spacer(1, 20))

        # Event information table
        info_data = [
            ['Event:', game['event'], 'Day:', f"Day {game['day']}"],
            ['Gender:', gender_text, 'Time:', str(game['time'])],
            ['Classes:', game['classes'], 'Phase:', game.get('phase', 'Final')],
            ['Athletes:', str(len(results)), 'Status:', game['status'].title()]
        ]

        info_table = Table(info_data, colWidths=[60, 120, 60, 120])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#4a5568')),
            ('TEXTCOLOR', (2, 0), (2, -1), colors.HexColor('#4a5568')),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 25))

        # Results table based on event type
        if game['event'] in Config.get_track_events():
            table = self._create_track_results_table(game, results)
        elif game['event'] == 'High Jump':
            table = self._create_high_jump_table(game, results)
        elif game['event'] in Config.get_field_events():
            table = self._create_field_results_table(game, results)
        else:
            table = self._create_generic_table(game, results)

        story.append(table)

        # Official status
        if game.get('official'):
            story.append(Spacer(1, 20))
            official_para = Paragraph(
                f"<b>OFFICIAL RESULTS</b> - Approved on {game.get('official_date', 'N/A')}",
                ParagraphStyle('Official', fontSize=10, alignment=TA_CENTER,
                               textColor=colors.HexColor('#38a169'))
            )
            story.append(official_para)

        doc.build(story, onFirstPage=self.create_header, onLaterPages=self.create_header)
        buffer.seek(0)
        return buffer

    def generate_startlist_pdf(self, game, startlist):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                topMargin=100, rightMargin=30, leftMargin=30, bottomMargin=70)
        story = []

        # Title
        story.append(Paragraph("START LIST", self.title_style))

        # Event details
        genders = game['gender'].split(',') if ',' in game['gender'] else [game['gender']]
        gender_text = ' & '.join(genders)
        event_title = f"{gender_text} {game['event']} {game['classes']}"
        story.append(Paragraph(event_title, self.subtitle_style))

        story.append(Paragraph("Tunis Grand Prix 2025", self.info_style))
        story.append(Spacer(1, 20))

        # Event information
        info_data = [
            ['Event:', game['event'], 'Day:', f"Day {game['day']}"],
            ['Gender:', gender_text, 'Time:', str(game['time'])],
            ['Classes:', game['classes'], 'Phase:', game.get('phase', 'Final')],
            ['Expected Athletes:', str(game['nb_athletes']), 'Registered:', str(len(startlist))]
        ]

        info_table = Table(info_data, colWidths=[80, 120, 60, 120])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#4a5568')),
            ('TEXTCOLOR', (2, 0), (2, -1), colors.HexColor('#4a5568')),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 25))

        # Start list table
        if game['event'] in Config.get_track_events():
            table = self._create_track_startlist_table(game, startlist)
        elif game['event'] in Config.get_field_events():
            table = self._create_field_startlist_table(game, startlist)
        else:
            table = self._create_generic_startlist_table(game, startlist)

        story.append(table)

        doc.build(story, onFirstPage=self.create_header, onLaterPages=self.create_header)
        buffer.seek(0)
        return buffer

    def _create_track_results_table(self, game, results):
        headers = ['Rank', 'Lane', 'SDMS', 'Name', 'NPC', 'Class', 'Result']

        if game.get('wpa_points'):
            headers.append('Points')

        if game['event'] in Config.get_wind_affected_field_events():
            headers.append('Wind')

        col_widths = [40, 40, 50, 120, 40, 50, 80]
        if game.get('wpa_points'):
            col_widths.append(50)
        if game['event'] in Config.get_wind_affected_field_events():
            col_widths.append(50)

        data = []
        for i, result in enumerate(results):
            row = [
                result.get('rank', str(i + 1)),
                str(i + 1),
                str(result['athlete_sdms']),
                f"{result['firstname']} {result['lastname']}",
                result['npc'],
                result['athlete_class'],
                self._format_performance(result['value'], game['event'])
            ]

            if game.get('wpa_points'):
                row.append(str(result.get('raza_score', '')))

            if game['event'] in Config.get_wind_affected_field_events():
                wind = result.get('wind_velocity') or game.get('wind_velocity')
                row.append(f"{wind:+.1f}" if wind is not None else '')

            data.append(row)

        table = Table([headers] + data, colWidths=col_widths, repeatRows=1)
        table.setStyle(self._get_results_table_style(len(headers), len(data)))
        return table

    def _create_field_results_table(self, game, results):
        headers = ['Rank', 'SDMS', 'Name', 'NPC', 'Class']

        # Add attempt columns
        max_attempts = 6 if game['event'] != 'High Jump' else 0
        for i in range(1, max_attempts + 1):
            headers.append(f'A{i}')

        headers.extend(['Result', 'Points'] if game.get('wpa_points') else ['Result'])

        base_widths = [40, 50, 100, 40, 50]
        attempt_widths = [35] * max_attempts
        final_widths = [60, 50] if game.get('wpa_points') else [60]
        col_widths = base_widths + attempt_widths + final_widths

        data = []
        for i, result in enumerate(results):
            row = [
                result.get('rank', str(i + 1)),
                str(result['athlete_sdms']),
                f"{result['firstname']} {result['lastname']}",
                result['npc'],
                result['athlete_class']
            ]

            # Add attempts
            attempts = result.get('attempts', [])
            for attempt_num in range(1, max_attempts + 1):
                attempt = next((a for a in attempts if a['attempt_number'] == attempt_num), None)
                if attempt and attempt.get('value'):
                    row.append(self._format_attempt_value(attempt['value']))
                else:
                    row.append('')

            row.append(self._format_performance(result['value'], game['event']))

            if game.get('wpa_points'):
                row.append(str(result.get('raza_score', '')))

            data.append(row)

        table = Table([headers] + data, colWidths=col_widths, repeatRows=1)
        table.setStyle(self._get_results_table_style(len(headers), len(data)))
        return table

    def _create_high_jump_table(self, game, results):
        # Collect all heights
        all_heights = set()
        for result in results:
            if result.get('attempts'):
                for attempt in result['attempts']:
                    if attempt.get('height'):
                        all_heights.add(float(attempt['height']))

        sorted_heights = sorted(all_heights)

        headers = ['Rank', 'SDMS', 'Name', 'NPC', 'Class']
        for height in sorted_heights:
            headers.append(f"{height:.2f}m")
        headers.append('Result')

        base_widths = [40, 50, 100, 40, 50]
        height_widths = [40] * len(sorted_heights)
        final_widths = [60]
        col_widths = base_widths + height_widths + final_widths

        data = []
        for i, result in enumerate(results):
            row = [
                result.get('rank', str(i + 1)),
                str(result['athlete_sdms']),
                f"{result['firstname']} {result['lastname']}",
                result['npc'],
                result['athlete_class']
            ]

            # Process heights
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

            row.append(self._format_performance(result['value'], game['event']))
            data.append(row)

        table = Table([headers] + data, colWidths=col_widths, repeatRows=1)
        table.setStyle(self._get_results_table_style(len(headers), len(data)))
        return table

    def _create_track_startlist_table(self, game, startlist):
        headers = ['Lane', 'SDMS', 'Name', 'NPC', 'Class', 'Guide', 'Result']
        col_widths = [40, 50, 120, 40, 50, 60, 80]

        data = []
        for i, entry in enumerate(startlist):
            row = [
                str(entry.get('lane_order', i + 1)),
                str(entry['athlete_sdms']),
                f"{entry['firstname']} {entry['lastname']}",
                entry['npc'],
                entry['class'],
                str(entry['guide_sdms']) if entry.get('guide_sdms') else '',
                ''  # Empty result column
            ]
            data.append(row)

        table = Table([headers] + data, colWidths=col_widths, repeatRows=1)
        table.setStyle(self._get_startlist_table_style(len(headers), len(data)))
        return table

    def _create_field_startlist_table(self, game, startlist):
        headers = ['Order', 'SDMS', 'Name', 'NPC', 'Class', 'Guide']

        # Add attempt columns
        max_attempts = 6 if game['event'] != 'High Jump' else 8
        for i in range(1, max_attempts + 1):
            headers.append(f'A{i}')

        headers.append('Result')

        base_widths = [40, 50, 100, 40, 50, 60]
        attempt_widths = [30] * max_attempts
        final_widths = [60]
        col_widths = base_widths + attempt_widths + final_widths

        data = []
        for i, entry in enumerate(startlist):
            row = [
                str(entry.get('final_order', i + 1)),
                str(entry['athlete_sdms']),
                f"{entry['firstname']} {entry['lastname']}",
                entry['npc'],
                entry['class'],
                str(entry['guide_sdms']) if entry.get('guide_sdms') else ''
            ]

            # Add empty attempt columns
            for _ in range(max_attempts):
                row.append('')

            row.append('')  # Empty result column
            data.append(row)

        table = Table([headers] + data, colWidths=col_widths, repeatRows=1)
        table.setStyle(self._get_startlist_table_style(len(headers), len(data)))
        return table

    def _create_generic_table(self, game, results):
        return self._create_track_results_table(game, results)

    def _create_generic_startlist_table(self, game, startlist):
        return self._create_track_startlist_table(game, startlist)

    def _format_performance(self, value, event):
        if value in Config.get_result_special_values():
            return value

        if event in Config.get_field_events():
            try:
                return f"{float(value):.2f}m"
            except (ValueError, TypeError):
                return str(value)

        return str(value)

    def _format_attempt_value(self, value):
        if value in ['X', 'O', '-']:
            return value
        try:
            return f"{float(value):.2f}"
        except (ValueError, TypeError):
            return str(value)

    def _get_results_table_style(self, num_cols, num_rows):
        style = [
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a5568')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),

            # Body
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
            ('ALIGN', (3, 1), (3, -1), 'LEFT'),  # Name column left aligned

            # Borders
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),

            # Padding
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]

        # Podium colors
        if num_rows > 1:
            style.append(('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#ffd700')))  # Gold
        if num_rows > 2:
            style.append(('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#c0c0c0')))  # Silver
        if num_rows > 3:
            style.append(('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#cd7f32')))  # Bronze

        return TableStyle(style)

    def _get_startlist_table_style(self, num_cols, num_rows):
        style = [
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d3748')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),

            # Body
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
            ('ALIGN', (2, 1), (2, -1), 'LEFT'),  # Name column left aligned

            # Borders
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),

            # Alternating rows
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7fafc')]),

            # Padding
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]

        return TableStyle(style)