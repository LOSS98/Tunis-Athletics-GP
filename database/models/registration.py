from database.db_manager import execute_query, execute_one


class Registration:
    @staticmethod
    def get_all(**filters):
        query = """
            SELECT r.*, a.firstname, a.lastname, a.npc, a.gender, a.class
            FROM registrations r
            JOIN athletes a ON r.sdms = a.sdms
            WHERE 1=1
        """
        params = []

        if filters:
            for key, value in filters.items():
                if value:
                    if key == 'sdms':
                        query += " AND r.sdms = %s"
                        params.append(value)
                    elif key == 'event_name':
                        query += " AND r.event_name = %s"
                        params.append(value)
                    elif key == 'search':
                        query += """ AND (
                            r.sdms::text LIKE %s OR
                            LOWER(r.event_name) LIKE LOWER(%s) OR
                            LOWER(a.firstname) LIKE LOWER(%s) OR
                            LOWER(a.lastname) LIKE LOWER(%s) OR
                            LOWER(a.npc) LIKE LOWER(%s)
                        )"""
                        search_param = f"%{value}%"
                        params.extend([search_param] * 5)

        query += " ORDER BY r.event_name, a.lastname, a.firstname"
        return execute_query(query, params, fetch=True)

    @staticmethod
    def get_by_athlete(sdms):
        return execute_query(
            "SELECT * FROM registrations WHERE sdms = %s ORDER BY event_name",
            (sdms,), fetch=True
        )

    @staticmethod
    def get_distinct_events():
        events = execute_query(
            "SELECT DISTINCT event_name FROM registrations ORDER BY event_name",
            fetch=True
        )
        return [event['event_name'] for event in events] if events else []

    @staticmethod
    def get_athletes_by_event(event_name):
        return execute_query("""
            SELECT DISTINCT r.sdms
            FROM registrations r
            WHERE r.event_name = %s
        """, (event_name,), fetch=True)

    @staticmethod
    def create(sdms, event_name):
        return execute_query(
            "INSERT INTO registrations (sdms, event_name) VALUES (%s, %s)",
            (sdms, event_name)
        )

    @staticmethod
    def delete(sdms, event_name):
        return execute_query(
            "DELETE FROM registrations WHERE sdms = %s AND event_name = %s",
            (sdms, event_name)
        )

    @staticmethod
    def exists(sdms, event_name):
        result = execute_one(
            "SELECT id FROM registrations WHERE sdms = %s AND event_name = %s",
            (sdms, event_name)
        )
        return result is not None

    @staticmethod
    def count_by_event():
        return execute_query("""
            SELECT event_name, COUNT(*) as athlete_count
            FROM registrations 
            GROUP BY event_name 
            ORDER BY event_name
        """, fetch=True)

    @staticmethod
    def count_by_athlete():
        return execute_query("""
            SELECT sdms, COUNT(*) as event_count
            FROM registrations 
            GROUP BY sdms 
            ORDER BY event_count DESC
        """, fetch=True)