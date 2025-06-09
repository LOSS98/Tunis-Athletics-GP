from database.db_manager import execute_query, execute_one
class Region:
    @staticmethod
    def get_all():
        return execute_query("SELECT * FROM regions ORDER BY name", fetch=True)
    @staticmethod
    def get_by_code(code):
        return execute_one("SELECT * FROM regions WHERE code = %s", (code,))
    @staticmethod
    def create(code, name, continent):
        return execute_query(
            "INSERT INTO regions (code, name, continent) VALUES (%s, %s, %s)",
            (code, name, continent)
        )
    @staticmethod
    def update(code, **data):
        set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
        query = f"UPDATE regions SET {set_clause} WHERE code = %s"
        params = list(data.values()) + [code]
        return execute_query(query, params)
    @staticmethod
    def delete(code):
        return execute_query("DELETE FROM regions WHERE code = %s", (code,))