from flask import render_template, request
from database.models.game import Game
from database.models import StartList
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
        return render_template('public/startlist_detail.html',
                            game=game,
                            startlist=startlist)
