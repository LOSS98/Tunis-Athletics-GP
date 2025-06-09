from database.db_manager import execute_one, execute_query
class WorldRecord:
    @staticmethod
    def get_all(approved_only=True):
        query = """
            SELECT wr.*, a.firstname, a.lastname, n.name as npc_name, 
                   n.region_code, r.name as region_name,
                   u.username as approved_by_username
            FROM world_records wr
            LEFT JOIN athletes a ON wr.sdms = a.sdms
            LEFT JOIN npcs n ON wr.npc = n.code
            LEFT JOIN regions r ON n.region_code = r.code
            LEFT JOIN users u ON wr.approved_by = u.id
        """
        if approved_only:
            query += " WHERE wr.approved = TRUE"
        query += " ORDER BY wr.record_date DESC, wr.created_at DESC"
        return execute_query(query, fetch=True)
    @staticmethod
    def get_pending():
        return execute_query("""
            SELECT wr.*, a.firstname, a.lastname, n.name as npc_name, 
                   n.region_code, r.name as region_name
            FROM world_records wr
            LEFT JOIN athletes a ON wr.sdms = a.sdms
            LEFT JOIN npcs n ON wr.npc = n.code
            LEFT JOIN regions r ON n.region_code = r.code
            WHERE wr.approved = FALSE
            ORDER BY wr.created_at DESC
        """, fetch=True)
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
    def check_existing_record(event, class_name, record_type, npc_code=None):
        if record_type == 'WR':
            return execute_one("""
                SELECT * FROM world_records 
                WHERE event = %s AND athlete_class = %s AND record_type = 'WR' AND approved = TRUE
                ORDER BY performance DESC LIMIT 1
            """, (event, class_name))
        elif record_type == 'AR':
            # Pour les records d'aire, on utilise la région du NPC
            return execute_one("""
                SELECT wr.* FROM world_records wr
                LEFT JOIN npcs n ON wr.npc = n.code
                LEFT JOIN npcs n2 ON n2.code = %s
                WHERE wr.event = %s AND wr.athlete_class = %s AND wr.record_type = 'AR' 
                AND n.region_code = n2.region_code AND wr.approved = TRUE
                ORDER BY wr.performance DESC LIMIT 1
            """, (npc_code, event, class_name))
        return None
    @staticmethod
    def delete(record_id):
        return execute_query("DELETE FROM world_records WHERE id = %s", (record_id,))