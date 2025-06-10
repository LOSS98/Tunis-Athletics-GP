from database.db_manager import execute_query, execute_one


class Medal:
    @staticmethod
    def get_all():
        """Get all medal standings with NPC info and proper ranking"""
        query = """
        SELECT m.*, n.name as npc_name, n.flag_file_path,
               r.name as region_name, r.continent
        FROM medals m
        JOIN npcs n ON m.npc = n.code
        LEFT JOIN regions r ON n.region_code = r.code
        ORDER BY m.gold DESC, m.silver DESC, m.bronze DESC, m.total DESC
        """
        medals = execute_query(query, fetch=True)

        # Add proper ranking with tie handling
        if medals:
            medals = add_proper_ranking(medals)

        return medals

    @staticmethod
    def get_by_npc(npc_code):
        """Get medal count for specific NPC"""
        query = """
        SELECT m.*, n.name as npc_name, n.flag_file_path
        FROM medals m
        JOIN npcs n ON m.npc = n.code
        WHERE m.npc = %s
        """
        return execute_one(query, (npc_code,))

    @staticmethod
    def calculate_from_results():
        """Calculate medals from official results automatically"""
        # First, clear existing auto-calculated medals
        execute_query("DELETE FROM medals WHERE manual_override = FALSE")

        # Calculate medals from results where rank is 1, 2, or 3 and game is official
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
        """Update medal count manually"""
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
        """Delete medal record for NPC"""
        return execute_query("DELETE FROM medals WHERE npc = %s", (npc_code,))


def add_proper_ranking(medals):
    """Add proper ranking with tie handling"""
    if not medals:
        return medals

    # Sort medals by gold, silver, bronze, total
    sorted_medals = sorted(medals, key=lambda x: (x['gold'], x['silver'], x['bronze'], x['total']), reverse=True)

    # Add ranking with proper tie handling
    current_rank = 1

    for i, medal in enumerate(sorted_medals):
        if i == 0:
            medal['rank'] = current_rank
        else:
            # Check if current medal is tied with previous
            prev_medal = sorted_medals[i - 1]
            if (medal['gold'] == prev_medal['gold'] and
                    medal['silver'] == prev_medal['silver'] and
                    medal['bronze'] == prev_medal['bronze'] and
                    medal['total'] == prev_medal['total']):
                # Same ranking as previous
                medal['rank'] = prev_medal['rank']
            else:
                # New ranking = current position + 1
                medal['rank'] = i + 1
                current_rank = i + 1

    return sorted_medals