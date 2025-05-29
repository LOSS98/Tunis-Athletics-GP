from database.db_manager import execute_query, execute_one
from datetime import datetime, date


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
        """Get tags for a configuration key"""
        tags = execute_query(
            "SELECT tag_value FROM config_tags WHERE config_key = %s ORDER BY tag_value",
            (key,),
            fetch=True
        )
        return [tag['tag_value'] for tag in tags] if tags else []

    @staticmethod
    def add_config_tag(key, tag_value):
        """Add a tag to a configuration key"""
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
        """Remove a tag from a configuration key"""
        execute_query(
            "DELETE FROM config_tags WHERE config_key = %s AND tag_value = %s",
            (key, tag_value)
        )

    @staticmethod
    def set_config_tags(key, tags):
        """Set all tags for a configuration key (replaces existing)"""
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
                       'wind_affected_field_events', 'weight_field_events']
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
    def get_countries():
        """Get all countries"""
        return execute_query(
            "SELECT * FROM countries ORDER BY name",
            fetch=True
        )

    @staticmethod
    def get_country_by_code(code):
        """Get country by code"""
        return execute_one(
            "SELECT * FROM countries WHERE code = %s",
            (code,)
        )

    @staticmethod
    def create_country(code, name, continent, flag_available=False):
        """Create a new country"""
        execute_query(
            "INSERT INTO countries (code, name, continent, flag_available) VALUES (%s, %s, %s, %s)",
            (code.upper(), name, continent, flag_available)
        )

    @staticmethod
    def update_country(country_id, code, name, continent, flag_available=False):
        """Update a country"""
        execute_query(
            "UPDATE countries SET code = %s, name = %s, continent = %s, flag_available = %s WHERE id = %s",
            (code.upper(), name, continent, flag_available, country_id)
        )

    @staticmethod
    def delete_country(country_id):
        """Delete a country"""
        execute_query(
            "DELETE FROM countries WHERE id = %s",
            (country_id,)
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