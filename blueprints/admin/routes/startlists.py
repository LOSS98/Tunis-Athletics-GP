from flask import render_template, jsonify, request, redirect, url_for, flash
from ..auth import admin_required
from ..forms import StartListForm
from database.models import Game, StartList, Athlete
from database.db_manager import execute_query


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
            athlete = Athlete.get_by_sdms(form.athlete_sdms.data)

            if not athlete:
                flash('Athlete not found', 'danger')
            else:
                game_classes = [c.strip() for c in game['classes'].split(',')]
                athlete_classes = [c.strip() for c in athlete['class'].split(',') if c.strip()] if athlete[
                    'class'] else []

                has_compatible_class = any(ac in game_classes for ac in athlete_classes)

                if not has_compatible_class:
                    flash(
                        f"Warning: Athlete classes {', '.join(athlete_classes)} do not match game classes {', '.join(game_classes)}",
                        'warning')

                guide_sdms = form.guide_sdms.data if form.guide_sdms.data else None

                try:
                    StartList.create(game_id, form.athlete_sdms.data, form.lane_order.data, guide_sdms)
                    flash('Athlete added to start list', 'success')
                except Exception as e:
                    flash(f'Error adding to start list: {str(e)}', 'danger')

        return redirect(url_for('admin.game_startlist', id=game_id))

    @bp.route('/games/<int:game_id>/startlist/<int:athlete_sdms>/delete', methods=['POST'])
    @admin_required
    def startlist_delete(game_id, athlete_sdms):
        try:
            StartList.delete(game_id, athlete_sdms)
            flash('Athlete removed from start list', 'success')
        except Exception as e:
            flash(f'Error removing from start list: {str(e)}', 'danger')

        return redirect(url_for('admin.game_startlist', id=game_id))
    @bp.route('/games/<int:game_id>/startlist/<int:athlete_sdms>/update-order', methods=['POST'])
    @admin_required
    def startlist_update_order(game_id, athlete_sdms):
        try:
            data = request.get_json()
            new_order = data.get('lane_order')

            execute_query(
                "UPDATE startlist SET lane_order = %s WHERE game_id = %s AND athlete_sdms = %s",
                (new_order, game_id, athlete_sdms)
            )
            return jsonify({'success': True})

        except Exception as e:
            print(f"Error updating startlist order: {e}")
            return jsonify({'error': str(e)}), 500