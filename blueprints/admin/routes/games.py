import traceback
from flask import render_template, redirect, url_for, flash, request, jsonify, send_file
from config import Config
from utils.pdf_generator import PDFGenerator
from ..auth import admin_required, loc_required
from ..forms import GameForm
from database.models import Game, Result, Attempt, StartList
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
    @bp.route('/games/<int:game_id>/wind-velocity', methods=['POST'])
    @admin_required
    def game_update_wind_velocity(game_id):
        try:
            game = Game.get_by_id(game_id)
            if not game:
                flash('Game not found', 'danger')
                return redirect(url_for('admin.games_list'))
            wind_velocity = request.form.get('wind_velocity', '').strip()
            if wind_velocity == '':
                flash('Wind velocity is required', 'danger')
                return redirect(url_for('admin.game_results', id=game_id))
            try:
                wind_velocity_float = float(wind_velocity)
            except ValueError:
                flash('Wind velocity must be a valid number', 'danger')
                return redirect(url_for('admin.game_results', id=game_id))
            if wind_velocity_float < -20.0 or wind_velocity_float > 20.0:
                flash('Wind velocity updated but too high !', 'danger')
            Game.update_velocity(game_id, wind_velocity_float)
            if wind_velocity_float > 2.0:
                flash(f'Wind velocity updated to +{wind_velocity_float} m/s (wind-assisted - records ineligible)',
                      'warning')
            elif wind_velocity_float < -2.0:
                flash(f'Wind velocity updated to {wind_velocity_float} m/s (strong headwind)', 'info')
            else:
                flash(f'Wind velocity updated to {wind_velocity_float} m/s', 'success')
            return redirect(url_for('admin.game_results', id=game_id))
        except Exception as e:
            print(f"Error updating wind velocity for game {game_id}: {e}")
            traceback.print_exc()
            flash(f'Error updating wind velocity: {str(e)}', 'danger')
            return redirect(url_for('admin.game_results', id=game_id))
    @bp.route('/games/<int:game_id>/remove-wind-velocity', methods=['POST'])
    @admin_required
    def game_remove_wind_velocity(game_id):
        try:
            game = Game.get_by_id(game_id)
            if not game:
                flash('Game not found', 'danger')
                return redirect(url_for('admin.games_list'))
            Game.update_velocity(game_id, 0)
            flash('Wind velocity measurement removed for this event', 'success')
            return redirect(url_for('admin.game_results', id=game_id))
        except Exception as e:
            print(f"Error removing wind velocity for game {game_id}: {e}")
            traceback.print_exc()
            flash(f'Error removing wind velocity: {str(e)}', 'danger')
            return redirect(url_for('admin.game_results', id=game_id))
    @bp.route('/games/create', methods=['GET', 'POST'])
    @admin_required
    def game_create():
        form = GameForm()
        if form.validate_on_submit():
            data = {
                'event': form.event.data,
                'gender': form.genders.data,
                'classes': form.classes.data,
                'phase': form.phase.data,
                'area': form.area.data,
                'day': form.day.data,
                'time': form.time.data,
                'nb_athletes': form.nb_athletes.data,
                'status': form.status.data,
                'published': form.published.data,
                'wpa_points': form.wpa_points.data
            }
            if form.start_file.data:
                filename = save_uploaded_file(form.start_file.data, 'startlists')
                if filename:
                    data['start_file'] = filename
            if form.result_file.data:
                filename = save_uploaded_file(form.result_file.data, 'results')
                if filename:
                    data['result_file'] = filename
            if form.photo_finish.data:
                filename = save_uploaded_file(form.photo_finish.data, 'photo_finish')
                if filename:
                    data['photo_finish'] = filename
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
            if request.method == 'POST':
                return {'error': 'Game not found'}, 404
            else:
                flash('Game not found', 'danger')
                return redirect(url_for('admin.games_list'))
        if request.method == 'POST':
            try:
                data = {
                    'event': request.form.get('event'),
                    'gender': request.form.get('gender'),
                    'classes': request.form.get('classes'),
                    'phase': request.form.get('phase') if request.form.get('phase') else None,
                    'area': request.form.get('area') if request.form.get('area') else None,
                    'day': int(request.form.get('day')),
                    'time': request.form.get('time'),
                    'nb_athletes': int(request.form.get('nb_athletes')),
                    'status': request.form.get('status'),
                    'published': bool(request.form.get('published')),
                    'wpa_points': bool(request.form.get('wpa_points'))
                }
                Game.update(id, **data)
                if request.headers.get('Content-Type', '').startswith('multipart/form-data'):
                    flash('Game updated successfully', 'success')
                    return redirect(url_for('admin.games_list'))
                else:
                    return '', 200
            except Exception as e:
                if request.headers.get('Content-Type', '').startswith('multipart/form-data'):
                    flash(f'Error updating game: {str(e)}', 'danger')
                    return redirect(url_for('admin.games_list'))
                else:
                    return {'error': str(e)}, 500
        # GET request - show edit form
        from ..forms import GameForm
        form = GameForm()
        # Pre-populate form
        form.event.data = game['event']
        form.gender.data = game['gender']
        form.classes.data = game['classes']
        form.phase.data = game.get('phase')
        form.area.data = game.get('area')
        form.day.data = game['day']
        form.time.data = game['time']
        form.nb_athletes.data = game['nb_athletes']
        form.status.data = game['status']
        form.published.data = game.get('published', False)
        form.wpa_points.data = game.get('wpa_points', False)
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
            success = Result.auto_rank_results(id)
            if success:
                return jsonify({'success': True})
            else:
                return jsonify({'error': 'Failed to auto-rank results'}), 500
        except Exception as e:
            print(f"Error in auto-rank: {e}")
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500
    @bp.route('/games/<int:id>/publish', methods=['POST'])
    @loc_required
    def game_toggle_publish(id):
        try:
            new_status = Game.toggle_publish(id)
            return jsonify({'published': new_status})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    @bp.route('/games/<int:game_id>/generate-pdf')
    @admin_required
    def generate_game_pdf(game_id):
        try:
            game = Game.get_by_id(game_id)
            if not game:
                flash('Game not found', 'danger')
                return redirect(url_for('admin.games_list'))
            results = Result.get_all(game_id=game_id)
            # Charger les tentatives pour les épreuves de terrain
            if game['event'] in Config.get_field_events():
                for result in results:
                    result['attempts'] = Attempt.get_by_result(result['id'])
            generator = PDFGenerator()
            pdf_buffer = generator.generate_results_pdf(game, results)
            filename = f"results_{game['event']}_{game['gender']}_{game['day']}.pdf"
            return send_file(
                pdf_buffer,
                as_attachment=False,
                download_name=filename,
                mimetype='application/pdf'
            )
        except Exception as e:
            print(f"Error generating PDF: {e}")
            flash(f'Error generating PDF: {str(e)}', 'danger')
            return redirect(url_for('admin.game_results', id=game_id))
    @bp.route('/games/<int:game_id>/generate-startlist-pdf')
    @admin_required
    def generate_startlist_pdf(game_id):
        try:
            game = Game.get_by_id(game_id)
            if not game:
                flash('Game not found', 'danger')
                return redirect(url_for('admin.games_list'))
            startlist = StartList.get_by_game(game_id)
            generator = PDFGenerator()
            pdf_buffer = generator.generate_startlist_pdf(game, startlist)
            filename = f"startlist_{game['event']}_{game['gender']}_{game['day']}.pdf"
            return send_file(
                pdf_buffer,
                as_attachment=False,
                download_name=filename,
                mimetype='application/pdf'
            )
        except Exception as e:
            print(f"Error generating startlist PDF: {e}")
            flash(f'Error generating PDF: {str(e)}', 'danger')
            return redirect(url_for('admin.game_startlist', id=game_id))