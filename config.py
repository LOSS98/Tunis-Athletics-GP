import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-in-production')

    DATABASE_URL = os.getenv('DATABASE_URL')
    DB_HOST = DATABASE_URL.split('@')[1].split('/')[0].split(':')[0] if DATABASE_URL else 'localhost'
    DB_USER = DATABASE_URL.split('://')[1].split(':')[0] if DATABASE_URL else 'root'
    DB_PASSWORD = DATABASE_URL.split('://')[1].split(':')[1].split('@')[0] if DATABASE_URL else 'root'
    DB_NAME = DATABASE_URL.split('/')[-1] if DATABASE_URL else 'npc_tunisia_db'

    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'static/uploads')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

    CLASSES = os.getenv('CLASSES', '').split(',')
    GENDERS = os.getenv('GENDERS', 'Male,Female').split(',')
    RECORD_TYPES = os.getenv('RECORD_TYPES', 'WR,AR,CR,NR,PB,SB').split(',')
    RESULT_SPECIAL_VALUES = os.getenv('RESULT_SPECIAL_VALUES', 'DNS,DNF,DSQ,NM,O,X,-').split(',')

    CURRENT_DAY = int(os.getenv('CURRENT_DAY', 1))

    FIELD_EVENTS = os.getenv('FIELD_EVENTS', '').split(',')
    TRACK_EVENTS = os.getenv('TRACK_EVENTS', '').split(',')

    COUNTRIES_COUNT = int(os.getenv('COUNTRIES_COUNT', 61))
    ATHLETES_COUNT = int(os.getenv('ATHLETES_COUNT', 529))
    VOLUNTEERS_COUNT = int(os.getenv('VOLUNTEERS_COUNT', 50))
    LOC_COUNT = int(os.getenv('LOC_COUNT', 10))
    OFFICIALS_COUNT = int(os.getenv('OFFICIALS_COUNT', 80))

    RASA_TABLE_PATH = os.path.join('static', 'rasa_table.xlsx')