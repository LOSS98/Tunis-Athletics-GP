from datetime import datetime
from flask import render_template
from database.models import Game
def register_routes(bp):
    @bp.route('/')
    def index():
        games = Game.get_with_status()
        published_games = [g for g in games if g.get('published', False) and g['has_results']]
        return render_template('public/index.html', games=published_games)
    @bp.route('/health')
    def health_check():
        return {'status': 'healthy', 'timestamp': datetime.now().isoformat()}
