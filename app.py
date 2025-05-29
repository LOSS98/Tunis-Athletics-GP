from flask import Flask, render_template
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from config import Config
from blueprints.admin import admin_bp
from blueprints.public import public_bp
from database.db_manager import init_db
from datetime import datetime
import os


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize CSRF protection
    csrf = CSRFProtect(app)

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'startlists'), exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'results'), exist_ok=True)
    os.makedirs(os.path.join('static/images/athletes'), exist_ok=True)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'admin.login'

    @login_manager.user_loader
    def load_user(user_id):
        from database.models import User
        return User.get(user_id)

    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(public_bp)
    csrf.exempt(public_bp)

    @app.context_processor
    def inject_template_vars():
        """Inject template variables including config and CSRF token"""
        from flask_wtf.csrf import generate_csrf

        # Create a config object compatible for templates
        class TemplateConfig:
            def __init__(self):
                pass

            @property
            def CLASSES(self):
                return Config.get_classes()

            @property
            def GENDERS(self):
                return Config.get_genders()

            @property
            def RECORD_TYPES(self):
                return Config.get_record_types()

            @property
            def RESULT_SPECIAL_VALUES(self):
                return Config.get_result_special_values()

            @property
            def FIELD_EVENTS(self):
                return Config.get_field_events()

            @property
            def TRACK_EVENTS(self):
                return Config.get_track_events()

            @property
            def WIND_AFFECTED_FIELD_EVENTS(self):
                return Config.get_wind_affected_field_events()

            @property
            def CURRENT_DAY(self):
                return Config.get_current_day()

            @property
            def COUNTRIES_COUNT(self):
                return Config.get_countries_count()

            @property
            def ATHLETES_COUNT(self):
                return Config.get_athletes_count()

            @property
            def VOLUNTEERS_COUNT(self):
                return Config.get_volunteers_count()

            @property
            def LOC_COUNT(self):
                return Config.get_loc_count()

            @property
            def OFFICIALS_COUNT(self):
                return Config.get_officials_count()

            # Methods for direct access from templates
            def get_classes(self):
                return Config.get_classes()

            def get_genders(self):
                return Config.get_genders()

            def get_record_types(self):
                return Config.get_record_types()

            def get_result_special_values(self):
                return Config.get_result_special_values()

            def get_field_events(self):
                return Config.get_field_events()

            def get_track_events(self):
                return Config.get_track_events()

            def get_wind_affected_field_events(self):
                return Config.get_wind_affected_field_events()

            # Formatting methods - these were missing!
            def format_time(self, time_value):
                return Config.format_time(time_value)

            def format_distance(self, distance_value):
                return Config.format_distance(distance_value)

            def format_wind(self, wind_value):
                return Config.format_wind(wind_value)

            def format_weight(self, weight_value):
                return Config.format_weight(weight_value)

            # Static properties
            UPLOAD_FOLDER = Config.UPLOAD_FOLDER
            RAZA_TABLE_PATH = Config.RAZA_TABLE_PATH

        return {
            'config': TemplateConfig(),
            'current_date': datetime.now().strftime('%B %d, %Y'),
            'csrf_token': generate_csrf
        }

    @app.errorhandler(404)
    def not_found(error):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('500.html'), 500

    return app


if __name__ == '__main__':
    init_db()
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)