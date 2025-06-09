from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash
from database.db_manager import execute_query, execute_one
class User(UserMixin):
    def __init__(self, id, username, admin_type='volunteer'):
        self.id = id
        self.username = username
        self.admin_type = admin_type
    def is_loc(self):
        return self.admin_type == 'loc'
    def is_technical_delegate(self):
        return self.admin_type == 'technical_delegate'
    def has_loc_privileges(self):
        return self.admin_type in ['loc', 'technical_delegate']
    @staticmethod
    def get(user_id):
        user = execute_one("SELECT * FROM users WHERE id = %s", (user_id,))
        if user:
            return User(user['id'], user['username'], user.get('admin_type', 'volunteer'))
        return None
    @staticmethod
    def get_by_username(username):
        user = execute_one("SELECT * FROM users WHERE username = %s", (username,))
        return user
    @staticmethod
    def get_all():
        return execute_query("SELECT * FROM users ORDER BY id", fetch=True)
    @staticmethod
    def create(username, password, admin_type='volunteer'):
        password_hash = generate_password_hash(password)
        return execute_query(
            "INSERT INTO users (username, password_hash, admin_type) VALUES (%s, %s, %s)",
            (username, password_hash, admin_type)
        )
    @staticmethod
    def update(user_id, **data):
        if 'password' in data:
            data['password_hash'] = generate_password_hash(data.pop('password'))
        set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
        query = f"UPDATE users SET {set_clause} WHERE id = %s"
        params = list(data.values()) + [user_id]
        return execute_query(query, params)
    @staticmethod
    def delete(user_id):
        return execute_query("DELETE FROM users WHERE id = %s", (user_id,))
    @staticmethod
    def verify_password(username, password):
        user = User.get_by_username(username)
        if user and check_password_hash(user['password_hash'], password):
            return User(user['id'], user['username'], user.get('admin_type', 'volunteer'))
        return None