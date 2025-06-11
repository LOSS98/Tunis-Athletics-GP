from flask import render_template, redirect, url_for, flash, request, jsonify
from ..auth import admin_required
from database.models import Registration, Athlete
from config import Config


def register_routes(bp):
    @bp.route('/registrations')
    @admin_required
    def registrations_list():
        search = request.args.get('search', '')
        event_filter = request.args.get('event_filter', '')

        filters = {}
        if search:
            filters['search'] = search
        if event_filter:
            filters['event_name'] = event_filter

        registrations = Registration.get_all(**filters)
        events = Registration.get_distinct_events()
        event_counts = Registration.count_by_event()

        return render_template('admin/registrations/list.html',
                               registrations=registrations,
                               events=events,
                               event_counts=event_counts,
                               search=search,
                               event_filter=event_filter)

    @bp.route('/registrations/add', methods=['GET', 'POST'])
    @admin_required
    def registration_add():
        if request.method == 'POST':
            sdms = request.form.get('sdms')
            event_name = request.form.get('event_name')

            if not sdms or not event_name:
                flash('SDMS and Event Name are required', 'danger')
                return redirect(url_for('admin.registration_add'))

            try:
                sdms = int(sdms)
                athlete = Athlete.get_by_sdms(sdms)
                if not athlete:
                    flash('Athlete not found', 'danger')
                    return redirect(url_for('admin.registration_add'))

                if Registration.exists(sdms, event_name):
                    flash(f'Athlete {sdms} is already registered for {event_name}', 'warning')
                    return redirect(url_for('admin.registration_add'))

                Registration.create(sdms, event_name)
                flash(
                    f'Registration added successfully for {athlete["firstname"]} {athlete["lastname"]} - {event_name}',
                    'success')
                return redirect(url_for('admin.registrations_list'))

            except ValueError:
                flash('Invalid SDMS number', 'danger')
            except Exception as e:
                flash(f'Error adding registration: {str(e)}', 'danger')

        events = Config.get_field_events() + Config.get_track_events()
        return render_template('admin/registrations/add.html', events=events)

    @bp.route('/athletes/<int:sdms>/registrations')
    @admin_required
    def athlete_registrations(sdms):
        athlete = Athlete.get_by_sdms(sdms)
        if not athlete:
            flash('Athlete not found', 'danger')
            return redirect(url_for('admin.athletes_list'))

        registrations = Registration.get_by_athlete(sdms)
        return render_template('admin/registrations/athlete.html',
                               athlete=athlete,
                               registrations=registrations)

    @bp.route('/athletes/<int:sdms>/registrations/add', methods=['POST'])
    @admin_required
    def add_athlete_registration(sdms):
        event_name = request.form.get('event_name')
        if not event_name:
            flash('Event name is required', 'danger')
            return redirect(url_for('admin.athlete_registrations', sdms=sdms))

        try:
            if Registration.exists(sdms, event_name):
                flash(f'Already registered for {event_name}', 'warning')
            else:
                Registration.create(sdms, event_name)
                flash(f'Registered for {event_name}', 'success')
        except Exception as e:
            flash(f'Error adding registration: {str(e)}', 'danger')

        return redirect(url_for('admin.athlete_registrations', sdms=sdms))

    @bp.route('/athletes/<int:sdms>/registrations/<event_name>/delete', methods=['POST'])
    @admin_required
    def delete_athlete_registration(sdms, event_name):
        try:
            Registration.delete(sdms, event_name)
            flash(f'Registration for {event_name} removed', 'success')
        except Exception as e:
            flash(f'Error removing registration: {str(e)}', 'danger')

        return redirect(url_for('admin.athlete_registrations', sdms=sdms))

    @bp.route('/registrations/<int:sdms>/<event_name>/delete', methods=['POST'])
    @admin_required
    def registration_delete(sdms, event_name):
        try:
            Registration.delete(sdms, event_name)
            flash('Registration deleted successfully', 'success')
        except Exception as e:
            flash(f'Error deleting registration: {str(e)}', 'danger')
        return redirect(url_for('admin.registrations_list'))

    @bp.route('/api/events/list')
    @admin_required
    def api_events_list():
        try:
            events = Registration.get_distinct_events()
            return jsonify(events)
        except Exception as e:
            print(f"Error getting events list: {e}")
            return jsonify([])