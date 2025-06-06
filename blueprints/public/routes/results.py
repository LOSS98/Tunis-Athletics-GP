from flask import render_template, request
from database.models import Game, Result, StartList

def register_routes(bp):
    @bp.route('/results')
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

    @bp.route('/game/<int:id>')
    def game_detail(id):
        game = Game.get_by_id(id)
        if not game:
            return render_template('404.html'), 404

        results = Result.get_all(game_id=id)
        startlist = StartList.get_by_game(id)

        combined_results = []
        heat_ids = Game.get_related_heats(id)
        if heat_ids and len(heat_ids) > 1:
            combined_results = Result.combine_and_rank_track(heat_ids, game['event'])

        game['has_results'] = len(results) > 0
        game['has_startlist'] = bool(game.get('start_file')) or len(startlist) > 0

        return render_template('public/game_detail.html',
                            game=game,
                            results=results,
                            startlist=startlist,
                            combined_results=combined_results)

