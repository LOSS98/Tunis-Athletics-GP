from flask import render_template, redirect, url_for, flash, request, jsonify
from ..auth import admin_required
from ..forms import AthleteForm
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

    @bp.route('/athletes/create', methods=['GET', 'POST'])
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

    @bp.route('/athletes/<int:id>/edit', methods=['GET', 'POST'])
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

    @bp.route('/athletes/<int:id>/delete', methods=['POST'])
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
