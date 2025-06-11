from flask import render_template, redirect, url_for, flash, request, jsonify
from ..auth import admin_required
from ..forms import AthleteForm
from config import Config
from database.models import Athlete, Registration
from database.db_manager import execute_query
from utils.helpers import save_uploaded_file
import os

def register_routes(bp):
    @bp.route('/athletes')
    @admin_required
    def athletes_list():
        search = request.args.get('search', '')
        if search:
            athletes = Athlete.search(search)
        else:
            athletes = Athlete.get_all()
        return render_template('admin/athletes/list.html', athletes=athletes, search=search)

    @bp.route('/athletes/search')
    @bp.route('/api/athletes/search')
    @admin_required
    def api_search_athletes():
        query = request.args.get('q', '').strip()
        guides_only = (request.args.get('guides_only', 'false').lower() == 'true' or
                       request.args.get('guides', '0') == '1')
        event_filter = request.args.get('event_filter', '').strip()

        if not query:
            return jsonify([])

        try:
            # Handle wildcard search for event filtering
            if query == '*' and event_filter:
                athletes = execute_query("""
                    SELECT a.*, COALESCE(STRING_AGG(DISTINCT reg.event_name, ', ' ORDER BY reg.event_name), '') as registered_events
                    FROM athletes a
                    JOIN registrations reg ON a.sdms = reg.sdms
                    WHERE reg.event_name = %s
                    GROUP BY a.sdms, a.firstname, a.lastname, a.npc, a.gender, a.class, a.date_of_birth, a.photo, a.is_guide, a.created_at
                    ORDER BY a.sdms
                """, (event_filter,), fetch=True)
            else:
                athletes = Athlete.search(query, guides_only, event_filter=event_filter)

            results = []
            for athlete in athletes:
                # Add classes_list processing
                if athlete.get('class'):
                    athlete['classes_list'] = [c.strip() for c in athlete['class'].split(',')]
                else:
                    athlete['classes_list'] = []

                result = {
                    'sdms': athlete['sdms'],
                    'firstname': athlete['firstname'],
                    'lastname': athlete['lastname'],
                    'name': f"{athlete['firstname']} {athlete['lastname']}",
                    'npc': athlete['npc'],
                    'gender': athlete['gender'],
                    'class': athlete['class'],
                    'classes_list': athlete['classes_list'],
                    'is_guide': athlete.get('is_guide', False),
                    'registered_events': athlete.get('registered_events', '')
                }
                results.append(result)
            return jsonify(results)
        except Exception as e:
            print(f"Error in athlete search: {e}")
            return jsonify([]), 500

    @bp.route('/athletes/create', methods=['GET', 'POST'])
    @admin_required
    def athlete_create():
        form = AthleteForm()
        if form.validate_on_submit():
            data = {
                'sdms': form.sdms.data,
                'firstname': form.firstname.data,
                'lastname': form.lastname.data,
                'npc': form.npc.data.upper(),
                'gender': form.gender.data,
                'class': form.athlete_classes.data,
                'date_of_birth': form.date_of_birth.data,
                'is_guide': form.is_guide.data
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

    @bp.route('/athletes/<int:sdms>/edit', methods=['GET', 'POST'])
    @admin_required
    def athlete_edit(sdms):
        athlete = Athlete.get_by_sdms(sdms)
        if not athlete:
            flash('Athlete not found', 'danger')
            return redirect(url_for('admin.athletes_list'))
        form = AthleteForm()
        if form.validate_on_submit():
            data = {
                'firstname': form.firstname.data,
                'lastname': form.lastname.data,
                'npc': form.npc.data.upper(),
                'gender': form.gender.data,
                'class': form.athlete_classes.data,
                'date_of_birth': form.date_of_birth.data,
                'is_guide': form.is_guide.data
            }
            if form.photo.data:
                filename = save_uploaded_file(form.photo.data, 'athletes')
                if filename:
                    data['photo'] = filename
                    if athlete['photo'] and os.path.exists(os.path.join('static/images/athletes', athlete['photo'])):
                        os.remove(os.path.join('static/images/athletes', athlete['photo']))
            try:
                Athlete.update(sdms, **data)
                flash('Athlete updated successfully', 'success')
                return redirect(url_for('admin.athletes_list'))
            except Exception as e:
                flash(f'Error updating athlete: {str(e)}', 'danger')
        elif request.method == 'GET':
            form.sdms.data = athlete['sdms']
            form.firstname.data = athlete['firstname']
            form.lastname.data = athlete['lastname']
            form.npc.data = athlete['npc']
            form.gender.data = athlete['gender']
            form.athlete_classes.data = athlete['class']
            form.date_of_birth.data = athlete['date_of_birth']
            form.is_guide.data = athlete['is_guide']
        return render_template('admin/athletes/edit.html', form=form, athlete=athlete)

    @bp.route('/athletes/<int:sdms>/delete', methods=['POST'])
    @admin_required
    def athlete_delete(sdms):
        try:
            athlete = Athlete.get_by_sdms(sdms)
            if athlete and athlete['photo']:
                photo_path = os.path.join('static/images/athletes', athlete['photo'])
                if os.path.exists(photo_path):
                    os.remove(photo_path)
            Athlete.delete(sdms)
            flash('Athlete deleted successfully', 'success')
        except Exception as e:
            flash(f'Error deleting athlete: {str(e)}', 'danger')
        return redirect(url_for('admin.athletes_list'))