from database.db_manager import execute_one, execute_query


class WorldRecord:
    @staticmethod
    def get_all(approved_only=True, competition_only=True):
        conditions = []
        if approved_only:
            conditions.append("wr.approved = TRUE")
        if competition_only:
            conditions.append("wr.made_in_competition = TRUE")

        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

        query = f"""
            SELECT wr.*, a.firstname, a.lastname, a.gender, n.name as npc_name, 
                   n.region_code, r.name as region_name,
                   u.username as approved_by_username,
                   g.day, g.time, g.event as game_event, g.id as game_id
            FROM world_records wr
            LEFT JOIN athletes a ON wr.sdms = a.sdms
            LEFT JOIN npcs n ON wr.npc = n.code
            LEFT JOIN regions r ON n.region_code = r.code
            LEFT JOIN users u ON wr.approved_by = u.id
            LEFT JOIN games g ON wr.competition_id = g.id
            {where_clause}
            ORDER BY wr.record_type, wr.gender, wr.event, wr.athlete_class, 
                     wr.record_date DESC, wr.created_at DESC
        """
        return execute_query(query, fetch=True)

    @staticmethod
    def get_pending(competition_only=True):
        conditions = ["wr.approved = FALSE"]
        if competition_only:
            conditions.append("wr.made_in_competition = TRUE")

        where_clause = " WHERE " + " AND ".join(conditions)

        query = f"""
            SELECT wr.*, a.firstname, a.lastname, a.gender, n.name as npc_name, 
                   n.region_code, r.name as region_name,
                   g.day, g.time, g.event as game_event, g.id as game_id
            FROM world_records wr
            LEFT JOIN athletes a ON wr.sdms = a.sdms
            LEFT JOIN npcs n ON wr.npc = n.code
            LEFT JOIN regions r ON n.region_code = r.code
            LEFT JOIN games g ON wr.competition_id = g.id
            {where_clause}
            ORDER BY wr.created_at DESC
        """
        return execute_query(query, fetch=True)

    @staticmethod
    def get_pending_for_event_class(event, athlete_class, record_type, gender):
        return execute_one("""
            SELECT * FROM world_records 
            WHERE event = %s AND athlete_class = %s AND record_type = %s 
            AND gender = %s AND approved = FALSE
            ORDER BY performance DESC LIMIT 1
        """, (event, athlete_class, record_type, gender))

    @staticmethod
    def get_pending_for_event_class_region(event, athlete_class, record_type, gender, region_code):
        return execute_one("""
            SELECT wr.* FROM world_records wr
            LEFT JOIN npcs n ON wr.npc = n.code
            WHERE wr.event = %s AND wr.athlete_class = %s AND wr.record_type = %s 
            AND wr.gender = %s AND n.region_code = %s AND wr.approved = FALSE
            ORDER BY wr.performance DESC LIMIT 1
        """, (event, athlete_class, record_type, gender, region_code))

    @staticmethod
    def create(**data):
        keys = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        query = f"INSERT INTO world_records ({keys}) VALUES ({placeholders}) RETURNING id"
        result = execute_query(query, list(data.values()))
        return result['id'] if result else None

    @staticmethod
    def approve(record_id, user_id):
        return execute_query("""
            UPDATE world_records 
            SET approved = TRUE, approved_by = %s, approved_date = CURRENT_TIMESTAMP 
            WHERE id = %s
        """, (user_id, record_id))

    @staticmethod
    def approve_all(user_id):
        result = execute_query("""
            UPDATE world_records 
            SET approved = TRUE, approved_by = %s, approved_date = CURRENT_TIMESTAMP 
            WHERE approved = FALSE
        """, (user_id,))
        return result if result else 0

    @staticmethod
    def delete_all_pending():
        result = execute_query("DELETE FROM world_records WHERE approved = FALSE AND made_in_competition = TRUE")
        return result if result else 0

    @staticmethod
    def check_existing_record(event, class_name, record_type, gender, npc_code=None):
        if record_type == 'WR':
            return execute_one("""
                SELECT * FROM world_records 
                WHERE event = %s AND athlete_class = %s AND record_type = 'WR' 
                AND gender = %s AND approved = TRUE
                ORDER BY CAST(performance AS FLOAT) DESC LIMIT 1
            """, (event, class_name, gender))
        elif record_type == 'AR':
            return execute_one("""
                SELECT wr.* FROM world_records wr
                LEFT JOIN npcs n ON wr.npc = n.code
                LEFT JOIN npcs n2 ON n2.code = %s
                WHERE wr.event = %s AND wr.athlete_class = %s AND wr.record_type = 'AR' 
                AND wr.gender = %s AND n.region_code = n2.region_code AND wr.approved = TRUE
                ORDER BY CAST(wr.performance AS FLOAT) DESC LIMIT 1
            """, (npc_code, event, class_name, gender))
        return None

    @staticmethod
    def delete(record_id):
        return execute_query("DELETE FROM world_records WHERE id = %s", (record_id,))

    @staticmethod
    def get_all_with_competition_details(approved_only=True):
        where_clause = " WHERE wr.approved = TRUE" if approved_only else ""

        query = f"""
            SELECT wr.*, a.firstname, a.lastname, a.photo, n.name as npc_name, 
                   n.region_code, r.name as region_name,
                   u.username as approved_by_username,
                   g.day, g.time, g.event as game_event, g.genders, g.classes,
                   g.id as game_id,
                   res.rank, res.value
            FROM world_records wr
            LEFT JOIN athletes a ON wr.sdms = a.sdms
            LEFT JOIN npcs n ON wr.npc = n.code
            LEFT JOIN regions r ON n.region_code = r.code
            LEFT JOIN users u ON wr.approved_by = u.id
            LEFT JOIN games g ON wr.competition_id = g.id
            LEFT JOIN results res ON (res.game_id = g.id AND res.athlete_sdms = wr.sdms)
            {where_clause}
            ORDER BY wr.record_type, wr.gender, wr.event, wr.athlete_class,
                     wr.record_date DESC, wr.created_at DESC
        """
        return execute_query(query, fetch=True)

    @staticmethod
    def get_by_athlete(sdms, approved_only=True):
        condition = " AND wr.approved = TRUE" if approved_only else ""

        query = f"""
            SELECT wr.*, n.name as npc_name, n.region_code, r.name as region_name,
                   u.username as approved_by_username,
                   g.day, g.time, g.event as game_event, g.id as game_id
            FROM world_records wr
            LEFT JOIN npcs n ON wr.npc = n.code
            LEFT JOIN regions r ON n.region_code = r.code
            LEFT JOIN users u ON wr.approved_by = u.id
            LEFT JOIN games g ON wr.competition_id = g.id
            WHERE wr.sdms = %s{condition}
            ORDER BY wr.record_type, wr.record_date DESC
        """
        return execute_query(query, (sdms,), fetch=True)

    @staticmethod
    def get_by_event_class_gender(event, athlete_class, gender, record_type=None, approved_only=True):
        conditions = ["wr.event = %s", "wr.athlete_class = %s", "wr.gender = %s"]
        params = [event, athlete_class, gender]

        if record_type:
            conditions.append("wr.record_type = %s")
            params.append(record_type)

        if approved_only:
            conditions.append("wr.approved = TRUE")

        where_clause = " WHERE " + " AND ".join(conditions)

        query = f"""
            SELECT wr.*, a.firstname, a.lastname, n.name as npc_name, 
                   n.region_code, r.name as region_name,
                   u.username as approved_by_username,
                   g.day, g.time, g.event as game_event, g.id as game_id
            FROM world_records wr
            LEFT JOIN athletes a ON wr.sdms = a.sdms
            LEFT JOIN npcs n ON wr.npc = n.code
            LEFT JOIN regions r ON n.region_code = r.code
            LEFT JOIN users u ON wr.approved_by = u.id
            LEFT JOIN games g ON wr.competition_id = g.id
            {where_clause}
            ORDER BY wr.record_type, CAST(wr.performance AS FLOAT) DESC, wr.record_date DESC
        """
        return execute_query(query, params, fetch=True)

    @staticmethod
    def get_by_region(region_code, approved_only=True):
        condition = " AND wr.approved = TRUE" if approved_only else ""

        query = f"""
            SELECT wr.*, a.firstname, a.lastname, n.name as npc_name, 
                   r.name as region_name,
                   u.username as approved_by_username,
                   g.day, g.time, g.event as game_event, g.id as game_id
            FROM world_records wr
            LEFT JOIN athletes a ON wr.sdms = a.sdms
            LEFT JOIN npcs n ON wr.npc = n.code
            LEFT JOIN regions r ON n.region_code = r.code
            LEFT JOIN users u ON wr.approved_by = u.id
            LEFT JOIN games g ON wr.competition_id = g.id
            WHERE wr.record_type = 'AR' AND n.region_code = %s{condition}
            ORDER BY wr.gender, wr.event, wr.athlete_class, 
                     CAST(wr.performance AS FLOAT) DESC, wr.record_date DESC
        """
        return execute_query(query, (region_code,), fetch=True)

    @staticmethod
    def get_latest_records(limit=10, approved_only=True):
        condition = " WHERE wr.approved = TRUE" if approved_only else ""

        query = f"""
            SELECT wr.*, a.firstname, a.lastname, n.name as npc_name, 
                   n.region_code, r.name as region_name,
                   u.username as approved_by_username,
                   g.day, g.time, g.event as game_event, g.id as game_id
            FROM world_records wr
            LEFT JOIN athletes a ON wr.sdms = a.sdms
            LEFT JOIN npcs n ON wr.npc = n.code
            LEFT JOIN regions r ON n.region_code = r.code
            LEFT JOIN users u ON wr.approved_by = u.id
            LEFT JOIN games g ON wr.competition_id = g.id
            {condition}
            ORDER BY wr.record_date DESC, wr.created_at DESC
            LIMIT %s
        """
        return execute_query(query, (limit,), fetch=True)

    @staticmethod
    def get_records_by_competition(competition_id, approved_only=True):
        condition = " AND wr.approved = TRUE" if approved_only else ""

        query = f"""
            SELECT wr.*, a.firstname, a.lastname, n.name as npc_name, 
                   n.region_code, r.name as region_name,
                   u.username as approved_by_username,
                   g.day, g.time, g.event as game_event
            FROM world_records wr
            LEFT JOIN athletes a ON wr.sdms = a.sdms
            LEFT JOIN npcs n ON wr.npc = n.code
            LEFT JOIN regions r ON n.region_code = r.code
            LEFT JOIN users u ON wr.approved_by = u.id
            LEFT JOIN games g ON wr.competition_id = g.id
            WHERE wr.competition_id = %s{condition}
            ORDER BY wr.record_type, wr.gender, wr.event, wr.athlete_class,
                     CAST(wr.performance AS FLOAT) DESC
        """
        return execute_query(query, (competition_id,), fetch=True)

    @staticmethod
    def count_records_by_type_and_gender():
        query = """
            SELECT record_type, gender, COUNT(*) as count
            FROM world_records 
            WHERE approved = TRUE
            GROUP BY record_type, gender
            ORDER BY record_type, gender
        """
        return execute_query(query, fetch=True)

    @staticmethod
    def count_records_by_region():
        query = """
            SELECT r.name as region_name, r.code as region_code, 
                   wr.gender, COUNT(*) as count
            FROM world_records wr
            LEFT JOIN npcs n ON wr.npc = n.code
            LEFT JOIN regions r ON n.region_code = r.code
            WHERE wr.record_type = 'AR' AND wr.approved = TRUE
            GROUP BY r.name, r.code, wr.gender
            ORDER BY r.name, wr.gender
        """
        return execute_query(query, fetch=True)

    @staticmethod
    def update(record_id, **data):
        set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
        query = f"UPDATE world_records SET {set_clause} WHERE id = %s"
        params = list(data.values()) + [record_id]
        return execute_query(query, params)

    @staticmethod
    def get_by_id(record_id):
        query = """
            SELECT wr.*, a.firstname, a.lastname, n.name as npc_name, 
                   n.region_code, r.name as region_name,
                   u.username as approved_by_username,
                   g.day, g.time, g.event as game_event, g.id as game_id
            FROM world_records wr
            LEFT JOIN athletes a ON wr.sdms = a.sdms
            LEFT JOIN npcs n ON wr.npc = n.code
            LEFT JOIN regions r ON n.region_code = r.code
            LEFT JOIN users u ON wr.approved_by = u.id
            LEFT JOIN games g ON wr.competition_id = g.id
            WHERE wr.id = %s
        """
        return execute_one(query, (record_id,))

    @staticmethod
    def search(search_term, approved_only=True):
        condition = " AND wr.approved = TRUE" if approved_only else ""

        query = f"""
            SELECT wr.*, a.firstname, a.lastname, n.name as npc_name, 
                   n.region_code, r.name as region_name,
                   u.username as approved_by_username,
                   g.day, g.time, g.event as game_event, g.id as game_id
            FROM world_records wr
            LEFT JOIN athletes a ON wr.sdms = a.sdms
            LEFT JOIN npcs n ON wr.npc = n.code
            LEFT JOIN regions r ON n.region_code = r.code
            LEFT JOIN users u ON wr.approved_by = u.id
            LEFT JOIN games g ON wr.competition_id = g.id
            WHERE (
                LOWER(a.firstname) LIKE LOWER(%s) OR
                LOWER(a.lastname) LIKE LOWER(%s) OR
                LOWER(wr.event) LIKE LOWER(%s) OR
                LOWER(wr.athlete_class) LIKE LOWER(%s) OR
                LOWER(n.name) LIKE LOWER(%s) OR
                wr.sdms::text LIKE %s
            ){condition}
            ORDER BY wr.record_date DESC, wr.created_at DESC
            LIMIT 50
        """
        search_pattern = f"%{search_term}%"
        params = [search_pattern] * 6
        return execute_query(query, params, fetch=True)

    @staticmethod
    def get_records_needing_approval():
        query = """
            SELECT wr.*, a.firstname, a.lastname, n.name as npc_name, 
                   n.region_code, r.name as region_name,
                   g.day, g.time, g.event as game_event, g.id as game_id
            FROM world_records wr
            LEFT JOIN athletes a ON wr.sdms = a.sdms
            LEFT JOIN npcs n ON wr.npc = n.code
            LEFT JOIN regions r ON n.region_code = r.code
            LEFT JOIN games g ON wr.competition_id = g.id
            WHERE wr.approved = FALSE
            ORDER BY wr.created_at DESC
        """
        return execute_query(query, fetch=True)

    @staticmethod
    def approve_multiple(record_ids, user_id):
        if not record_ids:
            return 0

        placeholders = ','.join(['%s'] * len(record_ids))
        query = f"""
            UPDATE world_records 
            SET approved = TRUE, approved_by = %s, approved_date = CURRENT_TIMESTAMP 
            WHERE id IN ({placeholders})
        """
        params = [user_id] + list(record_ids)
        return execute_query(query, params)

    @staticmethod
    def delete_multiple(record_ids):
        if not record_ids:
            return 0

        placeholders = ','.join(['%s'] * len(record_ids))
        query = f"DELETE FROM world_records WHERE id IN ({placeholders})"
        return execute_query(query, list(record_ids))

    @staticmethod
    def check_for_better_performance(event, athlete_class, gender, record_type, performance, npc_code=None):
        try:
            performance_float = float(performance)
        except (ValueError, TypeError):
            return False, None

        existing_record = WorldRecord.check_existing_record(event, athlete_class, record_type, gender, npc_code)

        if not existing_record:
            return True, None  # Would be a new record

        try:
            existing_performance = float(existing_record['performance'])
            return performance_float > existing_performance, existing_record
        except (ValueError, TypeError):
            return False, existing_record

    @staticmethod
    def get_event_progression(event, athlete_class, gender, record_type='WR'):
        query = """
            SELECT wr.*, a.firstname, a.lastname, n.name as npc_name,
                   g.day, g.time, g.event as game_event
            FROM world_records wr
            LEFT JOIN athletes a ON wr.sdms = a.sdms
            LEFT JOIN npcs n ON wr.npc = n.code
            LEFT JOIN games g ON wr.competition_id = g.id
            WHERE wr.event = %s AND wr.athlete_class = %s 
            AND wr.gender = %s AND wr.record_type = %s
            AND wr.approved = TRUE
            ORDER BY wr.record_date ASC, wr.created_at ASC
        """
        return execute_query(query, (event, athlete_class, gender, record_type), fetch=True)