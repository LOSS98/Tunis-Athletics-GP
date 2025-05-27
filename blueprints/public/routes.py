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
    game['has_startlist'] = bool(game.get('start_file')) or len(StartList.get_by_game(id)) > 0

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


@public_bp.route('/rasa')
def rasa():
    return render_template('public/rasa.html')


@public_bp.route('/api/rasa-data')
def get_rasa_data():
    """API endpoint to get RASA table data for JavaScript"""
    try:
        if not os.path.exists(Config.RASA_TABLE_PATH):
            return jsonify([])

        df = pd.read_excel(Config.RASA_TABLE_PATH)

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


@public_bp.route('/api/calculate-rasa', methods=['POST'])
def calculate_rasa():
    """API endpoint to calculate RASA score"""
    try:
        data = request.get_json()
        gender = data.get('gender')
        event = data.get('event')
        athlete_class = data.get('class')
        performance = float(data.get('performance'))

        if not os.path.exists(Config.RASA_TABLE_PATH):
            return jsonify({'error': 'RASA table not found'})

        df = pd.read_excel(Config.RASA_TABLE_PATH)

        # Find matching row
        mask = (df['Event'] == event) & (df['Class'] == athlete_class) & (df['Gender'] == gender)
        rasa_row = df[mask]

        if rasa_row.empty:
            return jsonify({'error': 'No RASA data found for this combination'})

        rasa_row = rasa_row.iloc[0]
        a = rasa_row['a']
        b = rasa_row['b']
        c = rasa_row['c']

        # Calculate RASA score using Gompertz function
        score = int(a * np.exp(-b - c * performance))

        return jsonify({'rasa_score': score})

    except Exception as e:
        return jsonify({'error': str(e)})


@public_bp.route('/api/calculate-performance', methods=['POST'])
def calculate_performance():
    """API endpoint to calculate performance from RASA score"""
    try:
        data = request.get_json()
        gender = data.get('gender')
        event = data.get('event')
        athlete_class = data.get('class')
        rasa_score = float(data.get('rasa_score'))

        if not os.path.exists(Config.RASA_TABLE_PATH):
            return jsonify({'error': 'RASA table not found'})

        df = pd.read_excel(Config.RASA_TABLE_PATH)

        # Find matching row
        mask = (df['Event'] == event) & (df['Class'] == athlete_class) & (df['Gender'] == gender)
        rasa_row = df[mask]

        if rasa_row.empty:
            return jsonify({'error': 'No RASA data found for this combination'})

        rasa_row = rasa_row.iloc[0]
        a = rasa_row['a']
        b = rasa_row['b']
        c = rasa_row['c']

        # Reverse calculate performance from RASA score
        # rasa_score = a * exp(-b - c * performance)
        # performance = (-ln(rasa_score/a) - b) / c
        performance = (-np.log(rasa_score / a) - b) / c

        return jsonify({'performance': performance})

    except Exception as e:
        return jsonify({'error': str(e)})