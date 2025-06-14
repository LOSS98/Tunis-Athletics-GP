import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    DATABASE_URL = os.getenv('DATABASE_URL')
    if DATABASE_URL:
        DB_HOST = DATABASE_URL.split('@')[1].split('/')[0].split(':')[0]
        DB_USER = DATABASE_URL.split('://')[1].split(':')[0]
        DB_PASSWORD = DATABASE_URL.split('://')[1].split(':')[1].split('@')[0]
        DB_NAME = DATABASE_URL.split('/')[-1]
        DB_PORT = os.getenv('DATABASE_PORT', '5432')
    else:
        DB_HOST = 'localhost'
        DB_USER = 'root'
        DB_PASSWORD = 'root'
        DB_NAME = 'npc_tunisia_db'
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'static/uploads')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin2025')
    RAZA_TABLE_PATH = os.path.join('static', 'raza_table_tunis_gp_25.xlsx')

    @staticmethod
    def get_classes():
        try:
            from database.config_manager import ConfigManager
            return ConfigManager.get_config_tags('classes')
        except (ImportError, Exception):
            track_classes = [
                'T11', 'T12', 'T13', 'T20', 'T32', 'T33', 'T34', 'T35', 'T36', 'T37', 'T38',
                'T40', 'T41', 'T42', 'T43', 'T44', 'T45', 'T46', 'T47', 'T51', 'T52', 'T53', 'T54',
                'T61', 'T62', 'T63', 'T64', 'T71', 'T72'
            ]
            field_classes = [
                'F11', 'F12', 'F13', 'F20', 'F31', 'F32', 'F33', 'F34', 'F35', 'F36', 'F37', 'F38',
                'F40', 'F41', 'F42', 'F43', 'F44', 'F45', 'F46', 'F51', 'F52', 'F53', 'F54', 'F55', 'F56', 'F57',
                'F61', 'F62', 'F63', 'F64'
            ]
            return sorted(track_classes + field_classes)

    @staticmethod
    def get_r1_qualifying_classes():
        try:
            from database.config_manager import ConfigManager
            return ConfigManager.get_config_tags('r1_qualifying_classes')
        except (ImportError, Exception):
            return ['F32', 'F33', 'F34', 'F35', 'F36', 'F37', 'F38', 'F40', 'F41', 'F42', 'F43', 'F44', 'F45', 'F46', 'F51', 'F52', 'F53', 'F54', 'F55', 'F56', 'F57', 'F61', 'F62', 'F63', 'F64']

    @staticmethod
    def get_record_types():
        try:
            from database.config_manager import ConfigManager
            return ConfigManager.get_config_tags('record_types')
        except (ImportError, Exception):
            return ['WR', 'AR', 'ER', 'CR', 'NR', 'PB', 'SB', 'WL', 'AL']

    @staticmethod
    def get_result_special_values():
        try:
            from database.config_manager import ConfigManager
            return ConfigManager.get_config_tags('result_special_values')
        except (ImportError, Exception):
            return ['DNS', 'DNF', 'NM', 'NH', 'O', 'X', '-', 'DQ']

    @staticmethod
    def get_field_events():
        try:
            from database.config_manager import ConfigManager
            return ConfigManager.get_config_tags('field_events')
        except (ImportError, Exception):
            return ['Shot Put', 'Discus Throw', 'Javelin Throw', 'Hammer Throw', 'Club Throw', 'Weight Throw']

    @staticmethod
    def get_track_events():
        try:
            from database.config_manager import ConfigManager
            return ConfigManager.get_config_tags('track_events')
        except (ImportError, Exception):
            return ['100m', '200m', '400m', '800m', '1500m', '5000m', '10000m', 'Marathon',
                    '4x100m Relay', '4x400m Relay', 'Universal Relay', 'Long Jump', 'High Jump',
                    'Triple Jump', 'Pole Vault']

    @staticmethod
    def get_wind_affected_field_events():
        try:
            from database.config_manager import ConfigManager
            return ConfigManager.get_config_tags('wind_affected_field_events')
        except (ImportError, Exception):
            return ['Long Jump', 'Triple Jump', '100m', '200m']

    @staticmethod
    def get_guide_classes():
        try:
            from database.config_manager import ConfigManager
            return ConfigManager.get_config_tags('guide_classes')
        except (ImportError, Exception):
            return ['T11', 'T12']

    @staticmethod
    def get_current_day():
        try:
            from database.config_manager import ConfigManager
            day = ConfigManager.get_current_competition_day()
            return int(day) if day is not None else 1
        except (ImportError, Exception):
            try:
                return int(os.getenv('CURRENT_DAY', 1))
            except (ValueError, TypeError):
                return 1

    @staticmethod
    def get_npcs_count():
        try:
            from database.config_manager import ConfigManager
            return ConfigManager.get_config('npcs_count', 61)
        except (ImportError, Exception):
            return int(os.getenv('NPCS_COUNT', 61))

    @staticmethod
    def get_athletes_count():
        try:
            from database.config_manager import ConfigManager
            return ConfigManager.get_config('athletes_count', 529)
        except (ImportError, Exception):
            return int(os.getenv('ATHLETES_COUNT', 529))

    @staticmethod
    def get_volunteers_count():
        try:
            from database.config_manager import ConfigManager
            return ConfigManager.get_config('volunteers_count', 50)
        except (ImportError, Exception):
            return int(os.getenv('VOLUNTEERS_COUNT', 50))

    @staticmethod
    def get_loc_count():
        try:
            from database.config_manager import ConfigManager
            return ConfigManager.get_config('loc_count', 15)
        except (ImportError, Exception):
            return int(os.getenv('LOC_COUNT', 15))

    @staticmethod
    def get_officials_count():
        try:
            from database.config_manager import ConfigManager
            return ConfigManager.get_config('officials_count', 80)
        except (ImportError, Exception):
            return int(os.getenv('OFFICIALS_COUNT', 80))

    @staticmethod
    def get_npcs():
        try:
            from database.config_manager import ConfigManager
            return ConfigManager.get_npcs()
        except (ImportError, Exception):
            return []

    @staticmethod
    def format_time(time_value, for_public=False):
        if not time_value or time_value in Config.get_result_special_values():
            return time_value
        try:
            time_str = str(time_value)
            if ':' in time_str:
                parts = time_str.split(':')
                minutes = int(parts[0])
                seconds = float(parts[1])
            else:
                time_float = float(time_str)
                minutes = int(time_float // 60)
                seconds = time_float % 60
            if for_public:
                return f"{minutes:02d}:{seconds:05.2f}"
            else:
                return f"{minutes:02d}:{seconds:06.3f}"
        except:
            return time_value

    @staticmethod
    def format_distance(distance_value):
        if not distance_value or str(distance_value) in Config.get_result_special_values():
            return distance_value
        try:
            return f"{float(distance_value):.2f}"
        except:
            return distance_value

    @staticmethod
    def format_wind(wind_value):
        if not wind_value:
            return "0.00"
        try:
            if float(wind_value) > 0:
                return f"+{float(wind_value):.2f}"
            elif float(wind_value) < 0:
                return f"{float(wind_value):.2f}"
            else:
                return f"{float(wind_value):.2f}"
        except:
            return str(wind_value)

    @staticmethod
    def format_weight(weight_value):
        if not weight_value:
            return ""
        try:
            weight_float = float(weight_value)
            if weight_float < 1:
                return f"{int(weight_float * 1000)} gr"
            else:
                return f"{weight_float:.3f} kg"
        except:
            return str(weight_value)

    @staticmethod
    def get_genders():
        return ['Male', 'Female']

    @staticmethod
    def get_weight_field_events():
        try:
            from database.config_manager import ConfigManager
            return ConfigManager.get_config_tags('weight_field_events')
        except (ImportError, Exception):
            return ['Shot Put', 'Discus Throw', 'Javelin Throw', 'Hammer Throw', 'Club Throw', 'Weight Throw']

    @staticmethod
    def format_gender_for_display(gender):
        if gender == 'Male':
            return "Men's"
        elif gender == 'Female':
            return "Women's"
        else:
            return gender.replace('Male', "Men's").replace('Female', "Women's")

    @property
    def CLASSES(self):
        return self.get_classes()

    @property
    def R1_QUALIFYING_CLASSES(self):
        return self.get_r1_qualifying_classes()

    @property
    def GENDERS(self):
        return self.get_genders()

    @property
    def RECORD_TYPES(self):
        return self.get_record_types()

    @property
    def RESULT_SPECIAL_VALUES(self):
        return self.get_result_special_values()

    @property
    def FIELD_EVENTS(self):
        return self.get_field_events()

    @property
    def TRACK_EVENTS(self):
        return self.get_track_events()

    @property
    def WIND_AFFECTED_FIELD_EVENTS(self):
        return self.get_wind_affected_field_events()

    @property
    def WEIGHT_FIELD_EVENTS(self):
        return self.get_weight_field_events()

    @property
    def CURRENT_DAY(self):
        return self.get_current_day()

    @property
    def NPCS_COUNT(self):
        return self.get_npcs_count()

    @property
    def ATHLETES_COUNT(self):
        return self.get_athletes_count()

    @property
    def VOLUNTEERS_COUNT(self):
        return self.get_volunteers_count()

    @property
    def LOC_COUNT(self):
        return self.get_loc_count()

    @property
    def OFFICIALS_COUNT(self):
        return self.get_officials_count()

config = Config()