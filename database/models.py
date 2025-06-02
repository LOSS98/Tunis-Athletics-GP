import traceback

from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from database.db_manager import execute_query, execute_one
from datetime import datetime, timedelta
from config import Config
import re
from utils.raza_calculation import calculate_raza, verify_combination


class User(UserMixin):
    def __init__(self, id, username, admin_type='volunteer'):
        self.id = id
        self.username = username
        self.admin_type = admin_type

    def is_loc(self):
        return self.admin_type == 'loc'

    @staticmethod
    def get(user_id):
        user = execute_one("SELECT * FROM users WHERE id = %s", (user_id,))
        if user:
            return User(user['id'], user['username'], user.get('admin_type', 'volunteer'))
        return None

    @staticmethod
    def get_by_username(username):
        user = execute_one("SELECT * FROM users WHERE username = %s", (username,))
        return user

    @staticmethod
    def get_all():
        return execute_query("SELECT * FROM users ORDER BY id", fetch=True)

    @staticmethod
    def create(username, password, admin_type='volunteer'):
        password_hash = generate_password_hash(password)
        return execute_query(
            "INSERT INTO users (username, password_hash, admin_type) VALUES (%s, %s, %s)",
            (username, password_hash, admin_type)
        )

    @staticmethod
    def update(user_id, **data):
        if 'password' in data:
            data['password_hash'] = generate_password_hash(data.pop('password'))

        set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
        query = f"UPDATE users SET {set_clause} WHERE id = %s"
        params = list(data.values()) + [user_id]
        return execute_query(query, params)

    @staticmethod
    def delete(user_id):
        return execute_query("DELETE FROM users WHERE id = %s", (user_id,))

    @staticmethod
    def verify_password(username, password):
        user = User.get_by_username(username)
        if user and check_password_hash(user['password_hash'], password):
            return User(user['id'], user['username'], user.get('admin_type', 'volunteer'))
        return None


class Athlete:
    @staticmethod
    def get_all(**filters):
        query = "SELECT * FROM athletes WHERE 1=1"
        params = []

        if filters:
            for key, value in filters.items():
                if value:
                    query += f" AND {key} = %s"
                    params.append(value)

        query += " ORDER BY bib"
        return execute_query(query, params, fetch=True)

    @staticmethod
    def get_by_bib(bib):
        return execute_one("SELECT * FROM athletes WHERE bib = %s", (bib,))

    @staticmethod
    def get_by_id(id):
        return execute_one("SELECT * FROM athletes WHERE id = %s", (id,))

    @staticmethod
    def create(**data):
        keys = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        query = f"INSERT INTO athletes ({keys}) VALUES ({placeholders})"
        return execute_query(query, list(data.values()))

    @staticmethod
    def update(id, **data):
        set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
        query = f"UPDATE athletes SET {set_clause} WHERE id = %s"
        params = list(data.values()) + [id]
        return execute_query(query, params)

    @staticmethod
    def delete(id):
        return execute_query("DELETE FROM athletes WHERE id = %s", (id,))

    @staticmethod
    def search(query):
        search_query = """
            SELECT * FROM athletes 
            WHERE LOWER(firstname) LIKE LOWER(%s)
            OR LOWER(lastname) LIKE LOWER(%s)
            OR LOWER(country) LIKE LOWER(%s)
            OR bib::text LIKE %s
            ORDER BY bib
        """
        search_term = f"%{query}%"
        return execute_query(search_query, (search_term, search_term, search_term, search_term), fetch=True)


