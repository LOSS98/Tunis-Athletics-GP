from database.db_manager import execute_one, execute_query


class PersonalBest:
    @staticmethod
    def get_all(approved_only=True, competition_only=True):
        conditions = []
        if approved_only:
            conditions.append("pb.approved = TRUE")
        if competition_only:
            conditions.append("pb.made_in_competition = TRUE")

        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

        query = f"""
            SELECT pb.*, a.firstname, a.lastname, a.npc, a.gender, n.name as npc_name,
                   n.region_code, r.name as region_name,
                   u.username as approved_by_username,
                   g.day, g.time, g.event as game_event, g.id as game_id
            FROM personal_bests pb
            JOIN athletes a ON pb.sdms = a.sdms
            LEFT JOIN npcs n ON a.npc = n.code
            LEFT JOIN regions r ON n.region_code = r.code
            LEFT JOIN users u ON pb.approved_by = u.id
            LEFT JOIN games g ON pb.competition_id = g.id
            {where_clause}
            ORDER BY a.gender, pb.event, pb.athlete_class, 
                     pb.record_date DESC, pb.created_at DESC
        """
        return execute_query(query, fetch=True)

    @staticmethod
    def get_pending(competition_only=True):
        conditions = ["pb.approved = FALSE"]
        if competition_only:
            conditions.append("pb.made_in_competition = TRUE")

        where_clause = " WHERE " + " AND ".join(conditions)

        query = f"""
            SELECT pb.*, a.firstname, a.lastname, a.npc, a.gender, n.name as npc_name,
                   n.region_code, r.name as region_name,
                   g.day, g.time, g.event as game_event, g.id as game_id
            FROM personal_bests pb
            JOIN athletes a ON pb.sdms = a.sdms
            LEFT JOIN npcs n ON a.npc = n.code
            LEFT JOIN regions r ON n.region_code = r.code
            LEFT JOIN games g ON pb.competition_id = g.id
            {where_clause}
            ORDER BY pb.created_at DESC
        """
        return execute_query(query, fetch=True)

    @staticmethod
    def get_pending_for_athlete(sdms, event, athlete_class):
        return execute_one("""
            SELECT pb.*, a.gender FROM personal_bests pb
            JOIN athletes a ON pb.sdms = a.sdms
            WHERE pb.sdms = %s AND pb.event = %s AND pb.athlete_class = %s 
            AND pb.approved = FALSE
            ORDER BY CAST(pb.performance AS FLOAT) DESC LIMIT 1
        """, (sdms, event, athlete_class))

    @staticmethod
    def create(**data):
        keys = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        query = f"""
            INSERT INTO personal_bests ({keys}) VALUES ({placeholders}) 
            ON CONFLICT (sdms, event, athlete_class) DO UPDATE SET 
            performance = EXCLUDED.performance, 
            location = EXCLUDED.location, 
            record_date = EXCLUDED.record_date, 
            approved = FALSE,
            competition_id = EXCLUDED.competition_id
            RETURNING id
        """
        result = execute_query(query, list(data.values()))
        return result['id'] if result else None

    @staticmethod
    def approve(record_id, user_id):
        return execute_query("""
            UPDATE personal_bests 
            SET approved = TRUE, approved_by = %s, approved_date = CURRENT_TIMESTAMP 
            WHERE id = %s
        """, (user_id, record_id))

    @staticmethod
    def approve_all(user_id):
        result = execute_query("""
            UPDATE personal_bests 
            SET approved = TRUE, approved_by = %s, approved_date = CURRENT_TIMESTAMP 
            WHERE approved = FALSE
        """, (user_id,))
        return result if result else 0

    @staticmethod
    def delete_all_pending():
        result = execute_query("DELETE FROM personal_bests WHERE approved = FALSE and made_in_competition = TRUE")
        return result if result else 0

    @staticmethod
    def check_existing_pb(sdms, event, class_name):
        return execute_one("""
            SELECT pb.*, a.gender FROM personal_bests pb
            JOIN athletes a ON pb.sdms = a.sdms
            WHERE pb.sdms = %s AND pb.event = %s AND pb.athlete_class = %s 
            AND pb.approved = TRUE
        """, (sdms, event, class_name))

    @staticmethod
    def delete(record_id):
        return execute_query("DELETE FROM personal_bests WHERE id = %s", (record_id,))

    @staticmethod
    def get_by_athlete(sdms, approved_only=True):
        condition = " AND pb.approved = TRUE" if approved_only else ""

        query = f"""
            SELECT pb.*, a.firstname, a.lastname, a.npc, a.gender, n.name as npc_name,
                   u.username as approved_by_username,
                   g.day, g.time, g.event as game_event, g.id as game_id
            FROM personal_bests pb
            JOIN athletes a ON pb.sdms = a.sdms
            LEFT JOIN npcs n ON a.npc = n.code
            LEFT JOIN users u ON pb.approved_by = u.id
            LEFT JOIN games g ON pb.competition_id = g.id
            WHERE pb.sdms = %s{condition}
            ORDER BY pb.event, pb.athlete_class, pb.record_date DESC
        """
        return execute_query(query, (sdms,), fetch=True)

    @staticmethod
    def get_by_event_class_gender(event, athlete_class, gender, approved_only=True):
        condition = " AND pb.approved = TRUE" if approved_only else ""

        query = f"""
            SELECT pb.*, a.firstname, a.lastname, a.npc, a.gender, n.name as npc_name,
                   n.region_code, r.name as region_name,
                   u.username as approved_by_username,
                   g.day, g.time, g.event as game_event, g.id as game_id
            FROM personal_bests pb
            JOIN athletes a ON pb.sdms = a.sdms
            LEFT JOIN npcs n ON a.npc = n.code
            LEFT JOIN regions r ON n.region_code = r.code
            LEFT JOIN users u ON pb.approved_by = u.id
            LEFT JOIN games g ON pb.competition_id = g.id
            WHERE pb.event = %s AND pb.athlete_class = %s AND a.gender = %s{condition}
            ORDER BY CAST(pb.performance AS FLOAT) DESC, pb.record_date DESC
        """
        return execute_query(query, (event, athlete_class, gender), fetch=True)

    @staticmethod
    def get_top_performances(event, athlete_class, gender, limit=10, approved_only=True):
        condition = " AND pb.approved = TRUE" if approved_only else ""

        query = f"""
            SELECT pb.*, a.firstname, a.lastname, a.npc, a.gender, n.name as npc_name,
                   n.region_code, r.name as region_name,
                   g.day, g.time, g.event as game_event, g.id as game_id
            FROM personal_bests pb
            JOIN athletes a ON pb.sdms = a.sdms
            LEFT JOIN npcs n ON a.npc = n.code
            LEFT JOIN regions r ON n.region_code = r.code
            LEFT JOIN games g ON pb.competition_id = g.id
            WHERE pb.event = %s AND pb.athlete_class = %s AND a.gender = %s{condition}
            ORDER BY CAST(pb.performance AS FLOAT) DESC
            LIMIT %s
        """
        return execute_query(query, (event, athlete_class, gender, limit), fetch=True)

    @staticmethod
    def get_latest_pbs(limit=20, approved_only=True):
        condition = " WHERE pb.approved = TRUE" if approved_only else ""

        query = f"""
            SELECT pb.*, a.firstname, a.lastname, a.npc, a.gender, n.name as npc_name,
                   n.region_code, r.name as region_name,
                   u.username as approved_by_username,
                   g.day, g.time, g.event as game_event, g.id as game_id
            FROM personal_bests pb
            JOIN athletes a ON pb.sdms = a.sdms
            LEFT JOIN npcs n ON a.npc = n.code
            LEFT JOIN regions r ON n.region_code = r.code
            LEFT JOIN users u ON pb.approved_by = u.id
            LEFT JOIN games g ON pb.competition_id = g.id
            {condition}
            ORDER BY pb.record_date DESC, pb.created_at DESC
            LIMIT %s
        """
        return execute_query(query, (limit,), fetch=True)

    @staticmethod
    def get_pbs_by_competition(competition_id, approved_only=True):
        condition = " AND pb.approved = TRUE" if approved_only else ""

        query = f"""
            SELECT pb.*, a.firstname, a.lastname, a.npc, a.gender, n.name as npc_name,
                   n.region_code, r.name as region_name,
                   u.username as approved_by_username,
                   g.day, g.time, g.event as game_event
            FROM personal_bests pb
            JOIN athletes a ON pb.sdms = a.sdms
            LEFT JOIN npcs n ON a.npc = n.code
            LEFT JOIN regions r ON n.region_code = r.code
            LEFT JOIN users u ON pb.approved_by = u.id
            LEFT JOIN games g ON pb.competition_id = g.id
            WHERE pb.competition_id = %s{condition}
            ORDER BY a.gender, pb.event, pb.athlete_class,
                     CAST(pb.performance AS FLOAT) DESC
        """
        return execute_query(query, (competition_id,), fetch=True)

    @staticmethod
    def count_pbs_by_athlete():
        query = """
            SELECT pb.sdms, a.firstname, a.lastname, a.npc, a.gender,
                   COUNT(*) as pb_count
            FROM personal_bests pb
            JOIN athletes a ON pb.sdms = a.sdms
            WHERE pb.approved = TRUE
            GROUP BY pb.sdms, a.firstname, a.lastname, a.npc, a.gender
            ORDER BY pb_count DESC, a.lastname, a.firstname
        """
        return execute_query(query, fetch=True)

    @staticmethod
    def count_pbs_by_event():
        query = """
            SELECT pb.event, a.gender, COUNT(*) as pb_count
            FROM personal_bests pb
            JOIN athletes a ON pb.sdms = a.sdms
            WHERE pb.approved = TRUE
            GROUP BY pb.event, a.gender
            ORDER BY pb.event, a.gender
        """
        return execute_query(query, fetch=True)

    @staticmethod
    def count_pbs_by_class():
        query = """
            SELECT pb.athlete_class, a.gender, COUNT(*) as pb_count
            FROM personal_bests pb
            JOIN athletes a ON pb.sdms = a.sdms
            WHERE pb.approved = TRUE
            GROUP BY pb.athlete_class, a.gender
            ORDER BY pb.athlete_class, a.gender
        """
        return execute_query(query, fetch=True)

    @staticmethod
    def update(pb_id, **data):
        set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
        query = f"UPDATE personal_bests SET {set_clause} WHERE id = %s"
        params = list(data.values()) + [pb_id]
        return execute_query(query, params)

    @staticmethod
    def get_by_id(pb_id):
        query = """
            SELECT pb.*, a.firstname, a.lastname, a.npc, a.gender, n.name as npc_name,
                   n.region_code, r.name as region_name,
                   u.username as approved_by_username,
                   g.day, g.time, g.event as game_event, g.id as game_id
            FROM personal_bests pb
            JOIN athletes a ON pb.sdms = a.sdms
            LEFT JOIN npcs n ON a.npc = n.code
            LEFT JOIN regions r ON n.region_code = r.code
            LEFT JOIN users u ON pb.approved_by = u.id
            LEFT JOIN games g ON pb.competition_id = g.id
            WHERE pb.id = %s
        """
        return execute_one(query, (pb_id,))

    @staticmethod
    def search(search_term, approved_only=True):
        condition = " AND pb.approved = TRUE" if approved_only else ""

        query = f"""
            SELECT pb.*, a.firstname, a.lastname, a.npc, a.gender, n.name as npc_name,
                   n.region_code, r.name as region_name,
                   u.username as approved_by_username,
                   g.day, g.time, g.event as game_event, g.id as game_id
            FROM personal_bests pb
            JOIN athletes a ON pb.sdms = a.sdms
            LEFT JOIN npcs n ON a.npc = n.code
            LEFT JOIN regions r ON n.region_code = r.code
            LEFT JOIN users u ON pb.approved_by = u.id
            LEFT JOIN games g ON pb.competition_id = g.id
            WHERE (
                LOWER(a.firstname) LIKE LOWER(%s) OR
                LOWER(a.lastname) LIKE LOWER(%s) OR
                LOWER(pb.event) LIKE LOWER(%s) OR
                LOWER(pb.athlete_class) LIKE LOWER(%s) OR
                LOWER(n.name) LIKE LOWER(%s) OR
                pb.sdms::text LIKE %s
            ){condition}
            ORDER BY pb.record_date DESC, pb.created_at DESC
            LIMIT 50
        """
        search_pattern = f"%{search_term}%"
        params = [search_pattern] * 6
        return execute_query(query, params, fetch=True)

    @staticmethod
    def get_pbs_needing_approval():
        query = """
            SELECT pb.*, a.firstname, a.lastname, a.npc, a.gender, n.name as npc_name,
                   n.region_code, r.name as region_name,
                   g.day, g.time, g.event as game_event, g.id as game_id
            FROM personal_bests pb
            JOIN athletes a ON pb.sdms = a.sdms
            LEFT JOIN npcs n ON a.npc = n.code
            LEFT JOIN regions r ON n.region_code = r.code
            LEFT JOIN games g ON pb.competition_id = g.id
            WHERE pb.approved = FALSE
            ORDER BY pb.created_at DESC
        """
        return execute_query(query, fetch=True)

    @staticmethod
    def approve_multiple(pb_ids, user_id):
        if not pb_ids:
            return 0

        placeholders = ','.join(['%s'] * len(pb_ids))
        query = f"""
            UPDATE personal_bests 
            SET approved = TRUE, approved_by = %s, approved_date = CURRENT_TIMESTAMP 
            WHERE id IN ({placeholders})
        """
        params = [user_id] + list(pb_ids)
        return execute_query(query, params)

    @staticmethod
    def delete_multiple(pb_ids):
        if not pb_ids:
            return 0

        placeholders = ','.join(['%s'] * len(pb_ids))
        query = f"DELETE FROM personal_bests WHERE id IN ({placeholders})"
        return execute_query(query, list(pb_ids))

    @staticmethod
    def check_for_better_performance(sdms, event, athlete_class, performance):
        try:
            performance_float = float(performance)
        except (ValueError, TypeError):
            return False, None

        existing_pb = PersonalBest.check_existing_pb(sdms, event, athlete_class)

        if not existing_pb:
            return True, None  # Would be a new PB

        try:
            existing_performance = float(existing_pb['performance'])
            return performance_float > existing_performance, existing_pb
        except (ValueError, TypeError):
            return False, existing_pb

    @staticmethod
    def get_athlete_progression(sdms, event, athlete_class):
        query = """
            SELECT pb.*, a.gender, g.day, g.time, g.event as game_event
            FROM personal_bests pb
            JOIN athletes a ON pb.sdms = a.sdms
            LEFT JOIN games g ON pb.competition_id = g.id
            WHERE pb.sdms = %s AND pb.event = %s AND pb.athlete_class = %s 
            AND pb.approved = TRUE
            ORDER BY pb.record_date ASC, pb.created_at ASC
        """
        return execute_query(query, (sdms, event, athlete_class), fetch=True)

    @staticmethod
    def get_competition_summary(competition_id):
        query = """
            SELECT 
                COUNT(*) as total_pbs,
                COUNT(CASE WHEN pb.approved = TRUE THEN 1 END) as approved_pbs,
                COUNT(CASE WHEN pb.approved = FALSE THEN 1 END) as pending_pbs,
                COUNT(DISTINCT pb.sdms) as athletes_with_pbs,
                COUNT(DISTINCT pb.event) as events_with_pbs
            FROM personal_bests pb
            WHERE pb.competition_id = %s
        """
        return execute_one(query, (competition_id,))

    @staticmethod
    def get_athlete_best_in_event(sdms, event, approved_only=True):
        condition = " AND pb.approved = TRUE" if approved_only else ""

        query = f"""
            SELECT pb.*, a.gender, g.day, g.time, g.event as game_event, g.id as game_id
            FROM personal_bests pb
            JOIN athletes a ON pb.sdms = a.sdms
            LEFT JOIN games g ON pb.competition_id = g.id
            WHERE pb.sdms = %s AND pb.event = %s{condition}
            ORDER BY CAST(pb.performance AS FLOAT) DESC
            LIMIT 1
        """
        return execute_one(query, (sdms, event))

    @staticmethod
    def get_season_bests(year, approved_only=True):
        condition = " AND pb.approved = TRUE" if approved_only else ""

        query = f"""
            SELECT pb.*, a.firstname, a.lastname, a.npc, a.gender, n.name as npc_name
            FROM personal_bests pb
            JOIN athletes a ON pb.sdms = a.sdms
            LEFT JOIN npcs n ON a.npc = n.code
            WHERE EXTRACT(YEAR FROM pb.record_date) = %s{condition}
            ORDER BY pb.event, pb.athlete_class, a.gender, 
                     CAST(pb.performance AS FLOAT) DESC
        """
        return execute_query(query, (year,), fetch=True)

    # Nouvelle méthode pour récupérer les informations de l'athlète
    @staticmethod
    def get_athlete_info(sdms):
        """Get athlete information including gender, npc, and classes for PB creation"""
        return execute_one("""
            SELECT sdms, firstname, lastname, gender, npc, class 
            FROM athletes WHERE sdms = %s
        """, (sdms,))

    @staticmethod
    def get_athlete_gender(sdms):
        """Get athlete gender by SDMS - utility method"""
        athlete = execute_one("SELECT gender FROM athletes WHERE sdms = %s", (sdms,))
        return athlete['gender'] if athlete else None

    @staticmethod
    def create_with_auto_gender(sdms, event, athlete_class, performance, location, record_date,
                               made_in_competition=False, competition_id=None, approved=False, approved_by=None):
        """Create personal best with automatic gender detection from athlete"""
        athlete = PersonalBest.get_athlete_info(sdms)
        if not athlete:
            raise ValueError(f"Athlete with SDMS {sdms} not found")

        pb_data = {
            'sdms': sdms,
            'event': event,
            'athlete_class': athlete_class,
            'performance': performance,
            'location': location,
            'record_date': record_date,
            'made_in_competition': made_in_competition,
            'approved': approved
        }

        if competition_id:
            pb_data['competition_id'] = competition_id
        if approved_by:
            pb_data['approved_by'] = approved_by

        return PersonalBest.create(**pb_data)

    @staticmethod
    def check_duplicate_pb(sdms, event, athlete_class):
        """Check if a PB already exists for this athlete/event/class combination"""
        return execute_one("""
            SELECT COUNT(*) as count FROM personal_bests 
            WHERE sdms = %s AND event = %s AND athlete_class = %s
        """, (sdms, event, athlete_class))['count'] > 0

    @staticmethod
    def get_pb_rankings_by_event_class(event, athlete_class, gender=None, approved_only=True):
        """Get rankings for a specific event and class, optionally filtered by gender"""
        conditions = ["pb.event = %s", "pb.athlete_class = %s"]
        params = [event, athlete_class]

        if gender:
            conditions.append("a.gender = %s")
            params.append(gender)

        if approved_only:
            conditions.append("pb.approved = TRUE")

        where_clause = " WHERE " + " AND ".join(conditions)

        query = f"""
            SELECT 
                ROW_NUMBER() OVER (ORDER BY CAST(pb.performance AS FLOAT) DESC) as rank,
                pb.*, a.firstname, a.lastname, a.npc, a.gender, n.name as npc_name
            FROM personal_bests pb
            JOIN athletes a ON pb.sdms = a.sdms
            LEFT JOIN npcs n ON a.npc = n.code
            {where_clause}
            ORDER BY CAST(pb.performance AS FLOAT) DESC
        """
        return execute_query(query, params, fetch=True)

    @staticmethod
    def get_athlete_pb_summary(sdms):
        """Get summary of all PBs for an athlete"""
        query = """
            SELECT 
                a.firstname, a.lastname, a.npc, a.gender, a.class,
                COUNT(pb.id) as total_pbs,
                COUNT(CASE WHEN pb.approved = TRUE THEN 1 END) as approved_pbs,
                MIN(pb.record_date) as first_pb_date,
                MAX(pb.record_date) as latest_pb_date
            FROM athletes a
            LEFT JOIN personal_bests pb ON a.sdms = pb.sdms
            WHERE a.sdms = %s
            GROUP BY a.sdms, a.firstname, a.lastname, a.npc, a.gender, a.class
        """
        return execute_one(query, (sdms,))

    @staticmethod
    def bulk_approve_by_competition(competition_id, user_id):
        """Approve all pending PBs from a specific competition"""
        return execute_query("""
            UPDATE personal_bests 
            SET approved = TRUE, approved_by = %s, approved_date = CURRENT_TIMESTAMP 
            WHERE competition_id = %s AND approved = FALSE
        """, (user_id, competition_id))