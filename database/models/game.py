from database.db_manager import execute_one, execute_query


class Game:
    @staticmethod
    def get_all():
        return execute_query("""
            SELECT g.*, 
                   g.manual_startlist_pdf,
                   g.generated_startlist_pdf, 
                   g.manual_results_pdf,
                   g.generated_results_pdf
            FROM games g 
            ORDER BY g.day, g.time
        """, fetch=True)

    @staticmethod
    def get_by_id(id):
        game = execute_one("""
            SELECT g.*,
                   g.manual_startlist_pdf,
                   g.generated_startlist_pdf, 
                   g.manual_results_pdf,
                   g.generated_results_pdf
            FROM games g 
            WHERE g.id = %s
        """, (id,))

        if game:
            classes = game.get('classes') or ''
            genders = game.get('genders') or ''
            game['classes_list'] = [c.strip() for c in classes.split(',') if c.strip()]
            game['genders_list'] = [g.strip() for g in genders.split(',') if g.strip()]

            pdf_fields = ['manual_startlist_pdf', 'generated_startlist_pdf', 'manual_results_pdf',
                          'generated_results_pdf']
            for field in pdf_fields:
                if field not in game:
                    game[field] = None

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
        state = execute_one("SELECT published FROM games WHERE id = %s", (game_id,))
        return (count['count'] > 0 or state['published']) if count else False

    @staticmethod
    def has_alerts(id):
        game = execute_one("SELECT genders, classes FROM games WHERE id = %s", (id,))
        if not game:
            return False
        game_genders = [g.strip() for g in game['genders'].split(',')]
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
    def get_last_5():
        last_5 = execute_query("""
            SELECT * FROM games 
            WHERE published = TRUE and (SELECT COUNT(*) FROM results
            WHERE game_id = games.id) > 0
            ORDER BY day DESC, time DESC
            LIMIT 5 ;
        """, fetch=True)

        for game in last_5:
            game['top_3'] = execute_query("""
            SELECT a.sdms, a.firstname, a.lastname, r.rank, r.value, a,class, a.npc 
            FROM results r JOIN athletes a ON r.athlete_sdms = a.sdms 
            WHERE r.game_id = %s ORDER BY r.rank::INTEGER ASC LIMIT 3;
            """, (game['id'],), fetch=True)
        return last_5

    @staticmethod
    def get_with_status():
        from config import Config
        from datetime import datetime

        current_day = Config.get_current_day()
        current_time = datetime.now()

        if current_day is None:
            current_day = 1
        try:
            current_day = int(current_day)
        except (ValueError, TypeError):
            current_day = 1

        games = execute_query("""
            SELECT g.*,
                   COALESCE(rc.result_count, 0) as result_count,
                   COALESCE(sc.startlist_count, 0) as startlist_count,
                   CASE WHEN g.start_file IS NOT NULL THEN TRUE ELSE FALSE END as has_startlist_file
            FROM games g
            LEFT JOIN (
                SELECT game_id, COUNT(*) as result_count 
                FROM results 
                GROUP BY game_id
            ) rc ON g.id = rc.game_id
            LEFT JOIN (
                SELECT game_id, COUNT(*) as startlist_count 
                FROM startlist 
                GROUP BY game_id
            ) sc ON g.id = sc.game_id
            ORDER BY g.day, g.time
        """, fetch=True)

        alert_games = execute_query("""
            SELECT DISTINCT g.id
            FROM games g
            JOIN (
                SELECT r.game_id FROM results r
                JOIN athletes a ON r.athlete_sdms = a.sdms
                JOIN games g2 ON r.game_id = g2.id
                WHERE a.gender != g2.genders OR 
                      NOT EXISTS (
                          SELECT 1 FROM unnest(string_to_array(a.class, ',')) as ac(class_name)
                          WHERE trim(ac.class_name) = ANY(string_to_array(g2.classes, ','))
                      )
                UNION
                SELECT s.game_id FROM startlist s
                JOIN athletes a ON s.athlete_sdms = a.sdms
                JOIN games g2 ON s.game_id = g2.id
                WHERE a.gender != g2.genders OR 
                      NOT EXISTS (
                          SELECT 1 FROM unnest(string_to_array(a.class, ',')) as ac(class_name)
                          WHERE trim(ac.class_name) = ANY(string_to_array(g2.classes, ','))
                      )
            ) alerts ON g.id = alerts.game_id
        """, fetch=True)

        alert_game_ids = {alert['id'] for alert in alert_games}

        for game in games:
            game['classes_list'] = [c.strip() for c in game['classes'].split(',')]
            game['genders_list'] = [g.strip() for g in game['genders'].split(',')]
            game['startlist_published'] = game.get('startlist_published', False)
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

            game['has_results'] = game['result_count'] > 0 or game.get('published', False)
            game['has_startlist'] = bool(game.get('start_file')) or game['startlist_count'] > 0 or game[
                'has_startlist_file']
            game['is_published'] = game.get('published', False)
            game['has_alerts'] = game['id'] in alert_game_ids
            game['result_is_complete'] = game['result_count'] >= game['nb_athletes']
            game['startlist_is_complete'] = game['startlist_count'] >= game['nb_athletes']

            pdf_fields = ['manual_startlist_pdf', 'generated_startlist_pdf', 'manual_results_pdf',
                          'generated_results_pdf']
            for field in pdf_fields:
                if field not in game:
                    game[field] = None

        return games

    @staticmethod
    def athlete_matches_game(athlete, game):
        if not athlete or not game:
            return False
        genders_str = game.get('genders') or ''
        athlete_gender = athlete.get('gender') or ''
        if not genders_str or not athlete_gender:
            return False
        game_genders = [g.strip() for g in genders_str.split(',') if g.strip()]
        if athlete_gender not in game_genders:
            return False
        classes_str = game.get('classes') or ''
        athlete_class_str = athlete.get('class') or ''
        if not classes_str or not athlete_class_str:
            return False
        game_classes = [c.strip() for c in classes_str.split(',') if c.strip()]
        athlete_classes = [c.strip() for c in athlete_class_str.split(',') if c.strip()]
        return any(ac in game_classes for ac in athlete_classes)

    @staticmethod
    def is_heat_game(game):
        return game.get('heat_group_id') is not None

    @staticmethod
    def add_to_heat_group(game_id, heat_group_id, heat_number):
        return execute_query(
            "UPDATE games SET heat_group_id = %s, heat_number = %s WHERE id = %s",
            (heat_group_id, heat_number, game_id)
        )

    @staticmethod
    def remove_from_heat_group(game_id):
        return execute_query(
            "UPDATE games SET heat_group_id = NULL, heat_number = NULL WHERE id = %s",
            (game_id,)
        )

    @staticmethod
    def get_heat_siblings(game):
        if not game.get('heat_group_id'):
            return []
        return execute_query("""
            SELECT * FROM games 
            WHERE heat_group_id = %s AND id != %s 
            ORDER BY heat_number
        """, (game['heat_group_id'], game['id']), fetch=True)

    @staticmethod
    def update_generated_pdfs(game_id, startlist_pdf=None, results_pdf=None):
        data = {}
        if startlist_pdf:
            data['generated_startlist_pdf'] = startlist_pdf
        if results_pdf:
            data['generated_results_pdf'] = results_pdf

        if data:
            set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
            query = f"UPDATE games SET {set_clause} WHERE id = %s"
            params = list(data.values()) + [game_id]
            return execute_query(query, params)
        return False

    @staticmethod
    def update_manual_pdfs(game_id, startlist_pdf=None, results_pdf=None):
        data = {}
        if startlist_pdf:
            data['manual_startlist_pdf'] = startlist_pdf
        if results_pdf:
            data['manual_results_pdf'] = results_pdf

        if data:
            set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
            query = f"UPDATE games SET {set_clause} WHERE id = %s"
            params = list(data.values()) + [game_id]
            return execute_query(query, params)
        return False

    @staticmethod
    def get_games_for_bulk_generation():
        return execute_query("""
            SELECT * FROM games 
            WHERE manual_startlist_pdf IS NULL 
            AND manual_results_pdf IS NULL
            ORDER BY day, time
        """, fetch=True)

    @staticmethod
    def get_games_with_pdfs():
        return execute_query("""
            SELECT * FROM games 
            WHERE generated_startlist_pdf IS NOT NULL 
            OR generated_results_pdf IS NOT NULL
            OR manual_startlist_pdf IS NOT NULL 
            OR manual_results_pdf IS NOT NULL
            ORDER BY day, time
        """, fetch=True)

    @staticmethod
    def toggle_publish_startlist(id):
        current = execute_one("SELECT startlist_published FROM games WHERE id = %s", (id,))
        if current:
            new_status = not current.get('startlist_published', False)
            execute_query("UPDATE games SET startlist_published = %s WHERE id = %s", (new_status, id))
            return new_status
        return False

    @staticmethod
    def toggle_corrected_status(id, user_id):
        current = execute_one("SELECT corrected FROM games WHERE id = %s", (id,))
        if current:
            new_status = not current.get('corrected', False)
            if new_status:
                execute_query(
                    "UPDATE games SET corrected = %s, corrected_by = %s, corrected_date = CURRENT_TIMESTAMP WHERE id = %s",
                    (new_status, user_id, id)
                )
            else:
                execute_query(
                    "UPDATE games SET corrected = %s, corrected_by = NULL, corrected_date = NULL WHERE id = %s",
                    (new_status, id)
                )
            return new_status
        return False