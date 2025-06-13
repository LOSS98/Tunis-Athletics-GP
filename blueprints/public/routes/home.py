from datetime import datetime
from flask import render_template
from database.models import Game
from config import config

def register_routes(bp):
    @bp.route('/')
    def index():
        games = Game.get_last_5()
        return render_template('public/index.html', games=games, config=config)
    @bp.route('/health')
    def health_check():
        return {'status': 'healthy', 'timestamp': datetime.now().isoformat()}
    @bp.route('/bus')
    def bus():
        return render_template('public/bus.html', config=config)