import traceback
import pytz
from datetime import datetime, date
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user
from utils.raza_calculation import calculate_raza, verify_combination
from ..auth import admin_required, technical_delegate_required
from ..forms import ResultForm
from database.models import Athlete, Game, StartList, Result, Attempt, WorldRecord, PersonalBest, HeatGroup
from database.db_manager import execute_one, execute_query
from config import Config, config
import re


def check_athlete_class_compatibility(athlete, game):
    if not athlete or not athlete.get('class'):
        return False, []

    athlete_classes = [c.strip() for c in athlete['class'].split(',') if c.strip()]
    game_classes = [c.strip() for c in game['classes'].split(',') if c.strip()]

    compatible_classes = [ac for ac in athlete_classes if ac in game_classes]
    has_compatible_class = len(compatible_classes) > 0

    return has_compatible_class, athlete_classes


def get_matching_class(athlete, game):
    """Get the athlete's class that matches the game classes"""
    if not athlete or not athlete.get('class'):
        return None

    athlete_classes = [c.strip() for c in athlete['class'].split(',') if c.strip()]
    game_classes = [c.strip() for c in game['classes'].split(',') if c.strip()]

    # Return the first matching class
    for athlete_class in athlete_classes:
        if athlete_class in game_classes:
            return athlete_class

    # If no match, return the first athlete class (for backwards compatibility)
    return athlete_classes[0] if athlete_classes else None


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


