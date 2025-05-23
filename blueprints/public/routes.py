from flask import render_template, request
from . import public_bp
from database.models import Game, Result, Athlete
from config import Config


@public_bp.route('/')
def index():
    games = Game.get_with_status()
    published_games = [g for g in games if g['has_results']]
    return render_template('public/index.html', games=published_games)


@public_bp.route('/results')
def results():
    search = request.args.get('search', '')
    games = Game.get_with_status()

    if search:
        games = [g for g in games if
                 search.lower() in g['event'].lower() or
                 search.lower() in g['gender'].lower() or
                 search.lower() in g['classes'].lower() or
                 str(g['day']) in search]

    published_games = [g for g in games if g['has_results']]
    return render_template('public/results.html', games=published_games, search=search)


@public_bp.route('/startlists')
def startlists():
    search = request.args.get('search', '')
    games = Game.get_with_status()

    if search:
        games = [g for g in games if
                 search.lower() in g['event'].lower() or
                 search.lower() in g['gender'].lower() or
                 search.lower() in g['classes'].lower() or
                 str(g['day']) in search]

    return render_template('public/startlists.html', games=games, search=search)


@public_bp.route('/game/<int:id>')
def game_detail(id):
    game = Game.get_by_id(id)
    if not game:
        return render_template('404.html'), 404

    results = Result.get_all(game_id=id)
    game['has_results'] = len(results) > 0
    game['has_startlist'] = bool(game['start_file'])

    return render_template('public/game_detail.html', game=game, results=results)


@public_bp.route('/records')
def records():
    search = request.args.get('search', '')
    records = Result.get_records()

    if search:
        records = [r for r in records if
                   search.lower() in r['firstname'].lower() or
                   search.lower() in r['lastname'].lower() or
                   search.lower() in r['country'].lower() or
                   search.lower() in r['event'].lower() or
                   search.lower() in r['record'].lower()]

    return render_template('public/records.html', records=records, search=search)


@public_bp.route('/athletes')
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
                           genders=Config.GENDERS)