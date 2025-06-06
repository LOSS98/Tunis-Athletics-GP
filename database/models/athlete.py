from database.db_manager import execute_query, execute_one


class Athlete:
    @staticmethod
    def get_all(**filters):
        query = """
            SELECT a.*, r.name as region_name, n.name as npc_name 
            FROM athletes a
            LEFT JOIN regions r ON a.region_code = r.code
            LEFT JOIN npcs n ON a.npc = n.code
            WHERE 1=1
        """
        params = []

        if filters:
            for key, value in filters.items():
                if value:
                    if key == 'class':
                        query += " AND a.class LIKE %s"
                        params.append(f"%{value}%")
                    else:
                        query += f" AND a.{key} = %s"
                        params.append(value)

        query += " ORDER BY a.sdms"
        return execute_query(query, params, fetch=True)

    @staticmethod
    def get_by_sdms(sdms):
        athlete = execute_one("""
            SELECT a.*, r.name as region_name, n.name as npc_name 
            FROM athletes a
            LEFT JOIN regions r ON a.region_code = r.code
            LEFT JOIN npcs n ON a.npc = n.code
            WHERE a.sdms = %s
        """, (sdms,))

        if athlete and athlete['class']:
            athlete['classes_list'] = [c.strip() for c in athlete['class'].split(',')]

        return athlete

    @staticmethod
    def search(query, guides_only=False, allowed_classes=None):
        search_query = """
            SELECT a.*, r.name as region_name, n.name as npc_name 
            FROM athletes a
            LEFT JOIN regions r ON a.region_code = r.code
            LEFT JOIN npcs n ON a.npc = n.code
            WHERE (LOWER(a.firstname) LIKE LOWER(%s)
                   OR LOWER(a.lastname) LIKE LOWER(%s)
                   OR LOWER(a.npc) LIKE LOWER(%s)
                   OR a.sdms::text LIKE %s)
        """
        params = [f"%{query}%"] * 4

        if guides_only:
            search_query += " AND a.is_guide = TRUE"

        if allowed_classes:
            class_conditions = []
            for class_name in allowed_classes:
                class_conditions.append("a.class LIKE %s")
                params.append(f"%{class_name}%")
            if class_conditions:
                search_query += f" AND ({' OR '.join(class_conditions)})"

        search_query += " ORDER BY a.sdms"

        athletes = execute_query(search_query, params, fetch=True)

        for athlete in athletes:
            if athlete['class']:
                athlete['classes_list'] = [c.strip() for c in athlete['class'].split(',')]
            else:
                athlete['classes_list'] = []

        return athletes

    @staticmethod
    def has_class(athlete, target_class):
        if not athlete or not athlete.get('class'):
            return False
        classes = [c.strip() for c in athlete['class'].split(',')]
        return target_class in classes

    @staticmethod
    def get_primary_class(athlete):
        if not athlete or not athlete.get('class'):
            return None
        classes = [c.strip() for c in athlete['class'].split(',')]
        return classes[0] if classes else None

    @staticmethod
    def create(**data):
        keys = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        query = f"INSERT INTO athletes ({keys}) VALUES ({placeholders}) RETURNING sdms"
        result = execute_query(query, list(data.values()))
        return result['sdms'] if result else None

    @staticmethod
    def update(sdms, **data):
        set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
        query = f"UPDATE athletes SET {set_clause} WHERE sdms = %s"
        params = list(data.values()) + [sdms]
        return execute_query(query, params)

    @staticmethod
    def delete(sdms):
        return execute_query("DELETE FROM athletes WHERE sdms = %s", (sdms,))