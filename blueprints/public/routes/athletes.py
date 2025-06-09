from flask import render_template, request
from database.models import Athlete
from config import Config
def register_routes(bp):
    @bp.route('/athletes')
    def athletes():
        search = request.args.get('search', '')
        gender_filter = request.args.get('gender', '')
        npc_filter = request.args.get('npc', '')
        if search:
            athletes = Athlete.search(search)
        else:
            filters = {}
            if gender_filter:
                filters['gender'] = gender_filter
            if npc_filter:
                filters['npc'] = npc_filter
            athletes = Athlete.get_all(**filters)
        npcs = list(set([a['npc'] for a in Athlete.get_all()]))
        npcs.sort()
        return render_template('public/athletes.html',
                            athletes=athletes,
                            search=search,
                            gender_filter=gender_filter,
                            npc_filter=npc_filter,
                            npcs=npcs,
                            genders=Config.get_genders())
