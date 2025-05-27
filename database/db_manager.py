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


def clean_params(params):
    """Clean parameters by converting empty strings and 'None' strings to None"""
    if not params:
        return params

    cleaned = []
    for param in params:
        if param == '' or param == 'None' or (isinstance(param, str) and param.strip() == ''):
            cleaned.append(None)
        else:
            cleaned.append(param)
    return tuple(cleaned)


def execute_query(query, params=None, fetch=False):
    """Execute a query and optionally fetch results"""
    try:
        # Clean parameters to handle None/empty values properly
        if params:
            params = clean_params(params)

        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)

                # For INSERT queries with RETURNING clause
                if query.strip().upper().startswith('INSERT') and 'RETURNING' in query.upper():
                    result = cursor.fetchone()
                    conn.commit()
                    print(f"✓ INSERT with RETURNING executed, result: {result}")
                    return result

                # For SELECT queries or when fetch=True
                if fetch or query.strip().upper().startswith('SELECT'):
                    result = cursor.fetchall()
                    return result

                # For other queries (UPDATE, DELETE, etc.)
                conn.commit()
                print(f"✓ Query executed successfully, affected rows: {cursor.rowcount}")
                return cursor.rowcount

    except Exception as e:
        print(f"✗ Database error in execute_query: {e}")
        print(f"Query: {query}")
        print(f"Original params: {params}")
        raise


def execute_one(query, params=None):
    """Execute a query and return one result"""
    try:
        # Clean parameters to handle None/empty values properly
        print(f"Executing query: {query}")
        if params:
            print(f"With params: {params}")
            params = clean_params(params)
            print(f"With params: {params}")

        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchone()
    except Exception as e:
        print(f"✗ Database error in execute_one: {e}")
        print(f"Query: {query}")
        print(f"Original params: {params}")
        raise


def init_db():
    queries = [
        """CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            admin_type VARCHAR(20) DEFAULT 'volunteer',
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
            classes VARCHAR(200) NOT NULL,
            phase VARCHAR(50),
            area VARCHAR(50),
            day INTEGER NOT NULL,
            time TIME NOT NULL,
            nb_athletes INTEGER DEFAULT 8,
            status VARCHAR(20) DEFAULT 'scheduled',
            published BOOLEAN DEFAULT FALSE,
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
        )""",

        """CREATE TABLE IF NOT EXISTS startlist (
            id SERIAL PRIMARY KEY,
            game_id INTEGER NOT NULL,
            athlete_bib INTEGER NOT NULL,
            lane_order INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
            UNIQUE (game_id, athlete_bib)
        )""",

        """CREATE TABLE IF NOT EXISTS attempts (
            id SERIAL PRIMARY KEY,
            result_id INTEGER NOT NULL,
            attempt_number INTEGER NOT NULL,
            value VARCHAR(20),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (result_id) REFERENCES results(id) ON DELETE CASCADE,
            UNIQUE (result_id, attempt_number)
        )""",

        """CREATE TABLE IF NOT EXISTS competition_config (
            id SERIAL PRIMARY KEY,
            setting_key VARCHAR(100) UNIQUE NOT NULL,
            setting_value TEXT NOT NULL,
            setting_type VARCHAR(20) DEFAULT 'string',
            description TEXT,
            updated_by INTEGER,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (updated_by) REFERENCES users(id)
        )""",

        """CREATE TABLE IF NOT EXISTS competition_days (
            id SERIAL PRIMARY KEY,
            day_number INTEGER UNIQUE NOT NULL,
            date_start DATE NOT NULL,
            date_end DATE,
            description VARCHAR(255),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )"""
    ]

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            for query in queries:
                try:
                    cursor.execute(query)
                    print(f"✓ Table created/verified: {query.split()[5] if 'CREATE TABLE' in query else 'unknown'}")
                except Exception as e:
                    print(f"✗ Error creating table: {e}")
                    print(f"Query: {query[:100]}...")
        conn.commit()

    insert_default_config()


