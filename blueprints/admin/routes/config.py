from flask import render_template, redirect, url_for, flash, request, jsonify
from ..auth import admin_required, loc_required
from ..config_forms import StatsConfigForm, CompetitionDayForm, CurrentDayForm, CountryForm, RecordTypeForm
from database.config_manager import ConfigManager, clear_config_cache
from config import Config
from datetime import date


def register_routes(bp):
    @bp.route('/config')
    @loc_required
    def config_index():
        configs = ConfigManager.get_all_config()
        days = ConfigManager.get_competition_days()
        countries = ConfigManager.get_countries()
        current_day = ConfigManager.get_current_competition_day()

        return render_template('admin/config/index.html',
                               configs=configs,
                               days=days,
                               countries=countries,
                               current_day=current_day)

    @bp.route('/config/general')
    @loc_required
    def config_general():
        configs = ConfigManager.get_all_config()
        return render_template('admin/config/general.html', configs=configs)

    @bp.route('/config/api/add-tag', methods=['POST'])
    @loc_required
    def config_add_tag():
        try:
            data = request.get_json()
            config_key = data.get('config_key')
            tag_value = data.get('tag_value')

            if not config_key or not tag_value:
                return jsonify({'success': False, 'error': 'Missing parameters'}), 400

            existing_tags = ConfigManager.get_config_tags(config_key)
            if tag_value in existing_tags:
                return jsonify({'success': False, 'error': 'Tag already exists'}), 400

            success = ConfigManager.add_config_tag(config_key, tag_value)
            clear_config_cache()

            if success:
                return jsonify({'success': True})
            else:
                return jsonify({'success': False, 'error': 'Failed to add tag'}), 500

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @bp.route('/config/api/remove-tag', methods=['POST'])
    @loc_required
    def config_remove_tag():
        try:
            data = request.get_json()
            config_key = data.get('config_key')
            tag_value = data.get('tag_value')

            if not config_key or not tag_value:
                return jsonify({'success': False, 'error': 'Missing parameters'}), 400

            ConfigManager.remove_config_tag(config_key, tag_value)
            clear_config_cache()

            return jsonify({'success': True})

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @bp.route('/config/stats', methods=['GET', 'POST'])
    @loc_required
    def config_stats():
        form = StatsConfigForm()

        if form.validate_on_submit():
            ConfigManager.set_config('countries_count', form.countries_count.data, 'integer')
            ConfigManager.set_config('athletes_count', form.athletes_count.data, 'integer')
            ConfigManager.set_config('volunteers_count', form.volunteers_count.data, 'integer')
            ConfigManager.set_config('loc_count', form.loc_count.data, 'integer')
            ConfigManager.set_config('officials_count', form.officials_count.data, 'integer')
            clear_config_cache()

            flash('Statistics updated successfully', 'success')
            return redirect(url_for('admin.config_index'))

        elif request.method == 'GET':
            form.countries_count.data = ConfigManager.get_config('countries_count', 61)
            form.athletes_count.data = ConfigManager.get_config('athletes_count', 529)
            form.volunteers_count.data = ConfigManager.get_config('volunteers_count', 50)
            form.loc_count.data = ConfigManager.get_config('loc_count', 15)
            form.officials_count.data = ConfigManager.get_config('officials_count', 80)

        return render_template('admin/config/stats.html', form=form)

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
            ConfigManager.set_competition_day(
                form.day_number.data,
                form.date_start.data,
                form.date_end.data,
                form.description.data
            )
            flash('Competition day added successfully', 'success')
            return redirect(url_for('admin.config_days'))

        return render_template('admin/config/day_form.html', form=form, title='Add Competition Day')

    @bp.route('/config/days/<int:day_number>/edit', methods=['GET', 'POST'])
    @loc_required
    def config_day_edit(day_number):
        days = ConfigManager.get_competition_days()
        day = next((d for d in days if d['day_number'] == day_number), None)

        if not day:
            flash('Competition day not found', 'danger')
            return redirect(url_for('admin.config_days'))

        form = CompetitionDayForm()

        if form.validate_on_submit():
            ConfigManager.set_competition_day(
                form.day_number.data,
                form.date_start.data,
                form.date_end.data,
                form.description.data
            )
            flash('Competition day updated successfully', 'success')
            return redirect(url_for('admin.config_days'))

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
        ConfigManager.delete_competition_day(day_number)
        flash('Competition day deleted successfully', 'success')
        return redirect(url_for('admin.config_days'))

    @bp.route('/config/current-day', methods=['GET', 'POST'])
    @loc_required
    def config_current_day():
        form = CurrentDayForm()

        if form.validate_on_submit():
            ConfigManager.set_config('current_day', form.current_day.data, 'integer')
            clear_config_cache()
            flash('Current day updated successfully', 'success')
            return redirect(url_for('admin.config_index'))

        elif request.method == 'GET':
            form.current_day.data = ConfigManager.get_current_competition_day()

        return render_template('admin/config/current_day.html', form=form)

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
            ConfigManager.create_country(
                form.code.data,
                form.name.data,
                form.continent.data,
                form.flag_available.data
            )
            flash('Country added successfully', 'success')
            return redirect(url_for('admin.config_countries'))

        return render_template('admin/config/country_form.html', form=form, title='Add Country')

    @bp.route('/config/countries/<int:country_id>/edit', methods=['GET', 'POST'])
    @loc_required
    def config_country_edit(country_id):
        countries = ConfigManager.get_countries()
        country = next((c for c in countries if c['id'] == country_id), None)

        if not country:
            flash('Country not found', 'danger')
            return redirect(url_for('admin.config_countries'))

        form = CountryForm()

        if form.validate_on_submit():
            ConfigManager.update_country(
                country_id,
                form.code.data,
                form.name.data,
                form.continent.data,
                form.flag_available.data
            )
            flash('Country updated successfully', 'success')
            return redirect(url_for('admin.config_countries'))

        elif request.method == 'GET':
            form.code.data = country['code']
            form.name.data = country['name']
            form.continent.data = country['continent']
            form.flag_available.data = country['flag_available']

        return render_template('admin/config/country_form.html', form=form, title='Edit Country', country=country)

    @bp.route('/config/countries/<int:country_id>/delete', methods=['POST'])
    @loc_required
    def config_country_delete(country_id):
        ConfigManager.delete_country(country_id)
        flash('Country deleted successfully', 'success')
        return redirect(url_for('admin.config_countries'))

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
            ConfigManager.create_record_type(
                form.abbreviation.data,
                form.full_name.data,
                form.scope_type.data,
                form.scope_values.data,
                form.description.data
            )
            flash('Record type added successfully', 'success')
            return redirect(url_for('admin.config_record_types'))

        return render_template('admin/config/record_type_form.html', form=form, title='Add Record Type')

    @bp.route('/config/record-types/<int:record_type_id>/edit', methods=['GET', 'POST'])
    @loc_required
    def config_record_type_edit(record_type_id):
        record_types = ConfigManager.get_record_types_with_details()
        record_type = next((rt for rt in record_types if rt['id'] == record_type_id), None)

        if not record_type:
            flash('Record type not found', 'danger')
            return redirect(url_for('admin.config_record_types'))

        form = RecordTypeForm()

        if form.validate_on_submit():
            ConfigManager.update_record_type(
                record_type_id,
                form.abbreviation.data,
                form.full_name.data,
                form.scope_type.data,
                form.scope_values.data,
                form.description.data
            )
            flash('Record type updated successfully', 'success')
            return redirect(url_for('admin.config_record_types'))

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
        ConfigManager.delete_record_type(record_type_id)
        flash('Record type deleted successfully', 'success')
        return redirect(url_for('admin.config_record_types'))

    @bp.route('/config/reset-cache', methods=['POST'])
    @loc_required
    def config_reset_cache():
        clear_config_cache()
        flash('Configuration cache cleared successfully', 'success')
        return redirect(url_for('admin.config_index'))
