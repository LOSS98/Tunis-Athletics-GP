from datetime import datetime
from flask import render_template
from database.models import Game

def register_routes(bp):
    @bp.route('/')
    def index():
        games = Game.get_last_5()
        print("Games fetched for index:", games)
        return render_template('public/index.html', games=games)
    @bp.route('/health')
    def health_check():
        return {'status': 'healthy', 'timestamp': datetime.now().isoformat()}
