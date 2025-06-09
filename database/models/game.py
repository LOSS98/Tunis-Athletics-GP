from database.db_manager import execute_one, execute_query
class Game:
    @staticmethod
    def get_all():
        return execute_query("SELECT * FROM games ORDER BY day, time", fetch=True)
    @staticmethod
    def get_by_id(id):
        game = execute_one("SELECT * FROM games WHERE id = %s", (id,))
        if game:
            classes = game.get('classes') or ''
            gender = game.get('gender') or ''
            game['classes_list'] = [c.strip() for c in classes.split(',') if c.strip()]
            game['genders_list'] = [g.strip() for g in gender.split(',') if g.strip()]
        return game
    @staticmethod
    def create(**data):
        keys = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        query = f"INSERT INTO games ({keys}) VALUES ({placeholders}) RETURNING id"
        result = execute_query(query, list(data.values()))
        return result['id'] if result else None
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
    def update_velocity(id, wind_velocity):
        return execute_query("UPDATE games SET wind_velocity = %s WHERE id = %s", (wind_velocity, id))
    @staticmethod
    def toggle_publish(id):
        current = execute_one("SELECT published FROM games WHERE id = %s", (id,))
        if current:
            new_status = not current.get('published', False)
            execute_query("UPDATE games SET published = %s WHERE id = %s", (new_status, id))
            return new_status
        return False
    @staticmethod
    def toggle_official_status(id, user_id):
        current = execute_one("SELECT official FROM games WHERE id = %s", (id,))
        if current:
            new_status = not current.get('official', False)
            if new_status:
                execute_query(
                    "UPDATE games SET official = %s, official_by = %s, official_date = CURRENT_TIMESTAMP WHERE id = %s",
                    (new_status, user_id, id)
                )
            else:
                execute_query(
                    "UPDATE games SET official = %s, official_by = NULL, official_date = NULL WHERE id = %s",
                    (new_status, id)
                )
            return new_status
        return False
    @staticmethod
    def has_results(game_id):
        count = execute_one("SELECT COUNT(*) as count FROM results WHERE game_id = %s", (game_id,))
        return count['count'] > 0 if count else False
    @staticmethod
    def has_alerts(id):
        game = execute_one("SELECT gender, classes FROM games WHERE id = %s", (id,))
        if not game:
            return False
        game_genders = [g.strip() for g in game['gender'].split(',')]
        game_classes = [c.strip() for c in game['classes'].split(',')]
        result = execute_one("""
            SELECT COUNT(*) as count FROM results r
            JOIN athletes a ON r.athlete_sdms = a.sdms
            WHERE r.game_id = %s AND (
                a.gender NOT IN %s OR 
                NOT EXISTS (
                    SELECT 1 
                    FROM unnest(string_to_array(a.class, ',')) as athlete_class(class_name)
                    WHERE trim(athlete_class.class_name) = ANY(%s)
                )
            )
        """, (id, tuple(game_genders), game_classes))
        startlist_result = execute_one("""
            SELECT COUNT(*) as count FROM startlist s
            JOIN athletes a ON s.athlete_sdms = a.sdms
            WHERE s.game_id = %s AND (
                a.gender NOT IN %s OR 
                NOT EXISTS (
                    SELECT 1 
                    FROM unnest(string_to_array(a.class, ',')) as athlete_class(class_name)
                    WHERE trim(athlete_class.class_name) = ANY(%s)
                )
            )
        """, (id, tuple(game_genders), game_classes))
        return (result and result['count'] > 0) or (startlist_result and startlist_result['count'] > 0)
    @staticmethod
    def get_with_status():
        games = Game.get_all()
        from config import Config
        current_day = Config.get_current_day()
        from datetime import datetime
        current_time = datetime.now()
        if current_day is None:
            current_day = 1
        try:
            current_day = int(current_day)
        except (ValueError, TypeError):
            current_day = 1
        for game in games:
            game['classes_list'] = [c.strip() for c in game['classes'].split(',')]
            game['genders_list'] = [g.strip() for g in game['gender'].split(',')]
            game_day = game['day']
            try:
                game_day = int(game_day)
            except (ValueError, TypeError):
                game_day = 1
            if game['status'] not in ['finished', 'cancelled']:
                if current_day == game_day:
                    game_time = datetime.strptime(str(game['time']), '%H:%M:%S').replace(
                        year=current_time.year,
                        month=current_time.month,
                        day=current_time.day
                    )
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
            from database.models.startlist import StartList
            game['has_startlist'] = bool(game.get('start_file')) or StartList.has_startlist(game['id'])
            game['is_published'] = game.get('published', False)
            game['has_alerts'] = Game.has_alerts(game['id'])
            from database.models.result import Result
            result_count = Result.count_by_game(game['id'])
            startlist_count = StartList.count_by_game(game['id'])
            game['result_count'] = result_count
            game['startlist_count'] = startlist_count
            game['result_is_complete'] = result_count >= game['nb_athletes']
            game['startlist_is_complete'] = startlist_count >= game['nb_athletes']
        return games
    @staticmethod
    def athlete_matches_game(athlete, game):
        if not athlete or not game:
            return False
        # Protection contre les valeurs None
        gender_str = game.get('gender') or ''
        athlete_gender = athlete.get('gender') or ''
        if not gender_str or not athlete_gender:
            return False
        game_genders = [g.strip() for g in gender_str.split(',') if g.strip()]
        if athlete_gender not in game_genders:
            return False
        # Protection pour les classes
        classes_str = game.get('classes') or ''
        athlete_class_str = athlete.get('class') or ''
        if not classes_str or not athlete_class_str:
            return False
        game_classes = [c.strip() for c in classes_str.split(',') if c.strip()]
        athlete_classes = [c.strip() for c in athlete_class_str.split(',') if c.strip()]
        return any(ac in game_classes for ac in athlete_classes)