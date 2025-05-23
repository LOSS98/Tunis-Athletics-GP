from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, current_user
from werkzeug.utils import secure_filename
from . import admin_bp
from .auth import admin_required
from .forms import LoginForm, AthleteForm, GameForm, ResultForm
from database.models import User, Athlete, Game, Result
from utils.helpers import allowed_file, save_uploaded_file
from config import Config
import os


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.verify_password(form.username.data, form.password.data)
        if user:
            login_user(user)
            return redirect(url_for('admin.dashboard'))
        flash('Invalid username or password', 'danger')

    return render_template('admin/login.html', form=form)


@admin_bp.route('/logout')
@admin_required
def logout():
    logout_user()
    return redirect(url_for('public.index'))


@admin_bp.route('/')
@admin_required
def dashboard():
    games = Game.get_with_status()
    athlete_count = len(Athlete.get_all())
    record_count = len(Result.get_records())
    return render_template('admin/dashboard.html',
                           games=games,
                           athlete_count=athlete_count,
                           record_count=record_count)


@admin_bp.route('/athletes')
@admin_required
def athletes_list():
    search = request.args.get('search', '')
    if search:
        athletes = Athlete.search(search)
    else:
        athletes = Athlete.get_all()
    return render_template('admin/athletes/list.html', athletes=athletes, search=search)


@admin_bp.route('/athletes/create', methods=['GET', 'POST'])
@admin_required
def athlete_create():
    form = AthleteForm()
    if form.validate_on_submit():
        data = {
            'bib': form.bib.data,
            'firstname': form.firstname.data,
            'lastname': form.lastname.data,
            'country': form.country.data.upper(),
            'gender': form.gender.data,
            'class': form.athlete_class.data
        }

        if form.photo.data:
            filename = save_uploaded_file(form.photo.data, 'athletes')
            if filename:
                data['photo'] = filename

        try:
            Athlete.create(**data)
            flash('Athlete created successfully', 'success')
            return redirect(url_for('admin.athletes_list'))
        except Exception as e:
            flash(f'Error creating athlete: {str(e)}', 'danger')

    return render_template('admin/athletes/create.html', form=form)


@admin_bp.route('/athletes/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def athlete_edit(id):
    athlete = Athlete.get_by_id(id)
    if not athlete:
        flash('Athlete not found', 'danger')
        return redirect(url_for('admin.athletes_list'))

    form = AthleteForm()

    if form.validate_on_submit():
        data = {
            'bib': form.bib.data,
            'firstname': form.firstname.data,
            'lastname': form.lastname.data,
            'country': form.country.data.upper(),
            'gender': form.gender.data,
            'class': form.athlete_class.data
        }

        if form.photo.data:
            filename = save_uploaded_file(form.photo.data, 'athletes')
            if filename:
                data['photo'] = filename
                if athlete['photo'] and os.path.exists(os.path.join('static/images/athletes', athlete['photo'])):
                    os.remove(os.path.join('static/images/athletes', athlete['photo']))

        try:
            Athlete.update(id, **data)
            flash('Athlete updated successfully', 'success')
            return redirect(url_for('admin.athletes_list'))
        except Exception as e:
            flash(f'Error updating athlete: {str(e)}', 'danger')

    elif request.method == 'GET':
        form.bib.data = athlete['bib']
        form.firstname.data = athlete['firstname']
        form.lastname.data = athlete['lastname']
        form.country.data = athlete['country']
        form.gender.data = athlete['gender']
        form.athlete_class.data = athlete['class']

    return render_template('admin/athletes/edit.html', form=form, athlete=athlete)


@admin_bp.route('/athletes/<int:id>/delete', methods=['POST'])
@admin_required
def athlete_delete(id):
    try:
        athlete = Athlete.get_by_id(id)
        if athlete and athlete['photo']:
            photo_path = os.path.join('static/images/athletes', athlete['photo'])
            if os.path.exists(photo_path):
                os.remove(photo_path)

        Athlete.delete(id)
        flash('Athlete deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting athlete: {str(e)}', 'danger')

    return redirect(url_for('admin.athletes_list'))


@admin_bp.route('/games')
@admin_required
def games_list():
    search = request.args.get('search', '')
    if search:
        games = Game.search(search)
    else:
        games = Game.get_with_status()
    return render_template('admin/games/list.html', games=games, search=search)


@admin_bp.route('/games/create', methods=['GET', 'POST'])
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
            'duration': form.duration.data,
            'nb_athletes': form.nb_athletes.data,
            'status': form.status.data
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


@admin_bp.route('/games/<int:id>/edit', methods=['GET', 'POST'])
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
            'duration': form.duration.data,
            'nb_athletes': form.nb_athletes.data,
            'status': form.status.data
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
        form.duration.data = game['duration']
        form.nb_athletes.data = game['nb_athletes']
        form.status.data = game['status']

    return render_template('admin/games/edit.html', form=form, game=game)


@admin_bp.route('/games/<int:id>/delete', methods=['POST'])
@admin_required
def game_delete(id):
    try:
        Game.delete(id)
        flash('Game deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting game: {str(e)}', 'danger')

    return redirect(url_for('admin.games_list'))


@admin_bp.route('/games/<int:id>/results')
@admin_required
def game_results(id):
    game = Game.get_by_id(id)
    if not game:
        flash('Game not found', 'danger')
        return redirect(url_for('admin.games_list'))

    results = Result.get_all(game_id=id)
    athletes = Athlete.get_all()
    form = ResultForm()

    return render_template('admin/results/manage.html',
                           game=game,
                           results=results,
                           athletes=athletes,
                           form=form)


@admin_bp.route('/games/<int:game_id>/results/add', methods=['POST'])
@admin_required
def result_add(game_id):
    form = ResultForm()
    if form.validate_on_submit():
        athlete = Athlete.get_by_bib(form.athlete_bib.data)
        if not athlete:
            flash('Athlete not found', 'danger')
            return redirect(url_for('admin.game_results', id=game_id))

        data = {
            'game_id': game_id,
            'athlete_bib': form.athlete_bib.data,
            'rank': form.rank.data,
            'value': form.value.data,
            'record': form.record.data if form.record.data else None
        }

        try:
            Result.delete_by_game_athlete(game_id, form.athlete_bib.data)
            Result.create(**data)
            flash('Result added successfully', 'success')
        except Exception as e:
            flash(f'Error adding result: {str(e)}', 'danger')

    return redirect(url_for('admin.game_results', id=game_id))


@admin_bp.route('/results/<int:id>/delete', methods=['POST'])
@admin_required
def result_delete(id):
    result = Result.get_by_id(id)
    if result:
        try:
            Result.delete(id)
            flash('Result deleted successfully', 'success')
        except Exception as e:
            flash(f'Error deleting result: {str(e)}', 'danger')
        return redirect(url_for('admin.game_results', id=result['game_id']))

    return redirect(url_for('admin.games_list'))


@admin_bp.route('/records')
@admin_required
def records_list():
    records = Result.get_records()
    return render_template('admin/records/list.html', records=records)


@admin_bp.route('/setup', methods=['GET'])
def setup():
    admin = User.get_by_username(Config.ADMIN_USERNAME)
    if not admin:
        User.create(Config.ADMIN_USERNAME, Config.ADMIN_PASSWORD)
        flash('Admin user created successfully', 'success')
    else:
        flash('Admin user already exists', 'info')
    return redirect(url_for('admin.login'))