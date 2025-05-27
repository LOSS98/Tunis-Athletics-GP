from flask import render_template, request, jsonify
from . import public_bp
from database.models import Game, Result, Athlete, StartList
from config import Config
import pandas as pd
import os
import numpy as np


@public_bp.route('/')
def index():
    games = Game.get_with_status()
    published_games = [g for g in games if g.get('published', False) and g['has_results']]
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

    published_games = [g for g in games if g.get('published', False) and g['has_results']]
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

    # Show all games, regardless of published status for startlists
    return render_template('public/startlists.html', games=games, search=search)


@public_bp.route('/game/<int:id>')
def game_detail(id):
    game = Game.get_by_id(id)
    if not game:
        return render_template('404.html'), 404

    results = Result.get_all(game_id=id)
    startlist = StartList.get_by_game(id)

    game['has_results'] = len(results) > 0
    game['has_startlist'] = bool(game.get('start_file')) or len(startlist) > 0

    return render_template('public/game_detail.html',
                           game=game,
                           results=results,
                           startlist=startlist)


@public_bp.route('/game/<int:id>/startlist')
def game_startlist_detail(id):
    game = Game.get_by_id(id)
    if not game:
        return render_template('404.html'), 404

    startlist = StartList.get_by_game(id)

    return render_template('public/startlist_detail.html',
                           game=game,
                           startlist=startlist)


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


@public_bp.route('/raza')
def raza():
    return render_template('public/raza.html')


@public_bp.route('/api/raza-data')
def get_raza_data():
    """API endpoint to get RAZA table data for JavaScript"""
    try:
        if not os.path.exists(Config.RAZA_TABLE_PATH):
            return jsonify([])

        df = pd.read_excel(Config.RAZA_TABLE_PATH)

        # Convert to list of dictionaries
        data = df.to_dict('records')

        # Clean up data types for JSON serialization
        for row in data:
            for key, value in row.items():
                if pd.isna(value):
                    row[key] = None
                elif isinstance(value, np.integer):
                    row[key] = int(value)
                elif isinstance(value, np.floating):
                    row[key] = float(value)

        return jsonify(data)
    except Exception as e:
        return jsonify([])


@public_bp.route('/api/calculate-raza', methods=['POST'])
def calculate_raza():
    """API endpoint to calculate RAZA score with CORRECT formula"""
    try:
        data = request.get_json()
        gender = data.get('gender')
        event = data.get('event')
        athlete_class = data.get('class')
        performance = float(data.get('performance'))

        if not os.path.exists(Config.RAZA_TABLE_PATH):
            return jsonify({'error': 'RAZA table not found'})

        df = pd.read_excel(Config.RAZA_TABLE_PATH)

        # Find matching row
        mask = (df['Event'] == event) & (df['Class'] == athlete_class) & (df['Gender'] == gender)
        raza_row = df[mask]

        if raza_row.empty:
            return jsonify({'error': 'No RAZA data found for this combination'})

        raza_row = raza_row.iloc[0]
        a = float(raza_row['a'])
        b = float(raza_row['b'])
        c = float(raza_row['c'])
        print(a, b, c)

        # ✅ FORMULE OFFICIELLE CORRIGÉE :
        # Points = PLANCHER(A × e^(-B-C×Performance))
        score_float = a * np.exp(-np.exp(b - c * performance))
        score = int(np.floor(score_float))  # ← CORRECTION : utiliser floor()
        print(score_float, score)
        return jsonify({'raza_score': score})

    except Exception as e:
        return jsonify({'error': str(e)})


@public_bp.route('/api/calculate-performance', methods=['POST'])
def calculate_performance():
    """API endpoint to calculate performance from RAZA score with CORRECT inverse formula"""
    try:
        data = request.get_json()
        gender = data.get('gender')
        event = data.get('event')
        athlete_class = data.get('class')
        raza_score = float(data.get('raza_score'))

        if not os.path.exists(Config.RAZA_TABLE_PATH):
            return jsonify({'error': 'RAZA table not found'})

        df = pd.read_excel(Config.RAZA_TABLE_PATH)

        # Find matching row
        mask = (df['Event'] == event) & (df['Class'] == athlete_class) & (df['Gender'] == gender)
        raza_row = df[mask]

        if raza_row.empty:
            return jsonify({'error': 'No RAZA data found for this combination'})

        raza_row = raza_row.iloc[0]
        a = float(raza_row['a'])
        b = float(raza_row['b'])
        c = float(raza_row['c'])

        # ✅ FORMULE INVERSE OFFICIELLE CORRIGÉE :
        # Performance = PLAFOND((B - ln(ln(Points/A))) / C, 0.01)
        # Cette formule correspond à celle montrée dans l'image
        if raza_score <= 0 or raza_score >= a:
            return jsonify({'error': 'Invalid RAZA score range'})

        try:
            # Formule inverse : (B - ln(ln(Points/A))) / C
            inner_ln = np.log(raza_score / a)
            if inner_ln >= 0:  # ln doit être négatif pour que l'inner_ln soit valide
                return jsonify({'error': 'Invalid RAZA score for calculation'})

            performance = (b - np.log(-inner_ln)) / c

            # Application du PLAFOND avec précision 0.01
            performance = np.ceil(performance * 100) / 100

            return jsonify({'performance': round(performance, 2)})

        except (ValueError, ZeroDivisionError) as e:
            return jsonify({'error': 'Mathematical error in calculation'})

    except Exception as e:
        return jsonify({'error': str(e)})