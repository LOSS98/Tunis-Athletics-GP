from flask import render_template, request
from database.models import Athlete
from config import Config

def register_routes(bp):
    @bp.route('/athletes')
    def athletes():
        search = request.args.get('search', '')
        gender_filter = request.args.get('gender', '')
        country_filter = request.args.get('country', '')

        if search:
            athletes = Athlete.search(search)
        else:
            filters = {}
            if gender_filter:
                filters['gender'] = gender_filter
            if country_filter:
                filters['country'] = country_filter
            athletes = Athlete.get_all(**filters)

        countries = list(set([a['country'] for a in Athlete.get_all()]))
        countries.sort()

        return render_template('public/athletes.html',
                            athletes=athletes,
                            search=search,
                            gender_filter=gender_filter,
                            country_filter=country_filter,
                            countries=countries,
                            genders=Config.get_genders())
