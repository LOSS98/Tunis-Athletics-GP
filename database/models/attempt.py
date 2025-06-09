from config import Config
from database.db_manager import execute_one, execute_query
from utils.raza_calculation import calculate_raza, verify_combination
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
            from database.models.game import Game
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