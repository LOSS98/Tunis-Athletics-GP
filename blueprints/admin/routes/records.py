from flask import render_template
from ..auth import admin_required
from database.models import Result

def register_routes(bp):
    @bp.route('/records')
    @admin_required
    def records_list():
        records = Result.get_records()
        return render_template('admin/records/list.html', records=records)
