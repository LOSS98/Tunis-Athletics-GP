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
    else:
        DB_HOST = 'localhost'
        DB_USER = 'root'
        DB_PASSWORD = 'root'
        DB_NAME = 'npc_tunisia_db'

    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'static/uploads')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

    # Athletics Configuration
    CLASSES = ['T11', 'T12', 'T13', 'T20', 'T33', 'T34', 'T35', 'T36', 'T37', 'T38', 'T40', 'T41', 'T42', 'T43', 'T44',
               'T45', 'T46', 'T47', 'T51', 'T52', 'T53', 'T54', 'T61', 'T62', 'T63', 'T64', 'F11', 'F12', 'F13', 'F20',
               'F31', 'F32', 'F33', 'F34', 'F35', 'F36', 'F37', 'F38', 'F40', 'F41', 'F42', 'F43', 'F44', 'F45', 'F46',
               'F51', 'F52', 'F53', 'F54', 'F55', 'F56', 'F57', 'F61', 'F62', 'F63', 'F64']

    GENDERS = ['Male', 'Female']
    RECORD_TYPES = ['WR', 'AR', 'CR', 'NR', 'PB', 'SB']
    RESULT_SPECIAL_VALUES = ['DNS', 'DNF', 'DSQ', 'NM', 'O', 'X', '-']

    CURRENT_DAY = int(os.getenv('CURRENT_DAY', 1))

    # Field Events (6 attempts, results in meters)
    FIELD_EVENTS = ['Javelin', 'Shot Put', 'Discus Throw', 'Club Throw', 'Long Jump', 'High Jump']

    # Track Events (time-based results)
    TRACK_EVENTS = ['100m', '200m', '400m', '800m', '1500m', '5000m', '4x100m', 'Universal Relay']

    # Statistics
    COUNTRIES_COUNT = int(os.getenv('COUNTRIES_COUNT', 61))
    ATHLETES_COUNT = int(os.getenv('ATHLETES_COUNT', 529))
    VOLUNTEERS_COUNT = int(os.getenv('VOLUNTEERS_COUNT', 50))
    LOC_COUNT = int(os.getenv('LOC_COUNT', 15))
    OFFICIALS_COUNT = int(os.getenv('OFFICIALS_COUNT', 80))

    # Admin Configuration
    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin2025')

    # RAZA Table Path
    RAZA_TABLE_PATH = os.path.join('static', 'raza_table_tunis_gp_25.xlsx')