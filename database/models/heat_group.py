from config import config
from database.db_manager import execute_one, execute_query

class HeatGroup:
    @staticmethod
    def get_all():
        return execute_query("SELECT * FROM heat_groups ORDER BY day, event", fetch=True)

    @staticmethod
    def get_by_id(id):
        return execute_one("SELECT * FROM heat_groups WHERE id = %s", (id,))

    @staticmethod
    def create(name, event, genders, classes, day):
        query = "INSERT INTO heat_groups (name, event, genders, classes, day) VALUES (%s, %s, %s, %s, %s) RETURNING id"
        result = execute_query(query, (name, event, genders, classes, day))
        return result['id'] if result else None

    @staticmethod
    def delete(id):
        execute_query("UPDATE games SET heat_group_id = NULL, heat_number = NULL WHERE heat_group_id = %s", (id,))
        return execute_query("DELETE FROM heat_groups WHERE id = %s", (id,))

    @staticmethod
    def get_games(heat_group_id):
        return execute_query("""
            SELECT * FROM games 
            WHERE heat_group_id = %s 
            ORDER BY heat_number
        """, (heat_group_id,), fetch=True)

    @staticmethod
    def get_combined_results(heat_group_id):
        return execute_query("""
            SELECT r.*, a.firstname, a.lastname, a.npc, a.gender as athlete_gender, a.class as athlete_class,
                   g.firstname AS guide_firstname, g.lastname AS guide_lastname,
                   gm.heat_number, gm.event, gm.id as game_id
            FROM results r
            JOIN athletes a ON r.athlete_sdms = a.sdms
            LEFT JOIN athletes g ON r.guide_sdms = g.sdms
            JOIN games gm ON r.game_id = gm.id
            WHERE gm.heat_group_id = %s AND r.value NOT IN ('DNS', 'DNF', 'DQ', 'NM')
            ORDER BY 
                CASE WHEN r.value ~ '^[0-9]+\.?[0-9]*$' THEN CAST(r.value AS FLOAT) ELSE 999999 END,
                r.value
        """, (heat_group_id,), fetch=True)

    @staticmethod
    def rank_combined_results(heat_group_id):
        results = HeatGroup.get_combined_results(heat_group_id)

        if not results:
            return True

        special_values = config.RESULT_SPECIAL_VALUES

        current_rank = 1
        previous_value = None
        athletes_at_current_rank = 0

        for i, result in enumerate(results):
            print(f"Processing result ID {result['id']} with value {result['value']}")
            current_value = result['value']

            if current_value in special_values:
                execute_query("UPDATE results SET rank = %s WHERE id = %s",
                              ('-', result['id']))
                print(f"✓ Special value, rank set to '-'")
                continue

            if previous_value is not None and current_value != previous_value:
                current_rank += athletes_at_current_rank
                athletes_at_current_rank = 1
            else:
                athletes_at_current_rank += 1

            execute_query("UPDATE results SET rank = %s WHERE id = %s",
                          (str(current_rank), result['id']))

            print(f"✓ Rank {current_rank} assigned (athletes at this rank: {athletes_at_current_rank})")
            previous_value = current_value

        return True