from flask import render_template
from database.models.medal import Medal

def register_routes(bp):
    @bp.route('/medals')
    def medals():
        medals = Medal.get_all()
        return render_template('public/medals.html', medals=medals)