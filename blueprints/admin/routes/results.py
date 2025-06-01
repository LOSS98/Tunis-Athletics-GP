import traceback
from flask import render_template, redirect, url_for, flash, request, jsonify
from utils.raza_calculation import calculate_raza, verify_combination
from ..auth import admin_required
from ..forms import ResultForm
from database.models import Game, Result, Athlete, Attempt, StartList
from database.db_manager import execute_one, execute_query
from config import Config
import re


def parse_time_to_seconds(time_str):
    time_str = time_str.strip()

    if not time_str:
        return 0.0

    if ':' in time_str:
        parts = time_str.split(':')
        if len(parts) != 2:
            raise ValueError('Invalid time format')

        minutes = int(parts[0])
        seconds_part = parts[1]

        if '.' in seconds_part:
            sec_parts = seconds_part.split('.')
            seconds = int(sec_parts[0])
            decimal_part = sec_parts[1].ljust(4, '0')[:4]
        else:
            seconds = int(seconds_part)
            decimal_part = '0000'

        total_seconds = minutes * 60 + seconds + (int(decimal_part) / 10000)
    else:
        if '.' in time_str:
            sec_parts = time_str.split('.')
            seconds = int(sec_parts[0])
            decimal_part = sec_parts[1].ljust(4, '0')[:4]
        else:
            seconds = int(time_str)
            decimal_part = '0000'

        total_seconds = seconds + (int(decimal_part) / 10000)

    return total_seconds


def format_time_output(seconds):
    if seconds == 0:
        return "0:00.0000"

    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60

    if minutes > 0:
        return f"{minutes}:{remaining_seconds:06.3f}"
    else:
        return f"{remaining_seconds:06.3f}"