def insert_default_config():
    """Insert default configuration if not exists"""
    default_configs = [
        ('classes',
         'T11,T12,T13,T20,T33,T34,T35,T36,T37,T38,T40,T41,T42,T43,T44,T45,T46,T47,T51,T52,T53,T54,T61,T62,T63,T64,F11,F12,F13,F20,F31,F32,F33,F34,F35,F36,F37,F38,F40,F41,F42,F43,F44,F45,F46,F51,F52,F53,F54,F55,F56,F57,F61,F62,F63,F64',
         'list', 'Available classification classes'),
        ('genders', 'Male,Female', 'list', 'Available genders'),
        ('record_types', 'WR,AR,CR,NR,PB,SB', 'list', 'Available record types'),
        ('result_special_values', 'DNS,DNF,DSQ,NM,O,X,-', 'list', 'Special result values'),
        ('field_events', 'Javelin,Shot Put,Discus Throw,Club Throw,Long Jump,High Jump', 'list', 'Field events'),
        ('track_events', '100m,200m,400m,800m,1500m,5000m,4x100m,Universal Relay', 'list', 'Track events'),
        ('current_day', '1', 'integer', 'Current competition day'),
        ('countries_count', '61', 'integer', 'Number of participating countries'),
        ('athletes_count', '529', 'integer', 'Number of registered athletes'),
        ('volunteers_count', '50', 'integer', 'Number of volunteers'),
        ('loc_count', '15', 'integer', 'Number of LOC members'),
        ('officials_count', '80', 'integer', 'Number of officials'),
    ]

    for key, value, setting_type, description in default_configs:
        try:
            existing = execute_one(
                "SELECT id FROM competition_config WHERE setting_key = %s",
                (key,)
            )
            if not existing:
                execute_query(
                    "INSERT INTO competition_config (setting_key, setting_value, setting_type, description) VALUES (%s, %s, %s, %s)",
                    (key, value, setting_type, description)
                )
                print(f"✓ Default config inserted: {key}")
        except Exception as e:
            print(f"✗ Warning: Could not insert config {key}: {e}")

    default_days = [
        (1, '2025-06-12', '2025-06-12', 'Day 1 - Opening Events'),
        (2, '2025-06-13', '2025-06-13', 'Day 2'),
        (3, '2025-06-14', '2025-06-14', 'Day 3'),
        (4, '2025-06-15', '2025-06-15', 'Day 4'),
        (5, '2025-06-16', '2025-06-16', 'Day 5'),
        (6, '2025-06-17', '2025-06-17', 'Day 6'),
        (7, '2025-06-18', '2025-06-18', 'Day 7'),
        (8, '2025-06-19', '2025-06-19', 'Day 8 - Finals'),
    ]

    for day_num, start_date, end_date, desc in default_days:
        try:
            existing = execute_one(
                "SELECT id FROM competition_days WHERE day_number = %s",
                (day_num,)
            )
            if not existing:
                execute_query(
                    "INSERT INTO competition_days (day_number, date_start, date_end, description) VALUES (%s, %s, %s, %s)",
                    (day_num, start_date, end_date, desc)
                )
                print(f"✓ Default day inserted: Day {day_num}")
        except Exception as e:
            print(f"✗ Warning: Could not insert day {day_num}: {e}")


def test_connection():
    """Test database connection"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                print("✓ Database connection successful")
                return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False


def check_tables():
    """Check if all required tables exist"""
    required_tables = [
        'users', 'athletes', 'games', 'results',
        'startlist', 'attempts', 'competition_config', 'competition_days'
    ]

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """)
                existing_tables = [row['table_name'] for row in cursor.fetchall()]

                print("Database tables status:")
                for table in required_tables:
                    if table in existing_tables:
                        print(f"✓ {table}")
                    else:
                        print(f"✗ {table} - MISSING")

                return all(table in existing_tables for table in required_tables)
    except Exception as e:
        print(f"Error checking tables: {e}")
        return False