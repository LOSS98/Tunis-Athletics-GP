from flask import render_template, request
from database.models.game import Game
from database.models import StartList
from config import config
def register_routes(bp):
    @bp.route('/startlists')
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
    @bp.route('/game/<int:id>/startlist')
    def game_startlist_detail(id):
        game = Game.get_by_id(id)
        if not game:
            return render_template('404.html'), 404

        startlist = StartList.get_by_game(id)

        pdf_fields = ['manual_startlist_pdf', 'generated_startlist_pdf', 'manual_results_pdf', 'generated_results_pdf']
        for field in pdf_fields:
            if field not in game:
                game[field] = None

        return render_template('public/startlist_detail.html',
                               game=game,
                               startlist=startlist,
                               config=config)
