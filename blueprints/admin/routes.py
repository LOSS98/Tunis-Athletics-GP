from flask import render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_user, logout_user, current_user
from werkzeug.utils import secure_filename
from . import admin_bp
from .auth import admin_required, loc_required
from .forms import LoginForm, UserForm, AthleteForm, GameForm, ResultForm, StartListForm
from database.models import User, Athlete, Game, Result, Attempt, StartList
from database.db_manager import execute_one
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
    stats = {
        'countries': Config.COUNTRIES_COUNT,
        'athletes': Config.ATHLETES_COUNT,
        'volunteers': Config.VOLUNTEERS_COUNT,
        'loc': Config.LOC_COUNT,
        'officials': Config.OFFICIALS_COUNT
    }
    return render_template('admin/dashboard.html', games=games, stats=stats)


# User Management (LOC only)
@admin_bp.route('/users')
@loc_required
def users_list():
    users = User.get_all()
    return render_template('admin/users/list.html', users=users)


@admin_bp.route('/users/create', methods=['GET', 'POST'])
@loc_required
def user_create():
    form = UserForm()
    if form.validate_on_submit():
        try:
            User.create(
                form.username.data,
                form.password.data,
                form.admin_type.data
            )
            flash('User created successfully', 'success')
            return redirect(url_for('admin.users_list'))
        except Exception as e:
            flash(f'Error creating user: {str(e)}', 'danger')

    return render_template('admin/users/create.html', form=form)


@admin_bp.route('/users/<int:id>/edit', methods=['GET', 'POST'])
@loc_required
def user_edit(id):
    user = execute_one("SELECT * FROM users WHERE id = %s", (id,))
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('admin.users_list'))

    form = UserForm()
    if form.validate_on_submit():
        data = {'admin_type': form.admin_type.data}
        if form.password.data:
            data['password'] = form.password.data

        try:
            User.update(id, **data)
            flash('User updated successfully', 'success')
            return redirect(url_for('admin.users_list'))
        except Exception as e:
            flash(f'Error updating user: {str(e)}', 'danger')

    elif request.method == 'GET':
        form.username.data = user['username']
        form.admin_type.data = user.get('admin_type', 'volunteer')

    return render_template('admin/users/edit.html', form=form, user=user)


@admin_bp.route('/users/<int:id>/delete', methods=['POST'])
@loc_required
def user_delete(id):
    try:
        User.delete(id)
        flash('User deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting user: {str(e)}', 'danger')

    return redirect(url_for('admin.users_list'))


# Athletes Management
@admin_bp.route('/athletes')
@admin_required
def athletes_list():
    athletes = Athlete.get_all()
    return render_template('admin/athletes/list.html', athletes=athletes)


@admin_bp.route('/athletes/search')
@admin_required
def athletes_search():
    query = request.args.get('q', '')
    if query:
        athletes = Athlete.search(query)
    else:
        athletes = []

    return jsonify([{
        'id': a['id'],
        'bib': a['bib'],
        'name': f"{a['firstname']} {a['lastname']}",
        'country': a['country'],
        'class': a['class'],
        'gender': a['gender']
    } for a in athletes])


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


# Games Management
@admin_bp.route('/games')
@admin_required
def games_list():
    games = Game.get_with_status()
    return render_template('admin/games/list.html', games=games)


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


@admin_bp.route('/games/<int:id>/delete', methods=['POST'])
@admin_required
def game_delete(id):
    try:
        Game.delete(id)
        flash('Game deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting game: {str(e)}', 'danger')

    return redirect(url_for('admin.games_list'))


@admin_bp.route('/games/<int:id>/toggle-publish', methods=['POST'])
@loc_required
def game_toggle_publish(id):
    try:
        new_status = Game.toggle_publish(id)
        flash(f'Game {"published" if new_status else "unpublished"} successfully', 'success')
    except Exception as e:
        flash(f'Error toggling publish status: {str(e)}', 'danger')

    return redirect(url_for('admin.games_list'))


@admin_bp.route('/games/<int:id>/update-status', methods=['POST'])
@admin_required
def game_update_status(id):
    status = request.form.get('status')
    if status in ['scheduled', 'started', 'in_progress', 'finished', 'cancelled']:
        try:
            Game.update_status(id, status)
            flash('Game status updated successfully', 'success')
        except Exception as e:
            flash(f'Error updating status: {str(e)}', 'danger')
    else:
        flash('Invalid status', 'danger')

    return redirect(request.referrer or url_for('admin.games_list'))


# Start List Management
@admin_bp.route('/games/<int:id>/startlist')
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


@admin_bp.route('/games/<int:game_id>/startlist/add', methods=['POST'])
@admin_required
def startlist_add(game_id):
    form = StartListForm()
    if form.validate_on_submit():
        game = Game.get_by_id(game_id)
        athlete = Athlete.get_by_bib(form.athlete_bib.data)

        if not athlete:
            flash('Athlete not found', 'danger')
        else:
            # Check if athlete class matches game classes
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


@admin_bp.route('/games/<int:game_id>/startlist/<int:athlete_bib>/delete', methods=['POST'])
@admin_required
def startlist_delete(game_id, athlete_bib):
    try:
        StartList.delete(game_id, athlete_bib)
        flash('Athlete removed from start list', 'success')
    except Exception as e:
        flash(f'Error removing from start list: {str(e)}', 'danger')

    return redirect(url_for('admin.game_startlist', id=game_id))


# Results Management
@admin_bp.route('/games/<int:id>/results')
@admin_required
def game_results(id):
    game = Game.get_by_id(id)
    if not game:
        flash('Game not found', 'danger')
        return redirect(url_for('admin.games_list'))

    results = Result.get_all(game_id=id)

    # Get attempts for field events
    if game['event'] in Config.FIELD_EVENTS:
        for result in results:
            result['attempts'] = Attempt.get_by_result(result['id'])

    startlist = StartList.get_by_game(id)
    form = ResultForm()

    return render_template('admin/results/manage.html',
                           game=game,
                           results=results,
                           startlist=startlist,
                           form=form,
                           is_field_event=game['event'] in Config.FIELD_EVENTS)


@admin_bp.route('/games/<int:game_id>/results/add', methods=['POST'])
@admin_required
def result_add(game_id):
    game = Game.get_by_id(game_id)
    form = ResultForm()

    if form.validate_on_submit():
        athlete = Athlete.get_by_bib(form.athlete_bib.data)
        if not athlete:
            flash('Athlete not found', 'danger')
            return redirect(url_for('admin.game_results', id=game_id))

        # Validate performance format
        if not Result.validate_performance(form.value.data, game['event']):
            if game['event'] in Config.FIELD_EVENTS:
                flash('Invalid performance format. Use XX.XX for field events', 'danger')
            else:
                flash('Invalid performance format. Use M:SS.CS or SS.CS for track events', 'danger')
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
            result_id = Result.create(**data)

            # If field event, save attempts
            if game['event'] in Config.FIELD_EVENTS and result_id:
                for i, attempt_form in enumerate(form.attempts):
                    if attempt_form.value.data:
                        Attempt.create(result_id, i + 1, attempt_form.value.data)

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
            # Delete attempts first
            Attempt.delete_by_result(id)
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
        User.create(Config.ADMIN_USERNAME, Config.ADMIN_PASSWORD, 'loc')
        flash('Admin user created successfully', 'success')
    else:
        flash('Admin user already exists', 'info')
    return redirect(url_for('admin.login'))