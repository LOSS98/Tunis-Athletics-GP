from database.db_manager import execute_one, execute_query
class PersonalBest:
    @staticmethod
    def get_all(approved_only=True):
        query = """
            SELECT pb.*, a.firstname, a.lastname, n.name as npc_name,
                   u.username as approved_by_username
            FROM personal_bests pb
            JOIN athletes a ON pb.sdms = a.sdms
            LEFT JOIN npcs n ON pb.npc = n.code
            LEFT JOIN users u ON pb.approved_by = u.id
        """
        if approved_only:
            query += " WHERE pb.approved = TRUE"
        query += " ORDER BY pb.record_date DESC, pb.created_at DESC"
        return execute_query(query, fetch=True)
    @staticmethod
    def get_pending():
        return execute_query("""
            SELECT pb.*, a.firstname, a.lastname, n.name as npc_name
            FROM personal_bests pb
            JOIN athletes a ON pb.sdms = a.sdms
            LEFT JOIN npcs n ON pb.npc = n.code
            WHERE pb.approved = FALSE
            ORDER BY pb.created_at DESC
        """, fetch=True)
    @staticmethod
    def create(**data):
        keys = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        query = f"INSERT INTO personal_bests ({keys}) VALUES ({placeholders}) ON CONFLICT (sdms, event, class) DO UPDATE SET performance = EXCLUDED.performance, location = EXCLUDED.location, record_date = EXCLUDED.record_date, approved = FALSE RETURNING id"
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
    def check_existing_pb(sdms, event, class_name):
        return execute_one("""
            SELECT * FROM personal_bests 
            WHERE sdms = %s AND event = %s AND class = %s AND approved = TRUE
        """, (sdms, event, class_name))
    @staticmethod
    def delete(record_id):
        return execute_query("DELETE FROM personal_bests WHERE id = %s", (record_id,))