from flask import render_template, redirect, url_for, flash, request, jsonify
from ..auth import admin_required, loc_required
from ..config_forms import StatsConfigForm, CompetitionDayForm, CurrentDayForm, NPCForm, RecordTypeForm
from database.config_manager import ConfigManager, clear_config_cache
from config import Config
from datetime import date
import os
from flask import current_app

def register_routes(bp):
    @bp.route('/config')
    @loc_required
    def config_index():
        configs = ConfigManager.get_all_config()
        days = ConfigManager.get_competition_days()
        npcs = ConfigManager.get_npcs()
        current_day = ConfigManager.get_current_competition_day()
        return render_template('admin/config/index.html',
                               configs=configs,
                               days=days,
                               npcs=npcs,
                               current_day=current_day)

    @bp.route('/config/general')
    @loc_required
    def config_general():
        configs = ConfigManager.get_all_config()
        config_values = ConfigManager.get_all_config()
        return render_template('admin/config/general.html',
                               configs=configs,
                               config_values=config_values)

    @bp.route('/config/api/add-tag', methods=['POST'])
    @loc_required
    def config_add_tag():
        try:
            # Handle both JSON and form data
            if request.is_json:
                data = request.get_json()
            else:
                data = request.form.to_dict()
            config_key = data.get('config_key')
            tag_value = data.get('tag_value')
            if not config_key or not tag_value:
                return jsonify({'success': False, 'error': 'Missing parameters'}), 400
            # Validate CSRF token
            csrf_token = data.get('csrf_token') or request.headers.get('X-CSRFToken')
            if not csrf_token:
                return jsonify({'success': False, 'error': 'CSRF token missing'}), 400
            # Check if tag already exists
            existing_tags = ConfigManager.get_config_tags(config_key)
            if tag_value in existing_tags:
                return jsonify({'success': False, 'error': 'Tag already exists'}), 400
            # Add the tag
            success = ConfigManager.add_config_tag(config_key, tag_value)
            clear_config_cache()
            if success:
                return jsonify({'success': True, 'message': 'Tag added successfully'})
            else:
                return jsonify({'success': False, 'error': 'Failed to add tag'}), 500
        except Exception as e:
            print(f"Error in config_add_tag: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    @bp.route('/config/api/remove-tag', methods=['POST'])
    @loc_required
    def config_remove_tag():
        try:
            # Handle both JSON and form data
            if request.is_json:
                data = request.get_json()
            else:
                data = request.form.to_dict()
            config_key = data.get('config_key')
            tag_value = data.get('tag_value')
            if not config_key or not tag_value:
                return jsonify({'success': False, 'error': 'Missing parameters'}), 400
            # Validate CSRF token
            csrf_token = data.get('csrf_token') or request.headers.get('X-CSRFToken')
            if not csrf_token:
                return jsonify({'success': False, 'error': 'CSRF token missing'}), 400
            # Remove the tag
            ConfigManager.remove_config_tag(config_key, tag_value)
            clear_config_cache()
            return jsonify({'success': True, 'message': 'Tag removed successfully'})
        except Exception as e:
            print(f"Error in config_remove_tag: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    @bp.route('/config/stats', methods=['GET', 'POST'])
    @loc_required
    def config_stats():
        form = StatsConfigForm()
        if form.validate_on_submit():
            ConfigManager.set_config('npcs_count', form.npcs_count.data, 'integer')
            ConfigManager.set_config('athletes_count', form.athletes_count.data, 'integer')
            ConfigManager.set_config('volunteers_count', form.volunteers_count.data, 'integer')
            ConfigManager.set_config('loc_count', form.loc_count.data, 'integer')
            ConfigManager.set_config('officials_count', form.officials_count.data, 'integer')
            clear_config_cache()
            flash('Statistics updated successfully', 'success')
            return redirect(url_for('admin.config_index'))
        elif request.method == 'GET':
            form.npcs_count.data = ConfigManager.get_config('npcs_count', 61)
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
    @bp.route('/config/npcs')
    @loc_required
    def config_npcs():
        from database.config_manager import ConfigManager
        npcs = ConfigManager.get_npcs()
        return render_template('admin/config/npcs.html', npcs=npcs)
    @bp.route('/config/npc/add', methods=['GET', 'POST'])
    @loc_required
    def config_npc_add():
        from blueprints.admin.config_forms import NPCForm
        from database.config_manager import ConfigManager
        form = NPCForm()
        if form.validate_on_submit():
            # Traitement du fichier de drapeau
            flag_file_path = None
            if form.flag_file.data:
                flag_file_path = save_flag_file(form.flag_file.data, form.code.data.upper())
            try:
                ConfigManager.create_npc(
                    code=form.code.data.upper(),
                    name=form.name.data,
                    region_code=form.region_code.data or None,
                    flag_file_path=flag_file_path
                )
                flash('NPC created successfully!', 'success')
                return redirect(url_for('admin.config_npcs'))
            except Exception as e:
                flash(f'Error creating NPC: {str(e)}', 'danger')
        return render_template('admin/config/npc_form.html',
                               form=form, title='Add NPC', npc=None)
    @bp.route('/config/npc/<npc_code>/edit', methods=['GET', 'POST'])
    @loc_required
    def config_npc_edit(npc_code):
        from blueprints.admin.config_forms import NPCForm
        from database.config_manager import ConfigManager
        npc = ConfigManager.get_npc_by_code(npc_code)
        if not npc:
            flash('NPC not found', 'danger')
            return redirect(url_for('admin.config_npcs'))
        form = NPCForm()
        if form.validate_on_submit():
            # Traitement du nouveau fichier de drapeau
            flag_file_path = npc.get('flag_file_path')
            if form.flag_file.data:
                # Supprimer l'ancien fichier si il existe
                if flag_file_path and os.path.exists(os.path.join(current_app.root_path, flag_file_path)):
                    try:
                        os.remove(os.path.join(current_app.root_path, flag_file_path))
                    except:
                        pass
                flag_file_path = save_flag_file(form.flag_file.data, form.code.data.upper())
            try:
                ConfigManager.update_npc(
                    npc_code=npc_code,
                    code=form.code.data.upper(),
                    name=form.name.data,
                    region_code=form.region_code.data or None,
                    flag_file_path=flag_file_path
                )
                flash('NPC updated successfully!', 'success')
                return redirect(url_for('admin.config_npcs'))
            except Exception as e:
                flash(f'Error updating NPC: {str(e)}', 'danger')
        elif request.method == 'GET':
            # Pré-remplir le formulaire avec les valeurs existantes
            form.code.data = npc.get('code', '')
            form.name.data = npc.get('name', '')
            form.region_code.data = npc.get('region_code', '')
            # Note: flag_file ne peut pas être pré-rempli pour des raisons de sécurité
        return render_template('admin/config/npc_form.html',
                               form=form, title='Edit NPC', npc=npc)
    @bp.route('/config/npc/<npc_code>/delete', methods=['POST'])
    @loc_required
    def config_npc_delete(npc_code):
        from database.config_manager import ConfigManager
        try:
            npc = ConfigManager.get_npc_by_code(npc_code)
            if npc and npc.get('flag_file_path'):
                # Supprimer le fichier de drapeau
                if os.path.exists(npc['flag_file_path']):
                    try:
                        os.remove(npc['flag_file_path'])
                    except:
                        pass
            ConfigManager.delete_npc(npc_code)
            flash('NPC deleted successfully!', 'success')
        except Exception as e:
            flash(f'Error deleting NPC: {str(e)}', 'danger')
        return redirect(url_for('admin.config_npcs'))
    def save_flag_file(file, npc_code):
        if not file:
            return None
        if not file.filename.lower().endswith('.svg'):
            raise ValueError('Only SVG files are allowed')
        flags_dir = os.path.join(current_app.static_folder, 'images', 'flags')
        os.makedirs(flags_dir, exist_ok=True)
        filename = f"{npc_code.upper()}.svg"
        file_path = os.path.join(flags_dir, filename)
        try:
            file.save(file_path)
            return f"static/images/flags/{filename}"
        except Exception as e:
            raise ValueError(f'Error saving flag file: {str(e)}')
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

    @bp.route('/config/update', methods=['POST'])
    @loc_required
    def config_update():
        key = request.form.get('key')
        value = request.form.get('value')

        if not key:
            flash('Configuration key is required', 'danger')
            return redirect(url_for('admin.config_general'))

        # Déterminer le type de configuration
        setting_type = 'string'
        if key in ['auto_approve_records', 'auto_approve_personal_bests']:
            setting_type = 'boolean'
        elif key in ['current_day', 'npcs_count', 'athletes_count', 'volunteers_count', 'loc_count', 'officials_count']:
            setting_type = 'integer'

        try:
            ConfigManager.set_config(key, value, setting_type)
            clear_config_cache()

            if key == 'auto_approve_records':
                status = 'enabled' if value == 'true' else 'disabled'
                flash(f'Auto-approval for records has been {status}', 'success')
            elif key == 'auto_approve_personal_bests':
                status = 'enabled' if value == 'true' else 'disabled'
                flash(f'Auto-approval for personal bests has been {status}', 'success')
            else:
                flash('Configuration updated successfully', 'success')

        except Exception as e:
            flash(f'Error updating configuration: {str(e)}', 'danger')

        return redirect(url_for('admin.config_general'))
@staticmethod
def get_genders():
    return ['Male', 'Female']
@staticmethod
def get_weight_field_events():
    try:
        from database.config_manager import ConfigManager
        return ConfigManager.get_config_tags('weight_field_events')
    except (ImportError, Exception):
        return ['Shot Put', 'Discus Throw', 'Javelin Throw', 'Hammer Throw', 'Club Throw', 'Weight Throw']

