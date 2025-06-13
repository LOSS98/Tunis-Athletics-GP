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
            SELECT pb.*, a.firstname, a.lastname,
                   u.username as approved_by_username
            FROM personal_bests pb
            JOIN athletes a ON pb.sdms = a.sdms
            LEFT JOIN users u ON pb.approved_by = u.id
            {where_clause}
            ORDER BY pb.record_date DESC, pb.created_at DESC
        """
        return execute_query(query, fetch=True)

    @staticmethod
    def get_pending(competition_only=True):
        conditions = ["pb.approved = FALSE"]
        if competition_only:
            conditions.append("pb.made_in_competition = TRUE")

        where_clause = " WHERE " + " AND ".join(conditions)

        query = f"""
            SELECT pb.*, a.firstname, a.lastname
            FROM personal_bests pb
            JOIN athletes a ON pb.sdms = a.sdms
            {where_clause}
            ORDER BY pb.created_at DESC
        """
        return execute_query(query, fetch=True)

    @staticmethod
    def get_pending_for_athlete(sdms, event, athlete_class):
        return execute_one("""
            SELECT * FROM personal_bests 
            WHERE sdms = %s AND event = %s AND athlete_class = %s AND approved = FALSE
            ORDER BY performance DESC LIMIT 1
        """, (sdms, event, athlete_class))

    @staticmethod
    def create(**data):
        keys = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        query = f"INSERT INTO personal_bests ({keys}) VALUES ({placeholders}) ON CONFLICT (sdms, event, athlete_class) DO UPDATE SET performance = EXCLUDED.performance, location = EXCLUDED.location, record_date = EXCLUDED.record_date, approved = FALSE RETURNING id"
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
        result = execute_query("DELETE FROM personal_bests WHERE approved = FALSE")
        return result if result else 0

    @staticmethod
    def check_existing_pb(sdms, event, class_name):
        return execute_one("""
            SELECT * FROM personal_bests 
            WHERE sdms = %s AND event = %s AND athlete_class = %s AND approved = TRUE
        """, (sdms, event, class_name))

    @staticmethod
    def delete(record_id):
        return execute_query("DELETE FROM personal_bests WHERE id = %s", (record_id,))