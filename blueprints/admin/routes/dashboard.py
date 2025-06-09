from flask import render_template
from ..auth import admin_required
from config import Config
def register_routes(bp):
    @bp.route('/')
    @admin_required
    def dashboard():
        stats = {
            'npcs': Config.get_npcs_count(),
            'athletes': Config.get_athletes_count(),
            'volunteers': Config.get_volunteers_count(),
            'loc': Config.get_loc_count(),
            'officials': Config.get_officials_count()
        }
        return render_template('admin/dashboard.html')
