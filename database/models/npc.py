from database.db_manager import execute_query, execute_one

class NPC:
    @staticmethod
    def get_all():
        query = """
        SELECT n.*, r.name as region_name, r.continent
        FROM npcs n
        LEFT JOIN regions r ON n.region_code = r.code
        ORDER BY n.code
        """
        return execute_query(query, fetch=True)

    @staticmethod
    def get_by_code(code):
        query = """
        SELECT n.*, r.name as region_name, r.continent
        FROM npcs n
        LEFT JOIN regions r ON n.region_code = r.code
        WHERE n.code = %s
        """
        return execute_one(query, (code,))

    @staticmethod
    def create(code, name, region_code=None, flag_file_path=None):
        query = """
        INSERT INTO npcs (code, name, region_code, flag_file_path)
        VALUES (%s, %s, %s, %s)
        RETURNING *
        """
        return execute_query(query, (code, name, region_code, flag_file_path))

    @staticmethod
    def update(code, name, region_code=None, flag_file_path=None):
        query = """
        UPDATE npcs 
        SET name = %s, region_code = %s, flag_file_path = %s
        WHERE code = %s
        """
        return execute_query(query, (name, region_code, flag_file_path, code))

    @staticmethod
    def delete(code):
        return execute_query("DELETE FROM npcs WHERE code = %s", (code,))

    @staticmethod
    def search(query_text):
        query = """
        SELECT n.*, r.name as region_name, r.continent
        FROM npcs n
        LEFT JOIN regions r ON n.region_code = r.code
        WHERE LOWER(n.code) LIKE LOWER(%s) OR LOWER(n.name) LIKE LOWER(%s)
        ORDER BY n.code
        """
        search_term = f"%{query_text}%"
        return execute_query(query, (search_term, search_term), fetch=True)