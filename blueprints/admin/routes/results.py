from flask import render_template, redirect, url_for, flash, request
from ..auth import admin_required
from ..forms import ResultForm
from database.models import Game, Result, Athlete, Attempt, StartList
from database.db_manager import execute_one, execute_query
from config import Config
import re
import traceback


def register_routes(bp):
    @bp.route('/games/<int:id>/results')
    @admin_required
    def game_results(id):
        game = Game.get_by_id(id)
        if not game:
            flash('Game not found', 'danger')
            return redirect(url_for('admin.games_list'))

        results = Result.get_all(game_id=id)
        startlist = StartList.get_by_game(id)
        form = ResultForm()

        return render_template('admin/results/manage.html',
                               game=game,
                               results=results,
                               startlist=startlist,
                               form=form,
                               is_field_event=game['event'] in Config.get_field_events(),
                               is_track_event=game['event'] in Config.get_track_events())

    @bp.route('/games/<int:game_id>/results/add', methods=['POST'])
    @admin_required
    def result_add(game_id):
        try:
            game = Game.get_by_id(game_id)
            if not game:
                flash('Game not found', 'danger')
                return redirect(url_for('admin.games_list'))
            athlete_bib = request.form.get('athlete_bib')
            value = request.form.get('value', '').strip()
            attempts = [request.form.get(f'attempt_{i}', '').strip() for i in range(1, 7)]

            print(f"Form data received - BIB: {athlete_bib}, Value: {value}, Attempts: {attempts}")

            errors = []

            if not athlete_bib:
                errors.append('Please select an athlete')
            else:
                try:
                    athlete_bib = int(athlete_bib)
                    athlete = Athlete.get_by_bib(athlete_bib)
                    if not athlete:
                        errors.append('Athlete not found')
                    print(f"Athlete found: {athlete}")
                except (ValueError, TypeError):
                    errors.append('Invalid athlete BIB')
            if game['event'] in Config.get_field_events() and not value:
                errors.append('Performance value is required for field events')

        except Exception as e:
            print(f"Unexpected error in result_add: {e}")
            traceback.print_exc()
            flash(f'Error adding result: {str(e)}', 'danger')
            return redirect(url_for('admin.game_results', id=game_id))

    @bp.route('/results/<int:id>/delete', methods=['POST'])
    @admin_required
    def result_delete(id):
        try:
            result = Result.get_by_id(id)
            if not result:
                flash('Result not found', 'danger')
                return redirect(url_for('admin.games_list'))

            game_id = result['game_id']

            Attempt.delete_by_result(id)

            Result.delete(id)

            flash('Result deleted successfully', 'success')
            return redirect(url_for('admin.game_results', id=game_id))

        except Exception as e:
            print(f"Error deleting result: {e}")
            traceback.print_exc()
            flash(f'Error deleting result: {str(e)}', 'danger')
            return redirect(url_for('admin.games_list'))
