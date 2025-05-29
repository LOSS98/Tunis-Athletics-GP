from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from database.db_manager import execute_query, execute_one
from datetime import datetime, timedelta
from config import Config
import re


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
            pattern = r'^\d+(\.\d{1,2})?$'
        else:
            pattern = r'^(\d{1,2}:)?\d{1,2}\.\d{1,4}$'

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


class Attempt:
    @staticmethod
    def get_by_result(result_id):
        return execute_query(
            "SELECT * FROM attempts WHERE result_id = %s ORDER BY attempt_number",
            (result_id,), fetch=True
        )

    @staticmethod
    def create(result_id, attempt_number, value, wind_velocity=None, raza_score=None):
        if wind_velocity is not None:
            wind_velocity = float(Config.format_wind(wind_velocity))

        return execute_query(
            "INSERT INTO attempts (result_id, attempt_number, value, raza_score, wind_velocity) VALUES (%s, %s, %s, %s, %s)",
            (result_id, attempt_number, value, raza_score, wind_velocity)
        )

    @staticmethod
    def create_multiple(result_id, attempts=None):
        if attempts is None:
            return False
        query = "INSERT INTO attempts (result_id, attempt_number, value, raza_score, wind_velocity) VALUES "
        params = ()
        for attempt in attempts:
            attempt_number = attempt
            value = attempts[attempt]['value']
            raza = attempts[attempt]['raza_score']
            wind = attempts[attempt].get('wind_velocity', None)
            if wind is not None:
                wind = float(Config.format_wind(wind))
            query += "(%s, %s, %s, %s, %s), "
            params += (result_id, attempt_number, value, raza, wind)
        query = query.rstrip(', ')
        return execute_query(query, params)

    @staticmethod
    def delete_by_result(result_id):
        return execute_query("DELETE FROM attempts WHERE result_id = %s", (result_id,))