import io
import os

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)
from reportlab.lib import colors
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.pdfgen import canvas
from config import Config
from datetime import datetime


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        self.game_title = kwargs.pop("game_title", "")
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for page_num, page_state in enumerate(self._saved_page_states):
            self.__dict__.update(page_state)
            self.draw_header_and_footer(page_num + 1, num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_num, total_pages):
        width, height = A4

        # Header avec titre du game
        if self.game_title:
            self.setFont("Helvetica-Bold", 10)
            # Calculate center position and draw centered text
            text_width = self.stringWidth(
                self.game_title, "Helvetica-Bold", 10
            )
            x_position = (width - text_width) / 2
            self.drawString(x_position, height - 15 * mm, self.game_title)

        # Footer avec numéro de page
        self.setFont("Helvetica", 8)
        self.drawRightString(
            width - 10 * mm, 15 * mm, f"Page {page_num} of {total_pages}"
        )

        # Date de génération
        self.drawString(
            10 * mm,
            15 * mm,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        )

    def draw_header_and_footer(self, page_num, total_pages):
        # --- Header ---
        try:
            # Logo gauche
            logo_path = os.path.join("static", "images", "logo.png")
            if os.path.exists(logo_path):
                self.drawImage(
                    logo_path,
                    15 * mm,
                    A4[1] - 25 * mm,
                    width=25 * mm,
                    height=15 * mm,
                    preserveAspectRatio=True,
                    mask="auto",
                )

            # Logo droit
            pa_logo_path = os.path.join("static", "images", "logos", "wpa.png")
            if os.path.exists(pa_logo_path):
                self.drawImage(
                    pa_logo_path,
                    A4[0] - 40 * mm,
                    A4[1] - 25 * mm,
                    width=25 * mm,
                    height=15 * mm,
                    preserveAspectRatio=True,
                    mask="auto",
                )
        except Exception:
            pass

        # Titre centré entre les logos
        if self.game_title:
            self.setFont("Helvetica-Bold", 12)
            title_y = A4[1] - 17.5 * mm

            left_logo_end = 15 * mm + 25 * mm
            right_logo_start = A4[0] - 40 * mm
            available_width = right_logo_start - left_logo_end
            center_x = left_logo_end + (available_width / 2)

            text_width = self.stringWidth(self.game_title, "Helvetica-Bold", 12)
            self.drawString(center_x - text_width / 2, title_y, self.game_title)

        # --- Footer ---
        # Numéro de page
        self.setFont("Helvetica", 8)
        self.drawRightString(
            A4[0] - 15 * mm, 15 * mm, f"Page {page_num} / {total_pages}"
        )

        # Date de génération
        generation_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.setFont("Helvetica", 6)
        self.drawString(15 * mm, 15 * mm, f"Generated on {generation_date}")

        # Logos sponsors
        try:
            footer_logos = [
                "basar.png",
                "ministere.png",
                "monoprix.png",
                "nextstep.png",
                "npc.png",
                "wpa.png",
            ]
            logo_width = 15 * mm
            total_width = len(footer_logos) * logo_width
            start_x = (A4[0] - total_width) / 2

            for i, logo_file in enumerate(footer_logos):
                logo_path = os.path.join("static", "images", "logos", logo_file)
                if os.path.exists(logo_path):
                    x_pos = start_x + (i * logo_width)
                    self.drawImage(
                        logo_path,
                        x_pos,
                        5 * mm,
                        width=12 * mm,
                        height=8 * mm,
                        preserveAspectRatio=True,
                        mask="auto",
                    )
        except Exception:
            pass

class PDFGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._add_custom_styles()

    def _add_custom_styles(self):
        self.styles.add(
            ParagraphStyle(
                name="PDFMainTitle",
                parent=self.styles["Title"],
                fontSize=16,
                spaceAfter=8,
                alignment=TA_CENTER,
                fontName="Helvetica-Bold",
            )
        )

        self.styles.add(
            ParagraphStyle(
                name="PDFEventTitle",
                parent=self.styles["Heading1"],
                fontSize=12,
                spaceAfter=6,
                alignment=TA_CENTER,
                fontName="Helvetica-Bold",
            )
        )

        self.styles.add(
            ParagraphStyle(
                name="PDFVenue",
                parent=self.styles["Normal"],
                fontSize=9,
                spaceAfter=4,
                alignment=TA_CENTER,
                fontName="Helvetica",
            )
        )

        self.styles.add(
            ParagraphStyle(
                name="PDFStatus",
                parent=self.styles["Normal"],
                fontSize=8,
                spaceAfter=6,
                alignment=TA_LEFT,
                fontName="Helvetica-Bold",
                textColor=colors.blue,
            )
        )

    def format_gender_title(self, gender):
        if gender == "Male":
            return "Men"
        elif gender == "Female":
            return "Women"
        else:
            return gender

    def create_status_text(self, status_info):
        """Créer le texte de statut pour officialisation et correction"""
        status_parts = []

        # Statut d'officialisation
        if status_info.get("official"):
            official_text = "OFFICIAL"
            if status_info.get("official_date"):
                official_text += f" - {status_info['official_date'].strftime('%Y-%m-%d %H:%M')}"
            status_parts.append(official_text)
        else:
            status_parts.append("UNOFFICIAL")

        # Statut de correction
        if status_info.get("corrected"):
            corrected_text = "CORRECTED"
            if status_info.get("corrected_date"):
                corrected_text += f" - {status_info['corrected_date'].strftime('%Y-%m-%d %H:%M')}"
            status_parts.append(corrected_text)

        return " | ".join(status_parts) if status_parts else ""

    def generate_results_pdf(
        self, game, results, heat_group=None, combined_results=None
    ):
        buffer = io.BytesIO()

        # Créer le titre pour le header
        gender_title = self.format_gender_title(game["genders"])
        game_title = f"{gender_title} {game['event']} {game['classes']}"
        if game.get("phase"):
            game_title += f" - {game['phase']}"
        game_title += " - Results"

        # Créer le canvas maker avec le titre
        def make_canvas(*args, **kwargs):
            kwargs["game_title"] = game_title
            return NumberedCanvas(*args, **kwargs)

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            topMargin=35 * mm,
            bottomMargin=25 * mm,
            leftMargin=10 * mm,
            rightMargin=10 * mm,
        )

        story = []

        # Ajouter les infos de base
        story.append(
            Paragraph(
                "World Para Athletics Grand Prix", self.styles["PDFMainTitle"]
            )
        )
        story.append(
            Paragraph(
                "Rades Stadium, Tunis, Tunisia", self.styles["PDFVenue"]
            )
        )
        story.append(
            Paragraph(f"Day {game['day']} - {game['time']}", self.styles["PDFVenue"])
        )
        story.append(Spacer(1, 3 * mm))

        # Déterminer le statut global pour les heats ou utiliser le statut du jeu individuel
        game_heat_group_id = game.get("heat_group_id")
        if game_heat_group_id or heat_group:
            from database.models.heat_group import HeatGroup
            from database.models.result import Result
            from database.models.game import Game as GameModel

            heat_group_id = (
                heat_group["id"] if heat_group else game_heat_group_id
            )
            all_heat_games = HeatGroup.get_games(heat_group_id)

            # Enrichir les données des heat games avec les statuts
            enriched_heat_games = []
            for heat_game in all_heat_games:
                enriched_game = GameModel.get_by_id(heat_game["id"])
                enriched_heat_games.append(enriched_game)

            # Déterminer le statut global
            all_official = all(
                hg.get("official", False) for hg in enriched_heat_games
            )
            any_official = any(
                hg.get("official", False) for hg in enriched_heat_games
            )
            all_corrected = all(
                hg.get("corrected", False) for hg in enriched_heat_games
            )
            any_corrected = any(
                hg.get("corrected", False) for hg in enriched_heat_games
            )

            # Déterminer les dates (prendre la plus récente)
            official_dates = [
                hg.get("official_date")
                for hg in enriched_heat_games
                if hg.get("official_date")
            ]
            corrected_dates = [
                hg.get("corrected_date")
                for hg in enriched_heat_games
                if hg.get("corrected_date")
            ]

            latest_official_date = max(official_dates) if official_dates else None
            latest_corrected_date = (
                max(corrected_dates) if corrected_dates else None
            )

            global_status = {
                "official": all_official,
                "corrected": all_corrected,
                "official_date": latest_official_date,
                "corrected_date": latest_corrected_date,
            }
        else:
            global_status = {
                "official": game.get("official", False),
                "corrected": game.get("corrected", False),
                "official_date": game.get("official_date"),
                "corrected_date": game.get("corrected_date"),
            }

        # Ajouter les mentions de statut en haut à gauche
        status_text = self.create_status_text(global_status)
        if status_text:
            story.append(Paragraph(status_text, self.styles["PDFStatus"]))
            story.append(Spacer(1, 5 * mm))

        # Gestion des heats ou jeu individuel
        if game_heat_group_id or heat_group:
            from database.models.heat_group import HeatGroup
            from database.models.result import Result

            heat_group_id = (
                heat_group["id"] if heat_group else game_heat_group_id
            )
            all_heat_games = HeatGroup.get_games(heat_group_id)
            all_heat_games = sorted(
                all_heat_games, key=lambda x: x.get("heat_number", 0)
            )

            for heat_game in all_heat_games:
                story.append(
                    Paragraph(
                        f"Heat {heat_game.get('heat_number', '?')} Results",
                        self.styles["PDFEventTitle"],
                    )
                )
                story.append(Spacer(1, 3 * mm))

                # Ajouter la vitesse du vent pour ce heat spécifique
                if (
                    heat_game.get("wind_velocity") is not None
                    and heat_game["event"] in Config.get_track_events()
                ):
                    wind_text = f"Wind: {heat_game['wind_velocity']:+.1f} m/s"
                    story.append(Paragraph(wind_text, self.styles["PDFVenue"]))
                    story.append(Spacer(1, 3 * mm))

                heat_results = Result.get_all(game_id=heat_game["id"])

                if heat_results:
                    if heat_game["event"] == "High Jump":
                        table = self.create_high_jump_table(
                            heat_game, heat_results
                        )
                    elif heat_game["event"] in Config.get_field_events():
                        table = self.create_field_event_table(
                            heat_game, heat_results
                        )
                    else:
                        table = self.create_track_event_table(
                            heat_results, heat_game
                        )

                    story.append(table)
                    story.append(Spacer(1, 8 * mm))

            # Résultats combinés
            if combined_results:
                story.append(PageBreak())
                story.append(
                    Paragraph(
                        "Final Combined Results", self.styles["PDFEventTitle"]
                    )
                )
                story.append(Spacer(1, 5 * mm))

                combined_table = self.create_combined_results_table(
                    combined_results, game
                )
                story.append(combined_table)
            else:
                story.append(PageBreak())
                story.append(
                    Paragraph(
                        "Final Combined Results", self.styles["PDFEventTitle"]
                    )
                )
                story.append(Spacer(1, 5 * mm))

                auto_combined_results = HeatGroup.get_combined_results(
                    heat_group_id
                )
                if auto_combined_results:
                    combined_table = self.create_combined_results_table(
                        auto_combined_results, game
                    )
                    story.append(combined_table)

        else:
            # Game individuel - afficher le vent du game principal
            if (
                game.get("wind_velocity") is not None
                and game["event"] in Config.get_track_events()
            ):
                wind_text = f"Wind: {game['wind_velocity']:+.1f} m/s"
                story.append(Paragraph(wind_text, self.styles["PDFVenue"]))
                story.append(Spacer(1, 3 * mm))

            if game["event"] == "High Jump":
                table = self.create_high_jump_table(game, results)
            elif game["event"] in Config.get_field_events():
                table = self.create_field_event_table(game, results)
            else:
                table = self.create_track_event_table(results, game)

            story.append(table)

        doc.build(story, canvasmaker=make_canvas)
        buffer.seek(0)
        return buffer

    def create_track_event_table(self, results, game):
        headers = [
            "Rank",
            "Lane",
            "SDMS",
            "First Name",
            "Last Name",
            "Gender",
            "NPC",
            "Class",
            "Electronic",
        ]

        if game.get("wpa_points", False):
            headers.append("WPA Points")

        data = [headers]

        for i, result in enumerate(results, 1):
            # Créer le texte de rang avec les records
            rank_text = result["rank"] or str(i)
            if result.get("is_world_record"):
                rank_text += " WR"
            if result.get("is_area_record") and result.get("ar_region"):
                rank_text += f" AR ({result['ar_region']})"

            row = [
                rank_text,
                str(i),
                str(result["athlete_sdms"]),
                result["firstname"] or "",
                result["lastname"] or "",
                result["athlete_gender"] or "",
                result["npc"] or "",
                (
                    result.get("athlete_class", "").split(",")[0]
                    if result.get("athlete_class")
                    else ""
                ),
                (
                    Config.format_time(result["value"], True)
                    if result["value"] not in Config.get_result_special_values()
                    else result["value"]
                ),
            ]

            if game.get("wpa_points", False):
                row.append(
                    str(result["raza_score"]) if result.get("raza_score") else ""
                )

            data.append(row)

        table = Table(data, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.Color(0.8, 0.9, 1.0),
                    ),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 7),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("TOPPADDING", (0, 0), (-1, 0), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 6),
                    ("ALIGN", (0, 1), (-1, -1), "CENTER"),
                    ("TOPPADDING", (0, 1), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 1), (-1, -1), 2),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )

        return table

    def create_field_event_table(self, game, results):
        headers = [
            "Rank",
            "Order",
            "SDMS",
            "First Name",
            "Last Name",
            "Gender",
            "NPC",
        ]

        if game["event"] in Config.get_weight_field_events():
            headers.append("Weight")

        if game["event"] in Config.get_r1_qualifying_classes():
            headers.append("R1/P1")
        headers.extend(["Class", "Performance"])

        if game.get("wpa_points", False):
            headers.append("WPA Points")

        data = [headers]
        athlete_rows = []

        for i, result in enumerate(results, 1):
            # Créer le texte de rang avec les records
            rank_text = result["rank"] or str(i)
            if result.get("is_world_record"):
                rank_text += " WR"
            if result.get("is_area_record") and result.get("ar_region"):
                rank_text += f" AR ({result['ar_region']})"

            row = [
                rank_text,
                str(i),
                str(result["athlete_sdms"]),
                result["firstname"] or "",
                result["lastname"] or "",
                result["athlete_gender"] or "",
                result["npc"] or "",
            ]

            if game["event"] in Config.get_weight_field_events():
                weight_val = (
                    f"{result['weight']:.3f} kg"
                    if result.get("weight")
                    else "3.000 kg"
                )
                row.append(weight_val)

            if game["event"] in Config.get_r1_qualifying_classes():
                total_finalists = len(
                    [r for r in results if r.get("final_order")]
                )
                r1_order = (
                    f"{result['final_order']}/{total_finalists}"
                    if result.get("final_order")
                    else ""
                )
                row.append(r1_order)

            row.extend(
                [
                    (
                        result.get("athlete_class", "").split(",")[0]
                        if result.get("athlete_class")
                        else ""
                    ),
                    (
                        Config.format_distance(result["value"])
                        if result["value"]
                        not in Config.get_result_special_values()
                        else result["value"]
                    ),
                ]
            )

            if game.get("wpa_points", False):
                row.append(
                    str(result["raza_score"]) if result.get("raza_score") else ""
                )

            data.append(row)
            athlete_rows.append(len(data) - 1)

            # Ajouter les tentatives
            attempts = result.get("attempts", [])
            for attempt_num in range(1, 7):
                attempt = next(
                    (
                        a
                        for a in attempts
                        if a["attempt_number"] == attempt_num
                    ),
                    None,
                )

                attempt_row = [""] * len(headers)
                attempt_row[1] = f"Attempt {attempt_num}"

                if attempt and attempt.get("value"):
                    attempt_row[2] = attempt["value"]

                    if game.get("wpa_points", False) and attempt.get(
                        "raza_score"
                    ):
                        attempt_row[3] = str(attempt["raza_score"])

                    if (
                        game["event"] in Config.get_wind_affected_field_events()
                        and attempt.get("wind_velocity")
                    ):
                        wind_col = 4 if game.get("wpa_points", False) else 3
                        attempt_row[
                            wind_col
                        ] = f"{attempt['wind_velocity']:+.2f} m/s"

                data.append(attempt_row)

        table = Table(data, repeatRows=1)

        style_commands = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.8, 0.9, 1.0)),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 6),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, 0), 3),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 3),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 6),
            ("ALIGN", (0, 1), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 1), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 1),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]

        for row_idx in athlete_rows:
            style_commands.append(
                (
                    "BACKGROUND",
                    (0, row_idx),
                    (-1, row_idx),
                    colors.Color(0.9, 0.95, 1.0),
                )
            )
            style_commands.append(
                ("FONTNAME", (0, row_idx), (-1, row_idx), "Helvetica-Bold")
            )

        table.setStyle(TableStyle(style_commands))
        return table

    def create_high_jump_table(self, game, results):
        headers = [
            "Rank",
            "Order",
            "SDMS",
            "First Name",
            "Last Name",
            "Gender",
            "NPC",
            "Class",
            "Best",
            "Failures",
        ]

        if game.get("wpa_points", False):
            headers.append("WPA Points")

        data = [headers]

        for i, result in enumerate(results, 1):
            # Créer le texte de rang avec les records
            rank_text = result["rank"] or str(i)
            if result.get("is_world_record"):
                rank_text += " WR"
            if result.get("is_area_record") and result.get("ar_region"):
                rank_text += f" AR ({result['ar_region']})"

            failures_text = ""
            attempts = result.get("attempts", [])
            if attempts:
                max_height = (
                    float(result["value"])
                    if result["value"] not in Config.get_result_special_values()
                    else 0
                )
                failures_at_max = 0
                total_failures = 0

                for attempt in attempts:
                    if attempt.get("height") and attempt.get("value"):
                        try:
                            height = float(attempt["height"])
                            value = str(attempt["value"]).upper().strip()

                            failure_count = 0
                            if value == "X":
                                failure_count = 1
                            elif value == "XO":
                                failure_count = 1
                            elif value == "XXO":
                                failure_count = 2

                            total_failures += failure_count

                            if abs(height - max_height) < 0.001:
                                failures_at_max += failure_count

                        except (ValueError, TypeError):
                            continue

                failures_text = f"{failures_at_max}/{total_failures}"

            row = [
                rank_text,
                str(i),
                str(result["athlete_sdms"]),
                result["firstname"] or "",
                result["lastname"] or "",
                result["athlete_gender"] or "",
                result["npc"] or "",
                (
                    result.get("athlete_class", "").split(",")[0]
                    if result.get("athlete_class")
                    else ""
                ),
                (
                    f"{result['value']} m"
                    if result["value"] not in Config.get_result_special_values()
                    else result["value"]
                ),
                failures_text,
            ]

            if game.get("wpa_points", False):
                row.append(
                    str(result["raza_score"]) if result.get("raza_score") else ""
                )

            data.append(row)

        table = Table(data, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.Color(0.8, 0.9, 1.0),
                    ),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 7),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("TOPPADDING", (0, 0), (-1, 0), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 6),
                    ("ALIGN", (0, 1), (-1, -1), "CENTER"),
                    ("TOPPADDING", (0, 1), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 1), (-1, -1), 2),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )

        return table

    def create_combined_results_table(self, combined_results, game):
        headers = [
            "Rank",
            "Heat",
            "Wind",
            "SDMS",
            "First Name",
            "Last Name",
            "NPC",
            "Class",
            "Performance",
        ]
        if game.get("wpa_points", False):
            headers.append("WPA Points")

        data = [headers]
        for result in combined_results:
            # Créer le texte de rang avec les records
            rank_text = str(result.get("rank", ""))
            if result.get("is_world_record"):
                rank_text += " WR"
            if result.get("is_area_record") and result.get("ar_region"):
                rank_text += f" AR ({result['ar_region']})"

            row = [
                rank_text,
                f"Heat {result.get('heat_number', '')}",
                (
                    f"{Config.format_wind(result.get('wind_velocity', ''))} m/s"
                    if result.get("wind_velocity")
                    else ""
                ),
                str(result["athlete_sdms"]),
                result["firstname"] or "",
                result["lastname"] or "",
                result["npc"] or "",
                (
                    result.get("athlete_class", "").split(",")[0]
                    if result.get("athlete_class")
                    else ""
                ),
                (
                    Config.format_time(result["value"], True)
                    if result["value"] not in Config.get_result_special_values()
                    else result["value"]
                ),
            ]

            if game.get("wpa_points", False):
                row.append(
                    str(result["raza_score"]) if result.get("raza_score") else ""
                )

            data.append(row)

        table = Table(data, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.Color(0.8, 0.9, 1.0),
                    ),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 7),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("TOPPADDING", (0, 0), (-1, 0), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 6),
                    ("ALIGN", (0, 1), (-1, -1), "CENTER"),
                    ("TOPPADDING", (0, 1), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 1), (-1, -1), 2),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )

        return table

    def generate_startlist_pdf(self, game, startlist):
        buffer = io.BytesIO()

        # Créer le titre pour le header
        gender_title = self.format_gender_title(game["genders"])
        game_title = f"{gender_title} {game['event']} {game['classes']}"
        if game.get("phase"):
            game_title += f" - {game['phase']}"
        game_title += " - Start List"

        # Créer le canvas maker avec le titre
        def make_canvas(*args, **kwargs):
            kwargs["game_title"] = game_title
            return NumberedCanvas(*args, **kwargs)

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            topMargin=35 * mm,
            bottomMargin=25 * mm,
            leftMargin=10 * mm,
            rightMargin=10 * mm,
        )

        story = []

        # Ajouter les infos de base
        story.append(
            Paragraph(
                "World Para Athletics Grand Prix", self.styles["PDFMainTitle"]
            )
        )
        story.append(
            Paragraph(
                "Rades Stadium, Tunis, Tunisia", self.styles["PDFVenue"]
            )
        )
        story.append(
            Paragraph(f"Day {game['day']} - {game['time']}", self.styles["PDFVenue"])
        )
        story.append(Spacer(1, 5 * mm))

        story.append(
            Paragraph("Start List", self.styles["PDFEventTitle"])
        )
        story.append(Spacer(1, 5 * mm))

        headers = [
            "Lane",
            "SDMS",
            "First Name",
            "Last Name",
            "NPC",
            "Class",
            "Gender",
        ]
        has_guide_column = startlist and any(
            entry.get("guide_sdms") for entry in startlist
        )
        if has_guide_column:
            headers.append("Guide")

        available_width = A4[0] - doc.leftMargin - doc.rightMargin
        weights = [8, 12, 20, 20, 8, 8, 9]
        if has_guide_column:
            weights.append(15)
        total_weight = sum(weights)
        data_col_widths = [
            (w / total_weight) * available_width for w in weights
        ]

        header_table = Table([headers], colWidths=data_col_widths)
        header_table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.Color(0.8, 0.9, 1.0),
                    ),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 7),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, 0), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.darkgrey),
                ]
            )
        )
        story.append(header_table)

        athlete_row_style = TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 6),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.darkgrey),
            ]
        )

        spacer_row_style = TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.Color(0.95, 0.95, 0.95)),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.darkgrey),
                # Définir une hauteur minimale pour que la ligne soit visible
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )

        spacer_data = [[""] * 8]
        spacer_col_widths = [available_width / 8] * 8

        for entry in startlist:
            # Créer la table pour la ligne de l'athlète
            row_data = [
                str(entry["lane_order"]) if entry.get("lane_order") else "",
                str(entry["athlete_sdms"]),
                entry["firstname"] or "",
                entry["lastname"] or "",
                entry["npc"] or "",
                entry["class"] or "",
                entry["gender"] or "",
            ]
            if has_guide_column:
                guide_info = ""
                if entry.get("guide_sdms"):
                    guide_info = f"{entry.get('guide_firstname', '')} {entry.get('guide_lastname', '')}".strip()
                    if guide_info:
                        guide_info = f"{entry['guide_sdms']} - {guide_info}"
                    else:
                        guide_info = str(entry["guide_sdms"])
                row_data.append(guide_info)

            athlete_table = Table([row_data], colWidths=data_col_widths)
            athlete_table.setStyle(athlete_row_style)
            story.append(athlete_table)

            # Créer la table pour la ligne d'espacement
            spacer_table = Table(
                spacer_data, colWidths=spacer_col_widths
            )
            spacer_table.setStyle(spacer_row_style)
            story.append(spacer_table)

        doc.build(story, canvasmaker=make_canvas)
        buffer.seek(0)
        return buffer