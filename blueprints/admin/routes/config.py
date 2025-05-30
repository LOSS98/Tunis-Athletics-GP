from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user
from ..auth import loc_required
from ..config_forms import ConfigForm, StatsConfigForm, CompetitionDayForm, CurrentDayForm, CountryForm, RecordTypeForm
from database.config_manager import ConfigManager, clear_config_cache
from database.db_manager import execute_one, execute_query


def register_routes(bp):
    @bp.route('/config')
    @loc_required
    def config_index():
        configs = ConfigManager.get_all_config()
        days = ConfigManager.get_competition_days()
        current_day = ConfigManager.get_current_competition_day()
        countries = ConfigManager.get_countries()
        record_types = ConfigManager.get_record_types_with_details()

        return render_template('admin/config/index.html',
                               configs=configs,
                               days=days,
                               current_day=current_day,
                               countries=countries,
                               record_types=record_types)

    @bp.route('/config/general', methods=['GET', 'POST'])
    @loc_required
    def config_general():
        configs = ConfigManager.get_all_config()
        return render_template('admin/config/general.html', configs=configs)

    @bp.route('/config/api/add-tag', methods=['POST'])
    @loc_required
    def config_add_tag():
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400

            config_key = data.get('config_key')
            tag_value = data.get('tag_value')

            if not config_key or not tag_value:
                return jsonify({'error': 'Missing config_key or tag_value'}), 400

            tag_value = tag_value.strip()
            if not tag_value:
                return jsonify({'error': 'Tag value cannot be empty'}), 400

            existing = execute_one(
                "SELECT id FROM config_tags WHERE config_key = %s AND tag_value = %s",
                (config_key, tag_value)
            )

            if existing:
                return jsonify({'error': 'Tag already exists'}), 400

            execute_query(
                "INSERT INTO config_tags (config_key, tag_value) VALUES (%s, %s)",
                (config_key, tag_value)
            )

            clear_config_cache()
            return jsonify({'success': True, 'message': 'Tag added successfully'})

        except Exception as e:
            print(f"Error adding tag: {e}")
            return jsonify({'error': 'Server error occurred'}), 500

    @bp.route('/config/api/remove-tag', methods=['POST'])
    @loc_required
    def config_remove_tag():
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400

            config_key = data.get('config_key')
            tag_value = data.get('tag_value')

            if not config_key or not tag_value:
                return jsonify({'error': 'Missing config_key or tag_value'}), 400

            result = execute_query(
                "DELETE FROM config_tags WHERE config_key = %s AND tag_value = %s",
                (config_key, tag_value)
            )

            clear_config_cache()
            return jsonify({'success': True, 'message': 'Tag removed successfully'})

        except Exception as e:
            print(f"Error removing tag: {e}")
            return jsonify({'error': 'Server error occurred'}), 500

    @bp.route('/config/stats', methods=['GET', 'POST'])
    @loc_required
    def config_stats():
        form = StatsConfigForm()

        if form.validate_on_submit():
            try:
                ConfigManager.set_config('countries_count', form.countries_count.data, 'integer',
                                         'Number of participating countries', current_user.id)
                ConfigManager.set_config('athletes_count', form.athletes_count.data, 'integer',
                                         'Number of registered athletes', current_user.id)
                ConfigManager.set_config('volunteers_count', form.volunteers_count.data, 'integer',
                                         'Number of volunteers', current_user.id)
                ConfigManager.set_config('loc_count', form.loc_count.data, 'integer',
                                         'Number of LOC members', current_user.id)
                ConfigManager.set_config('officials_count', form.officials_count.data, 'integer',
                                         'Number of officials', current_user.id)

                clear_config_cache()
                flash('Statistics updated successfully', 'success')
                return redirect(url_for('admin.config_index'))
            except Exception as e:
                flash(f'Error updating statistics: {str(e)}', 'danger')

        elif request.method == 'GET':
            configs = ConfigManager.get_all_config()
            form.countries_count.data = configs.get('countries_count', 61)
            form.athletes_count.data = configs.get('athletes_count', 529)
            form.volunteers_count.data = configs.get('volunteers_count', 50)
            form.loc_count.data = configs.get('loc_count', 15)
            form.officials_count.data = configs.get('officials_count', 80)

        return render_template('admin/config/stats.html', form=form)

    @bp.route('/config/record-types')
    @loc_required
    def config_record_types():
        record_types = ConfigManager.get_record_types_with_details()
        return render_template('admin/config/record_types.html', record_types=record_types)

    @bp.route('/config/record-types/add', methods=['GET', 'POST'])
    @loc_required
    def config_record_type_add():
        form = RecordTypeForm()

        if form.validate_on_submit():
            try:
                existing = execute_one(
                    "SELECT id FROM record_types WHERE abbreviation = %s",
                    (form.abbreviation.data.upper(),)
                )
                if existing:
                    flash('Record type abbreviation already exists', 'danger')
                    return render_template('admin/config/record_type_form.html', form=form, title='Add Record Type')

                ConfigManager.create_record_type(
                    form.abbreviation.data.upper(),
                    form.full_name.data,
                    form.scope_type.data,
                    form.scope_values.data,
                    form.description.data
                )
                flash('Record type added successfully', 'success')
                return redirect(url_for('admin.config_record_types'))
            except Exception as e:
                flash(f'Error adding record type: {str(e)}', 'danger')

        return render_template('admin/config/record_type_form.html', form=form, title='Add Record Type')

    @bp.route('/config/record-types/<int:record_type_id>/edit', methods=['GET', 'POST'])
    @loc_required
    def config_record_type_edit(record_type_id):
        record_type = execute_one("SELECT * FROM record_types WHERE id = %s", (record_type_id,))
        if not record_type:
            flash('Record type not found', 'danger')
            return redirect(url_for('admin.config_record_types'))

        form = RecordTypeForm()

        if form.validate_on_submit():
            try:
                existing = execute_one(
                    "SELECT id FROM record_types WHERE abbreviation = %s AND id != %s",
                    (form.abbreviation.data.upper(), record_type_id)
                )
                if existing:
                    flash('Record type abbreviation already exists', 'danger')
                    return render_template('admin/config/record_type_form.html', form=form, title='Edit Record Type',
                                           record_type=record_type)

                ConfigManager.update_record_type(
                    record_type_id,
                    form.abbreviation.data.upper(),
                    form.full_name.data,
                    form.scope_type.data,
                    form.scope_values.data,
                    form.description.data
                )
                flash('Record type updated successfully', 'success')
                return redirect(url_for('admin.config_record_types'))
            except Exception as e:
                flash(f'Error updating record type: {str(e)}', 'danger')

        elif request.method == 'GET':
            form.abbreviation.data = record_type['abbreviation']
            form.full_name.data = record_type['full_name']
            form.scope_type.data = record_type['scope_type']
            form.scope_values.data = record_type['scope_values']
            form.description.data = record_type['description']

        return render_template('admin/config/record_type_form.html', form=form, title='Edit Record Type',
                               record_type=record_type)

    @bp.route('/config/record-types/<int:record_type_id>/delete', methods=['POST'])
    @loc_required
    def config_record_type_delete(record_type_id):
        try:
            ConfigManager.delete_record_type(record_type_id)
            flash('Record type deleted successfully', 'success')
        except Exception as e:
            flash(f'Error deleting record type: {str(e)}', 'danger')

        return redirect(url_for('admin.config_record_types'))

    @bp.route('/config/countries')
    @loc_required
    def config_countries():
        countries = ConfigManager.get_countries()
        return render_template('admin/config/countries.html', countries=countries)

    @bp.route('/config/countries/add', methods=['GET', 'POST'])
    @loc_required
    def config_country_add():
        form = CountryForm()

        if form.validate_on_submit():
            try:
                existing = ConfigManager.get_country_by_code(form.code.data.upper())
                if existing:
                    flash('Country code already exists', 'danger')
                    return render_template('admin/config/country_form.html', form=form, title='Add Country')

                ConfigManager.create_country(
                    form.code.data.upper(),
                    form.name.data,
                    form.continent.data,
                    form.flag_available.data
                )
                flash('Country added successfully', 'success')
                return redirect(url_for('admin.config_countries'))
            except Exception as e:
                flash(f'Error adding country: {str(e)}', 'danger')

        return render_template('admin/config/country_form.html', form=form, title='Add Country')

    @bp.route('/config/countries/<int:country_id>/edit', methods=['GET', 'POST'])
    @loc_required
    def config_country_edit(country_id):
        country = execute_one("SELECT * FROM countries WHERE id = %s", (country_id,))
        if not country:
            flash('Country not found', 'danger')
            return redirect(url_for('admin.config_countries'))

        form = CountryForm()

        if form.validate_on_submit():
            try:
                existing = execute_one(
                    "SELECT id FROM countries WHERE code = %s AND id != %s",
                    (form.code.data.upper(), country_id)
                )
                if existing:
                    flash('Country code already exists', 'danger')
                    return render_template('admin/config/country_form.html', form=form, title='Edit Country',
                                           country=country)

                ConfigManager.update_country(
                    country_id,
                    form.code.data.upper(),
                    form.name.data,
                    form.continent.data,
                    form.flag_available.data
                )
                flash('Country updated successfully', 'success')
                return redirect(url_for('admin.config_countries'))
            except Exception as e:
                flash(f'Error updating country: {str(e)}', 'danger')

        elif request.method == 'GET':
            form.code.data = country['code']
            form.name.data = country['name']
            form.continent.data = country['continent']
            form.flag_available.data = country['flag_available']

        return render_template('admin/config/country_form.html', form=form, title='Edit Country', country=country)

    @bp.route('/config/countries/<int:country_id>/delete', methods=['POST'])
    @loc_required
    def config_country_delete(country_id):
        try:
            ConfigManager.delete_country(country_id)
            flash('Country deleted successfully', 'success')
        except Exception as e:
            flash(f'Error deleting country: {str(e)}', 'danger')

        return redirect(url_for('admin.config_countries'))

    @bp.route('/config/days')
    @loc_required
    def config_days():
        days = ConfigManager.get_competition_days()
        current_day = ConfigManager.get_current_competition_day()

        return render_template('admin/config/days.html', days=days, current_day=current_day)

    @bp.route('/config/days/add', methods=['GET', 'POST'])
    @loc_required
    def config_day_add():
        form = CompetitionDayForm()

        if form.validate_on_submit():
            try:
                ConfigManager.set_competition_day(
                    form.day_number.data,
                    form.date_start.data,
                    form.date_end.data,
                    form.description.data
                )
                flash('Competition day added successfully', 'success')
                return redirect(url_for('admin.config_days'))
            except Exception as e:
                flash(f'Error adding competition day: {str(e)}', 'danger')

        return render_template('admin/config/day_form.html', form=form, title='Add Competition Day')

    @bp.route('/config/days/<int:day_number>/edit', methods=['GET', 'POST'])
    @loc_required
    def config_day_edit(day_number):
        day = execute_one(
            "SELECT * FROM competition_days WHERE day_number = %s",
            (day_number,)
        )

        if not day:
            flash('Competition day not found', 'danger')
            return redirect(url_for('admin.config_days'))

        form = CompetitionDayForm()

        if form.validate_on_submit():
            try:
                ConfigManager.set_competition_day(
                    form.day_number.data,
                    form.date_start.data,
                    form.date_end.data,
                    form.description.data
                )
                flash('Competition day updated successfully', 'success')
                return redirect(url_for('admin.config_days'))
            except Exception as e:
                flash(f'Error updating competition day: {str(e)}', 'danger')

        elif request.method == 'GET':
            form.day_number.data = day['day_number']
            form.date_start.data = day['date_start']
            form.date_end.data = day['date_end']
            form.description.data = day['description']
            form.is_active.data = day.get('is_active', True)

        return render_template('admin/config/day_form.html', form=form, title='Edit Competition Day', day=day)

    @bp.route('/config/days/<int:day_number>/delete', methods=['POST'])
    @loc_required
    def config_day_delete(day_number):
        try:
            ConfigManager.delete_competition_day(day_number)
            flash('Competition day deleted successfully', 'success')
        except Exception as e:
            flash(f'Error deleting competition day: {str(e)}', 'danger')

        return redirect(url_for('admin.config_days'))

    @bp.route('/config/current-day', methods=['GET', 'POST'])
    @loc_required
    def config_current_day():
        form = CurrentDayForm()

        if form.validate_on_submit():
            try:
                ConfigManager.set_config('current_day', form.current_day.data, 'integer',
                                         'Manually set current day', current_user.id)
                clear_config_cache()
                flash('Current day updated successfully', 'success')
                return redirect(url_for('admin.config_index'))
            except Exception as e:
                flash(f'Error updating current day: {str(e)}', 'danger')

        elif request.method == 'GET':
            form.current_day.data = ConfigManager.get_config('current_day', 1)

        return render_template('admin/config/current_day.html', form=form)

    @bp.route('/config/reset-cache', methods=['POST'])
    @loc_required
    def config_reset_cache():
        clear_config_cache()
        flash('Configuration cache cleared successfully', 'success')
        return redirect(url_for('admin.config_index'))