from flask import render_template, redirect, url_for, flash, request

from utils.raza_calculation import calculate_raza, verify_combination
from ..auth import admin_required
from ..forms import ResultForm
from database.models import Game, Result, Athlete, Attempt, StartList
from database.db_manager import execute_one, execute_query
from config import Config
import re
import traceback


def register_routes(bp):
    @bp.route('/games/<int:id>/results')
    @admin_required
    def game_results(id):
        game = Game.get_by_id(id)
        if not game:
            flash('Game not found', 'danger')
            return redirect(url_for('admin.games_list'))

        results = Result.get_all(game_id=id)
        startlist = StartList.get_by_game(id)
        form = ResultForm()

        return render_template('admin/results/manage.html',
                               game=game,
                               results=results,
                               startlist=startlist,
                               form=form,
                               is_field_event=game['event'] in Config.get_field_events(),
                               is_track_event=game['event'] in Config.get_track_events())

    @bp.route('/games/<int:game_id>/results/add', methods=['POST'])
    @admin_required
    def result_add(game_id):
        try:
            game = Game.get_by_id(game_id)
            if not game:
                flash('Game not found', 'danger')
                return redirect(url_for('admin.games_list'))

            # Safe extraction of form data with None checks
            athlete_bib = request.form.get('athlete_bib')
            value = request.form.get('value', '').strip() if request.form.get('value') else ''
            weight_raw = request.form.get('weight')
            weight = weight_raw.strip() if weight_raw else None

            # Safe extraction of attempts and wind data
            attempts = []
            wind_attempts = []

            for i in range(1, 7):
                attempt_raw = request.form.get(f'attempt-{i}-value')
                wind_raw = request.form.get(f'wind-attempt-{i}-value')

                attempts.append(attempt_raw.strip() if attempt_raw else None)
                wind_attempts.append(wind_raw.strip() if wind_raw else None)

            errors = []
            athlete = None

            # Validate athlete
            if not athlete_bib:
                errors.append('Please select an athlete')
            else:
                try:
                    athlete_bib = int(athlete_bib)
                    athlete = Athlete.get_by_bib(athlete_bib)
                    if not athlete:
                        errors.append('Athlete not found')
                except (ValueError, TypeError):
                    errors.append('Invalid athlete BIB')

            # Validate based on event type
            if game['event'] in Config.get_field_events():
                if not any(attempt for attempt in attempts if attempt):
                    errors.append('At least one valid attempt is required for field events')
            elif game['event'] in Config.get_track_events():
                if not value:
                    errors.append('Performance value is required for track events')
                elif value not in Config.get_result_special_values():
                    # Validate time format only if it's not a special value
                    if not re.match(r'^\d+:\d{2}(\.\d{1,3})?$', value):
                        errors.append('Invalid time format. Use MM:SS or MM:SS.sss')

            if errors:
                for error in errors:
                    flash(error, 'danger')
                return redirect(url_for('admin.game_results', id=game_id))

            # Check for existing result
            existing_result = Result.get_by_game_athlete(game_id, athlete_bib)
            if existing_result:
                flash('Result for this athlete already exists, old result was deleted', 'warning')
                Attempt.delete_by_result(existing_result['id'])
                Result.delete(existing_result['id'])

            # Process field events
            if game['event'] in Config.get_field_events():
                valid_attempts = []
                raza_scores = []
                attempts_data = {}

                for i, attempt_value in enumerate(attempts):
                    raza_score = 0

                    if attempt_value and attempt_value.upper() not in Config.get_result_special_values():
                        try:
                            attempt_float = float(attempt_value)
                            valid_attempts.append(attempt_float)

                            if verify_combination(gender=athlete['gender'], event=game['event'],
                                                  athlete_class=athlete['class']):
                                result = calculate_raza(
                                    gender=athlete['gender'],
                                    event=game['event'],
                                    athlete_class=athlete['class'],
                                    performance=attempt_float
                                )

                                response, status = result if isinstance(result, tuple) else (result, 200)
                                raza_score = response.get_json().get('raza_score', 0)
                                raza_scores.append(raza_score)
                        except (ValueError, TypeError) as e:
                            print(f"Error processing attempt {i + 1}: {e}")

                    attempts_data[i + 1] = {
                        'value': attempt_value,
                        'raza_score': str(raza_score),
                        'wind_velocity': wind_attempts[i] if i < len(wind_attempts) else None
                    }

                performance_value = max(valid_attempts) if valid_attempts else 0.0
                max_raza_score = max(raza_scores) if raza_scores else 0

                # Create result
                result_id = Result.create(
                    game_id=game_id,
                    athlete_bib=athlete_bib,
                    value=performance_value,
                    raza_score=max_raza_score,
                    weight=weight
                )

                if not result_id:
                    flash('Failed to create result', 'danger')
                    return redirect(url_for('admin.game_results', id=game_id))

                # Create attempts
                Attempt.create_multiple(result_id=result_id, attempts=attempts_data)

            # Process track events
            elif game['event'] in Config.get_track_events():
                max_raza_score = 0

                # Handle special values
                if value.upper() in Config.get_result_special_values():
                    performance_value = value.upper()
                else:
                    # Parse time format
                    try:
                        time_parts = value.split(':')
                        minutes = int(time_parts[0])
                        seconds_parts = time_parts[1].split('.')
                        seconds = int(seconds_parts[0])
                        milliseconds = int(seconds_parts[1]) if len(seconds_parts) > 1 else 0

                        performance_value = minutes * 60 + seconds + (milliseconds / 1000)

                        # Calculate RAZA score for numerical values
                        if verify_combination(gender=athlete['gender'], event=game['event'],
                                              athlete_class=athlete['class']):
                            try:
                                result = calculate_raza(
                                    gender=athlete['gender'],
                                    event=game['event'],
                                    athlete_class=athlete['class'],
                                    performance=performance_value
                                )

                                response, status = result if isinstance(result, tuple) else (result, 200)
                                max_raza_score = response.get_json().get('raza_score', 0)

                            except Exception as e:
                                print(f"Error calculating track raza score: {e}")

                    except (ValueError, IndexError) as e:
                        flash('Invalid time format', 'danger')
                        return redirect(url_for('admin.game_results', id=game_id))

                print(f"Calculated RAZA score: {max_raza_score} for performance: {performance_value}")

                # Create result
                result_id = Result.create(
                    game_id=game_id,
                    athlete_bib=athlete_bib,
                    value=performance_value,
                    raza_score=max_raza_score
                )

                if not result_id:
                    flash('Failed to create result', 'danger')
                    return redirect(url_for('admin.game_results', id=game_id))

            flash('Result added successfully', 'success')
            return redirect(url_for('admin.game_results', id=game_id))

        except Exception as e:
            print(f"Unexpected error in result_add: {e}")
            traceback.print_exc()
            flash('An unexpected error occurred', 'danger')
            return redirect(url_for('admin.game_results', id=game_id))

    @bp.route('/results/<int:id>/delete', methods=['POST'])
    @admin_required
    def result_delete(id):
        try:
            result = Result.get_by_id(id)
            if not result:
                flash('Result not found', 'danger')
                return redirect(url_for('admin.games_list'))

            game_id = result['game_id']

            Attempt.delete_by_result(id)
            Result.delete(id)

            flash('Result deleted successfully', 'success')
            return redirect(url_for('admin.game_results', id=game_id))

        except Exception as e:
            print(f"Error deleting result: {e}")
            traceback.print_exc()
            flash(f'Error deleting result: {str(e)}', 'danger')
            return redirect(url_for('admin.games_list'))