class Game:
    @staticmethod
    def get_all(**filters):
        query = "SELECT * FROM games WHERE 1=1"
        params = []

        if filters:
            for key, value in filters.items():
                if value:
                    query += f" AND {key} = %s"
                    params.append(value)

        query += " ORDER BY day, time"
        return execute_query(query, params, fetch=True)

    @staticmethod
    def get_by_id(id):
        game = execute_one("SELECT * FROM games WHERE id = %s", (id,))
        if game:
            game['classes_list'] = [c.strip() for c in game['classes'].split(',')]
        return game

    @staticmethod
    def create(**data):
        keys = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        query = f"INSERT INTO games ({keys}) VALUES ({placeholders})"
        return execute_query(query, list(data.values()))

    @staticmethod
    def update(id, **data):
        set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
        query = f"UPDATE games SET {set_clause} WHERE id = %s"
        params = list(data.values()) + [id]
        return execute_query(query, params)

    @staticmethod
    def delete(id):
        return execute_query("DELETE FROM games WHERE id = %s", (id,))

    @staticmethod
    def update_status(id, status):
        return execute_query("UPDATE games SET status = %s WHERE id = %s", (status, id))

    @staticmethod
    def update_velocity(id, velocity_value):
        if velocity_value == 0:
            velocity_value = None
        return execute_query("UPDATE games SET wind_velocity = %s WHERE id = %s", (velocity_value, id))

    @staticmethod
    def toggle_publish(id):
        game = execute_one("SELECT published FROM games WHERE id = %s", (id,))
        if game:
            new_status = not game.get('published', False)
            execute_query("UPDATE games SET published = %s WHERE id = %s", (new_status, id))
            return new_status
        return False

    @staticmethod
    def has_alerts(id):
        game = execute_one("SELECT gender, classes FROM games WHERE id = %s", (id,))
        if not game:
            return False

        game_gender = game['gender']
        game_classes = [c.strip() for c in game['classes'].split(',')]

        result = execute_one("""
            SELECT COUNT(*) as count FROM results r
            JOIN athletes a ON r.athlete_bib = a.bib
            WHERE r.game_id = %s AND (a.gender != %s OR a.class NOT IN %s)
        """, (id, game_gender, tuple(game_classes)))

        startlist_result = execute_one("""
            SELECT COUNT(*) as count FROM startlist s
            JOIN athletes a ON s.athlete_bib = a.bib
            WHERE s.game_id = %s AND (a.gender != %s OR a.class NOT IN %s)
        """, (id, game_gender, tuple(game_classes)))

        return (result['count'] > 0) or (startlist_result['count'] > 0)

    @staticmethod
    def get_with_status():
        games = Game.get_all()
        current_day = Config.get_current_day()
        current_time = datetime.now()

        if current_day is None:
            current_day = 1
        try:
            current_day = int(current_day)
        except (ValueError, TypeError):
            current_day = 1

        for game in games:
            game_day = game['day']

            try:
                game_day = int(game_day)
            except (ValueError, TypeError):
                game_day = 1

            game_time = datetime.strptime(str(game['time']), '%H:%M:%S').replace(
                year=current_time.year,
                month=current_time.month,
                day=current_time.day
            )

            if game['status'] not in ['finished', 'cancelled']:
                if current_day == game_day:
                    if current_time < game_time:
                        game['computed_status'] = 'scheduled'
                    else:
                        game['computed_status'] = 'in_progress'
                elif current_day < game_day:
                    game['computed_status'] = 'scheduled'
                else:
                    game['computed_status'] = 'finished'
            else:
                game['computed_status'] = game['status']

            game['has_results'] = Game.has_results(game['id'])
            game['has_startlist'] = bool(game.get('start_file')) or StartList.has_startlist(game['id'])
            game['is_published'] = game.get('published', False)
            game['has_alerts'] = Game.has_alerts(game['id'])

            result_count = Result.count_by_game(game['id'])
            startlist_count = StartList.count_by_game(game['id'])
            game['result_count'] = result_count
            game['startlist_count'] = startlist_count
            game['result_is_complete'] = result_count >= game['nb_athletes']
            game['startlist_is_complete'] = startlist_count >= game['nb_athletes']
            game['classes_list'] = [c.strip() for c in game['classes'].split(',')]

        return games

    @staticmethod
    def has_results(game_id):
        count = execute_one("SELECT COUNT(*) as count FROM results WHERE game_id = %s", (game_id,))
        return count['count'] > 0 if count else False

    @staticmethod
    def auto_rank_results(game_id):
        try:
            game = Game.get_by_id(game_id)
            if not game:
                return False

            results = execute_query("""
                SELECT r.*, a.gender as athlete_gender, a.class as athlete_class
                FROM results r
                JOIN athletes a ON r.athlete_bib = a.bib
                WHERE r.game_id = %s
            """, (game_id,), fetch=True)

            if not results:
                return False

            is_track = game['event'] in Config.get_track_events()
            is_field = game['event'] in Config.get_field_events()
            use_wpa_points = game.get('wpa_points', False)
            special_values = Config.get_result_special_values()

            valid_results = []
            for result in results:
                if result['value'] not in special_values:
                    if is_field:
                        attempts = Attempt.get_by_result(result['id'])
                        result['attempts_list'] = []
                        for attempt in attempts:
                            if attempt['value'] and attempt['value'] not in special_values:
                                try:
                                    result['attempts_list'].append(float(attempt['value']))
                                except ValueError:
                                    pass
                        result['attempts_list'].sort(reverse=True)
                    valid_results.append(result)

            if not valid_results:
                return True

            def compare_results(result):
                if use_wpa_points:
                    primary_key = -(result.get('raza_score') or 0)
                    secondary_key = -(result.get('raza_score_precise') or 0)
                else:
                    try:
                        if is_track:
                            primary_key = float(result['value'])
                            secondary_key = 0
                        else:
                            primary_key = -float(result['value'])
                            secondary_key = 0
                    except ValueError:
                        primary_key = float('inf') if is_track else 0
                        secondary_key = 0

                tie_breakers = []
                if is_field and 'attempts_list' in result:
                    tie_breakers = result['attempts_list'][:6]
                    while len(tie_breakers) < 6:
                        tie_breakers.append(0)

                return (primary_key, secondary_key, *tie_breakers)

            valid_results.sort(key=compare_results)

            current_rank = 1
            previous_comparison = None

            for i, result in enumerate(valid_results):
                current_comparison = compare_results(result)

                if i > 0 and current_comparison != previous_comparison:
                    current_rank = i + 1

                execute_query("UPDATE results SET rank = %s WHERE id = %s", (str(current_rank), result['id']))
                previous_comparison = current_comparison

            for result in results:
                if result['value'] in special_values:
                    execute_query("UPDATE results SET rank = %s WHERE id = %s", ('-', result['id']))

            return True

        except Exception as e:
            print(f"Error in auto_rank_results: {e}")
            import traceback
            traceback.print_exc()
            return False

    @staticmethod
    def update_field_event_progression(game_id):
        game = Game.get_by_id(game_id)
        if not game or game['event'] in ['High Jump'] or game['event'] not in Config.get_field_events():
            return False

        results = execute_query("""
            SELECT r.id, r.athlete_bib, r.value, 
                   COUNT(DISTINCT a.attempt_number) as attempt_count
            FROM results r
            LEFT JOIN attempts a ON r.id = a.result_id AND a.attempt_number <= 3
            WHERE r.game_id = %s AND r.value NOT IN %s
            GROUP BY r.id, r.athlete_bib, r.value
            HAVING COUNT(DISTINCT a.attempt_number) >= 3
        """, (game_id, tuple(Config.get_result_special_values())), fetch=True)

        if len(results) <= 8:
            return False

        sorted_results = sorted(results, key=lambda x: float(x['value']), reverse=True)

        top_8 = sorted_results[:8]

        final_order_results = sorted(top_8, key=lambda x: float(x['value']))

        for i, result in enumerate(final_order_results):
            execute_query(
                "UPDATE results SET final_order = %s WHERE id = %s",
                (i + 1, result['id'])
            )

        for result in sorted_results[8:]:
            execute_query(
                "UPDATE results SET final_order = NULL WHERE id = %s",
                (result['id'],)
            )

        return True

    @staticmethod
    def check_and_update_progression(game_id):
        game = Game.get_by_id(game_id)
        if not game or game['event'] in ['High Jump'] or game['event'] not in Config.get_field_events():
            return

        results_with_3_attempts = execute_query("""
            SELECT COUNT(*) as count
            FROM results r
            WHERE r.game_id = %s 
            AND r.value NOT IN %s
            AND (
                SELECT COUNT(DISTINCT attempt_number) 
                FROM attempts a 
                WHERE a.result_id = r.id 
                AND a.attempt_number <= 3
            ) >= 3
        """, (game_id, tuple(Config.get_result_special_values())), fetch=True)

        if results_with_3_attempts and results_with_3_attempts[0]['count'] >= 8:
            Game.update_field_event_progression(game_id)


