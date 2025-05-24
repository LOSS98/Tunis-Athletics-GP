import psycopg2
from psycopg2.extras import RealDictCursor
from config import Config
from contextlib import contextmanager


@contextmanager
def get_db_connection():
    connection = psycopg2.connect(
        host=Config.DB_HOST,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        cursor_factory=RealDictCursor
    )
    try:
        yield connection
    finally:
        connection.close()


def execute_query(query, params=None, fetch=False):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            if fetch:
                return cursor.fetchall()
            conn.commit()
            if query.strip().upper().startswith('INSERT'):
                return cursor.lastrowid if hasattr(cursor, 'lastrowid') else None
            return None


def execute_one(query, params=None):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchone()


def init_db():
    queries = [
        """CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",

        """CREATE TABLE IF NOT EXISTS athletes (
            id SERIAL PRIMARY KEY,
            bib INTEGER UNIQUE NOT NULL,
            firstname VARCHAR(100) NOT NULL,
            lastname VARCHAR(100) NOT NULL,
            country VARCHAR(3) NOT NULL,
            gender VARCHAR(10) NOT NULL,
            class VARCHAR(10) NOT NULL,
            photo VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",

        """CREATE TABLE IF NOT EXISTS games (
            id SERIAL PRIMARY KEY,
            event VARCHAR(100) NOT NULL,
            gender VARCHAR(10) NOT NULL,
            classes VARCHAR(50) NOT NULL,
            phase VARCHAR(50),
            area VARCHAR(50),
            day INTEGER NOT NULL,
            time TIME NOT NULL,
            duration INTEGER DEFAULT 60,
            nb_athletes INTEGER DEFAULT 8,
            status VARCHAR(20) DEFAULT 'scheduled',
            start_file VARCHAR(255),
            result_file VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",

        """CREATE TABLE IF NOT EXISTS results (
            id SERIAL PRIMARY KEY,
            game_id INTEGER NOT NULL,
            athlete_bib INTEGER NOT NULL,
            rank VARCHAR(10),
            value VARCHAR(20) NOT NULL,
            record VARCHAR(10),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
            UNIQUE (game_id, athlete_bib)
        )"""
    ]

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            for query in queries:
                cursor.execute(query)
        conn.commit()