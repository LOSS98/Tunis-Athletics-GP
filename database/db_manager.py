import psycopg2
from psycopg2.extras import RealDictCursor
from config import Config
from contextlib import contextmanager
@contextmanager
def get_db_connection():
    connection = None
    try:
        connection = psycopg2.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            cursor_factory=RealDictCursor
        )
        yield connection
    except psycopg2.Error as e:
        print(f"Database connection error: {e}")
        if connection:
            connection.rollback()
        raise
    finally:
        if connection:
            connection.close()
def clean_params(params):
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
    try:
        if params:
            params = clean_params(params)
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                if query.strip().upper().startswith('INSERT') and 'RETURNING' in query.upper():
                    result = cursor.fetchone()
                    conn.commit()
                    print(f"✓ INSERT with RETURNING executed, result: {result}")
                    return result
                if fetch or query.strip().upper().startswith('SELECT'):
                    result = cursor.fetchall()
                    return result
                conn.commit()
                print(f"✓ Query executed successfully, affected rows: {cursor.rowcount}")
                return cursor.rowcount
    except psycopg2.Error as e:
        print(f"✗ Database error in execute_query: {e}")
        print(f"Query: {query}")
        print(f"Original params: {params}")
        raise
    except Exception as e:
        print(f"✗ Unexpected error in execute_query: {e}")
        print(f"Query: {query}")
        print(f"Original params: {params}")
        raise
