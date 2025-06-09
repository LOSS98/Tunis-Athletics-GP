from flask import render_template
from ..auth import admin_required
def register_routes(bp):
    @bp.route('/')
    @admin_required
    def dashboard():
        return render_template('admin/dashboard.html')
