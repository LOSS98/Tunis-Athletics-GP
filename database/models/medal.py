from database.db_manager import execute_query, execute_one

class Medal:
    @staticmethod
    def get_all():
        query = """
        SELECT m.*, n.name as npc_name, n.flag_file_path,
               r.name as region_name, r.continent,
               RANK() OVER (ORDER BY m.gold DESC, m.silver DESC, m.bronze DESC, m.total DESC) as rank
        FROM medals m
        JOIN npcs n ON m.npc = n.code
        LEFT JOIN regions r ON n.region_code = r.code
        ORDER BY m.gold DESC, m.silver DESC, m.bronze DESC, m.total DESC
        """
        return execute_query(query, fetch=True)

    @staticmethod
    def get_by_npc(npc_code):
        query = """
        SELECT m.*, n.name as npc_name, n.flag_file_path
        FROM medals m
        JOIN npcs n ON m.npc = n.code
        WHERE m.npc = %s
        """
        return execute_one(query, (npc_code,))

    @staticmethod
    def calculate_from_results():
        execute_query("DELETE FROM medals WHERE manual_override = FALSE")

        query = """
        INSERT INTO medals (npc, gold, silver, bronze, total, manual_override, last_calculated)
        SELECT 
            a.npc,
            COUNT(CASE WHEN r.rank = '1' THEN 1 END) as gold,
            COUNT(CASE WHEN r.rank = '2' THEN 1 END) as silver,
            COUNT(CASE WHEN r.rank = '3' THEN 1 END) as bronze,
            COUNT(CASE WHEN r.rank IN ('1', '2', '3') THEN 1 END) as total,
            FALSE as manual_override,
            CURRENT_TIMESTAMP as last_calculated
        FROM results r
        JOIN athletes a ON r.athlete_sdms = a.sdms
        JOIN games g ON r.game_id = g.id
        WHERE r.rank IN ('1', '2', '3') AND g.official = TRUE
        GROUP BY a.npc
        ON CONFLICT (npc) DO UPDATE SET
            gold = EXCLUDED.gold,
            silver = EXCLUDED.silver,
            bronze = EXCLUDED.bronze,
            total = EXCLUDED.total,
            last_calculated = EXCLUDED.last_calculated
        """

        return execute_query(query)

    @staticmethod
    def update_manual(npc_code, gold, silver, bronze):
        total = gold + silver + bronze
        query = """
        INSERT INTO medals (npc, gold, silver, bronze, total, manual_override, updated_at)
        VALUES (%s, %s, %s, %s, %s, TRUE, CURRENT_TIMESTAMP)
        ON CONFLICT (npc) DO UPDATE SET
            gold = EXCLUDED.gold,
            silver = EXCLUDED.silver,
            bronze = EXCLUDED.bronze,
            total = EXCLUDED.total,
            manual_override = TRUE,
            updated_at = EXCLUDED.updated_at
        """
        return execute_query(query, (npc_code, gold, silver, bronze, total))

    @staticmethod
    def delete_by_npc(npc_code):
        return execute_query("DELETE FROM medals WHERE npc = %s", (npc_code,))