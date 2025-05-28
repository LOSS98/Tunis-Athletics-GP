from flask import render_template, redirect, url_for, flash, request, jsonify
from ..auth import admin_required, loc_required
from ..forms import GameForm
from database.models import Game, Result
from utils.helpers import save_uploaded_file

def register_routes(bp):
    @bp.route('/games')
    @admin_required
    def games_list():
        search = request.args.get('search', '')
        games = Game.get_with_status()

        if search:
            games = [g for g in games if
                    search.lower() in g['event'].lower() or
                    search.lower() in g['gender'].lower() or
                    search.lower() in g['classes'].lower() or
                    str(g['day']) in search]

        return render_template('admin/games/list.html', games=games, search=search)

    @bp.route('/games/create', methods=['GET', 'POST'])
    @admin_required
    def game_create():
        form = GameForm()
        if form.validate_on_submit():
            data = {
                'event': form.event.data,
                'gender': form.gender.data,
                'classes': form.classes.data,
                'phase': form.phase.data,
                'area': form.area.data,
                'day': form.day.data,
                'time': form.time.data,
                'nb_athletes': form.nb_athletes.data,
                'status': form.status.data,
                'published': form.published.data
            }

            if form.start_file.data:
                filename = save_uploaded_file(form.start_file.data, 'startlists')
                if filename:
                    data['start_file'] = filename

            if form.result_file.data:
                filename = save_uploaded_file(form.result_file.data, 'results')
                if filename:
                    data['result_file'] = filename

            try:
                Game.create(**data)
                flash('Game created successfully', 'success')
                return redirect(url_for('admin.games_list'))
            except Exception as e:
                flash(f'Error creating game: {str(e)}', 'danger')

        return render_template('admin/games/create.html', form=form)

    @bp.route('/games/<int:id>/edit', methods=['GET', 'POST'])
    @admin_required
    def game_edit(id):
        game = Game.get_by_id(id)
        if not game:
            flash('Game not found', 'danger')
            return redirect(url_for('admin.games_list'))

        form = GameForm()

        if form.validate_on_submit():
            data = {
                'event': form.event.data,
                'gender': form.gender.data,
                'classes': form.classes.data,
                'phase': form.phase.data,
                'area': form.area.data,
                'day': form.day.data,
                'time': form.time.data,
                'nb_athletes': form.nb_athletes.data,
                'status': form.status.data,
                'published': form.published.data
            }

            if form.start_file.data:
                filename = save_uploaded_file(form.start_file.data, 'startlists')
                if filename:
                    data['start_file'] = filename

            if form.result_file.data:
                filename = save_uploaded_file(form.result_file.data, 'results')
                if filename:
                    data['result_file'] = filename

            try:
                Game.update(id, **data)
                flash('Game updated successfully', 'success')
                return redirect(url_for('admin.games_list'))
            except Exception as e:
                flash(f'Error updating game: {str(e)}', 'danger')

        elif request.method == 'GET':
            form.event.data = game['event']
            form.gender.data = game['gender']
            form.classes.data = game['classes']
            form.phase.data = game['phase']
            form.area.data = game['area']
            form.day.data = game['day']
            form.time.data = game['time']
            form.nb_athletes.data = game['nb_athletes']
            form.status.data = game['status']
            form.published.data = game.get('published', False)

        return render_template('admin/games/edit.html', form=form, game=game)

    @bp.route('/games/<int:id>/delete', methods=['POST'])
    @admin_required
    def game_delete(id):
        try:
            Game.delete(id)
            flash('Game deleted successfully', 'success')
        except Exception as e:
            flash(f'Error deleting game: {str(e)}', 'danger')

        return redirect(url_for('admin.games_list'))

    @bp.route('/games/<int:id>/status', methods=['POST'])
    @admin_required
    def game_update_status(id):
        status = request.form.get('status')
        valid_statuses = ['scheduled', 'started', 'in_progress', 'finished', 'cancelled']

        if status not in valid_statuses:
            return jsonify({'error': 'Invalid status'}), 400

        try:
            Game.update_status(id, status)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @bp.route('/games/<int:id>/auto-rank', methods=['POST'])
    @admin_required
    def game_auto_rank(id):
        try:
            game = Game.get_by_id(id)
            if not game:
                return jsonify({'error': 'Game not found'}), 404

            results = Result.get_all(game_id=id)

            for result in results:
                if result.get('auto_rank'):
                    Result.update(result['id'], rank=result['auto_rank'])

            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @bp.route('/games/<int:id>/publish', methods=['POST'])
    @loc_required
    def game_toggle_publish(id):
        try:
            new_status = Game.toggle_publish(id)
            return jsonify({'published': new_status})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
