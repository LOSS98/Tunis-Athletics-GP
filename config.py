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

    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin2025')