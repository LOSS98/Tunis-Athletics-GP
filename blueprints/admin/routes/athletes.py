# blueprints/admin/routes/athletes.py
from flask import render_template, redirect, url_for, flash, request, jsonify
from ..auth import admin_required
from ..forms import AthleteForm
from config import Config
from database.models import Athlete
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
    @admin_required
    def athletes_search():
        query = request.args.get('q', '')
        guides_only = request.args.get('guides')
        guides_only = guides_only in ['1', 'true', 'True']
        if query:
            allowed_classes = Config.get_guide_classes() if guides_only else None
            athletes = Athlete.search(query, guides_only=guides_only, allowed_classes=allowed_classes)
        else:
            athletes = []

        return jsonify([{
            'sdms': a['sdms'],
            'name': f"{a['firstname']} {a['lastname']}",
            'npc': a['npc'],
            'classes': a.get('classes_list', []),
            'class': a['class'],  # Pour compatibilité
            'gender': a['gender']
        } for a in athletes])

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
                'class': form.athlete_classes.data,  # Stocké comme chaîne séparée par des virgules
                'date_of_birth': form.date_of_birth.data,
                'region_code': form.region_code.data if form.region_code.data else None,
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
                'region_code': form.region_code.data if form.region_code.data else None,
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
            form.region_code.data = athlete['region_code']
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