from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
import os
from config import Config
from datetime import datetime
class PDFGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.comp_title_style = ParagraphStyle(
            'CompetitionTitle',
            parent=self.styles['Heading1'],
            fontSize=14,
            alignment=TA_CENTER,
            spaceAfter=2,
            fontName='Helvetica-Bold',
            textColor=colors.black
        )
        self.location_style = ParagraphStyle(
            'Location',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_CENTER,
            spaceAfter=2,
            fontName='Helvetica',
            textColor=colors.black
        )
        self.event_title_style = ParagraphStyle(
            'EventTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            alignment=TA_CENTER,
            spaceAfter=8,
            fontName='Helvetica-Bold',
            textColor=colors.black
        )
        self.phase_style = ParagraphStyle(
            'Phase',
            parent=self.styles['Heading2'],
            fontSize=14,
            alignment=TA_CENTER,
            spaceAfter=15,
            fontName='Helvetica-Bold',
            textColor=colors.black
        )
        self.results_title_style = ParagraphStyle(
            'ResultsTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            alignment=TA_LEFT,
            spaceAfter=12,
            fontName='Helvetica-Bold',
            textColor=colors.black
        )
        self.record_style = ParagraphStyle(
            'Record',
            parent=self.styles['Normal'],
            fontSize=9,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold',
            textColor=colors.black
        )
    def create_header_footer(self, canvas, doc):
        page_width = doc.pagesize[0]
        page_height = doc.pagesize[1]
        logo_path = "static/images/logos/logo.png"
        if os.path.exists(logo_path):
            canvas.drawImage(logo_path, 30, page_height - 80, width=80, height=50,
                             preserveAspectRatio=True, mask='auto')
        wpa_logo_path = "static/images/logos/wpa.png"
        if os.path.exists(wpa_logo_path):
            canvas.drawImage(wpa_logo_path, page_width - 110, page_height - 80, width=80, height=50,
                             preserveAspectRatio=True, mask='auto')
        footer_y = 20
        footer_logos = [
            ("static/images/logos/tunisian.png", 50),
            ("static/images/logos/monoprix.png", page_width / 2 - 40),
            ("static/images/logos/partner3.png", page_width - 130)
        ]
        for logo_path, x_pos in footer_logos:
            if os.path.exists(logo_path):
                canvas.drawImage(logo_path, x_pos, footer_y, width=80, height=25,
                                 preserveAspectRatio=True, mask='auto')
        canvas.setFont("Helvetica", 8)
        canvas.drawString(30, footer_y + 30, f"Report Created: {datetime.now().strftime('%a %d %b %Y %H:%M')}")
        canvas.drawRightString(page_width - 30, footer_y + 30, "Page 1/1")
    def generate_results_pdf(self, game, results, include_attempts=True):
        buffer = BytesIO()
        pagesize = landscape(A4) if self._needs_landscape(game, results) else A4
        doc = SimpleDocTemplate(buffer, pagesize=pagesize,
                                topMargin=100, rightMargin=30, leftMargin=30, bottomMargin=70)
        story = []
        story.append(Paragraph("Rades Stadium", self.location_style))
        story.append(Paragraph("Tunis 2025 Para Athletics Grand Prix", self.comp_title_style))
        story.append(Paragraph("Tunis (Tunisia)", self.location_style))
        story.append(Paragraph("9-17 July 2025", self.location_style))
        story.append(Spacer(1, 15))
        gender_str = game.get('gender') or 'Mixed'
        if ',' in gender_str:
            genders = [g.strip() for g in gender_str.split(',') if g.strip()]
        else:
            genders = [gender_str] if gender_str else ['Mixed']
        gender_text = ' & '.join(genders)
        classes_str = game.get('classes') or 'Open'
        event_title = f"{gender_text} {game['event']} {classes_str}"
        story.append(Paragraph(event_title, self.event_title_style))
        phase = game.get('phase') or 'Final'
        story.append(Paragraph(phase, self.phase_style))
        story.append(Paragraph("Results", self.results_title_style))
        self._add_record_section(story, game, results)
        game_time = game.get('time', 'TBD')
        story.append(Paragraph(f"Start Time: {game_time}  End Time: -", self.record_style))
        story.append(Spacer(1, 10))
        if game['event'] == 'High Jump':
            table = self._create_high_jump_results_table(game, results)
        elif game['event'] in ['Long Jump', 'Triple Jump']:
            table = self._create_horizontal_jump_table(game, results)
        elif game['event'] in ['Shot Put', 'Discus Throw', 'Javelin Throw', 'Club Throw']:
            table = self._create_throwing_events_table(game, results)
        elif game['event'] in Config.get_track_events():
            table = self._create_track_results_table(game, results)
        else:
            table = self._create_generic_table(game, results)
        story.append(table)
        if game['event'] in Config.get_wind_affected_field_events() or game['event'] in Config.get_track_events():
            self._add_weather_section(story, game)
        self._add_legend_section(story, game)
        doc.build(story, onFirstPage=self.create_header_footer, onLaterPages=self.create_header_footer)
        buffer.seek(0)
        return buffer
    def _needs_landscape(self, game, results):
        if game['event'] == 'High Jump':
            heights = set()
            for result in results:
                if result.get('attempts'):
                    for attempt in result['attempts']:
                        if attempt.get('height'):
                            heights.add(float(attempt['height']))
            return len(heights) > 6
        elif game['event'] in ['Shot Put', 'Discus Throw', 'Javelin Throw', 'Club Throw']:
            return True
        return False
    def _add_record_section(self, story, game, results):
        record_holders = {}
        for result in results:
            if result.get('record') in ['WR', 'AR', 'CR']:
                record_holders[result['record']] = {
                    'athlete': f"{result['firstname']} {result['lastname']}",
                    'npc': result['npc'],
                    'performance': result['value'],
                    'location': 'Tunis (TUN)',
                    'date': datetime.now().strftime('%d %b %Y')
                }
        if game['classes'] in ['T47', 'F13', 'T13']:
            record_data = [
                ['T46 L', '', '', '', '', '', ''],
                ['WORLD RECORD', '2.15', 'TOWNSEND Roderick', 'USA', 'Tokyo (JPN)', '', '29 AUG 2021'],
                ['T47 L', '', '', '', '', '', ''],
                ['WORLD RECORD', '2.15', 'TOWNSEND Roderick', 'USA', 'Tokyo (JPN)', '', '29 AUG 2021'],
                ['CHAMPIONSHIP RECORD', '2.10', 'TOWNSEND Roderick', 'USA', 'London (GBR)', '', '16 JUL 2017']
            ]
            record_table = Table(record_data, colWidths=[80, 40, 100, 40, 80, 30, 80])
            record_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 2),
                ('RIGHTPADDING', (0, 0), (-1, -1), 2),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            story.append(record_table)
            story.append(Spacer(1, 15))
    def _create_high_jump_results_table(self, game, results):
        all_heights = set()
        for result in results:
            if result.get('attempts'):
                for attempt in result['attempts']:
                    if attempt.get('height'):
                        all_heights.add(float(attempt['height']))
        sorted_heights = sorted(all_heights)
        headers = ['Rank', 'Bib', 'Name', 'NPC Code', 'Date of Birth', 'Sport Class']
        for height in sorted_heights:
            headers.append(f"{height:.2f}")
        headers.append('Result')
        base_widths = [30, 30, 120, 40, 60, 40]
        height_widths = [25] * len(sorted_heights)
        result_width = [40]
        col_widths = base_widths + height_widths + result_width
        data = []
        for i, result in enumerate(results):
            row = [
                result.get('rank', str(i + 1)),
                str(result['athlete_sdms']),
                f"{result['lastname']} {result['firstname']}",
                result['npc'],
                result.get('date_of_birth', '1 JUL 1992'),
                result['athlete_class']
            ]
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
            final_result = self._format_performance(result['value'], game['event'])
            if result.get('record'):
                final_result += f" {result['record']}"
            row.append(final_result)
            data.append(row)
        table = Table([headers] + data, colWidths=col_widths, repeatRows=1)
        table.setStyle(self._get_high_jump_table_style(len(headers), len(data)))
        return table
    def _create_horizontal_jump_table(self, game, results):
        headers = ['Rank', 'Bib', 'Name', 'NPC Code', 'Date of Birth', 'Sport Class']
        for i in range(1, 7):
            headers.append(str(i))
        headers.append('Result')
        if game.get('wpa_points'):
            headers.append('Points')
        base_widths = [30, 30, 120, 40, 60, 40]
        attempt_widths = [35] * 6
        result_widths = [50, 40] if game.get('wpa_points') else [50]
        col_widths = base_widths + attempt_widths + result_widths
        data = []
        for i, result in enumerate(results):
            row = [
                result.get('rank', str(i + 1)),
                str(result['athlete_sdms']),
                f"{result['lastname']} {result['firstname']}",
                result['npc'],
                result.get('date_of_birth', '1 JUL 1992'),
                result['athlete_class']
            ]
            attempts = result.get('attempts', [])
            for attempt_num in range(1, 7):
                attempt = next((a for a in attempts if a['attempt_number'] == attempt_num), None)
                if attempt and attempt.get('value'):
                    attempt_str = self._format_attempt_value(attempt['value'])
                    if attempt.get('wind_velocity') is not None:
                        attempt_str += f"\n{attempt['wind_velocity']:+.1f}"
                    row.append(attempt_str)
                else:
                    row.append('-')
            final_result = self._format_performance(result['value'], game['event'])
            if result.get('record'):
                final_result += f" {result['record']}"
            row.append(final_result)
            if game.get('wpa_points'):
                row.append(str(result.get('raza_score', '')))
            data.append(row)
        table = Table([headers] + data, colWidths=col_widths, repeatRows=1)
        table.setStyle(self._get_field_table_style(len(headers), len(data)))
        return table
    def _create_throwing_events_table(self, game, results):
        headers = ['Rank', 'Bib', 'Name', 'NPC Code', 'Date of Birth', 'Sport Class']
        for i in range(1, 7):
            headers.append(str(i))
        headers.append('Result')
        if game.get('wpa_points'):
            headers.append('Points')
        base_widths = [35, 35, 140, 45, 70, 45]
        attempt_widths = [40] * 6
        result_widths = [55, 45] if game.get('wpa_points') else [55]
        col_widths = base_widths + attempt_widths + result_widths
        data = []
        for i, result in enumerate(results):
            row = [
                result.get('rank', str(i + 1)),
                str(result['athlete_sdms']),
                f"{result['lastname']} {result['firstname']}",
                result['npc'],
                result.get('date_of_birth', '22 JAN 1998'),
                result['athlete_class']
            ]
            attempts = result.get('attempts', [])
            for attempt_num in range(1, 7):
                attempt = next((a for a in attempts if a['attempt_number'] == attempt_num), None)
                if attempt and attempt.get('value'):
                    row.append(self._format_attempt_value(attempt['value']))
                else:
                    row.append('-')
            final_result = self._format_performance(result['value'], game['event'])
            if result.get('record'):
                final_result += f" {result['record']}"
            row.append(final_result)
            if game.get('wpa_points'):
                row.append(str(result.get('raza_score', '')))
            data.append(row)
        starting_order = ['Starting order'] + [''] * (len(headers) - 7)
        attempt_order = [str(i + 1) for i in range(6)]
        starting_order.extend(attempt_order)
        starting_order.append('')
        if game.get('wpa_points'):
            starting_order.append('')
        data.append(starting_order)
        table = Table([headers] + data, colWidths=col_widths, repeatRows=1)
        table.setStyle(self._get_throwing_table_style(len(headers), len(data)))
        return table
    def _create_track_results_table(self, game, results):
        headers = ['Rank', 'Bib', 'Name', 'NPC Code', 'Date of Birth', 'Sport Class', 'Lane', 'Reaction Time', 'Result']
        if game.get('wpa_points'):
            headers.append('Points')

        base_widths = [35, 35, 120, 45, 70, 45, 35, 50, 60]
        if game.get('wpa_points'):
            base_widths.append(40)
        col_widths = base_widths
        data = []
        for i, result in enumerate(results):
            row = [
                result.get('rank', str(i + 1)),
                str(result['athlete_sdms']),
                f"{result['lastname']} {result['firstname']}",
                result['npc'],
                result.get('date_of_birth', '5 APR 2002'),
                result['athlete_class'],
                str(i + 1),
                '0.165',
                self._format_performance_with_record(result['value'], result.get('record'), game['event'])
            ]
            if game.get('wpa_points'):
                points = f"({result.get('raza_score', '')}.983)" if result.get('raza_score') else ''
                row.append(points)
            data.append(row)

        if game['event'] in Config.get_wind_affected_field_events():
            wind_row = ['Wind: +0.3 m/s'] + [''] * (len(headers) - 1)
            data.insert(0, wind_row)
        table = Table([headers] + data, colWidths=col_widths, repeatRows=1)
        table.setStyle(self._get_track_table_style(len(headers), len(data)))
        return table
    def _add_weather_section(self, story, game):
        if game['event'] in Config.get_wind_affected_field_events() or game['event'] in Config.get_track_events():
            story.append(Spacer(1, 15))
            weather_data = [
                ['Weather conditions', '', 'Temperature', '', 'Humidity', '', 'Conditions'],
                ['Start of the event:', '', '24°C', '', '58%', '', 'Medium-level cloud'],
                ['End of the event:', '', '24°C', '', '51%', '', 'Medium-level cloud']
            ]
            weather_table = Table(weather_data, colWidths=[80, 20, 60, 20, 50, 20, 80])
            weather_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
                ('FONTNAME', (4, 0), (4, -1), 'Helvetica-Bold'),
                ('FONTNAME', (6, 0), (6, -1), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(weather_table)
    def _add_legend_section(self, story, game):
        story.append(Spacer(1, 10))
        legend_items = []
        if game['event'] in Config.get_field_events():
            legend_items = [
                ('X', 'Pass', 'AR', 'Area Record', 'PB', 'Personal Best', 'SB', 'Season Best')
            ]
        else:
            legend_items = [
                ('SB', 'Season Best')
            ]
        if legend_items:
            legend_table = Table(legend_items)
            legend_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 15),
            ]))
            story.append(legend_table)
    def _format_performance(self, value, event):
        if value in Config.get_result_special_values():
            return value
        if event in Config.get_field_events():
            try:
                return f"{float(value):.2f}"
            except (ValueError, TypeError):
                return str(value)
        elif event in Config.get_track_events():
            return str(value)
        return str(value)
    def _format_performance_with_record(self, value, record, event):
        formatted = self._format_performance(value, event)
        if record:
            formatted += f" {record}"
        return formatted
    def _format_attempt_value(self, value):
        if value in ['X', 'O', '-']:
            return value
        try:
            return f"{float(value):.2f}"
        except (ValueError, TypeError):
            return str(value)
    def _get_high_jump_table_style(self, num_cols, num_rows):
        style = [

            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E6E6E6')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),

            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
            ('ALIGN', (2, 1), (2, -1), 'LEFT'),
            ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),

            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),

            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]
        return TableStyle(style)
    def _get_field_table_style(self, num_cols, num_rows):
        return self._get_high_jump_table_style(num_cols, num_rows)
    def _get_throwing_table_style(self, num_cols, num_rows):
        style = self._get_high_jump_table_style(num_cols, num_rows)

        if num_rows > 1:
            style.extend([
                ('BACKGROUND', (0, num_rows), (-1, num_rows), colors.HexColor('#F0F0F0')),
                ('FONTNAME', (0, num_rows), (0, num_rows), 'Helvetica-Bold'),
                ('FONTSIZE', (0, num_rows), (-1, num_rows), 7),
            ])
        return TableStyle(style)
    def _get_track_table_style(self, num_cols, num_rows):
        return self._get_high_jump_table_style(num_cols, num_rows)
    def _create_generic_table(self, game, results):
        return self._create_track_results_table(game, results)
    def generate_startlist_pdf(self, game, startlist):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                topMargin=100, rightMargin=30, leftMargin=30, bottomMargin=70)
        story = []

        story.append(Paragraph("Charlety Stadium", self.location_style))
        story.append(Paragraph("Tunis 2025 Para Athletics Grand Prix", self.comp_title_style))
        story.append(Paragraph("Tunis (Tunisia)", self.location_style))
        story.append(Paragraph("9-17 July 2025", self.location_style))
        story.append(Spacer(1, 15))

        gender_str = game.get('gender') or 'Mixed'
        if ',' in gender_str:
            genders = [g.strip() for g in gender_str.split(',') if g.strip()]
        else:
            genders = [gender_str] if gender_str else ['Mixed']
        gender_text = ' & '.join(genders)
        classes_str = game.get('classes') or 'Open'
        event_title = f"{gender_text} {game['event']} {classes_str}"
        story.append(Paragraph(event_title, self.event_title_style))

        phase = game.get('phase', 'Final')
        story.append(Paragraph(phase, self.phase_style))

        story.append(Paragraph("Start List", self.results_title_style))
        story.append(Spacer(1, 10))

        headers = ['Lane/Order', 'Bib', 'Name', 'NPC', 'Date of Birth', 'Sport Class', 'Guide', 'Result']
        col_widths = [50, 40, 120, 40, 70, 50, 60, 80]
        data = []
        for i, entry in enumerate(startlist):
            row = [
                str(entry.get('lane_order', i + 1)),
                str(entry['athlete_sdms']),
                f"{entry['lastname']} {entry['firstname']}",
                entry['npc'],
                entry.get('date_of_birth', '1 JAN 1990'),
                entry['class'],
                str(entry['guide_sdms']) if entry.get('guide_sdms') else '',
                ''
            ]
            data.append(row)
        table = Table([headers] + data, colWidths=col_widths, repeatRows=1)
        table.setStyle(self._get_high_jump_table_style(len(headers), len(data)))
        story.append(table)
        doc.build(story, onFirstPage=self.create_header_footer, onLaterPages=self.create_header_footer)
        buffer.seek(0)
        return buffer