def execute_one(query, params=None):
    try:
        if params:
            params = clean_params(params)
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchone()
    except psycopg2.Error as e:
        print(f"✗ Database error in execute_one: {e}")
        print(f"Query: {query}")
        print(f"Original params: {params}")
        raise
    except Exception as e:
        print(f"✗ Unexpected error in execute_one: {e}")
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
        """CREATE TABLE IF NOT EXISTS regions (
            code VARCHAR(10) PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            continent VARCHAR(50) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS npcs (
            code VARCHAR(3) PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            region_code VARCHAR(10),
            flag_file_path VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (region_code) REFERENCES regions(code) ON DELETE SET NULL
        )""",
        """CREATE TABLE IF NOT EXISTS record_types (
            id SERIAL PRIMARY KEY,
            abbreviation VARCHAR(10) UNIQUE NOT NULL,
            full_name VARCHAR(100) NOT NULL,
            scope_type VARCHAR(20) NOT NULL,
            scope_values TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS athletes (
            sdms INTEGER PRIMARY KEY,
            firstname VARCHAR(100) NOT NULL,
            lastname VARCHAR(100) NOT NULL,
            npc VARCHAR(3) NOT NULL,
            gender VARCHAR(10) NOT NULL,
            class VARCHAR(10) NOT NULL,
            date_of_birth DATE,
            photo VARCHAR(255),
            is_guide BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (npc) REFERENCES npcs(code) ON DELETE RESTRICT
        )""",
        """CREATE TABLE IF NOT EXISTS games (
            id SERIAL PRIMARY KEY,
            event VARCHAR(100) NOT NULL,
            genders TEXT NOT NULL,
            classes TEXT NOT NULL,
            phase VARCHAR(50),
            area VARCHAR(50),
            day INTEGER NOT NULL,
            time TIME NOT NULL,
            nb_athletes INTEGER DEFAULT 8,
            status VARCHAR(20) DEFAULT 'scheduled',
            published BOOLEAN DEFAULT FALSE,
            official BOOLEAN DEFAULT FALSE,
            official_date TIMESTAMP,
            official_by INTEGER,
            start_file VARCHAR(255),
            result_file VARCHAR(255),
            wind_velocity double precision DEFAULT 0.0,
            wpa_points BOOLEAN DEFAULT FALSE,
            generated_startlist_pdf VARCHAR(255),
            generated_results_pdf VARCHAR(255),
            manual_startlist_pdf VARCHAR(255),
            manual_results_pdf VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS results (
            id SERIAL PRIMARY KEY,
            game_id INTEGER NOT NULL,
            athlete_sdms INTEGER NOT NULL,
            guide_sdms INTEGER,
            rank VARCHAR(10),
            value VARCHAR(20) NOT NULL,
            raza_score INTEGER,
            raza_score_precise double precision,
            wind_velocity double precision,
            weight double precision,
            record VARCHAR(10),
            final_order INTEGER,
            best_attempt VARCHAR(20),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
            FOREIGN KEY (athlete_sdms) REFERENCES athletes(sdms) ON DELETE CASCADE,
            FOREIGN KEY (guide_sdms) REFERENCES athletes(sdms) ON DELETE SET NULL,
            UNIQUE (game_id, athlete_sdms)
        )""",
        """CREATE TABLE IF NOT EXISTS startlist (
            id SERIAL PRIMARY KEY,
            game_id INTEGER NOT NULL,
            athlete_sdms INTEGER NOT NULL,
            guide_sdms INTEGER,
            lane_order INTEGER,
            final_order INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
            FOREIGN KEY (athlete_sdms) REFERENCES athletes(sdms) ON DELETE CASCADE,
            FOREIGN KEY (guide_sdms) REFERENCES athletes(sdms) ON DELETE SET NULL,
            UNIQUE (game_id, athlete_sdms)
        )""",
        """CREATE TABLE IF NOT EXISTS attempts (
            id SERIAL PRIMARY KEY,
            result_id INTEGER NOT NULL,
            attempt_number INTEGER NOT NULL,
            value VARCHAR(20),
            raza_score INTEGER,
            raza_score_precise double precision,
            wind_velocity double precision,
            height double precision,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (result_id) REFERENCES results(id) ON DELETE CASCADE,
            UNIQUE (result_id, attempt_number)
        )""",
        """CREATE TABLE IF NOT EXISTS world_records (
            id SERIAL PRIMARY KEY,
            sdms INTEGER,
            event VARCHAR(100) NOT NULL,
            athlete_class VARCHAR(10) NOT NULL,
            performance VARCHAR(20) NOT NULL,
            location VARCHAR(100) NOT NULL,
            npc VARCHAR(3),
            region_code VARCHAR(10),
            record_date DATE NOT NULL,
            record_type VARCHAR(10) NOT NULL,
            approved BOOLEAN DEFAULT FALSE,
            approved_by INTEGER,
            approved_date TIMESTAMP,
            made_in_competition BOOLEAN DEFAULT FALSE,
            competition_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sdms) REFERENCES athletes(sdms) ON DELETE SET NULL,
            FOREIGN KEY (npc) REFERENCES npcs(code) ON DELETE SET NULL,
            FOREIGN KEY (region_code) REFERENCES regions(code) ON DELETE SET NULL,
            FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY (competition_id) REFERENCES games(id) ON DELETE SET NULL
        )""",
        """CREATE TABLE IF NOT EXISTS personal_bests (
            id SERIAL PRIMARY KEY,
            sdms INTEGER NOT NULL,
            event VARCHAR(100) NOT NULL,
            athlete_class VARCHAR(10) NOT NULL,
            performance VARCHAR(20) NOT NULL,
            location VARCHAR(100) NOT NULL,
            record_date DATE NOT NULL,
            approved BOOLEAN DEFAULT FALSE,
            approved_by INTEGER,
            approved_date TIMESTAMP,
            made_in_competition BOOLEAN DEFAULT FALSE,
            competition_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sdms) REFERENCES athletes(sdms) ON DELETE CASCADE,
            FOREIGN KEY (npc) REFERENCES npcs(code) ON DELETE RESTRICT,
            FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY (competition_id) REFERENCES games(id) ON DELETE SET NULL,
            UNIQUE (sdms, event, athlete_class)
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
        )""",
        """CREATE TABLE IF NOT EXISTS config_tags (
            id SERIAL PRIMARY KEY,
            config_key VARCHAR(100) NOT NULL,
            tag_value VARCHAR(100) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (config_key, tag_value)
        )""",
        """CREATE TABLE IF NOT EXISTS registrations (
                    id SERIAL PRIMARY KEY,
                    sdms INTEGER NOT NULL,
                    event_name VARCHAR(100) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (sdms) REFERENCES athletes(sdms) ON DELETE CASCADE,
                    UNIQUE (sdms, event_name)
                )""",
        """CREATE TABLE IF NOT EXISTS medals (
            id SERIAL PRIMARY KEY,
            npc VARCHAR(3) NOT NULL UNIQUE,
            gold INTEGER DEFAULT 0,
            silver INTEGER DEFAULT 0,
            bronze INTEGER DEFAULT 0,
            total INTEGER DEFAULT 0,
            manual_override BOOLEAN DEFAULT FALSE,
            last_calculated TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (npc) REFERENCES npcs(code) ON DELETE CASCADE
        )""",
        """CREATE TABLE IF NOT EXISTS heat_groups (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    event VARCHAR(100) NOT NULL,
                    genders TEXT NOT NULL,
                    classes TEXT NOT NULL,
                    day INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )"""
    ]
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                for query in queries:
                    try:
                        cursor.execute(query)
                        table_name = query.split()[5] if 'CREATE TABLE' in query else 'unknown'
                        print(f"✓ Table created/verified: {table_name}")
                    except psycopg2.Error as e:
                        print(f"✗ Error creating table: {e}")
                        print(f"Query: {query[:100]}...")
                        raise
            conn.commit()
            print("✓ Database initialization completed successfully")
        insert_default_config()
        insert_default_regions()
    except Exception as e:
        print(f"✗ Critical error during database initialization: {e}")
        raise
def insert_default_regions():
    default_regions = [
        ('AFR', 'Africa', 'Africa'),
        ('AMR', 'Americas', 'Americas'),
        ('ASR', 'Asia', 'Asia'),
        ('EUR', 'Europe', 'Europe'),
        ('ACR', 'Oceania', 'Oceania'),
    ]
    for code, name, continent in default_regions:
        try:
            existing = execute_one(
                "SELECT code FROM regions WHERE code = %s",
                (code,)
            )
            if not existing:
                execute_query(
                    "INSERT INTO regions (code, name, continent) VALUES (%s, %s, %s)",
                    (code, name, continent)
                )
        except Exception as e:
            print(f"✗ Warning: Could not insert region {code}: {e}")
    print("✓ Default regions inserted")
