from flask import render_template, redirect, url_for, flash, request, jsonify
from utils.raza_calculation import calculate_raza, verify_combination
from ..auth import admin_required
from ..forms import ResultForm
from database.models import Game, Result, Athlete, Attempt, StartList
from database.db_manager import execute_one, execute_query
from config import Config
import re
import traceback


def parse_time_to_seconds(time_str):
    time_str = time_str.strip()

    if ':' in time_str:
        parts = time_str.split(':')
        if len(parts) != 2:
            raise ValueError('Invalid time format')

        minutes = int(parts[0])
        seconds_part = parts[1]

        if '.' in seconds_part:
            sec_parts = seconds_part.split('.')
            seconds = int(sec_parts[0])
            decimal_part = sec_parts[1]
            decimal_part = decimal_part.ljust(4, '0')[:4]
            milliseconds = int(decimal_part)
        else:
            seconds = int(seconds_part)
            milliseconds = 0

        total_seconds = minutes * 60 + seconds + (milliseconds / 10000)
    else:
        if '.' in time_str:
            sec_parts = time_str.split('.')
            seconds = int(sec_parts[0])
            decimal_part = sec_parts[1]
            decimal_part = decimal_part.ljust(4, '0')[:4]
            milliseconds = int(decimal_part)
        else:
            seconds = int(time_str)
            milliseconds = 0

        total_seconds = seconds + (milliseconds / 10000)

    return total_seconds


