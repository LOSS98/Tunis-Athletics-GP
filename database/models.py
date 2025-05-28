from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from database.db_manager import execute_query, execute_one
from datetime import datetime, timedelta
from config import Config
import re
import pandas as pd
import numpy as np
import os


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
    def toggle_publish(id):
        game = execute_one("SELECT published FROM games WHERE id = %s", (id,))
        if game:
            new_status = not game.get('published', False)
            execute_query("UPDATE games SET published = %s WHERE id = %s", (new_status, id))
            return new_status
        return False

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

                if len(game['classes_list']) > 1:
                    results = Result.calculate_raza_scores(results, game)

                results = Result._auto_rank_results(results, game)

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
    def _auto_rank_results(results, game):
        special_values = Config.get_result_special_values()
        field_events = Config.get_field_events()

        valid_results = []
        invalid_results = []

        for result in results:
            if result['value'] in special_values:
                invalid_results.append(result)
            else:
                valid_results.append(result)

        if len(game['classes_list']) > 1 and any(r.get('raza_score') for r in valid_results):
            valid_results.sort(key=lambda x: x.get('raza_score', 0), reverse=True)
        else:
            if game['event'] in field_events:
                def get_performance_value(result):
                    try:
                        return float(result.get('auto_performance', result['value']) or 0)
                    except:
                        return 0

                valid_results.sort(key=get_performance_value, reverse=True)
            else:
                def parse_time(time_str):
                    try:
                        if ':' in time_str:
                            parts = time_str.split(':')
                            return float(parts[0]) * 60 + float(parts[1])
                        return float(time_str)
                    except:
                        return float('inf')

                valid_results.sort(key=lambda x: parse_time(x.get('auto_performance', x['value']) or '999:99.99'))

        for i, result in enumerate(valid_results):
            result['auto_rank'] = str(i + 1)

        for result in invalid_results:
            result['auto_rank'] = result['value']

        return valid_results + invalid_results

    @staticmethod
    def calculate_raza_scores(results, game):
        if not os.path.exists(Config.RAZA_TABLE_PATH):
            return results

        try:
            df = pd.read_excel(Config.RAZA_TABLE_PATH)
            special_values = Config.get_result_special_values()
            field_events = Config.get_field_events()

            event_mapping = {
                'Javelin': 'Javelin Throw',
                'Shot Put': 'Shot Put',
                'Discus Throw': 'Discus Throw',
                'Club Throw': 'Club Throw',
                'Long Jump': 'Long Jump',
                'High Jump': 'High Jump',
                '100m': '100 m',
                '200m': '200 m',
                '400m': '400 m',
                '800m': '800 m',
                '1500m': '1500 m',
                '5000m': '5000 m',
                '4x100m': '4x100 m',
                'Universal Relay': 'Universal Relay'
            }

            for result in results:
                if result['value'] in special_values:
                    result['raza_score'] = None
                    continue

                try:
                    performance_str = result.get('auto_performance', result['value'])

                    if game['event'] in field_events:
                        performance = float(performance_str)
                    else:
                        time_parts = performance_str.split(':')
                        if len(time_parts) == 2:
                            minutes, seconds = time_parts
                            performance = float(minutes) * 60 + float(seconds)
                        else:
                            performance = float(performance_str)

                    athlete_class = result['athlete_class']
                    event_name = event_mapping.get(game['event'], game['event'])
                    gender = 'Men' if result['athlete_gender'] == 'Male' else 'Women'

                    mask = (df['Event'] == event_name) & \
                           (df['Class'] == athlete_class) & \
                           (df['Gender'] == gender)

                    raza_row = df[mask]

                    if not raza_row.empty:
                        raza_row = raza_row.iloc[0]
                        a = float(raza_row['a'])
                        b = float(raza_row['b'])
                        c = float(raza_row['c'])

                        score_float = a * np.exp(-np.exp(b - c * performance))
                        score = int(np.floor(score_float))

                        result['raza_score'] = score
                    else:
                        result['raza_score'] = None

                except Exception as e:
                    print(f"Error calculating RAZA for result {result.get('id', 'unknown')}: {e}")
                    result['raza_score'] = None

        except Exception as e:
            print(f"Error loading RAZA table: {e}")

        return results

    @staticmethod
    def get_by_id(id):
        return execute_one("SELECT * FROM results WHERE id = %s", (id,))

    @staticmethod
    def create(**data):
        keys = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        query = f"INSERT INTO results ({keys}) VALUES ({placeholders}) RETURNING id"
        result = execute_one(query, list(data.values()))
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
    def delete_by_game_athlete(game_id, athlete_bib):
        return execute_query(
            "DELETE FROM results WHERE game_id = %s AND athlete_bib = %s",
            (game_id, athlete_bib)
        )

    @staticmethod
    def validate_performance(value, event_type):
        special_values = Config.get_result_special_values()
        field_events = Config.get_field_events()

        if value in special_values:
            return True

        if event_type in field_events:
            pattern = r'^\d+(\.\d{1,2})?$'
        else:
            pattern = r'^(\d{1,2}:)?\d{1,2}\.\d{2}$'

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
    def create(result_id, attempt_number, value, raza='Null'):
        return execute_query(
            "INSERT INTO attempts (result_id, attempt_number, value, raza_score) VALUES (%s, %s, %s, %s)",
            (result_id, attempt_number, value, raza)
        )

    @staticmethod
    def createMultiple(result_id, attemps=None):
        if attemps is None:
            return False
        query = "INSERT INTO attempts (result_id, attempt_number, value, raza_score) VALUES "
        parms= ()
        for attemp in attemps:
            attempt_number = attemp
            value = attemps[attemp]['value']
            raza = attemps[attemp]['raza_score']
            query += "(%s, %s, %s, %s), "
            parms += (result_id, attempt_number, value, raza)
        query = query.rstrip(', ')
        return execute_query(query, parms)

    @staticmethod
    def delete_by_result(result_id):
        return execute_query("DELETE FROM attempts WHERE result_id = %s", (result_id,))