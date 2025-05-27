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
import re  # ← AJOUT DE L'IMPORT RE


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
    search = request.args.get('search', '')
    if search:
        athletes = Athlete.search(search)
    else:
        athletes = Athlete.get_all()
    return render_template('admin/athletes/list.html', athletes=athletes, search=search)


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
    search = request.args.get('search', '')
    games = Game.get_with_status()

    if search:
        games = [g for g in games if
                 search.lower() in g['event'].lower() or
                 search.lower() in g['gender'].lower() or
                 search.lower() in g['classes'].lower() or
                 str(g['day']) in search]

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


@admin_bp.route('/games/<int:id>/status', methods=['POST'])
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


@admin_bp.route('/games/<int:id>/auto-rank', methods=['POST'])
@admin_required
def game_auto_rank(id):
    try:
        game = Game.get_by_id(id)
        if not game:
            return jsonify({'error': 'Game not found'}), 404

        # Get results with auto-ranking applied
        results = Result.get_all(game_id=id)

        # Update ranks in database
        for result in results:
            if result.get('auto_rank'):
                Result.update(result['id'], rank=result['auto_rank'])

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/games/<int:id>/publish', methods=['POST'])
@loc_required
def game_toggle_publish(id):
    try:
        new_status = Game.toggle_publish(id)
        return jsonify({'published': new_status})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Results Management
@admin_bp.route('/games/<int:id>/results')
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
                           is_field_event=game['event'] in Config.FIELD_EVENTS)


@admin_bp.route('/games/<int:game_id>/results/add', methods=['POST'])
@admin_required
def result_add(game_id):
    game = Game.get_by_id(game_id)
    if not game:
        flash('Game not found', 'danger')
        return redirect(url_for('admin.games_list'))

    # Récupérer les données du formulaire
    athlete_bib = request.form.get('athlete_bib')
    rank = request.form.get('rank', '').strip()
    value = request.form.get('value', '').strip()
    record = request.form.get('record', '').strip()

    # Validation des données
    errors = []

    # Validation athlete_bib
    if not athlete_bib:
        errors.append('Please select an athlete')
    else:
        try:
            athlete_bib = int(athlete_bib)
            athlete = Athlete.get_by_bib(athlete_bib)
            if not athlete:
                errors.append('Athlete not found')
        except (ValueError, TypeError):
            errors.append('Invalid athlete BIB')

    # Validation performance
    if not value:
        errors.append('Performance value is required')
    elif value not in Config.RESULT_SPECIAL_VALUES:
        # Validation du format selon le type d'événement
        if game['event'] in Config.FIELD_EVENTS:
            # Field events: XX.XX format
            if not re.match(r'^\d+(\.\d{1,2})?$', value):
                errors.append('Invalid performance format for field events. Use XX.XX (e.g., 15.67)')
        else:
            # Track events: M:SS.CS ou SS.CS format
            if not re.match(r'^(\d{1,2}:)?\d{1,2}\.\d{2}$', value):
                errors.append(
                    'Invalid performance format for track events. Use MM:SS.CS or SS.CS (e.g., 1:23.45 or 23.45)')

    # Si erreurs, les afficher et retourner
    if errors:
        for error in errors:
            flash(error, 'danger')
        return redirect(url_for('admin.game_results', id=game_id))

    # Traitement des tentatives pour les field events
    performance_value = value
    attempts_data = []

    if game['event'] in Config.FIELD_EVENTS:
        # Collecter les tentatives
        for i in range(1, 7):
            attempt_value = request.form.get(f'attempt_{i}', '').strip()
            if attempt_value:
                attempts_data.append({'number': i, 'value': attempt_value})

        # Si pas de performance manuelle mais des tentatives valides, calculer la meilleure
        if not value and attempts_data:
            valid_attempts = []
            for attempt in attempts_data:
                attempt_val = attempt['value']
                if attempt_val and attempt_val not in ['X', '-', 'O', '']:
                    try:
                        val = float(attempt_val)
                        valid_attempts.append(val)
                    except ValueError:
                        continue

            if valid_attempts:
                best_attempt = max(valid_attempts)
                performance_value = f"{best_attempt:.2f}"
            else:
                flash('No valid attempts found. Please enter at least one valid attempt or a performance value.',
                      'danger')
                return redirect(url_for('admin.game_results', id=game_id))

    # Vérifier si un résultat existe déjà pour cet athlète
    try:
        existing_result = execute_one(
            "SELECT id FROM results WHERE game_id = %s AND athlete_bib = %s",
            (game_id, athlete_bib)
        )
        if existing_result:
            # Supprimer l'ancien résultat et ses tentatives
            Attempt.delete_by_result(existing_result['id'])
            Result.delete(existing_result['id'])
    except Exception as e:
        print(f"Error checking existing result: {e}")

    # Créer le nouveau résultat
    data = {
        'game_id': game_id,
        'athlete_bib': athlete_bib,
        'rank': rank if rank else None,
        'value': performance_value,
        'record': record if record else None
    }

    try:
        result_id = Result.create(**data)

        if not result_id:
            flash('Error creating result', 'danger')
            return redirect(url_for('admin.game_results', id=game_id))

        # Sauvegarder les tentatives pour les field events
        if game['event'] in Config.FIELD_EVENTS and attempts_data:
            for attempt in attempts_data:
                try:
                    Attempt.create(result_id, attempt['number'], attempt['value'])
                except Exception as e:
                    print(f"Error saving attempt: {e}")

        flash('Result added successfully', 'success')

    except Exception as e:
        print(f"Error adding result: {e}")
        flash(f'Error adding result: {str(e)}', 'danger')

    return redirect(url_for('admin.game_results', id=game_id))


@admin_bp.route('/results/<int:id>/delete', methods=['POST'])
@admin_required
def result_delete(id):
    try:
        result = Result.get_by_id(id)
        if not result:
            flash('Result not found', 'danger')
            return redirect(url_for('admin.games_list'))

        game_id = result['game_id']

        # Supprimer les tentatives d'abord
        Attempt.delete_by_result(id)
        # Puis supprimer le résultat
        Result.delete(id)

        flash('Result deleted successfully', 'success')
        return redirect(url_for('admin.game_results', id=game_id))

    except Exception as e:
        print(f"Error deleting result: {e}")
        flash(f'Error deleting result: {str(e)}', 'danger')
        return redirect(url_for('admin.games_list'))


@admin_bp.route('/records')
@admin_required
def records_list():
    records = Result.get_records()
    return render_template('admin/records/list.html', records=records)


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


@admin_bp.route('/setup', methods=['GET'])
def setup():
    admin = User.get_by_username(Config.ADMIN_USERNAME)
    if not admin:
        User.create(Config.ADMIN_USERNAME, Config.ADMIN_PASSWORD, 'loc')
        flash('Admin user created successfully', 'success')
    else:
        flash('Admin user already exists', 'info')
    return redirect(url_for('admin.login'))