def format_time_output(seconds):
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60

    if minutes > 0:
        return f"{minutes:02d}:{remaining_seconds:06.3f}"
    else:
        return f"{remaining_seconds:06.3f}"


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

            athlete_bib = request.form.get('athlete_bib')
            value = request.form.get('value', '').strip() if request.form.get('value') else ''
            weight_raw = request.form.get('weight')
            weight = weight_raw.strip() if weight_raw else None

            attempts = []
            wind_attempts = []
            heights = []

            for i in range(1, 7):
                attempt_raw = request.form.get(f'attempt-{i}-value')
                wind_raw = request.form.get(f'wind-attempt-{i}-value')
                height_raw = request.form.get(f'height-attempt-{i}-value')

                attempts.append(attempt_raw.strip() if attempt_raw else None)
                wind_attempts.append(wind_raw.strip() if wind_raw else None)
                heights.append(height_raw.strip() if height_raw else None)

            errors = []
            athlete = None

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

            if game['event'] in Config.get_field_events():
                if not any(attempt for attempt in attempts if attempt):
                    errors.append('At least one valid attempt is required for field events')
            elif game['event'] in Config.get_track_events():
                if not value:
                    errors.append('Performance value is required for track events')
                elif value not in Config.get_result_special_values():
                    if not re.match(r'^(\d{1,2}:)?\d{1,2}\.\d{1,4}$', value):
                        errors.append('Invalid time format. Use MM:SS.SSSS or SS.SSSS')

            if errors:
                for error in errors:
                    flash(error, 'danger')
                return redirect(url_for('admin.game_results', id=game_id))

            existing_result = Result.get_by_game_athlete(game_id, athlete_bib)
            if existing_result:
                if game['event'] in Config.get_field_events():
                    attempts_data = {}
                    for i, attempt_value in enumerate(attempts):
                        if attempt_value:
                            raza_score = 0
                            raza_score_decimal = 0

                            if attempt_value.upper() not in Config.get_result_special_values():
                                try:
                                    attempt_float = float(attempt_value)

                                    if game.get('wpa_points', False) and verify_combination(gender=athlete['gender'], event=game['event'], athlete_class=athlete['class']):
                                        result = calculate_raza(
                                            gender=athlete['gender'],
                                            event=game['event'],
                                            athlete_class=athlete['class'],
                                            performance=attempt_float
                                        )

                                        response, status = result if isinstance(result, tuple) else (result, 200)
                                        raza_score = int(response.get_json().get('raza_score', 0))
                                        raza_score_decimal = round(response.get_json().get('raza_score', 0), 3)
                                except (ValueError, TypeError) as e:
                                    print(f"Error processing attempt {i + 1}: {e}")

                            wind_velocity = None
                            if i < len(wind_attempts) and wind_attempts[i]:
                                try:
                                    wind_velocity = float(wind_attempts[i])
                                except (ValueError, TypeError):
                                    wind_velocity = None

                            height_value = None
                            if i < len(heights) and heights[i]:
                                try:
                                    height_value = float(heights[i])
                                except (ValueError, TypeError):
                                    height_value = None

                            attempts_data[i + 1] = {
                                'value': attempt_value,
                                'raza_score': raza_score,
                                'raza_score_decimal': raza_score_decimal,
                                'wind_velocity': wind_velocity,
                                'height': height_value
                            }

                    Attempt.update_partial(existing_result['id'], attempts_data)

                    valid_attempts = []
                    raza_scores = []
                    for attempt_value in attempts:
                        if attempt_value and attempt_value.upper() not in Config.get_result_special_values():
                            try:
                                attempt_float = float(attempt_value)
                                valid_attempts.append(attempt_float)

                                if game.get('wpa_points', False) and verify_combination(gender=athlete['gender'], event=game['event'], athlete_class=athlete['class']):
                                    result = calculate_raza(
                                        gender=athlete['gender'],
                                        event=game['event'],
                                        athlete_class=athlete['class'],
                                        performance=attempt_float
                                    )

                                    response, status = result if isinstance(result, tuple) else (result, 200)
                                    raza_scores.append(int(response.get_json().get('raza_score', 0)))
                            except (ValueError, TypeError):
                                continue

                    performance_value = max(valid_attempts) if valid_attempts else 0.0
                    max_raza_score = max(raza_scores) if raza_scores else 0

                    update_data = {
                        'value': performance_value,
                        'raza_score': max_raza_score,
                        'raza_score_decimal': round(max_raza_score, 3) if max_raza_score else None
                    }

                    if weight:
                        try:
                            update_data['weight'] = float(weight)
                        except (ValueError, TypeError):
                            pass

                    Result.update(existing_result['id'], **update_data)
                    flash('Result updated successfully', 'success')
                else:
                    flash('Cannot update track event result with attempts', 'danger')
                return redirect(url_for('admin.game_results', id=game_id))

            if game['event'] in Config.get_field_events():
                valid_attempts = []
                raza_scores = []
                attempts_data = {}

                for i, attempt_value in enumerate(attempts):
                    raza_score = 0
                    raza_score_decimal = 0

                    if attempt_value and attempt_value.upper() not in Config.get_result_special_values():
                        try:
                            attempt_float = float(attempt_value)
                            valid_attempts.append(attempt_float)

                            if game.get('wpa_points', False) and verify_combination(gender=athlete['gender'], event=game['event'], athlete_class=athlete['class']):
                                result = calculate_raza(
                                    gender=athlete['gender'],
                                    event=game['event'],
                                    athlete_class=athlete['class'],
                                    performance=attempt_float
                                )

                                response, status = result if isinstance(result, tuple) else (result, 200)
                                raza_score = int(response.get_json().get('raza_score', 0))
                                raza_score_decimal = round(response.get_json().get('raza_score', 0), 3)
                                raza_scores.append(raza_score)
                        except (ValueError, TypeError) as e:
                            print(f"Error processing attempt {i + 1}: {e}")

                    wind_velocity = None
                    if i < len(wind_attempts) and wind_attempts[i]:
                        try:
                            wind_velocity = float(wind_attempts[i])
                        except (ValueError, TypeError):
                            wind_velocity = None

                    height_value = None
                    if i < len(heights) and heights[i]:
                        try:
                            height_value = float(heights[i])
                        except (ValueError, TypeError):
                            height_value = None

                    if attempt_value:
                        attempts_data[i + 1] = {
                            'value': attempt_value,
                            'raza_score': raza_score,
                            'raza_score_decimal': raza_score_decimal,
                            'wind_velocity': wind_velocity,
                            'height': height_value
                        }

                performance_value = max(valid_attempts) if valid_attempts else 0.0
                max_raza_score = max(raza_scores) if raza_scores else 0

                result_data = {
                    'game_id': game_id,
                    'athlete_bib': athlete_bib,
                    'value': performance_value,
                    'raza_score': max_raza_score,
                    'raza_score_decimal': round(max_raza_score, 3) if max_raza_score else None
                }

                if weight:
                    try:
                        result_data['weight'] = float(weight)
                    except (ValueError, TypeError):
                        pass

                result_id = Result.create(**result_data)

                if not result_id:
                    flash('Failed to create result', 'danger')
                    return redirect(url_for('admin.game_results', id=game_id))

                Attempt.create_multiple(result_id=result_id, attempts=attempts_data)

                if game['event'] == 'Long Jump':
                    StartList.update_order_for_long_jump(game_id)

            elif game['event'] in Config.get_track_events():
                max_raza_score = 0
                max_raza_score_decimal = 0

                if value.upper() in Config.get_result_special_values():
                    performance_value = value.upper()
                else:
                    try:
                        performance_value = parse_time_to_seconds(value)
                        formatted_value = format_time_output(performance_value)

                        if game.get('wpa_points', False) and verify_combination(gender=athlete['gender'], event=game['event'], athlete_class=athlete['class']):
                            try:
                                result = calculate_raza(
                                    gender=athlete['gender'],
                                    event=game['event'],
                                    athlete_class=athlete['class'],
                                    performance=performance_value
                                )

                                response, status = result if isinstance(result, tuple) else (result, 200)
                                max_raza_score = int(response.get_json().get('raza_score', 0))
                                max_raza_score_decimal = round(response.get_json().get('raza_score', 0), 3)

                            except Exception as e:
                                print(f"Error calculating track raza score: {e}")

                        performance_value = formatted_value

                    except (ValueError, IndexError) as e:
                        flash('Invalid time format', 'danger')
                        return redirect(url_for('admin.game_results', id=game_id))

                result_data = {
                    'game_id': game_id,
                    'athlete_bib': athlete_bib,
                    'value': performance_value,
                    'raza_score': max_raza_score,
                    'raza_score_decimal': max_raza_score_decimal
                }

                result_id = Result.create(**result_data)

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

    @bp.route('/results/<int:result_id>/add-attempt', methods=['POST'])
    @admin_required
    def add_long_jump_attempt(result_id):
        try:
            result = Result.get_by_id(result_id)
            if not result:
                return jsonify({'error': 'Result not found'}), 404

            game = Game.get_by_id(result['game_id'])
            if not game or game['event'] != 'Long Jump':
                return jsonify({'error': 'Only available for Long Jump events'}), 400

            value = request.json.get('value')
            height = request.json.get('height')
            wind_velocity = request.json.get('wind_velocity')

            if not value:
                return jsonify({'error': 'Attempt value is required'}), 400

            try:
                float(value)
            except ValueError:
                if value.upper() not in Config.get_result_special_values():
                    return jsonify({'error': 'Invalid attempt value'}), 400

            Attempt.add_long_jump_attempt(result_id, value, height, wind_velocity)

            existing_attempts = Attempt.get_by_result(result_id)
            valid_attempts = []
            raza_scores = []

            for attempt in existing_attempts:
                if attempt['value'] and attempt['value'].upper() not in Config.get_result_special_values():
                    try:
                        attempt_float = float(attempt['value'])
                        valid_attempts.append(attempt_float)
                        if attempt['raza_score']:
                            raza_scores.append(attempt['raza_score'])
                    except (ValueError, TypeError):
                        continue

            if valid_attempts:
                best_performance = max(valid_attempts)
                best_raza = max(raza_scores) if raza_scores else 0

                Result.update(result_id,
                             value=best_performance,
                             raza_score=best_raza,
                             raza_score_decimal=round(best_raza, 3) if best_raza else None)

            StartList.update_order_for_long_jump(result['game_id'])

            return jsonify({'success': True, 'message': 'Attempt added successfully'})

        except Exception as e:
            print(f"Error adding Long Jump attempt: {e}")
            traceback.print_exc()
            return jsonify({'error': 'Server error occurred'}), 500