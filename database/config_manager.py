from datetime import datetime, date

from database.db_manager import execute_one, execute_query


class ConfigManager:
    @staticmethod
    def get_config(key, default=None):
        result = execute_one(
            "SELECT setting_value, setting_type FROM competition_config WHERE setting_key = %s",
            (key,)
        )
        if not result:
            return default
        value = result['setting_value']
        setting_type = result['setting_type']
        if setting_type == 'integer':
            try:
                return int(value)
            except ValueError:
                return default
        elif setting_type == 'boolean':
            return value.lower() in ('true', '1', 'yes', 'on')
        else:
            return value

    @staticmethod
    def set_config(key, value, setting_type='string', description=None, user_id=None):
        if setting_type in ['integer', 'boolean']:
            value = str(value)
        existing = execute_one(
            "SELECT id FROM competition_config WHERE setting_key = %s",
            (key,)
        )
        if existing:
            execute_query(
                "UPDATE competition_config SET setting_value = %s, updated_by = %s, updated_at = CURRENT_TIMESTAMP WHERE setting_key = %s",
                (value, user_id, key)
            )
        else:
            execute_query(
                "INSERT INTO competition_config (setting_key, setting_value, setting_type, description, updated_by) VALUES (%s, %s, %s, %s, %s)",
                (key, value, setting_type, description, user_id)
            )

    @staticmethod
    def get_config_tags(key):
        tags = execute_query(
            "SELECT tag_value FROM config_tags WHERE config_key = %s ORDER BY tag_value",
            (key,),
            fetch=True
        )
        return [tag['tag_value'] for tag in tags] if tags else []

    @staticmethod
    def add_config_tag(key, tag_value):
        try:
            execute_query(
                "INSERT INTO config_tags (config_key, tag_value) VALUES (%s, %s)",
                (key, tag_value)
            )
            return True
        except:
            return False

    @staticmethod
    def remove_config_tag(key, tag_value):
        execute_query(
            "DELETE FROM config_tags WHERE config_key = %s AND tag_value = %s",
            (key, tag_value)
        )

    @staticmethod
    def set_config_tags(key, tags):
        execute_query(
            "DELETE FROM config_tags WHERE config_key = %s",
            (key,)
        )
        for tag in tags:
            if tag.strip():
                execute_query(
                    "INSERT INTO config_tags (config_key, tag_value) VALUES (%s, %s)",
                    (key, tag.strip())
                )

    @staticmethod
    def get_all_config():
        configs = execute_query(
            "SELECT * FROM competition_config ORDER BY setting_key",
            fetch=True
        )
        result = {}
        for config in configs:
            key = config['setting_key']
            value = config['setting_value']
            setting_type = config['setting_type']
            if setting_type == 'integer':
                try:
                    result[key] = int(value)
                except ValueError:
                    result[key] = 0
            elif setting_type == 'boolean':
                result[key] = value.lower() in ('true', '1', 'yes', 'on')
            else:
                result[key] = value

        tag_configs = ['classes', 'record_types', 'result_special_values', 'field_events', 'track_events',
                       'wind_affected_field_events', 'weight_field_events', 'guide_classes']
        for key in tag_configs:
            result[key] = ConfigManager.get_config_tags(key)
        return result

    @staticmethod
    def get_competition_days():
        return execute_query(
            "SELECT * FROM competition_days ORDER BY day_number",
            fetch=True
        )

    @staticmethod
    def get_current_competition_day():
        today = date.today()
        day = execute_one(
            "SELECT day_number FROM competition_days WHERE %s BETWEEN date_start AND COALESCE(date_end, date_start) AND is_active = true",
            (today,)
        )
        if day:
            return day['day_number']
        return ConfigManager.get_config('current_day', 1)

    @staticmethod
    def set_competition_day(day_number, date_start, date_end=None, description=None):
        existing = execute_one(
            "SELECT id FROM competition_days WHERE day_number = %s",
            (day_number,)
        )
        if existing:
            execute_query(
                "UPDATE competition_days SET date_start = %s, date_end = %s, description = %s WHERE day_number = %s",
                (date_start, date_end, description, day_number)
            )
        else:
            execute_query(
                "INSERT INTO competition_days (day_number, date_start, date_end, description) VALUES (%s, %s, %s, %s)",
                (day_number, date_start, date_end, description)
            )

    @staticmethod
    def delete_competition_day(day_number):
        execute_query(
            "DELETE FROM competition_days WHERE day_number = %s",
            (day_number,)
        )

    @staticmethod
    def get_npcs():
        npcs = execute_query(
            "SELECT * FROM npcs ORDER BY name",
            fetch=True
        )
        from utils.helpers import check_flag_exists, get_flag_url
        for npc in npcs:
            npc['flag_exists'] = check_flag_exists(npc['code'], npc.get('flag_file_path'))
            npc['flag_url'] = get_flag_url(npc['code'], npc.get('flag_file_path'))
        return npcs

    @staticmethod
    def get_npc_by_code(code):
        npc = execute_one(
            "SELECT * FROM npcs WHERE code = %s",
            (code,)
        )
        if npc:
            from utils.helpers import check_flag_exists, get_flag_url
            npc['flag_exists'] = check_flag_exists(npc['code'], npc.get('flag_file_path'))
            npc['flag_url'] = get_flag_url(npc['code'], npc.get('flag_file_path'))
        return npc

    @staticmethod
    def create_npc(code, name, region_code=None, flag_file_path=None):
        execute_query(
            "INSERT INTO npcs (code, name, region_code, flag_file_path) VALUES (%s, %s, %s, %s)",
            (code.upper(), name, region_code, flag_file_path)
        )

    @staticmethod
    def update_npc(npc_code, code, name, region_code=None, flag_file_path=None):
        execute_query(
            "UPDATE npcs SET code = %s, name = %s, region_code = %s, flag_file_path = %s WHERE code = %s",
            (code.upper(), name, region_code, flag_file_path, npc_code)
        )

    @staticmethod
    def delete_npc(npc_code):
        execute_query(
            "DELETE FROM npcs WHERE code = %s",
            (npc_code,)
        )

    @staticmethod
    def get_record_types_with_details():
        return execute_query(
            "SELECT * FROM record_types ORDER BY abbreviation",
            fetch=True
        )

    @staticmethod
    def create_record_type(abbreviation, full_name, scope_type, scope_values=None, description=None):
        execute_query(
            "INSERT INTO record_types (abbreviation, full_name, scope_type, scope_values, description) VALUES (%s, %s, %s, %s, %s)",
            (abbreviation, full_name, scope_type, scope_values, description)
        )

    @staticmethod
    def update_record_type(record_type_id, abbreviation, full_name, scope_type, scope_values=None, description=None):
        execute_query(
            "UPDATE record_types SET abbreviation = %s, full_name = %s, scope_type = %s, scope_values = %s, description = %s WHERE id = %s",
            (abbreviation, full_name, scope_type, scope_values, description, record_type_id)
        )

    @staticmethod
    def delete_record_type(record_type_id):
        execute_query(
            "DELETE FROM record_types WHERE id = %s",
            (record_type_id,)
        )

    @staticmethod
    def get_record_type_by_abbreviation(abbreviation):
        return execute_one(
            "SELECT * FROM record_types WHERE abbreviation = %s",
            (abbreviation,)
        )


_config_cache = {}
_cache_timestamp = None


def get_cached_config(key, default=None, cache_duration=300):
    global _config_cache, _cache_timestamp
    now = datetime.now()
    if _cache_timestamp is None or (now - _cache_timestamp).seconds > cache_duration:
        _config_cache = ConfigManager.get_all_config()
        _cache_timestamp = now
    return _config_cache.get(key, default)


def clear_config_cache():
    global _config_cache, _cache_timestamp
    _config_cache = {}
    _cache_timestamp = None