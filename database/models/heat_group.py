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
        query = """
            SELECT r.*, a.firstname, a.lastname, a.npc, a.gender as athlete_gender, 
                   a.class as athlete_class,
                   g.firstname AS guide_firstname, g.lastname AS guide_lastname,
                   gm.classes as game_classes, gm.event as game_event,
                   gm.wind_velocity, gm.id as game_id,

                   -- Heat information
                   CASE 
                       WHEN gm.id = (SELECT MIN(id) FROM games WHERE heat_group_id = %s) THEN 1
                       WHEN gm.id = (SELECT MAX(id) FROM games WHERE heat_group_id = %s) THEN 2
                       ELSE 1
                   END as heat_number,

                   -- Check for World Record
                   CASE WHEN EXISTS (
                       SELECT 1 FROM world_records wr 
                       WHERE wr.sdms = r.athlete_sdms 
                       AND wr.event = gm.event 
                       AND wr.athlete_class = ANY(string_to_array(a.class, ','))
                       AND wr.gender = a.gender
                       AND wr.record_type = 'WR'
                       AND wr.competition_id = r.game_id
                   ) THEN TRUE ELSE FALSE END as is_world_record,

                   -- Check WR approval status
                   (SELECT wr.approved FROM world_records wr 
                    WHERE wr.sdms = r.athlete_sdms AND wr.event = gm.event 
                    AND wr.athlete_class = ANY(string_to_array(a.class, ','))
                    AND wr.gender = a.gender
                    AND wr.record_type = 'WR' AND wr.competition_id = r.game_id
                    LIMIT 1) as wr_approved,

                   -- Check for Area Record
                   CASE WHEN EXISTS (
                       SELECT 1 FROM world_records wr 
                       JOIN npcs n ON wr.npc = n.code
                       WHERE wr.sdms = r.athlete_sdms 
                       AND wr.event = gm.event 
                       AND wr.athlete_class = ANY(string_to_array(a.class, ','))
                       AND wr.gender = a.gender
                       AND wr.record_type = 'AR'
                       AND wr.competition_id = r.game_id
                   ) THEN TRUE ELSE FALSE END as is_area_record,

                   -- Get AR region and approval status
                   (SELECT n.region_code FROM world_records wr 
                    JOIN npcs n ON wr.npc = n.code
                    WHERE wr.sdms = r.athlete_sdms AND wr.event = gm.event 
                    AND wr.athlete_class = ANY(string_to_array(a.class, ','))
                    AND wr.gender = a.gender
                    AND wr.record_type = 'AR' AND wr.competition_id = r.game_id
                    LIMIT 1) as ar_region,

                   (SELECT wr.approved FROM world_records wr 
                    WHERE wr.sdms = r.athlete_sdms AND wr.event = gm.event 
                    AND wr.athlete_class = ANY(string_to_array(a.class, ','))
                    AND wr.gender = a.gender
                    AND wr.record_type = 'AR' AND wr.competition_id = r.game_id
                    LIMIT 1) as ar_approved,

                   -- Check for Personal Best
                   CASE WHEN EXISTS (
                       SELECT 1 FROM personal_bests pb 
                       WHERE pb.sdms = r.athlete_sdms 
                       AND pb.event = gm.event 
                       AND pb.athlete_class = ANY(string_to_array(a.class, ','))
                       AND pb.competition_id = r.game_id
                   ) THEN TRUE ELSE FALSE END as is_personal_best,

                   -- Check PB approval status
                   (SELECT pb.approved FROM personal_bests pb 
                    WHERE pb.sdms = r.athlete_sdms AND pb.event = gm.event 
                    AND pb.athlete_class = ANY(string_to_array(a.class, ','))
                    AND pb.competition_id = r.game_id
                    LIMIT 1) as pb_approved

            FROM results r
            JOIN athletes a ON r.athlete_sdms = a.sdms
            LEFT JOIN athletes g ON r.guide_sdms = g.sdms
            JOIN games gm ON r.game_id = gm.id
            WHERE gm.heat_group_id = %s
            ORDER BY 
                CASE WHEN r.rank ~ '^[0-9]+' THEN CAST(r.rank AS INTEGER) ELSE 999 END,
                r.rank
        """

        results = execute_query(query, (heat_group_id, heat_group_id, heat_group_id), fetch=True)

        # Process athlete classes
        for result in results:
            if result['athlete_class']:
                result['athlete_classes'] = [c.strip() for c in result['athlete_class'].split(',')]
            else:
                result['athlete_classes'] = []

            if result.get('game_classes'):
                result['game_classes_list'] = [c.strip() for c in result['game_classes'].split(',')]
            else:
                result['game_classes_list'] = []

        return results

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