class Result:
    @staticmethod
    def get_all(**filters):
        query = """
            SELECT r.*, a.firstname, a.lastname, a.country, a.gender as athlete_gender, a.class as athlete_class
            FROM results r
            JOIN athletes a ON r.athlete_bib = a.bib
            WHERE 1=1
        """
        params = []

        if filters:
            for key, value in filters.items():
                if value:
                    query += f" AND r.{key} = %s"
                    params.append(value)

        query += " ORDER BY CASE WHEN r.rank ~ '^[0-9]+' THEN CAST(r.rank AS INTEGER) ELSE 999 END, r.rank"
        results = execute_query(query, params, fetch=True)

        if results and filters.get('game_id'):
            game = Game.get_by_id(filters['game_id'])
            if game:
                field_events = Config.get_field_events()

                if game['event'] in field_events:
                    for result in results:
                        result['attempts'] = Attempt.get_by_result(result['id'])

        return results

    @staticmethod
    def get_by_id(id):
        return execute_one("SELECT * FROM results WHERE id = %s", (id,))

    @staticmethod
    def get_by_game_athlete(game_id, athlete_bib):
        return execute_one("SELECT * FROM results WHERE game_id = %s AND athlete_bib = %s", (game_id, athlete_bib))

    @staticmethod
    def create(**data):
        if 'value' in data and isinstance(data['value'], (int, float)):
            game_id = data.get('game_id')
            if game_id:
                game = Game.get_by_id(game_id)
                if game and game['event'] in Config.get_track_events():
                    data['value'] = Config.format_time(data['value'])
                elif game and game['event'] in Config.get_field_events():
                    data['value'] = Config.format_distance(data['value'])

        if 'wind_velocity' in data and data['wind_velocity'] is not None:
            data['wind_velocity'] = float(Config.format_wind(data['wind_velocity']))

        if 'weight' in data and data['weight'] is not None:
            data['weight'] = float(data['weight'])

        keys = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        query = f"INSERT INTO results ({keys}) VALUES ({placeholders}) RETURNING id"
        result = execute_query(query, list(data.values()))
        return result['id'] if result else None

    @staticmethod
    def update(id, **data):
        set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
        query = f"UPDATE results SET {set_clause} WHERE id = %s"
        params = list(data.values()) + [id]
        return execute_query(query, params)

    @staticmethod
    def delete(id):
        return execute_query("DELETE FROM results WHERE id = %s", (id,))

    @staticmethod
    def count_by_game(game_id):
        count = execute_one("SELECT COUNT(*) as count FROM results WHERE game_id = %s", (game_id,))
        return count['count'] if count else 0

    @staticmethod
    def get_records():
        query = """
            SELECT r.*, a.firstname, a.lastname, a.country, a.photo,
                   g.event, g.gender, g.classes, g.day, g.time, g.id as game_id
            FROM results r
            JOIN athletes a ON r.athlete_bib = a.bib
            JOIN games g ON r.game_id = g.id
            WHERE r.record IS NOT NULL AND r.record != ''
            ORDER BY g.day DESC, g.time DESC
        """
        return execute_query(query, fetch=True)

    @staticmethod
    def auto_rank_results(game_id):
        try:
            game = Game.get_by_id(game_id)
            if not game:
                return False

            results = execute_query("""
                SELECT r.*, a.gender as athlete_gender, a.class as athlete_class
                FROM results r
                JOIN athletes a ON r.athlete_bib = a.bib
                WHERE r.game_id = %s
            """, (game_id,), fetch=True)

            if not results:
                return False

            is_track = game['event'] in Config.get_track_events()
            is_field = game['event'] in Config.get_field_events()
            use_wpa_points = game.get('wpa_points', False)
            special_values = Config.get_result_special_values()

            # Process valid results
            valid_results = []
            for result in results:
                if result['value'] not in special_values:
                    # Get all attempts for field events
                    if is_field:
                        attempts = Attempt.get_by_result(result['id'])
                        result['attempts_list'] = []

                        # Sort attempts by value (descending for field events)
                        for attempt in sorted(attempts, key=lambda x: x['attempt_number']):
                            if attempt['value'] and attempt['value'] not in special_values:
                                try:
                                    result['attempts_list'].append(float(attempt['value']))
                                except ValueError:
                                    pass

                    valid_results.append(result)

            if not valid_results:
                return True

            def compare_results(result):
                # Primary comparison: RAZA score or performance
                if use_wpa_points:
                    primary_key = -(result.get('raza_score_precise') or result.get('raza_score') or 0)
                else:
                    try:
                        if is_track:
                            primary_key = float(result['value'])
                        else:
                            primary_key = -float(result['value'])
                    except ValueError:
                        primary_key = float('inf') if is_track else 0

                # Secondary comparison: subsequent attempts for field events
                tie_breakers = []
                if is_field and 'attempts_list' in result:
                    # Sort attempts in descending order
                    sorted_attempts = sorted(result['attempts_list'], reverse=True)
                    # Use all attempts as tie breakers
                    tie_breakers = sorted_attempts + [0] * (6 - len(sorted_attempts))

                return (primary_key, *tie_breakers)

            # Sort results
            valid_results.sort(key=compare_results)

            # Assign ranks
            current_rank = 1
            previous_comparison = None

            for i, result in enumerate(valid_results):
                current_comparison = compare_results(result)

                # Check if this result is truly different from the previous
                if i > 0 and current_comparison != previous_comparison:
                    current_rank = i + 1

                execute_query("UPDATE results SET rank = %s WHERE id = %s",
                              (str(current_rank), result['id']))
                previous_comparison = current_comparison

            # Handle special values
            for result in results:
                if result['value'] in special_values:
                    execute_query("UPDATE results SET rank = %s WHERE id = %s",
                                  ('-', result['id']))

            return True

        except Exception as e:
            print(f"Error in auto_rank_results: {e}")
            traceback.print_exc()
            return False


