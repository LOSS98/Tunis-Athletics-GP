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
                    search.lower() in g['genders'].lower() or
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

        return render_template('public/game_detail.html',
                               game=game,
                               results=results,
                               startlist=startlist,
                               heat_group=heat_group,
                               heat_games=heat_games,
                               combined_results=combined_results,
                               all_startlists=all_startlists)