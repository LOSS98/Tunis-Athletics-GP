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

    def is_technical_delegate(self):
        return self.admin_type == 'technical_delegate'

    def has_loc_privileges(self):
        return self.admin_type in ['loc', 'technical_delegate']

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

        query += " ORDER BY sdms"
        return execute_query(query, params, fetch=True)

    @staticmethod
    def get_by_sdms(sdms):
        return execute_one("SELECT * FROM athletes WHERE sdms = %s", (sdms,))

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
            OR sdms::text LIKE %s
            ORDER BY sdms
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
            JOIN athletes a ON r.athlete_sdms = a.sdms
            WHERE r.game_id = %s AND (a.gender != %s OR a.class NOT IN %s)
        """, (id, game_gender, tuple(game_classes)))

        startlist_result = execute_one("""
            SELECT COUNT(*) as count FROM startlist s
            JOIN athletes a ON s.athlete_sdms = a.sdms
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
    def update_field_event_progression(game_id):
        game = Game.get_by_id(game_id)
        if not game or game['event'] in ['High Jump'] or game['event'] not in Config.get_field_events():
            return False

        results = execute_query("""
            SELECT r.id, r.athlete_sdms, r.value, 
                   COUNT(DISTINCT a.attempt_number) as attempt_count
            FROM results r
            LEFT JOIN attempts a ON r.id = a.result_id AND a.attempt_number <= 3
            WHERE r.game_id = %s AND r.value NOT IN %s
            GROUP BY r.id, r.athlete_sdms, r.value
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

    @staticmethod
    def toggle_official_status(game_id, user_id):
        """Toggle official status of all results for a game"""
        game = execute_one("SELECT official FROM games WHERE id = %s", (game_id,))
        if not game:
            return False

        new_status = not game.get('official', False)

        if new_status:
            # Mark as official
            execute_query(
                "UPDATE games SET official = %s, official_date = CURRENT_TIMESTAMP, official_by = %s WHERE id = %s",
                (True, user_id, game_id)
            )
        else:
            # Mark as unofficial
            execute_query(
                "UPDATE games SET official = %s, official_date = NULL, official_by = NULL WHERE id = %s",
                (False, game_id)
            )

        return new_status

    @staticmethod
    def get_by_id_with_official(id):
        game = execute_one("""
                SELECT g.*, u.username as official_by_username
                FROM games g
                LEFT JOIN users u ON g.official_by = u.id
                WHERE g.id = %s
            """, (id,))

        if game:
            game['classes_list'] = [c.strip() for c in game['classes'].split(',')]
        return game


class Result:
    @staticmethod
    def get_all(**filters):
        query = """
            SELECT r.*, a.firstname, a.lastname, a.country, a.gender as athlete_gender, a.class as athlete_class,
                   g.firstname AS guide_firstname, g.lastname AS guide_lastname
            FROM results r
            JOIN athletes a ON r.athlete_sdms = a.sdms
            LEFT JOIN athletes g ON r.guide_sdms = g.sdms
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
    def get_by_game_athlete(game_id, athlete_sdms):
        return execute_one("SELECT * FROM results WHERE game_id = %s AND athlete_sdms = %s", (game_id, athlete_sdms))

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
            JOIN athletes a ON r.athlete_sdms = a.sdms
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
                JOIN athletes a ON r.athlete_sdms = a.sdms
                WHERE r.game_id = %s
            """, (game_id,), fetch=True)

            if not results:
                return False

            is_track = game['event'] in Config.get_track_events()
            is_field = game['event'] in Config.get_field_events()
            is_high_jump = game['event'] == 'High Jump'
            use_wpa_points = game.get('wpa_points', False)
            special_values = Config.get_result_special_values()

            # Process valid results
            valid_results = []
            for result in results:
                if result['value'] not in special_values:
                    # Get all attempts for field events (especially High Jump)
                    if is_field:
                        attempts = execute_query("""
                            SELECT value, height FROM attempts 
                            WHERE result_id = %s 
                            ORDER BY attempt_number
                        """, (result['id'],), fetch=True)

                        if is_high_jump:
                            # Calculate High Jump specific stats
                            result['high_jump_stats'] = Result.calculate_high_jump_stats(attempts, float(result['value']))
                        else:
                            # For other field events
                            all_attempts = []
                            for attempt in attempts:
                                val = attempt['value']
                                if val and str(val).strip() not in special_values:
                                    try:
                                        attempt_float = float(val)
                                        all_attempts.append(attempt_float)
                                    except (ValueError, TypeError):
                                        pass
                            all_attempts.sort(reverse=True)
                            result['sorted_attempts'] = all_attempts

                    valid_results.append(result)

            if not valid_results:
                return True

            def get_sort_key(result):
                """Generate sort key for ranking"""

                if is_high_jump:
                    # High Jump specific ranking
                    try:
                        max_height = float(result['value'])
                        hj_stats = result.get('high_jump_stats', {})

                        # Primary: max height (higher is better, so negative)
                        primary = -max_height

                        # Secondary: failures at max height (fewer is better)
                        failures_at_max = hj_stats.get('failures_at_max_height', 999)

                        # Tertiary: total failures (fewer is better)
                        total_failures = hj_stats.get('total_failures', 999)

                        return (primary, failures_at_max, total_failures)
                    except (ValueError, TypeError):
                        return (float('inf'), 999, 999)

                # Primary: best performance (or RAZA if enabled)
                if use_wpa_points and result.get('raza_score_precise'):
                    primary = -float(result['raza_score_precise'])
                elif use_wpa_points and result.get('raza_score'):
                    primary = -float(result['raza_score'])
                else:
                    try:
                        if is_track:
                            primary = float(result['value'])  # Lower is better
                        else:
                            primary = -float(result['value'])  # Higher is better, so negative
                    except (ValueError, TypeError):
                        primary = float('inf') if is_track else float('-inf')

                # Tie-breakers for field events (except High Jump)
                tie_breakers = []
                if is_field and not is_high_jump and 'sorted_attempts' in result:
                    attempts = result['sorted_attempts']
                    # Add up to 6 attempts as tie-breakers
                    for i in range(6):
                        if i < len(attempts):
                            tie_breakers.append(-attempts[i])  # Negative for descending
                        else:
                            tie_breakers.append(float('inf'))  # Worst possible value

                return (primary, *tie_breakers)

            # Sort results
            valid_results.sort(key=get_sort_key)

            # Assign ranks
            for i, result in enumerate(valid_results):
                rank = i + 1
                execute_query("UPDATE results SET rank = %s WHERE id = %s", (str(rank), result['id']))

            # Handle special values (DNS, DNF, etc.)
            for result in results:
                if result['value'] in special_values:
                    execute_query("UPDATE results SET rank = %s WHERE id = %s", ('-', result['id']))

            return True

        except Exception as e:
            print(f"Error in auto_rank_results: {e}")
            traceback.print_exc()
            return False

    @staticmethod
    def calculate_high_jump_stats(attempts, max_height):
        """Calculate High Jump specific statistics for ranking"""
        stats = {
            'failures_at_max_height': 0,
            'total_failures': 0
        }

        failures_at_max = 0
        total_failures = 0

        for attempt in attempts:
            if attempt.get('height') and attempt.get('value'):
                try:
                    height = float(attempt['height'])
                    value = str(attempt['value']).upper().strip()

                    # Compter les échecs dans chaque valeur
                    failure_count = 0

                    if value == 'X':
                        failure_count = 1
                    elif value == 'XO':
                        failure_count = 1  # 1 échec + 1 réussite
                    elif value == 'XXO':
                        failure_count = 2  # 2 échecs + 1 réussite
                    elif value == 'XXX':
                        failure_count = 3  # 3 échecs (élimination)
                    # O et - n'ont pas d'échecs

                    # Ajouter au total des échecs
                    total_failures += failure_count

                    # Compter les échecs à la hauteur maximale
                    if abs(height - max_height) < 0.001:  # Éviter les problèmes de précision float
                        failures_at_max += failure_count

                except (ValueError, TypeError) as e:
                    print(f"Error processing attempt: {attempt}, error: {e}")
                    continue

        stats['failures_at_max_height'] = failures_at_max
        stats['total_failures'] = total_failures

        return stats

class StartList:
    @staticmethod
    def get_by_game(game_id):
        query = """
            SELECT s.*, a.firstname, a.lastname, a.country, a.class, a.gender,
                   g.firstname AS guide_firstname, g.lastname AS guide_lastname
            FROM startlist s
            JOIN athletes a ON s.athlete_sdms = a.sdms
            LEFT JOIN athletes g ON s.guide_sdms = g.sdms
            WHERE s.game_id = %s
            ORDER BY s.final_order IS NULL, s.final_order, s.lane_order, a.sdms
        """
        return execute_query(query, (game_id,), fetch=True)

    @staticmethod
    def create(game_id, athlete_sdms, lane_order=None, guide_sdms=None):
        return execute_query(
            "INSERT INTO startlist (game_id, athlete_sdms, lane_order, guide_sdms) VALUES (%s, %s, %s, %s)",
            (game_id, athlete_sdms, lane_order, guide_sdms)
        )

    @staticmethod
    def delete(game_id, athlete_sdms):
        return execute_query(
            "DELETE FROM startlist WHERE game_id = %s AND athlete_sdms = %s",
            (game_id, athlete_sdms)
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
    def athlete_in_startlist(game_id, athlete_sdms):
        result = execute_one("SELECT id FROM startlist WHERE game_id = %s AND athlete_sdms = %s", (game_id, athlete_sdms))
        return result is not None

    @staticmethod
    def update_order_for_long_jump(game_id):
        game = Game.get_by_id(game_id)
        if not game or game['event'] != 'Long Jump':
            return False

        results = execute_query("""
            SELECT r.athlete_sdms, r.value as best_performance
            FROM results r
            WHERE r.game_id = %s AND r.value NOT IN ('DNS', 'DNF', 'DSQ', 'NM')
        """, (game_id,), fetch=True)

        if len(results) < 3:
            return False

        results.sort(key=lambda x: float(x['best_performance']))

        for i, result in enumerate(results):
            execute_query(
                "UPDATE startlist SET final_order = %s WHERE game_id = %s AND athlete_sdms = %s",
                (i + 1, game_id, result['athlete_sdms'])
            )

        return True

    @staticmethod
    def update_final_order_long_jump(game_id):
        game = Game.get_by_id(game_id)
        if not game or game['event'] != 'Long Jump':
            return False

        results = execute_query("""
            SELECT r.athlete_sdms, r.value as best_performance, r.best_attempt,
                   a.firstname, a.lastname
            FROM results r
            JOIN athletes a ON r.athlete_sdms = a.sdms
            WHERE r.game_id = %s AND r.value NOT IN ('DNS', 'DNF', 'DSQ', 'NM')
        """, (game_id,), fetch=True)

        if len(results) < 8:
            return False

        final_order_results = []
        for result in results:
            attempts_count = execute_one(
                "SELECT COUNT(*) as count FROM attempts WHERE result_id = (SELECT id FROM results WHERE game_id = %s AND athlete_sdms = %s)",
                (game_id, result['athlete_sdms'])
            )

            if attempts_count and attempts_count['count'] >= 3:
                final_order_results.append(result)

        if len(final_order_results) < 8:
            return False

        final_order_results.sort(key=lambda x: float(x['best_attempt'] or x['best_performance'] or 0))

        for i, result in enumerate(final_order_results[:8]):
            execute_query(
                "UPDATE startlist SET final_order = %s WHERE game_id = %s AND athlete_sdms = %s",
                (i + 1, game_id, result['athlete_sdms'])
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
                athlete = execute_one("SELECT * FROM athletes WHERE sdms = %s", (result['athlete_sdms'],))
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