class StartList:
    @staticmethod
    def get_by_game(game_id):
        query = """
            SELECT s.*, a.firstname, a.lastname, a.country, a.class, a.gender
            FROM startlist s
            JOIN athletes a ON s.athlete_bib = a.bib
            WHERE s.game_id = %s
            ORDER BY s.final_order IS NULL, s.final_order, s.lane_order, a.bib
        """
        return execute_query(query, (game_id,), fetch=True)

    @staticmethod
    def create(game_id, athlete_bib, lane_order=None):
        return execute_query(
            "INSERT INTO startlist (game_id, athlete_bib, lane_order) VALUES (%s, %s, %s)",
            (game_id, athlete_bib, lane_order)
        )

    @staticmethod
    def delete(game_id, athlete_bib):
        return execute_query(
            "DELETE FROM startlist WHERE game_id = %s AND athlete_bib = %s",
            (game_id, athlete_bib)
        )

    @staticmethod
    def has_startlist(game_id):
        count = execute_one("SELECT COUNT(*) as count FROM startlist WHERE game_id = %s", (game_id,))
        return count['count'] > 0 if count else False

    @staticmethod
    def count_by_game(game_id):
        count = execute_one("SELECT COUNT(*) as count FROM startlist WHERE game_id = %s", (game_id,))
        return count['count'] if count else 0

    @staticmethod
    def athlete_in_startlist(game_id, athlete_bib):
        result = execute_one("SELECT id FROM startlist WHERE game_id = %s AND athlete_bib = %s", (game_id, athlete_bib))
        return result is not None

    @staticmethod
    def update_order_for_long_jump(game_id):
        game = Game.get_by_id(game_id)
        if not game or game['event'] != 'Long Jump':
            return False

        results = execute_query("""
            SELECT r.athlete_bib, r.value as best_performance
            FROM results r
            WHERE r.game_id = %s AND r.value NOT IN ('DNS', 'DNF', 'DSQ', 'NM')
        """, (game_id,), fetch=True)

        if len(results) < 3:
            return False

        results.sort(key=lambda x: float(x['best_performance']))

        for i, result in enumerate(results):
            execute_query(
                "UPDATE startlist SET final_order = %s WHERE game_id = %s AND athlete_bib = %s",
                (i + 1, game_id, result['athlete_bib'])
            )

        return True

    @staticmethod
    def update_final_order_long_jump(game_id):
        game = Game.get_by_id(game_id)
        if not game or game['event'] != 'Long Jump':
            return False

        results = execute_query("""
            SELECT r.athlete_bib, r.value as best_performance, r.best_attempt,
                   a.firstname, a.lastname
            FROM results r
            JOIN athletes a ON r.athlete_bib = a.bib
            WHERE r.game_id = %s AND r.value NOT IN ('DNS', 'DNF', 'DSQ', 'NM')
        """, (game_id,), fetch=True)

        if len(results) < 8:
            return False

        final_order_results = []
        for result in results:
            attempts_count = execute_one(
                "SELECT COUNT(*) as count FROM attempts WHERE result_id = (SELECT id FROM results WHERE game_id = %s AND athlete_bib = %s)",
                (game_id, result['athlete_bib'])
            )

            if attempts_count and attempts_count['count'] >= 3:
                final_order_results.append(result)

        if len(final_order_results) < 8:
            return False

        final_order_results.sort(key=lambda x: float(x['best_attempt'] or x['best_performance'] or 0))

        for i, result in enumerate(final_order_results[:8]):
            execute_query(
                "UPDATE startlist SET final_order = %s WHERE game_id = %s AND athlete_bib = %s",
                (i + 1, game_id, result['athlete_bib'])
            )

        return True