def calculate_and_store_raza(athlete, game, performance_value):
    raza_score = 0
    raza_score_precise = 0.0

    if verify_combination(athlete['gender'], game['event'], athlete['class']):
        try:
            result = calculate_raza(
                gender=athlete['gender'],
                event=game['event'],
                athlete_class=athlete['class'],
                performance=float(performance_value)
            )

            response, status = result if isinstance(result, tuple) else (result, 200)
            if status == 200:
                raza_data = response.get_json()
                raza_score = int(raza_data.get('raza_score', 0))
                raza_score_precise = float(raza_data.get('raza_score_precise', 0.0))
        except Exception as e:
            print(f"Error calculating RAZA: {e}")

    return raza_score, raza_score_precise



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

        game_json = {
            'id': game['id'],
            'event': game['event'],
            'gender': game['gender'],
            'classes': game['classes'],
            'phase': game.get('phase'),
            'area': game.get('area'),
            'day': game['day'],
            'time': str(game['time']),
            'nb_athletes': game['nb_athletes'],
            'status': game['status'],
            'published': game.get('published', False),
            'wpa_points': game.get('wpa_points', False)
        }
        selected_r1 = [r for r in results if r['final_order'] is not None]
        total_selected_r1 = len(selected_r1)
        return render_template('admin/results/manage.html',
                               game=game,
                               game_json=game_json,
                               results=results,
                               startlist=startlist,
                               form=form,
                               is_field_event=game['event'] in Config.get_field_events(),
                               is_track_event=game['event'] in Config.get_track_events(),
                               total_selected_r1 = total_selected_r1,)

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
            record = request.form.get('record', '').strip()

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
                    if not re.match(r'^(\d{1,2}:)?\d{1,2}(\.\d{1,4})?$', value):
                        errors.append('Invalid time format. Use MM:SS.SSSS, MM:SS, SS.SSSS, or SS')

            if errors:
                for error in errors:
                    flash(error, 'danger')
                return redirect(url_for('admin.game_results', id=game_id))

            existing_result = Result.get_by_game_athlete(game_id, athlete_bib)
            if existing_result:
                flash('Result already exists for this athlete. Please delete the existing result first.', 'warning')
                return redirect(url_for('admin.game_results', id=game_id))

            if not StartList.athlete_in_startlist(game_id, athlete_bib):
                flash(f'Warning: Athlete BIB {athlete_bib} is not in the start list. Add to start list?', 'warning')

            if game['event'] in Config.get_field_events():
                valid_attempts = []
                raza_scores = []
                attempts_data = {}
                all_attempt_values = []

                for i, attempt_value in enumerate(attempts):
                    raza_score = 0
                    raza_score_precise = 0.0

                    if attempt_value and attempt_value.upper() not in Config.get_result_special_values():
                        try:
                            attempt_float = float(attempt_value)
                            valid_attempts.append(attempt_float)
                            all_attempt_values.append(attempt_float)

                            raza_score, raza_score_precise = calculate_and_store_raza(athlete, game, attempt_float)
                            if raza_score > 0:
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
                            'raza_score_precise': raza_score_precise,
                            'wind_velocity': wind_velocity,
                            'height': height_value
                        }

                if not valid_attempts:
                    performance_value = "NM"
                    max_raza_score = 0
                    max_raza_score_precise = 0.0
                else:
                    performance_value = max(valid_attempts)
                    max_raza_score = max(raza_scores) if raza_scores else 0
                    max_raza_score_precise = 0.0
                    if raza_scores:
                        for i, attempt_value in enumerate(all_attempt_values):
                            if attempt_value == performance_value:
                                raza_score, raza_score_precise = calculate_and_store_raza(athlete, game, attempt_value)
                                max_raza_score_precise = raza_score_precise
                                break

                result_data = {
                    'game_id': game_id,
                    'athlete_bib': athlete_bib,
                    'value': performance_value,
                    'best_attempt': f"{performance_value:.2f}" if performance_value != "NM" else None,
                    'raza_score': max_raza_score,
                    'raza_score_precise': max_raza_score_precise
                }

                if weight:
                    try:
                        result_data['weight'] = float(weight)
                    except (ValueError, TypeError):
                        pass

                if record and record != '':
                    result_data['record'] = record

                result_id = Result.create(**result_data)

                if not result_id:
                    flash('Failed to create result', 'danger')
                    return redirect(url_for('admin.game_results', id=game_id))

                if attempts_data:
                    Attempt.create_multiple(result_id=result_id, attempts=attempts_data)

                if game['event'] not in ['High Jump'] and len(attempts_data) >= 3:
                    update_final_order_after_three_attempts(game_id)

            elif game['event'] in Config.get_track_events():
                if value.upper() in Config.get_result_special_values():
                    performance_value = value.upper()
                    max_raza_score = 0
                    max_raza_score_precise = 0.0
                else:
                    try:
                        performance_seconds = parse_time_to_seconds(value)
                        performance_value = format_time_output(performance_seconds)

                        max_raza_score, max_raza_score_precise = calculate_and_store_raza(athlete, game,
                                                                                          performance_seconds)

                    except (ValueError, IndexError) as e:
                        flash('Invalid time format', 'danger')
                        return redirect(url_for('admin.game_results', id=game_id))

                result_data = {
                    'game_id': game_id,
                    'athlete_bib': athlete_bib,
                    'value': performance_value,
                    'raza_score': max_raza_score,
                    'raza_score_precise': max_raza_score_precise
                }

                if record and record != '':
                    result_data['record'] = record

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
    def add_high_jump_attempt(result_id):
        try:
            result = Result.get_by_id(result_id)
            if not result:
                return jsonify({'error': 'Result not found'}), 404

            game = Game.get_by_id(result['game_id'])
            if not game or game['event'] != 'High Jump':
                return jsonify({'error': 'Only available for High Jump events'}), 400

            height = request.json.get('height')
            attempt_result = request.json.get('result', 'O')

            if not height:
                return jsonify({'error': 'Height is required'}), 400

            try:
                height_float = float(height)
            except ValueError:
                return jsonify({'error': 'Invalid height value'}), 400

            athlete = Athlete.get_by_bib(result['athlete_bib'])

            existing_attempts = execute_query(
                "SELECT MAX(attempt_number) as max_num FROM attempts WHERE result_id = %s",
                (result_id,), fetch=True
            )

            next_attempt = 1
            if existing_attempts and existing_attempts[0]['max_num']:
                next_attempt = existing_attempts[0]['max_num'] + 1

            raza_score = 0
            raza_score_precise = 0.0

            if attempt_result == 'O' and athlete:
                raza_score, raza_score_precise = calculate_and_store_raza(athlete, game, height_float)

            Attempt.create(result_id, next_attempt, attempt_result, None, raza_score, raza_score_precise, height_float)

            if attempt_result == 'O':
                current_best = execute_one(
                    "SELECT MAX(height) as best_height FROM attempts WHERE result_id = %s AND value = 'O'",
                    (result_id,)
                )

                if current_best and current_best['best_height']:
                    best_height = current_best['best_height']
                    best_raza_score, best_raza_score_precise = calculate_and_store_raza(athlete, game, best_height)

                    Result.update(result_id,
                                  value=best_height,
                                  best_attempt=f"{best_height:.2f}",
                                  raza_score=best_raza_score,
                                  raza_score_precise=best_raza_score_precise)

            return jsonify({'success': True, 'message': 'Attempt added successfully'})

        except Exception as e:
            print(f"Error adding High Jump attempt: {e}")
            traceback.print_exc()
            return jsonify({'error': 'Server error occurred'}), 500

    @bp.route('/games/<int:game_id>/recalculate-raza', methods=['POST'])
    @admin_required
    def recalculate_raza_scores(game_id):
        try:
            game = Game.get_by_id(game_id)
            if not game:
                return jsonify({'error': 'Game not found'}), 404

            results = execute_query("""
                SELECT r.*, a.gender, a.class
                FROM results r
                JOIN athletes a ON r.athlete_bib = a.bib
                WHERE r.game_id = %s
            """, (game_id,), fetch=True)

            updated_count = 0
            for result in results:
                if result['value'] not in Config.get_result_special_values():
                    try:
                        performance = float(result['value'])
                        athlete_data = {'gender': result['gender'], 'class': result['class']}

                        raza_score, raza_score_precise = calculate_and_store_raza(athlete_data, game, performance)

                        Result.update(result['id'],
                                      raza_score=raza_score,
                                      raza_score_precise=raza_score_precise)
                        updated_count += 1

                        attempts = Attempt.get_by_result(result['id'])
                        for attempt in attempts:
                            if attempt['value'] and attempt['value'].upper() not in Config.get_result_special_values():
                                try:
                                    attempt_perf = float(attempt['value'])
                                    attempt_raza, attempt_raza_precise = calculate_and_store_raza(athlete_data, game,
                                                                                                  attempt_perf)

                                    execute_query("""
                                        UPDATE attempts 
                                        SET raza_score = %s, raza_score_precise = %s 
                                        WHERE id = %s
                                    """, (attempt_raza, attempt_raza_precise, attempt['id']))
                                except (ValueError, TypeError):
                                    continue

                    except (ValueError, TypeError):
                        continue

            return jsonify({'success': True, 'updated': updated_count})

        except Exception as e:
            print(f"Error recalculating RAZA scores: {e}")
            traceback.print_exc()
            return jsonify({'error': 'Server error occurred'}), 500

    @bp.route('/startlist/add-from-result', methods=['POST'])
    @admin_required
    def add_to_startlist_from_result():
        try:
            game_id = request.json.get('game_id')
            athlete_bib = request.json.get('athlete_bib')

            if not game_id or not athlete_bib:
                return jsonify({'error': 'Missing parameters'}), 400

            StartList.create(game_id, athlete_bib, None)
            return jsonify({'success': True})

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @bp.route('/games/<int:game_id>/check-result/<int:athlete_bib>')
    @admin_required
    def check_result_exists(game_id, athlete_bib):
        result = Result.get_by_game_athlete(game_id, athlete_bib)
        if result:
            return jsonify({'exists': True, 'result_id': result['id']})
        return jsonify({'exists': False})

    @bp.route('/games/<int:game_id>/auto-rank-round1', methods=['POST'])
    @admin_required
    def auto_rank_round1(game_id):
        try:
            game = Game.get_by_id(game_id)
            if not game or game['event'] != 'Long Jump':
                return jsonify({'error': 'Invalid game or not a Long Jump event'}), 400

            # Get all results with at least 3 attempts
            results = execute_query("""
                SELECT r.*, a.gender, a.class,
                       (SELECT MAX(CAST(att.value AS FLOAT)) 
                        FROM attempts att 
                        WHERE att.result_id = r.id 
                        AND att.attempt_number <= 3 
                        AND att.value NOT IN %s) as best_of_three
                FROM results r
                JOIN athletes a ON r.athlete_bib = a.bib
                WHERE r.game_id = %s
                AND (SELECT COUNT(*) FROM attempts att WHERE att.result_id = r.id AND att.attempt_number <= 3) >= 3
                ORDER BY best_of_three DESC NULLS LAST
            """, (tuple(Config.get_result_special_values()), game_id,), fetch=True)

            # Prend les 8 meilleurs si >= 8, sinon tous ceux qui ont 3 essais
            n = min(8, len(results))
            if n == 0:
                return jsonify({'error': "No athlete with 3 valid attempts found."}), 400

            top = results[:n]
            top.reverse()  # Du pire au meilleur

            # Update final_order pour les sélectionnés
            for i, result in enumerate(top):
                execute_query(
                    "UPDATE results SET final_order = %s WHERE id = %s",
                    (i + 1, result['id'])
                )

            # Clear final_order pour les autres
            for result in results[n:]:
                execute_query(
                    "UPDATE results SET final_order = NULL WHERE id = %s",
                    (result['id'],)
                )

            return jsonify({
                'success': True,
                'message': f'{n} athletes selected for final. Order: {top[0]["athlete_bib"]} (worst) to {top[-1]["athlete_bib"]} (best)'
            })

        except Exception as e:
            print(f"Error in auto_rank_round1: {e}")
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500

    @bp.route('/results/<int:result_id>/update-attempts', methods=['POST'])
    @admin_required
    def update_attempts(result_id):
        try:
            result = Result.get_by_id(result_id)
            if not result:
                return jsonify({'error': 'Result not found'}), 404

            game = Game.get_by_id(result['game_id'])
            if not game:
                return jsonify({'error': 'Game not found'}), 404

            data = request.json
            attempts_data = data.get('attempts', {})
            record = data.get('record')
            weight = data.get('weight')

            athlete = Athlete.get_by_bib(result['athlete_bib'])
            if not athlete:
                return jsonify({'error': 'Athlete not found'}), 404

            # Get existing attempts
            existing_attempts = Attempt.get_by_result(result_id)
            existing_dict = {a['attempt_number']: a for a in existing_attempts}

            # Process new/updated attempts
            valid_attempts = []
            for attempt_num, attempt_info in attempts_data.items():
                attempt_num = int(attempt_num)
                attempt_value = attempt_info.get('value', '').strip()

                if not attempt_value:
                    continue

                # Calculate RAZA score if needed
                raza_score = 0
                raza_score_precise = 0.0

                if attempt_value not in Config.get_result_special_values():
                    try:
                        attempt_float = float(attempt_value)
                        valid_attempts.append(attempt_float)

                        if game.get('wpa_points', False):
                            raza_score, raza_score_precise = calculate_and_store_raza(
                                athlete, game, attempt_float
                            )
                    except ValueError:
                        pass

                # Update or create attempt
                attempt_data = {
                    'value': attempt_value,
                    'raza_score': raza_score,
                    'raza_score_precise': raza_score_precise,
                    'wind_velocity': attempt_info.get('wind_velocity'),
                    'height': attempt_info.get('height')
                }

                if attempt_num in existing_dict:
                    # Update existing attempt
                    Attempt.update(existing_dict[attempt_num]['id'], **attempt_data)
                else:
                    # Create new attempt
                    Attempt.create(result_id, attempt_num, **attempt_data)

            # Update result with best performance
            if valid_attempts:
                best_performance = max(valid_attempts)
                max_raza_score = 0
                max_raza_score_precise = 0.0

                if game.get('wpa_points', False):
                    max_raza_score, max_raza_score_precise = calculate_and_store_raza(
                        athlete, game, best_performance
                    )

                Result.update(
                    result_id,
                    value=best_performance,
                    best_attempt=f"{best_performance:.2f}",
                    raza_score=max_raza_score,
                    raza_score_precise=max_raza_score_precise,
                    record=record,
                    weight=weight
                )

            # Check if we need to update final order (Long Jump specific)
            if game['event'] == 'Long Jump':
                check_and_update_long_jump_progression(game['id'])

            return jsonify({'success': True, 'message': 'Attempts updated successfully'})

        except Exception as e:
            print(f"Error updating attempts: {e}")
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500

    @bp.route('/games/<int:game_id>/high-jump-results', methods=['POST'])
    @admin_required
    def save_high_jump_results(game_id):
        try:
            game = Game.get_by_id(game_id)
            if not game or game['event'] != 'High Jump':
                return jsonify({'error': 'Invalid game or not a High Jump event'}), 400

            data = request.json
            results_data = data.get('results', {})

            for athlete_bib, heights in results_data.items():
                athlete = Athlete.get_by_bib(int(athlete_bib))
                if not athlete:
                    continue

                # Find or create result
                result = Result.get_by_game_athlete(game_id, athlete_bib)
                if not result:
                    result_id = Result.create(
                        game_id=game_id,
                        athlete_bib=athlete_bib,
                        value='NH'  # No Height initially
                    )
                else:
                    result_id = result['id']

                # Process heights
                best_height = 0
                attempt_number = 0

                for height, attempts in sorted(heights.items(), key=lambda x: float(x[0])):
                    height_float = float(height)

                    # Process each attempt at this height
                    for i, char in enumerate(attempts):
                        attempt_number += 1

                        # Create attempt record
                        Attempt.create(
                            result_id=result_id,
                            attempt_number=attempt_number,
                            value=char,
                            height=height_float
                        )

                        # Update best height if cleared
                        if char == 'O' and height_float > best_height:
                            best_height = height_float

                # Update result with best height
                if best_height > 0:
                    raza_score = 0
                    raza_score_precise = 0.0

                    if game.get('wpa_points', False):
                        raza_score, raza_score_precise = calculate_and_store_raza(
                            athlete, game, best_height
                        )

                    Result.update(
                        result_id,
                        value=best_height,
                        best_attempt=f"{best_height:.2f}",
                        raza_score=raza_score,
                        raza_score_precise=raza_score_precise
                    )

            return jsonify({'success': True})

        except Exception as e:
            print(f"Error saving High Jump results: {e}")
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500