def calculate_and_store_raza(athlete, game, performance_value, specific_class=None):
    raza_score = 0
    raza_score_precise = 0.0

    # Utiliser la classe spécifique si fournie, sinon la première classe de l'athlète
    athlete_class = specific_class or athlete['class']

    if verify_combination(athlete['gender'], game['event'], athlete_class):
        try:
            result = calculate_raza(
                gender=athlete['gender'],
                event=game['event'],
                athlete_class=athlete_class,
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


def check_for_records_and_pbs(result, athlete, game, athlete_class):
    if not game.get('official'):
        return 0, 0

    performance_value = result['value']
    if performance_value in Config.get_result_special_values():
        return 0, 0

    try:
        performance_float = float(performance_value)
    except (ValueError, TypeError):
        return 0, 0

    event = game['event']
    records_created = 0
    pbs_created = 0

    # Check for World Record
    if check_and_create_wr(athlete, event, athlete_class, performance_value, performance_float, game):
        records_created += 1

    # Check for Area Record
    if athlete.get('region_code') and check_and_create_ar(athlete, event, athlete_class, performance_value,
                                                          performance_float, game):
        records_created += 1

    # Check for Personal Best
    if check_and_create_pb(athlete, event, athlete_class, performance_value, performance_float, game):
        pbs_created += 1

    return records_created, pbs_created


# Dans results/routes.py
def check_and_create_wr(athlete, event, athlete_class, performance_value, performance_float, game):
    """Check and create World Record if applicable"""
    # Check existing approved WR
    existing_wr = WorldRecord.check_existing_record(event, athlete_class, 'WR', athlete['gender'])

    # Check pending WR
    pending_wr = WorldRecord.get_pending_for_event_class(event, athlete_class, 'WR', athlete['gender'])

    is_new_record = False

    if not existing_wr or performance_float > float(existing_wr['performance']):
        if not pending_wr or performance_float > float(pending_wr['performance']):
            is_new_record = True
        elif pending_wr:
            # Delete the inferior pending record
            WorldRecord.delete(pending_wr['id'])
            is_new_record = True

    if is_new_record:
        WorldRecord.create(
            sdms=athlete['sdms'],
            event=event,
            athlete_class=athlete_class,
            gender=athlete['gender'],  # Ajout du genre
            performance=performance_value,
            location='Tunis, Tunisia',
            npc=athlete['npc'],
            region_code=athlete.get('region_code'),
            record_date=date.today(),
            record_type='WR',
            made_in_competition=True,
            competition_id=game['id'],  # Ajout du game_id
            approved=False
        )
        return True

    return False

def check_and_create_ar(athlete, event, athlete_class, performance_value, performance_float, game):
    """Check and create Area Record if applicable"""
    region_code = athlete.get('region_code')
    if not region_code:
        return False

    # Check existing approved AR for this region and gender
    existing_ar = WorldRecord.check_existing_record(event, athlete_class, 'AR', athlete['gender'], athlete['npc'])

    # Check pending AR for this region and gender
    pending_ar = WorldRecord.get_pending_for_event_class_region(event, athlete_class, 'AR', athlete['gender'], region_code)

    is_new_record = False

    if not existing_ar or performance_float > float(existing_ar['performance']):
        if not pending_ar or performance_float > float(pending_ar['performance']):
            is_new_record = True
        elif pending_ar:
            # Delete the inferior pending record
            WorldRecord.delete(pending_ar['id'])
            is_new_record = True

    if is_new_record:
        WorldRecord.create(
            sdms=athlete['sdms'],
            event=event,
            athlete_class=athlete_class,
            gender=athlete['gender'],  # Ajout du genre
            performance=performance_value,
            location='Tunis, Tunisia',
            npc=athlete['npc'],
            region_code=region_code,
            record_date=date.today(),
            record_type='AR',
            made_in_competition=True,
            competition_id=game['id'],  # Ajout du game_id
            approved=False
        )
        return True

    return False

def check_and_create_pb(athlete, event, athlete_class, performance_value, performance_float, game):
    """Check and create Personal Best if applicable"""
    # Check existing approved PB
    existing_pb = PersonalBest.check_existing_pb(athlete['sdms'], event, athlete_class, athlete['gender'])

    # Check pending PB
    pending_pb = PersonalBest.get_pending_for_athlete(athlete['sdms'], event, athlete_class, athlete['gender'])

    is_new_pb = False

    if not existing_pb or performance_float > float(existing_pb['performance']):
        if not pending_pb or performance_float > float(pending_pb['performance']):
            is_new_pb = True
        elif pending_pb:
            # Delete the inferior pending PB
            PersonalBest.delete(pending_pb['id'])
            is_new_pb = True

    if is_new_pb:
        PersonalBest.create(
            sdms=athlete['sdms'],
            event=event,
            athlete_class=athlete_class,
            gender=athlete['gender'],  # Ajout du genre
            performance=performance_value,
            location='Tunis, Tunisia',
            record_date=date.today(),
            made_in_competition=True,
            competition_id=game['id'],  # Ajout du game_id
            approved=False
        )
        return True

    return False


def register_routes(bp):
    @bp.route('/games/<int:id>/results')
    @admin_required
    def game_results(id):
        game = Game.get_by_id(id)
        if not game:
            flash('Game not found', 'danger')
            return redirect(url_for('admin.games_list'))

        game['classes_list'] = [c.strip() for c in game['classes'].split(',') if c.strip()]

        results = Result.get_all(game_id=id)
        startlist = StartList.get_by_game(id)
        form = ResultForm()

        # Heat group data
        heat_group = None
        heat_siblings = []
        combined_results = []

        if Game.is_heat_game(game):
            heat_group = HeatGroup.get_by_id(game['heat_group_id'])
            heat_siblings = Game.get_heat_siblings(game)
            combined_results = HeatGroup.get_combined_results(game['heat_group_id'])
            for i, result in enumerate(combined_results):
                result['athlete_classes'] = result['athlete_class'].split(',') if result['athlete_class'] else []

        game_json = {
            'id': game['id'],
            'event': game['event'],
            'genders': game['genders'],
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
        finalists_count = len([r for r in results if r.get('final_order')])

        has_r1_qualifying = False
        if game['event'] in config.FIELD_EVENTS:
            r1_classes = config.R1_QUALIFYING_CLASSES
            for cls in game['classes_list']:
                if cls in r1_classes:
                    has_r1_qualifying = True
                    break

        return render_template('admin/results/manage.html',
                               game=game,
                               game_json=game_json,
                               results=results,
                               startlist=startlist,
                               form=form,
                               config=config,
                               has_r1_qualifying=has_r1_qualifying,
                               heat_group=heat_group,
                               heat_siblings=heat_siblings,
                               combined_results=combined_results,
                               is_field_event=game['event'] in Config.get_field_events(),
                               is_track_event=game['event'] in Config.get_track_events(),
                               total_selected_r1=total_selected_r1,
                               finalists_count=finalists_count,
                               total_finalists=8)


    @bp.route('/games/<int:game_id>/results/add', methods=['POST'])
    @admin_required
    def result_add(game_id):
        try:
            game = Game.get_by_id(game_id)
            if not game:
                flash('Game not found', 'danger')
                return redirect(url_for('admin.games_list'))

            game['classes_list'] = [c.strip() for c in game['classes'].split(',') if c.strip()]

            athlete_sdms = request.form.get('athlete_sdms')
            guide_sdms = request.form.get('guide_sdms')
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
            athlete_classes = []

            if not athlete_sdms:
                errors.append('Please select an athlete')
            else:
                try:
                    athlete_sdms = int(athlete_sdms)
                    athlete = Athlete.get_by_sdms(athlete_sdms)
                    if not athlete:
                        errors.append('Athlete not found')
                    else:
                        has_compatible_class, athlete_classes = check_athlete_class_compatibility(athlete, game)

                        if not has_compatible_class:
                            flash(
                                f"Warning: Athlete classes {', '.join(athlete_classes)} do not match game classes {game['classes']}",
                                'warning'
                            )

                        if athlete['gender'] != game['genders']:
                            flash(
                                f"Warning: Athlete gender ({athlete['gender']}) does not match game gender ({game['genders']})",
                                'warning'
                            )
                except (ValueError, TypeError):
                    errors.append('Invalid athlete SDMS')

            if guide_sdms:
                try:
                    guide_sdms = int(guide_sdms)
                except (ValueError, TypeError):
                    guide_sdms = None

            if game['event'] == 'High Jump':
                height = request.form.get('height')
                attempt_result = request.form.get('attempt_result', 'O')

                if not height:
                    errors.append('Height is required for High Jump')

                if errors:
                    for error in errors:
                        flash(error, 'danger')
                    return redirect(url_for('admin.game_results', id=game_id))

                try:
                    height_float = float(height)
                except (ValueError, TypeError):
                    flash('Invalid height value', 'danger')
                    return redirect(url_for('admin.game_results', id=game_id))

                existing_result = Result.get_by_game_athlete(game_id, athlete_sdms)
                if not existing_result:
                    result_data = {
                        'game_id': game_id,
                        'athlete_sdms': athlete_sdms,
                        'guide_sdms': guide_sdms,
                        'value': 'NH',
                        'raza_score': 0,
                        'raza_score_precise': 0.0
                    }
                    result_id = Result.create(**result_data)
                else:
                    result_id = existing_result['id']

                raza_score = 0
                raza_score_precise = 0.0
                if attempt_result == 'O' and game.get('wpa_points', False):
                    matching_class = get_matching_class(athlete, game)
                    raza_score, raza_score_precise = calculate_and_store_raza(athlete, game, height_float,
                                                                              matching_class)

                existing_attempts = execute_query(
                    "SELECT MAX(attempt_number) as max_num FROM attempts WHERE result_id = %s",
                    (result_id,), fetch=True
                )
                next_attempt = 1
                if existing_attempts and existing_attempts[0]['max_num']:
                    next_attempt = existing_attempts[0]['max_num'] + 1

                Attempt.create(result_id, next_attempt, attempt_result, None, raza_score, raza_score_precise,
                               height_float)

                if attempt_result == 'O':
                    successful_heights = execute_query(
                        "SELECT MAX(height) as best_height FROM attempts WHERE result_id = %s AND value = 'O'",
                        (result_id,), fetch=True
                    )
                    if successful_heights and successful_heights[0]['best_height']:
                        best_height = successful_heights[0]['best_height']
                        best_raza_score = 0
                        best_raza_score_precise = 0.0
                        if game.get('wpa_points', False):
                            matching_class = get_matching_class(athlete, game)
                            best_raza_score, best_raza_score_precise = calculate_and_store_raza(athlete, game,
                                                                                                best_height,
                                                                                                matching_class)

                        Result.update(result_id,
                                      value=best_height,
                                      best_attempt=f"{best_height:.2f}",
                                      raza_score=best_raza_score,
                                      raza_score_precise=best_raza_score_precise)
                else:
                    successful_attempts = execute_query(
                        "SELECT COUNT(*) as count FROM attempts WHERE result_id = %s AND value = 'O'",
                        (result_id,), fetch=True
                    )
                    if successful_attempts and successful_attempts[0]['count'] == 0:
                        Result.update(result_id, value='NH', best_attempt=None, raza_score=0, raza_score_precise=0.0)

                flash('High Jump attempt added successfully', 'success')
                return redirect(url_for('admin.game_results', id=game_id))

            elif game['event'] in Config.get_field_events():
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

            existing_result = Result.get_by_game_athlete(game_id, athlete_sdms)
            matching_class = get_matching_class(athlete, game)

            if existing_result:
                result_id = existing_result['id']
                flash_message = 'Result updated successfully (overwritten)'

                if game['event'] in Config.get_field_events():
                    existing_attempts_from_db = execute_query("""
                        SELECT attempt_number, value, wind_velocity, height, raza_score, raza_score_precise
                        FROM attempts 
                        WHERE result_id = %s 
                        ORDER BY attempt_number
                    """, (result_id,), fetch=True)

                    existing_attempts_dict = {}
                    for att in existing_attempts_from_db:
                        existing_attempts_dict[att['attempt_number']] = {
                            'value': att['value'],
                            'wind_velocity': att['wind_velocity'],
                            'height': att['height'],
                            'raza_score': att['raza_score'] or 0,
                            'raza_score_precise': att['raza_score_precise'] or 0.0
                        }

                    attempts_data = {}
                    for i, attempt_value in enumerate(attempts):
                        attempt_num = i + 1
                        if attempt_value:
                            raza_score = 0
                            raza_score_precise = 0.0

                            if attempt_value.upper() not in Config.get_result_special_values():
                                try:
                                    attempt_float = float(attempt_value)
                                    if game.get('wpa_points', False):
                                        raza_score, raza_score_precise = calculate_and_store_raza(athlete,
                                                                                                  game, attempt_float,
                                                                                                  matching_class)
                                except (ValueError, TypeError) as e:
                                    print(f"Error processing attempt {attempt_num}: {e}")

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

                            attempts_data[attempt_num] = {
                                'value': attempt_value,
                                'raza_score': raza_score,
                                'raza_score_precise': raza_score_precise,
                                'wind_velocity': wind_velocity,
                                'height': height_value
                            }
                        elif attempt_num in existing_attempts_dict:
                            attempts_data[attempt_num] = existing_attempts_dict[attempt_num]

                    all_valid_attempts = []
                    all_raza_scores = []
                    for attempt_num, attempt_data in attempts_data.items():
                        if attempt_data['value'] and attempt_data[
                            'value'].upper() not in Config.get_result_special_values():
                            try:
                                attempt_float = float(attempt_data['value'])
                                all_valid_attempts.append(attempt_float)
                                if attempt_data['raza_score'] > 0:
                                    all_raza_scores.append(attempt_data['raza_score'])
                            except (ValueError, TypeError):
                                continue

                    if not all_valid_attempts:
                        performance_value = "NM"
                        max_raza_score = 0
                        max_raza_score_precise = 0.0
                        best_attempt_display = None
                    else:
                        performance_value = max(all_valid_attempts)
                        best_attempt_display = f"{performance_value:.2f}"
                        max_raza_score = 0
                        max_raza_score_precise = 0.0
                        if game.get('wpa_points', False):
                            max_raza_score, max_raza_score_precise = calculate_and_store_raza(athlete, game,
                                                                                              performance_value,
                                                                                              matching_class)

                    result_data = {
                        'value': performance_value,
                        'best_attempt': best_attempt_display,
                        'raza_score': max_raza_score,
                        'raza_score_precise': max_raza_score_precise
                    }
                    if weight:
                        try:
                            result_data['weight'] = float(weight)
                        except (ValueError, TypeError):
                            pass

                    Result.update(result_id, **result_data)

                    for attempt_num, attempt_data in attempts_data.items():
                        existing_attempt = execute_one("""
                            SELECT id FROM attempts 
                            WHERE result_id = %s AND attempt_number = %s
                        """, (result_id, attempt_num))

                        if existing_attempt:
                            execute_query("""
                                UPDATE attempts 
                                SET value = %s, wind_velocity = %s, height = %s, 
                                    raza_score = %s, raza_score_precise = %s
                                WHERE id = %s
                            """, (
                                attempt_data['value'],
                                attempt_data.get('wind_velocity'),
                                attempt_data.get('height'),
                                attempt_data['raza_score'],
                                attempt_data['raza_score_precise'],
                                existing_attempt['id']
                            ))
                        else:
                            Attempt.create(
                                result_id=result_id,
                                attempt_number=attempt_num,
                                value=attempt_data['value'],
                                wind_velocity=attempt_data.get('wind_velocity'),
                                raza_score=attempt_data['raza_score'],
                                raza_score_precise=attempt_data['raza_score_precise'],
                                height=attempt_data.get('height')
                            )

                    if game['event'] in ['Long Jump', 'Triple Jump', 'Shot Put', 'Discus Throw', 'Javelin Throw',
                                         'Club Throw']:
                        qualifying_attempts = sum(1 for i in range(1, 4) if i in attempts_data and
                                                  attempts_data[i]['value'] and
                                                  attempts_data[i][
                                                      'value'].upper() not in Config.get_result_special_values())
                        if qualifying_attempts >= 3:
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
                            if game.get('wpa_points', False):
                                max_raza_score, max_raza_score_precise = calculate_and_store_raza(athlete,
                                                                                                  game,
                                                                                                  performance_seconds,
                                                                                                  matching_class)
                            else:
                                max_raza_score = 0
                                max_raza_score_precise = 0.0
                        except (ValueError, IndexError) as e:
                            flash('Invalid time format', 'danger')
                            return redirect(url_for('admin.game_results', id=game_id))

                    result_data = {
                        'value': performance_value,
                        'raza_score': max_raza_score,
                        'raza_score_precise': max_raza_score_precise
                    }

                    Result.update(result_id, **result_data)

                flash(flash_message, 'success')
                return redirect(url_for('admin.game_results', id=game_id))

            if not StartList.athlete_in_startlist(game_id, athlete_sdms):
                flash(f'Warning: Athlete SDMS {athlete_sdms} is not in the start list.', 'warning')

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
                            if game.get('wpa_points', False):
                                raza_score, raza_score_precise = calculate_and_store_raza(athlete, game,
                                                                                          attempt_float, matching_class)
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
                    if raza_scores and game.get('wpa_points', False):
                        for i, attempt_value in enumerate(all_attempt_values):
                            if attempt_value == performance_value:
                                raza_score, raza_score_precise = calculate_and_store_raza(athlete, game,
                                                                                          attempt_value, matching_class)
                                max_raza_score_precise = raza_score_precise
                                break

                result_data = {
                    'game_id': game_id,
                    'athlete_sdms': athlete_sdms,
                    'guide_sdms': guide_sdms,
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


                result_id = Result.create(**result_data)
                if not result_id:
                    flash('Failed to create result', 'danger')
                    return redirect(url_for('admin.game_results', id=game_id))

                if attempts_data:
                    Attempt.create_multiple(result_id=result_id, attempts=attempts_data)

                if game['event'] in ['Long Jump', 'Triple Jump', 'Shot Put', 'Discus Throw', 'Javelin Throw',
                                     'Club Throw'] and len(attempts_data) >= 3:
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
                        if game.get('wpa_points', False):
                            max_raza_score, max_raza_score_precise = calculate_and_store_raza(athlete, game,
                                                                                              performance_seconds,
                                                                                              matching_class)
                        else:
                            max_raza_score = 0
                            max_raza_score_precise = 0.0
                    except (ValueError, IndexError) as e:
                        flash('Invalid time format', 'danger')
                        return redirect(url_for('admin.game_results', id=game_id))

                result_data = {
                    'game_id': game_id,
                    'athlete_sdms': athlete_sdms,
                    'guide_sdms': guide_sdms,
                    'value': performance_value,
                    'raza_score': max_raza_score,
                    'raza_score_precise': max_raza_score_precise
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

    @bp.route('/games/<int:game_id>/recalculate-high-jump', methods=['POST'])
    @admin_required
    def recalculate_high_jump_results(game_id):
        try:
            game = Game.get_by_id(game_id)
            if not game or game['event'] != 'High Jump':
                return jsonify({'error': 'Not a High Jump event'}), 400
            # Recalculer le classement automatique
            success = Result.auto_rank_results(game_id)
            if success:
                return jsonify({'success': True, 'message': 'High Jump ranking recalculated successfully'})
            else:
                return jsonify({'error': 'Failed to recalculate ranking'}), 500
        except Exception as e:
            print(f"Error recalculating High Jump: {e}")
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500

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
            athlete = Athlete.get_by_sdms(result['athlete_sdms'])
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
                matching_class = get_matching_class(athlete, game)
                raza_score, raza_score_precise = calculate_and_store_raza(athlete, game, height_float, matching_class)
            Attempt.create(result_id, next_attempt, attempt_result, None, raza_score, raza_score_precise, height_float)
            if attempt_result == 'O':
                current_best = execute_one(
                    "SELECT MAX(height) as best_height FROM attempts WHERE result_id = %s AND value = 'O'",
                    (result_id,)
                )
                if current_best and current_best['best_height']:
                    best_height = current_best['best_height']
                    matching_class = get_matching_class(athlete, game)
                    best_raza_score, best_raza_score_precise = calculate_and_store_raza(athlete, game, best_height,
                                                                                        matching_class)
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
                JOIN athletes a ON r.athlete_sdms = a.sdms
                WHERE r.game_id = %s
            """, (game_id,), fetch=True)
            updated_count = 0
            for result in results:
                if result['value'] not in Config.get_result_special_values():
                    try:
                        performance = float(result['value'])
                        athlete_data = {'gender': result['gender'], 'class': result['class']}
                        matching_class = get_matching_class(athlete_data, game)
                        raza_score, raza_score_precise = calculate_and_store_raza(athlete_data, game, performance,
                                                                                  matching_class)
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
                                                                                                  attempt_perf,
                                                                                                  matching_class)
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
            athlete_sdms = request.json.get('athlete_sdms')
            if not game_id or not athlete_sdms:
                return jsonify({'error': 'Missing parameters'}), 400
            StartList.create(game_id, athlete_sdms, None)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @bp.route('/games/<int:game_id>/check-result/<int:athlete_sdms>')
    @admin_required
    def check_result_exists(game_id, athlete_sdms):
        result = Result.get_by_game_athlete(game_id, athlete_sdms)
        if result:
            return jsonify({'exists': True, 'result_id': result['id']})
        return jsonify({'exists': False})

    @bp.route('/games/<int:game_id>/auto-rank-round1', methods=['POST'])
    @admin_required
    def auto_rank_round1(game_id):
        try:
            game = Game.get_by_id(game_id)
            if not game or game['event'] not in ['Long Jump', 'Triple Jump', 'Shot Put', 'Discus Throw',
                                                 'Javelin Throw', 'Club Throw']:
                return jsonify({'error': 'Invalid game or not a qualifying field event'}), 400

            # Get all results with at least 3 attempts and their attempts
            results = execute_query("""
                SELECT r.*, a.gender, a.class, a.firstname, a.lastname
                FROM results r
                JOIN athletes a ON r.athlete_sdms = a.sdms
                WHERE r.game_id = %s
                AND (SELECT COUNT(*) FROM attempts att WHERE att.result_id = r.id AND att.attempt_number <= 3) >= 3
            """, (game_id,), fetch=True)

            if not results:
                return jsonify({'error': "No athletes with 3 valid attempts found."}), 400

            special_values = Config.get_result_special_values()

            # Pour chaque résultat, récupérer les 3 premiers essais et calculer les tie-breakers
            for result in results:
                attempts = execute_query("""
                    SELECT value FROM attempts 
                    WHERE result_id = %s AND attempt_number <= 3
                    ORDER BY attempt_number
                """, (result['id'],), fetch=True)

                # Convertir les essais en valeurs numériques
                valid_attempts = []
                for attempt in attempts:
                    val = attempt['value']
                    if val and str(val).strip() not in special_values:
                        try:
                            valid_attempts.append(float(val))
                        except (ValueError, TypeError):
                            pass

                # Trier les essais par ordre décroissant (meilleur en premier)
                valid_attempts.sort(reverse=True)

                # Stocker les tie-breakers (jusqu'à 3 essais)
                result['best_of_three'] = valid_attempts[0] if valid_attempts else 0.0
                result['second_best'] = valid_attempts[1] if len(valid_attempts) > 1 else 0.0
                result['third_best'] = valid_attempts[2] if len(valid_attempts) > 2 else 0.0

            # Fonction de tri avec tie-breakers
            def get_sort_key(result):
                return (
                    -result['best_of_three'],  # Meilleur essai (négatif car on veut décroissant)
                    -result['second_best'],  # 2ème meilleur essai
                    -result['third_best']  # 3ème meilleur essai
                )

            # Trier les résultats selon les critères de tie-breaking
            results.sort(key=get_sort_key)

            total_athletes = len(results)

            # Dynamic selection: min 3, max 8, or all if less than 8
            if total_athletes <= 3:
                selected_count = total_athletes
            elif total_athletes <= 8:
                selected_count = total_athletes  # All advance if 8 or less
            else:
                selected_count = 8  # Top 8 if more than 8

            # Select finalists (reverse order for final round)
            finalists = results[:selected_count]
            finalists.reverse()  # Reverse order: worst to best for final round

            # Update final_order for finalists
            for i, result in enumerate(finalists):
                execute_query(
                    "UPDATE results SET final_order = %s WHERE id = %s",
                    (i + 1, result['id'])
                )

            # Clear final_order for non-finalists
            for result in results[selected_count:]:
                execute_query(
                    "UPDATE results SET final_order = NULL WHERE id = %s",
                    (result['id'],)
                )

            # Message détaillé avec les performances
            message = f'{selected_count}/{total_athletes} athletes selected for final round.'
            if selected_count > 1:
                first_finalist = finalists[0]
                last_finalist = finalists[-1]
                message += f' Order: {first_finalist["firstname"]} {first_finalist["lastname"]} ({first_finalist["best_of_three"]:.2f}m, 1st) to {last_finalist["firstname"]} {last_finalist["lastname"]} ({last_finalist["best_of_three"]:.2f}m, {selected_count}th)'

            # Log des tie-breakers pour debug si nécessaire
            print(f"Final selection for game {game_id}:")
            for i, finalist in enumerate(finalists):
                print(
                    f"  {i + 1}. {finalist['firstname']} {finalist['lastname']}: {finalist['best_of_three']:.2f} / {finalist['second_best']:.2f} / {finalist['third_best']:.2f}")

            return jsonify({
                'success': True,
                'message': message,
                'finalists': len(finalists),
                'total_athletes': total_athletes
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
            weight = data.get('weight')
            guide_sdms = data.get('guide_sdms')
            athlete = Athlete.get_by_sdms(result['athlete_sdms'])
            if not athlete:
                return jsonify({'error': 'Athlete not found'}), 404

            matching_class = get_matching_class(athlete, game)

            # High Jump specific handling
            if game['event'] == 'High Jump':
                high_jump_attempts = data.get('high_jump_attempts', {})
                # Supprimer toutes les tentatives existantes
                execute_query("DELETE FROM attempts WHERE result_id = %s", (result_id,))
                # Ajouter les nouvelles tentatives
                max_height = 0
                for attempt_num, attempt_data in high_jump_attempts.items():
                    height = attempt_data.get('height')
                    value = attempt_data.get('value')
                    if height and value:
                        raza_score = 0
                        raza_score_precise = 0.0
                        if value == 'O' and game.get('wpa_points', False):
                            raza_score, raza_score_precise = calculate_and_store_raza(athlete, game, height,
                                                                                      matching_class)
                        Attempt.create(result_id, int(attempt_num), value, None, raza_score, raza_score_precise, height)
                        if value == 'O' and height > max_height:
                            max_height = height
                # Mettre à jour le résultat principal
                if max_height > 0:
                    best_raza_score, best_raza_score_precise = calculate_and_store_raza(athlete, game, max_height,
                                                                                        matching_class)
                    Result.update(result_id,
                                  value=max_height,
                                  best_attempt=f"{max_height:.2f}",
                                  raza_score=best_raza_score,
                                  raza_score_precise=best_raza_score_precise,
                                  guide_sdms=guide_sdms)
                else:
                    Result.update(result_id, value='NH', best_attempt=None, raza_score=0, raza_score_precise=0.0, guide_sdms=guide_sdms)
            else:
                # Other field events (code existant)
                attempts_data = data.get('attempts', {})
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
                                raza_score, raza_score_precise = calculate_and_store_raza(athlete, game, attempt_float,
                                                                                          matching_class)
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
                        max_raza_score, max_raza_score_precise = calculate_and_store_raza(athlete, game,
                                                                                          best_performance,
                                                                                          matching_class)
                    Result.update(result_id,
                                  value=best_performance,
                                  best_attempt=f"{best_performance:.2f}",
                                  raza_score=max_raza_score,
                                  raza_score_precise=max_raza_score_precise,
                                  weight=weight,
                                  guide_sdms=guide_sdms)
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
            for athlete_sdms, heights in results_data.items():
                athlete = Athlete.get_by_sdms(int(athlete_sdms))
                if not athlete:
                    continue
                # Find or create result
                result = Result.get_by_game_athlete(game_id, athlete_sdms)
                if not result:
                    result_id = Result.create(
                        game_id=game_id,
                        athlete_sdms=athlete_sdms,
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
                        matching_class = get_matching_class(athlete, game)
                        raza_score, raza_score_precise = calculate_and_store_raza(
                            athlete, game, best_height, matching_class
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

    @bp.route('/games/<int:game_id>/select-finalists', methods=['POST'])
    @admin_required
    def select_finalists_for_field_event(game_id):
        try:
            game = Game.get_by_id(game_id)
            if not game or game['event'] not in ['Long Jump', 'Triple Jump', 'Shot Put', 'Discus Throw',
                                                 'Javelin Throw', 'Club Throw']:
                return jsonify({'error': 'Invalid game or not a qualifying field event'}), 400
            # Get all results with at least 3 attempts
            results = execute_query("""
                SELECT r.*, a.gender, a.class,
                       (SELECT MAX(CAST(att.value AS FLOAT)) 
                        FROM attempts att 
                        WHERE att.result_id = r.id 
                        AND att.attempt_number <= 3 
                        AND att.value NOT IN %s
                        AND att.value IS NOT NULL
                        AND att.value != '') as best_of_three
                FROM results r
                JOIN athletes a ON r.athlete_sdms = a.sdms
                WHERE r.game_id = %s
                AND (SELECT COUNT(*) FROM attempts att 
                     WHERE att.result_id = r.id 
                     AND att.attempt_number <= 3
                     AND att.value IS NOT NULL
                     AND att.value != '') >= 3
                ORDER BY best_of_three DESC NULLS LAST
            """, (tuple(Config.get_result_special_values()), game_id,), fetch=True)
            if len(results) < 8:
                # If fewer than 8 athletes, all advance
                selected_count = len(results)
            else:
                selected_count = 8
            if selected_count == 0:
                return jsonify({'error': "No athletes with 3 valid attempts found."}), 400
            # Select top performers (reverse order for final round)
            finalists = results[:selected_count]
            finalists.reverse()  # Reverse order: worst to best for final round
            # Update final_order for finalists (1 = first to jump in final)
            for i, result in enumerate(finalists):
                execute_query(
                    "UPDATE results SET final_order = %s WHERE id = %s",
                    (i + 1, result['id'])
                )
            # Clear final_order for non-finalists
            for result in results[selected_count:]:
                execute_query(
                    "UPDATE results SET final_order = NULL WHERE id = %s",
                    (result['id'],)
                )
            message = f'{selected_count} athletes selected for final round.'
            if selected_count == 8:
                message += f' Order: {finalists[0]["athlete_sdms"]} (1st to jump) to {finalists[-1]["athlete_sdms"]} (8th to jump)'
            return jsonify({
                'success': True,
                'message': message
            })
        except Exception as e:
            print(f"Error in select_finalists_for_field_event: {e}")
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500

    @bp.route('/games/<int:game_id>/update-manual-ranking', methods=['POST'])
    @admin_required
    def update_manual_ranking(game_id):
        try:
            game = Game.get_by_id(game_id)
            if not game:
                return jsonify({'error': 'Game not found'}), 404
            data = request.json
            rankings = data.get('rankings', [])
            if not rankings:
                return jsonify({'error': 'No rankings provided'}), 400
            # Update rankings in database
            for ranking in rankings:
                result_id = ranking.get('result_id')
                new_rank = ranking.get('rank')
                if result_id and new_rank:
                    execute_query(
                        "UPDATE results SET rank = %s WHERE id = %s AND game_id = %s",
                        (new_rank, result_id, game_id)
                    )
            return jsonify({'success': True, 'message': 'Rankings updated successfully'})
        except Exception as e:
            print(f"Error updating manual ranking: {e}")
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500

    @bp.route('/games/<int:game_id>/toggle-official', methods=['POST'])
    @technical_delegate_required
    def toggle_game_official(game_id):
        try:
            new_status = Game.toggle_official_status(game_id, current_user.id)
            if new_status:
                results = Result.get_all(game_id=game_id)
                records_found = 0
                pbs_found = 0

                for result in results:
                    print(f"Result keys: {result.keys()}")
                    print(f"Result data: {result}")

                    athlete = Athlete.get_by_sdms(result['athlete_sdms'])
                    if athlete:
                        game = Game.get_by_id(game_id)
                        athlete_class = get_matching_class(athlete, game)
                        if athlete_class:
                            time_field = None
                            time_value = None

                            possible_time_fields = ['time', 'result_time', 'performance', 'result', 'score']

                            for field in possible_time_fields:
                                if field in result:
                                    time_field = field
                                    time_value = result[field]
                                    break

                            if time_field and time_value:
                                print(f"Found time field '{time_field}' with value: {time_value}")

                                processed_result = result.copy()
                                if isinstance(time_value, str):
                                    processed_result[time_field] = time_string_to_seconds(time_value)

                                created_records, created_pbs = check_for_records_and_pbs(
                                    processed_result, athlete, game, athlete_class
                                )
                                records_found += created_records
                                pbs_found += created_pbs
                            else:
                                print(f"No time field found in result: {result}")

                message = f'Game marked as OFFICIAL. Found {records_found} new records and {pbs_found} personal bests.'
            else:
                message = 'Game results marked as UNOFFICIAL'
            tunis_tz = pytz.timezone('Africa/Tunis')
            return jsonify({
                'success': True,
                'message': message,
                'official': new_status,
                'official_by': current_user.username if new_status else None,
                'official_date': datetime.now(tunis_tz).strftime('%Y-%m-%d %H:%M:%S') if new_status else None
            })
        except Exception as e:
            print(f"Error toggling game official status: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

def time_string_to_seconds(time_str):
    if not time_str or time_str == '':
        return None

    try:
        if ':' in time_str:
            parts = time_str.split(':')
            minutes = int(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds
        else:
            return float(time_str)
    except (ValueError, IndexError):
        return None


def update_final_order_after_three_attempts(game_id):
    try:
        results_with_three_attempts = execute_query("""
            SELECT r.id, r.athlete_sdms, r.value as best_performance
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
                "UPDATE startlist SET final_order = %s WHERE game_id = %s AND athlete_sdms = %s",
                (i + 1, game_id, result['athlete_sdms'])
            )
    except Exception as e:
        print(f"Error updating final order: {e}")


def check_and_update_long_jump_progression(attempts):
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


def process_result_for_records(result_id):
    result = Result.get_by_id(result_id)
    if not result:
        return
    game = Game.get_by_id(result['game_id'])
    athlete = Athlete.get_by_sdms(result['athlete_sdms'])
    if not game or not athlete or not game.get('official'):
        return

    athlete_class = get_matching_class(athlete, game)
    if athlete_class:
        check_for_records_and_pbs(result, athlete, game, athlete_class)