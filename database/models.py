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
        print(f"Updating velocity for game {id} to {velocity_value}")
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
        has_wpa_points = game.get('wpa_points', False)
        special_values = Config.get_result_special_values()

        valid_results = []
        for result in results:
            if result['value'] in special_values:
                continue
            valid_results.append(result)

        if is_track:
            if has_wpa_points:
                valid_results.sort(key=lambda x: (
                    -(x['raza_score'] or 0),
                    -(x['raza_score_precise'] or 0),
                    float(x['value']) if x['value'] not in special_values else float('inf')
                ))
            else:
                valid_results.sort(
                    key=lambda x: float(x['value']) if x['value'] not in special_values else float('inf'))

        elif is_field:
            for result in valid_results:
                result['attempts'] = Attempt.get_by_result(result['id'])
                result['best_attempt_value'] = 0
                result['attempt_sequence'] = []

                for attempt in result['attempts']:
                    if attempt['value'] and attempt['value'] not in ['X', '-', 'O', '']:
                        try:
                            val = float(attempt['value'])
                            result['attempt_sequence'].append(val)
                            if val > result['best_attempt_value']:
                                result['best_attempt_value'] = val
                        except ValueError:
                            continue

                while len(result['attempt_sequence']) < 6:
                    result['attempt_sequence'].append(0)

            if has_wpa_points:
                def sort_key(x):
                    return (
                        -(x['raza_score'] or 0),
                        -(x['raza_score_precise'] or 0),
                        -x['best_attempt_value'],
                        -x['attempt_sequence'][0],
                        -x['attempt_sequence'][1],
                        -x['attempt_sequence'][2],
                        -x['attempt_sequence'][3],
                        -x['attempt_sequence'][4],
                        -x['attempt_sequence'][5]
                    )
            else:
                def sort_key(x):
                    return (
                        -x['best_attempt_value'],
                        -x['attempt_sequence'][0],
                        -x['attempt_sequence'][1],
                        -x['attempt_sequence'][2],
                        -x['attempt_sequence'][3],
                        -x['attempt_sequence'][4],
                        -x['attempt_sequence'][5]
                    )

            valid_results.sort(key=sort_key)

        current_rank = 1
        previous_key = None
        tied_count = 0

        for i, result in enumerate(valid_results):
            if is_track:
                if has_wpa_points:
                    current_key = (result['raza_score'] or 0, result['raza_score_precise'] or 0, result['value'])
                else:
                    current_key = result['value']
            else:
                if has_wpa_points:
                    current_key = (
                        result['raza_score'] or 0,
                        result['raza_score_precise'] or 0,
                        tuple(result['attempt_sequence'])
                    )
                else:
                    current_key = tuple(result['attempt_sequence'])

            if previous_key is not None and current_key != previous_key:
                current_rank += tied_count + 1
                tied_count = 0
            else:
                tied_count += 1

            execute_query("UPDATE results SET rank = %s WHERE id = %s", (str(current_rank), result['id']))
            previous_key = current_key

        for result in results:
            if result['value'] in special_values:
                execute_query("UPDATE results SET rank = %s WHERE id = %s", ('-', result['id']))

        if game['event'] == 'Long Jump':
            StartList.update_order_for_long_jump(game_id)

        return True


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

        results = execute_query(query, params, fetch=True)

        if results and filters.get('game_id'):
            game = Game.get_by_id(filters['game_id'])
            if game:
                field_events = Config.get_field_events()

                if game['event'] in field_events:
                    for result in results:
                        result['attempts'] = Attempt.get_by_result(result['id'])
                        result = Result._select_best_attempt(result, game)

        return results

    @staticmethod
    def _select_best_attempt(result, game):
        special_values = Config.get_result_special_values()

        if not result.get('attempts') or result['value'] in special_values:
            return result

        valid_attempts = []
        for attempt in result['attempts']:
            if attempt['value'] and attempt['value'] not in ['X', '-', 'O', '']:
                try:
                    value = float(attempt['value'])
                    valid_attempts.append(value)
                except ValueError:
                    continue

        if valid_attempts:
            best_attempt = max(valid_attempts)
            result['best_attempt'] = f"{best_attempt:.2f}"

            if result['value'] != result['best_attempt']:
                result['auto_performance'] = result['best_attempt']

        return result

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
    def validate_performance(value, event_type):
        special_values = Config.get_result_special_values()
        field_events = Config.get_field_events()

        if value in special_values:
            return True

        if event_type in field_events:
            pattern = "r'^\d+(\.\d{1,2})?"
        else:
            pattern = "r'^(\d{1,2}:)?\d{1,2}\.\d{1,4}"

        return bool(re.match(pattern, value))


class StartList:
    @staticmethod
    def get_by_game(game_id):
        query = """
            SELECT s.*, a.firstname, a.lastname, a.country, a.class, a.gender
            FROM startlist s
            JOIN athletes a ON s.athlete_bib = a.bib
            WHERE s.game_id = %s
            ORDER BY s.lane_order, a.bib
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
    def update_order_for_long_jump(game_id):
        game = Game.get_by_id(game_id)
        if not game or game['event'] != 'Long Jump':
            return False

        results = execute_query("""
            SELECT r.athlete_bib, r.value as best_performance
            FROM results r
            WHERE r.game_id = %s
            ORDER BY CAST(r.value AS DECIMAL) ASC
        """, (game_id,), fetch=True)

        top_8_results = execute_query("""
            SELECT r.athlete_bib, r.value as best_performance
            FROM results r
            WHERE r.game_id = %s
            ORDER BY CAST(r.value AS DECIMAL) DESC
            LIMIT 8
        """, (game_id,), fetch=True)

        if len(top_8_results) < 8:
            return False

        top_8_results.reverse()

        for i, result in enumerate(top_8_results):
            execute_query(
                "UPDATE results SET final_order = %s WHERE game_id = %s AND athlete_bib = %s",
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
    def create(result_id, attempt_number, value, wind_velocity=None, raza_score=None, raza_score_decimal=None,
               height=None):
        if wind_velocity is not None:
            wind_velocity = float(Config.format_wind(wind_velocity))

        return execute_query(
            "INSERT INTO attempts (result_id, attempt_number, value, raza_score, raza_score_precise, wind_velocity, height) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (result_id, attempt_number, value, raza_score, raza_score_decimal, wind_velocity, height)
        )

    @staticmethod
    def create_multiple(result_id, attempts=None):
        if attempts is None:
            return False

        for attempt_number, attempt_data in attempts.items():
            value = attempt_data.get('value')
            if not value:
                continue

            raza_score = attempt_data.get('raza_score')
            raza_score_decimal = attempt_data.get('raza_score_decimal')
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

            existing = execute_one(
                "SELECT id FROM attempts WHERE result_id = %s AND attempt_number = %s",
                (result_id, attempt_number)
            )

            raza_score = attempt_data.get('raza_score')
            raza_score_decimal = attempt_data.get('raza_score_decimal')
            wind_velocity = attempt_data.get('wind_velocity')
            height = attempt_data.get('height')

            if wind_velocity is not None:
                wind_velocity = float(Config.format_wind(wind_velocity))

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
                                raza_score_decimal = round(float(raza_data.get('raza_score', 0)), 3)
                    except Exception as e:
                        print(f"Error calculating RAZA for attempt: {e}")

        return Attempt.create(result_id, next_attempt, value, wind_velocity, raza_score, raza_score_decimal, height)