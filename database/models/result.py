import traceback
from config import Config
from database.db_manager import execute_query, execute_one


class Result:
    @staticmethod
    def get_all(**filters):
        query = """
            SELECT r.*, a.firstname, a.lastname, a.npc, a.gender as athlete_gender, a.class as athlete_class,
                   g.firstname AS guide_firstname, g.lastname AS guide_lastname,
                   gm.classes as game_classes
            FROM results r
            JOIN athletes a ON r.athlete_sdms = a.sdms
            LEFT JOIN athletes g ON r.guide_sdms = g.sdms
            LEFT JOIN games gm ON r.game_id = gm.id
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

        for result in results:
            if result['athlete_class']:
                result['athlete_classes'] = [c.strip() for c in result['athlete_class'].split(',')]
            else:
                result['athlete_classes'] = []

            if result.get('game_classes'):
                result['game_classes_list'] = [c.strip() for c in result['game_classes'].split(',')]
            else:
                result['game_classes_list'] = []

        if results and filters.get('game_id'):
            from database.models.game import Game
            game = Game.get_by_id(filters['game_id'])
            if game:
                field_events = Config.get_field_events()
                if game['event'] in field_events:
                    from database.models.attempt import Attempt
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
                from database.models.game import Game
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
            SELECT r.*, a.firstname, a.lastname, a.npc, a.photo,
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
            from database.models.game import Game
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

            valid_results = []
            for result in results:
                if result['value'] not in special_values:
                    if is_field:
                        attempts = execute_query("""
                            SELECT value, height FROM attempts 
                            WHERE result_id = %s 
                            ORDER BY attempt_number
                        """, (result['id'],), fetch=True)

                        if is_high_jump:
                            result['high_jump_stats'] = Result.calculate_high_jump_stats(attempts,
                                                                                         float(result['value']))
                        else:
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
                if is_high_jump:
                    try:
                        max_height = float(result['value'])
                        hj_stats = result.get('high_jump_stats', {})
                        primary = -max_height
                        failures_at_max = hj_stats.get('failures_at_max_height', 999)
                        total_failures = hj_stats.get('total_failures', 999)
                        return (primary, failures_at_max, total_failures)
                    except (ValueError, TypeError):
                        return (float('inf'), 999, 999)

                if use_wpa_points and result.get('raza_score_precise'):
                    primary = -float(result['raza_score_precise'])
                elif use_wpa_points and result.get('raza_score'):
                    primary = -float(result['raza_score'])
                else:
                    try:
                        if is_track:
                            primary = float(result['value'])
                        else:
                            primary = -float(result['value'])
                    except (ValueError, TypeError):
                        primary = float('inf') if is_track else float('-inf')

                tie_breakers = []
                if is_field and not is_high_jump and 'sorted_attempts' in result:
                    attempts = result['sorted_attempts']
                    for i in range(6):
                        if i < len(attempts):
                            tie_breakers.append(-attempts[i])
                        else:
                            tie_breakers.append(float('inf'))

                return (primary, *tie_breakers)

            valid_results.sort(key=get_sort_key)

            for i, result in enumerate(valid_results):
                rank = i + 1
                execute_query("UPDATE results SET rank = %s WHERE id = %s", (str(rank), result['id']))

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

                    failure_count = 0
                    if value == 'X':
                        failure_count = 1
                    elif value == 'XO':
                        failure_count = 1
                    elif value == 'XXO':
                        failure_count = 2
                    elif value == 'XXX':
                        failure_count = 3

                    total_failures += failure_count

                    if abs(height - max_height) < 0.001:
                        failures_at_max += failure_count

                except (ValueError, TypeError) as e:
                    print(f"Error processing attempt: {attempt}, error: {e}")
                    continue

        stats['failures_at_max_height'] = failures_at_max
        stats['total_failures'] = total_failures
        return stats