def update_final_order_after_three_attempts(game_id):
    try:
        results_with_three_attempts = execute_query("""
            SELECT r.id, r.athlete_bib, r.value as best_performance
            FROM results r
            WHERE r.game_id = %s 
            AND r.value != 'NM'
            AND (
                SELECT COUNT(*) 
                FROM attempts a 
                WHERE a.result_id = r.id 
                AND a.attempt_number <= 3
            ) >= 3
        """, (game_id,), fetch=True)

        if len(results_with_three_attempts) <= 8:
            return

        sorted_results = sorted(results_with_three_attempts,
                                key=lambda x: float(x['best_performance']) if x['best_performance'] != 'NM' else 0,
                                reverse=True)

        top_8 = sorted_results[:8]

        final_order_results = sorted(top_8,
                                     key=lambda x: float(x['best_performance']) if x['best_performance'] != 'NM' else 0)

        for i, result in enumerate(final_order_results):
            execute_query(
                "UPDATE startlist SET final_order = %s WHERE game_id = %s AND athlete_bib = %s",
                (i + 1, game_id, result['athlete_bib'])
            )

    except Exception as e:
        print(f"Error updating final order: {e}")

def check_and_update_long_jump_progression(attempts):
    """
    Vérifie et met à jour la progression des essais en saut en longueur.
    - attempts : liste de chaînes (ex : ["5.66", "5.78", "X", "5.50", "", ""])
    Retourne (best_valid, progression, is_valid)
      - best_valid : meilleure marque valide (float ou None)
      - progression : liste d'essais nettoyés (valeur float ou None, "X" ou "F" pour raté)
      - is_valid : True si la progression est valide (max 6 essais, formats ok, pas de doublons incohérents...)
    """
    special_values = {"X", "F", "NM", "DNS", "DNF"}  # valeurs d'échec ou spéciales
    cleaned_attempts = []
    best_valid = None

    for val in attempts:
        val = val.strip() if val else ""
        if not val:
            cleaned_attempts.append(None)
            continue
        if val.upper() in special_values:
            cleaned_attempts.append(val.upper())
            continue
        try:
            jump = float(val.replace(',', '.'))  # accepter aussi "5,55"
            cleaned_attempts.append(jump)
            if best_valid is None or jump > best_valid:
                best_valid = jump
        except Exception:
            # Valeur non reconnue, on considère la progression invalide
            return None, [], False

    # Validation règle concours : max 6 essais
    if len(cleaned_attempts) > 6:
        return None, cleaned_attempts, False

    # Option : on peut ici vérifier des règles métiers supplémentaires

    return best_valid, cleaned_attempts, True

