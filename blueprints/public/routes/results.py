from flask import render_template, request, send_file, abort
import os
from config import config
from database.models import Game, Result, StartList, HeatGroup


def register_routes(bp):
    @bp.route('/results')
    def results():
        search = request.args.get('search', '')
        games = Game.get_with_status()
        if search:
            games = [g for g in games if
                     search.lower() in g['event'].lower() or
                     search.lower() in g['genders'].lower() or
                     search.lower() in g['classes'].lower() or
                     str(g['day']) in search]
        published_games = [g for g in games if g.get('published', False) and g['has_results']]

        # S'assurer que les champs PDF existent
        for game in published_games:
            if 'manual_startlist_pdf' not in game:
                game['manual_startlist_pdf'] = None
            if 'generated_startlist_pdf' not in game:
                game['generated_startlist_pdf'] = None
            if 'manual_results_pdf' not in game:
                game['manual_results_pdf'] = None
            if 'generated_results_pdf' not in game:
                game['generated_results_pdf'] = None

        return render_template('public/results.html', games=published_games, search=search, config=config)

    @bp.route('/game/<int:id>')
    def game_detail(id):
        game = Game.get_by_id(id)
        if not game:
            return render_template('404.html'), 404

        results = Result.get_all(game_id=id)
        startlist = StartList.get_by_game(id)

        heat_group = None
        heat_games = []
        combined_results = []
        all_startlists = {}

        if Game.is_heat_game(game):
            heat_group = HeatGroup.get_by_id(game['heat_group_id'])
            heat_games = HeatGroup.get_games(game['heat_group_id'])
            combined_results = HeatGroup.get_combined_results(game['heat_group_id'])

            for i, result in enumerate(combined_results):
                result['final_rank'] = i + 1
                result['athlete_classes'] = result['athlete_class'].split(',') if result['athlete_class'] else []

            for heat_game in heat_games:
                all_startlists[heat_game['id']] = StartList.get_by_game(heat_game['id'])

        game['has_results'] = len(results) > 0
        game['has_startlist'] = bool(game.get('start_file')) or len(startlist) > 0

        # S'assurer que les champs PDF existent
        pdf_fields = ['manual_startlist_pdf', 'generated_startlist_pdf', 'manual_results_pdf', 'generated_results_pdf']
        for field in pdf_fields:
            if field not in game:
                game[field] = None

        has_r1_qualifying = False
        if game['event'] in config.get_field_events():
            r1_classes = config.get_r1_qualifying_classes()
            for cls in game['classes_list']:
                if cls in r1_classes:
                    has_r1_qualifying = True
                    break
        finalists_count = len([r for r in results if r.get('final_order')])

        return render_template('public/game_detail.html',
                               game=game,
                               results=results,
                               startlist=startlist,
                               heat_group=heat_group,
                               heat_games=heat_games,
                               combined_results=combined_results,
                               all_startlists=all_startlists,
                               has_r1_qualifying=has_r1_qualifying,
                               finalists_count=finalists_count,
                               config=config)



    @bp.route('/pdf/<path:pdf_type>/<path:filename>')
    def serve_pdf(pdf_type, filename):
        try:
            if pdf_type == 'manual_startlists':
                filepath = os.path.join('static', 'manual_pdfs', 'startlists', filename)
            elif pdf_type == 'manual_results':
                filepath = os.path.join('static', 'manual_pdfs', 'results', filename)
            elif pdf_type == 'generated_startlists':
                filepath = os.path.join('static', 'generated_pdfs', 'startlists', filename)
            elif pdf_type == 'generated_results':
                filepath = os.path.join('static', 'generated_pdfs', 'results', filename)
            else:
                print(f"Invalid PDF type: {pdf_type}")
                abort(404)

            if os.path.exists(filepath):
                return send_file(filepath, as_attachment=False, mimetype='application/pdf')
            else:
                print(f"PDF file not found: {filepath}")
                abort(404)

        except Exception as e:
            print(f"Error serving PDF {pdf_type}/{filename}: {e}")
            abort(404)