class Attempt:
    @staticmethod
    def get_by_result(result_id):
        return execute_query(
            "SELECT * FROM attempts WHERE result_id = %s ORDER BY attempt_number",
            (result_id,), fetch=True
        )

    @staticmethod
    def create(result_id, attempt_number, value, wind_velocity=None, raza_score=None, raza_score_precise=None,
               height=None):
        if wind_velocity is not None:
            wind_velocity = float(Config.format_wind(wind_velocity))

        return execute_query(
            "INSERT INTO attempts (result_id, attempt_number, value, raza_score, raza_score_precise, wind_velocity, height) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (result_id, attempt_number, value, raza_score, raza_score_precise, wind_velocity, height)
        )

    @staticmethod
    def update(attempt_id, **data):
        set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
        query = f"UPDATE attempts SET {set_clause} WHERE id = %s"
        params = list(data.values()) + [attempt_id]
        return execute_query(query, params)

    @staticmethod
    def create_multiple(result_id, attempts=None):
        if attempts is None:
            return False

        for attempt_number, attempt_data in attempts.items():
            value = attempt_data.get('value')
            if not value:
                continue

            raza_score = attempt_data.get('raza_score')
            raza_score_decimal = attempt_data.get('raza_score_precise')
            wind_velocity = attempt_data.get('wind_velocity')
            height = attempt_data.get('height')

            if wind_velocity is not None:
                wind_velocity = float(Config.format_wind(wind_velocity))

            execute_query(
                "INSERT INTO attempts (result_id, attempt_number, value, raza_score, raza_score_precise, wind_velocity, height) VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (result_id, attempt_number) DO UPDATE SET value = EXCLUDED.value, raza_score = EXCLUDED.raza_score, raza_score_precise = EXCLUDED.raza_score_precise, wind_velocity = EXCLUDED.wind_velocity, height = EXCLUDED.height",
                (result_id, attempt_number, value, raza_score, raza_score_decimal, wind_velocity, height)
            )

        return True

    @staticmethod
    def update_partial(result_id, attempts_data):
        for attempt_number, attempt_data in attempts_data.items():
            value = attempt_data.get('value')
            if not value:
                continue

            raza_score = attempt_data.get('raza_score')
            raza_score_decimal = attempt_data.get('raza_score_precise')
            wind_velocity = attempt_data.get('wind_velocity')
            height = attempt_data.get('height')

            if wind_velocity is not None:
                wind_velocity = float(Config.format_wind(wind_velocity))

            existing = execute_one(
                "SELECT id FROM attempts WHERE result_id = %s AND attempt_number = %s",
                (result_id, attempt_number)
            )

            if existing:
                execute_query(
                    "UPDATE attempts SET value = %s, raza_score = %s, raza_score_precise = %s, wind_velocity = %s, height = %s WHERE result_id = %s AND attempt_number = %s",
                    (value, raza_score, raza_score_decimal, wind_velocity, height, result_id, attempt_number)
                )
            else:
                execute_query(
                    "INSERT INTO attempts (result_id, attempt_number, value, raza_score, raza_score_precise, wind_velocity, height) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (result_id, attempt_number, value, raza_score, raza_score_decimal, wind_velocity, height)
                )

        return True

    @staticmethod
    def delete_by_result(result_id):
        return execute_query("DELETE FROM attempts WHERE result_id = %s", (result_id,))

    @staticmethod
    def add_long_jump_attempt(result_id, value, height=None, wind_velocity=None):
        existing_attempts = execute_query(
            "SELECT MAX(attempt_number) as max_num FROM attempts WHERE result_id = %s",
            (result_id,), fetch=True
        )

        next_attempt = 1
        if existing_attempts and existing_attempts[0]['max_num']:
            next_attempt = existing_attempts[0]['max_num'] + 1

        raza_score = None
        raza_score_decimal = None

        result = execute_one("SELECT * FROM results WHERE id = %s", (result_id,))
        if result:
            game = Game.get_by_id(result['game_id'])
            if game and game.get('wpa_points', False):
                athlete = execute_one("SELECT * FROM athletes WHERE bib = %s", (result['athlete_bib'],))
                if athlete and verify_combination(athlete['gender'], game['event'], athlete['class']):
                    try:
                        raza_result = calculate_raza(
                            gender=athlete['gender'],
                            event=game['event'],
                            athlete_class=athlete['class'],
                            performance=float(value)
                        )
                        if isinstance(raza_result, tuple):
                            response, status = raza_result
                            if status == 200:
                                raza_data = response.get_json()
                                raza_score = int(raza_data.get('raza_score', 0))
                                raza_score_precise = float(raza_data.get('raza_score_precise', 0))
                    except Exception as e:
                        print(f"Error calculating RAZA for attempt: {e}")

        return Attempt.create(result_id, next_attempt, value, wind_velocity, raza_score, raza_score_precise, height)
