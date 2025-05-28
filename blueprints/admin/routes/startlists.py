from flask import render_template, redirect, url_for, flash
from ..auth import admin_required
from ..forms import StartListForm
from database.models import Game, StartList, Athlete

def register_routes(bp):
    @bp.route('/games/<int:id>/startlist')
    @admin_required
    def game_startlist(id):
        game = Game.get_by_id(id)
        if not game:
            flash('Game not found', 'danger')
            return redirect(url_for('admin.games_list'))

        startlist = StartList.get_by_game(id)
        form = StartListForm()

        return render_template('admin/games/startlist.html',
                           game=game,
                           startlist=startlist,
                           form=form)

    @bp.route('/games/<int:game_id>/startlist/add', methods=['POST'])
    @admin_required
    def startlist_add(game_id):
        form = StartListForm()
        if form.validate_on_submit():
            game = Game.get_by_id(game_id)
            athlete = Athlete.get_by_bib(form.athlete_bib.data)

            if not athlete:
                flash('Athlete not found', 'danger')
            else:
                game_classes = [c.strip() for c in game['classes'].split(',')]
                if athlete['class'] not in game_classes:
                    flash(f"Warning: Athlete class {athlete['class']} not in game classes {', '.join(game_classes)}",
                        'warning')

                try:
                    StartList.create(game_id, form.athlete_bib.data, form.lane_order.data)
                    flash('Athlete added to start list', 'success')
                except Exception as e:
                    flash(f'Error adding to start list: {str(e)}', 'danger')

        return redirect(url_for('admin.game_startlist', id=game_id))

    @bp.route('/games/<int:game_id>/startlist/<int:athlete_bib>/delete', methods=['POST'])
    @admin_required
    def startlist_delete(game_id, athlete_bib):
        try:
            StartList.delete(game_id, athlete_bib)
            flash('Athlete removed from start list', 'success')
        except Exception as e:
            flash(f'Error removing from start list: {str(e)}', 'danger')

        return redirect(url_for('admin.game_startlist', id=game_id))
