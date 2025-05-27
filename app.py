from flask import Flask, render_template
from flask_login import LoginManager
from config import Config
from blueprints.admin import admin_bp
from blueprints.public import public_bp
from database.db_manager import init_db
from datetime import datetime
import os


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Create upload directories
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'startlists'), exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'results'), exist_ok=True)
    os.makedirs(os.path.join('static/images/athletes'), exist_ok=True)

    # Setup Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'admin.login'

    @login_manager.user_loader
    def load_user(user_id):
        from database.models import User
        return User.get(user_id)

    # Register blueprints
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(public_bp)

    # Template context processors
    @app.context_processor
    def inject_template_vars():
        return {
            'config': Config,
            'current_date': datetime.now().strftime('%B %d, %Y')
        }

    # Error handlers
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