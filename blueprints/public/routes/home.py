from datetime import datetime
from flask import render_template
from database.models import Game
from config import Config

def register_routes(bp):
    @bp.route('/')
    def index():
        games = Game.get_with_status()
        published_games = [g for g in games if g.get('published', False) and g['has_results']]
        stats = {
            'npcs': Config.get_npcs_count(),
            'athletes': Config.get_athletes_count(),
            'volunteers': Config.get_volunteers_count(),
            'loc': Config.get_loc_count(),
            'officials': Config.get_officials_count()
        }
        return render_template('public/index.html', games=published_games,stats=stats)
    @bp.route('/health')
    def health_check():
        return {'status': 'healthy', 'timestamp': datetime.now().isoformat()}
