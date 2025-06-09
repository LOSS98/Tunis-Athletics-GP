from database.db_manager import execute_query, execute_one
class StartList:
    @staticmethod
    def get_by_game(game_id):
        query = """
            SELECT s.*, a.firstname, a.lastname, a.npc, a.class, a.gender,
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
        from database.models.game import Game
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
        from database.models.game import Game
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