def insert_default_config():
    default_configs = [
        ('current_day', '1', 'integer', 'Current competition day'),
        ('npcs_count', '61', 'integer', 'Number of participating npcs'),
        ('athletes_count', '529', 'integer', 'Number of registered athletes'),
        ('volunteers_count', '50', 'integer', 'Number of volunteers'),
        ('loc_count', '15', 'integer', 'Number of LOC members'),
        ('officials_count', '80', 'integer', 'Number of officials'),
        ('auto_approve_records', 'false', 'boolean', 'Auto-approve world and area records'),
        ('auto_approve_personal_bests', 'false', 'boolean', 'Auto-approve personal bests'),
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
    # CLASSES - Classification officielle World Para Athletics 2024-2025
    track_classes = [
        # Vision impairment
        'T11', 'T12', 'T13',
        # Intellectual impairment
        'T20',
        # Co-ordination impairments - Wheelchair racing
        'T32', 'T33', 'T34',
        # Co-ordination impairments - Running/Jumping
        'T35', 'T36', 'T37', 'T38',
        # Short stature
        'T40', 'T41',
        # Lower limb without prosthesis
        'T42', 'T43', 'T44',
        # Upper limb impairments
        'T45', 'T46', 'T47',
        # Wheelchair racing - Limb impairments
        'T51', 'T52', 'T53', 'T54',
        # Lower limb with prosthesis
        'T61', 'T62', 'T63', 'T64',
        # Frame Running
        'T71', 'T72'
    ]
    field_classes = [
        # Vision impairment
        'F11', 'F12', 'F13',
        # Intellectual impairment
        'F20',
        # Co-ordination impairments - Seated throws
        'F31', 'F32', 'F33', 'F34',
        # Co-ordination impairments - Standing throws
        'F35', 'F36', 'F37', 'F38',
        # Short stature
        'F40', 'F41',
        # Lower limb without prosthesis
        'F42', 'F43', 'F44',
        # Upper limb impairments
        'F45', 'F46',
        # Seated throws - Limb impairments
        'F51', 'F52', 'F53', 'F54', 'F55', 'F56', 'F57',
        # Lower limb with prosthesis
        'F61', 'F62', 'F63', 'F64'
    ]
    all_classes = sorted(track_classes + field_classes)
    default_tags = [
        ('classes', all_classes),
        ('record_types', ['WR', 'AR', 'ER', 'CR', 'NR', 'PB', 'SB', 'WL', 'AL']),
        ('result_special_values', ['DNS', 'DNF', 'NM', 'NH', 'O', 'X', '-', 'DQ']),
        ('field_events', [
            'Shot Put', 'Discus Throw', 'Javelin Throw', 'Hammer Throw',
            'Club Throw', 'Weight Throw'
        ]),
        ('track_events', [
            '100m', '200m', '400m', '800m', '1500m', '5000m', '10000m',
            'Marathon', '4x100m Relay', '4x400m Relay', 'Universal Relay',
            'Long Jump', 'High Jump', 'Triple Jump', 'Pole Vault'
        ]),
        ('guide_classes', ['T11', 'T12']),
        ('wind_affected_field_events', ['Long Jump', 'Triple Jump', '100m', '200m']),
        ('weight_field_events', [
            'Shot Put', 'Discus Throw', 'Javelin Throw', 'Hammer Throw',
            'Club Throw', 'Weight Throw'
        ])
    ]
    for key, tags in default_tags:
        try:
            existing = execute_one(
                "SELECT COUNT(*) as count FROM config_tags WHERE config_key = %s",
                (key,)
            )
            if existing['count'] == 0:
                for tag in tags:
                    execute_query(
                        "INSERT INTO config_tags (config_key, tag_value) VALUES (%s, %s)",
                        (key, tag)
                    )
                print(f"✓ Default tags inserted for: {key} ({len(tags)} items)")
        except Exception as e:
            print(f"✗ Warning: Could not insert tags for {key}: {e}")
    # Competition days - Tunis GP 2025
    default_days = [
        (1, '2025-06-12', '2025-06-12', 'Day 1 - Opening Events'),
        (2, '2025-06-13', '2025-06-13', 'Day 2 - Track & Field'),
        (3, '2025-06-14', '2025-06-14', 'Day 3 - Track & Field'),
        (4, '2025-06-15', '2025-06-15', 'Day 4 - Track & Field'),
        (5, '2025-06-16', '2025-06-16', 'Day 5 - Track & Field'),
        (6, '2025-06-17', '2025-06-17', 'Day 6 - Track & Field'),
        (7, '2025-06-18', '2025-06-18', 'Day 7 - Semi-Finals'),
        (8, '2025-06-19', '2025-06-19', 'Day 8 - Finals & Closing'),
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
    required_tables = [
        'users', 'npcs', 'athletes', 'games', 'results',
        'startlist', 'attempts', 'competition_config', 'competition_days', 'config_tags', 'record_types'
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