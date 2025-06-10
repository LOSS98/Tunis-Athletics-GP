from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user
from ..auth import admin_required, technical_delegate_required, loc_required
from ..forms import WorldRecordForm, PersonalBestForm
from database.models import WorldRecord, PersonalBest, Athlete, Region, Game, Result
from config import Config
from datetime import date


def register_routes(bp):
    @bp.route('/records')
    @loc_required
    def records_list():
        records = WorldRecord.get_all()
        pending_records = WorldRecord.get_pending() if current_user.is_technical_delegate() else []
        return render_template('admin/records/list.html',
                               records=records,
                               pending_records=pending_records)

    @bp.route('/records/add', methods=['GET', 'POST'])
    @technical_delegate_required
    def record_add():
        form = WorldRecordForm()
        if form.validate_on_submit():
            athlete = None
            if form.sdms.data:
                athlete = Athlete.get_by_sdms(form.sdms.data)
                if not athlete:
                    flash('Athlete not found', 'danger')
                    return render_template('admin/records/add.html', form=form)

            data = {
                'sdms': form.sdms.data,
                'event': form.event.data,
                'athlete_class': form.athlete_class.data,
                'performance': form.performance.data,
                'location': form.location.data,
                'npc': form.npc.data or (athlete['npc'] if athlete else None),
                'region_code': form.region_code.data or (athlete['region_code'] if athlete else None),
                'record_date': form.record_date.data,
                'record_type': form.record_type.data,
                'made_in_competition': form.made_in_competition.data,
                'approved': True,
                'approved_by': current_user.id
            }
            try:
                WorldRecord.create(**data)
                flash('Record added successfully', 'success')
                return redirect(url_for('admin.records_list'))
            except Exception as e:
                flash(f'Error adding record: {str(e)}', 'danger')

        return render_template('admin/records/add.html', form=form)

    @bp.route('/records/<int:record_id>/approve', methods=['POST'])
    @technical_delegate_required
    def record_approve(record_id):
        try:
            WorldRecord.approve(record_id, current_user.id)
            flash('Record approved successfully', 'success')
        except Exception as e:
            flash(f'Error approving record: {str(e)}', 'danger')
        return redirect(url_for('admin.records_list'))

    @bp.route('/records/<int:record_id>/delete', methods=['POST'])
    @technical_delegate_required
    def record_delete(record_id):
        try:
            WorldRecord.delete(record_id)
            flash('Record deleted successfully', 'success')
        except Exception as e:
            flash(f'Error deleting record: {str(e)}', 'danger')
        return redirect(url_for('admin.records_list'))

    @bp.route('/records/approve-all', methods=['POST'])
    @technical_delegate_required
    def records_approve_all():
        try:
            count = WorldRecord.approve_all(current_user.id)
            flash(f'{count} records approved successfully', 'success')
        except Exception as e:
            flash(f'Error approving records: {str(e)}', 'danger')
        return redirect(url_for('admin.records_list'))

    @bp.route('/records/delete-pending', methods=['POST'])
    @technical_delegate_required
    def records_delete_pending():
        try:
            count = WorldRecord.delete_all_pending()
            flash(f'{count} pending records deleted successfully', 'success')
        except Exception as e:
            flash(f'Error deleting pending records: {str(e)}', 'danger')
        return redirect(url_for('admin.records_list'))

    @bp.route('/personal-bests')
    @loc_required
    def personal_bests_list():
        personal_bests = PersonalBest.get_all()
        pending_pbs = PersonalBest.get_pending() if current_user.is_technical_delegate() else []
        return render_template('admin/records/personal_bests.html',
                               personal_bests=personal_bests,
                               pending_pbs=pending_pbs)

    @bp.route('/personal-bests/add', methods=['GET', 'POST'])
    @technical_delegate_required
    def personal_best_add():
        form = PersonalBestForm()
        if form.validate_on_submit():
            athlete = Athlete.get_by_sdms(form.sdms.data)
            if not athlete:
                flash('Athlete not found', 'danger')
                return render_template('admin/records/add_pb.html', form=form)

            data = {
                'sdms': form.sdms.data,
                'event': form.event.data,
                'athlete_class': form.athlete_class.data,
                'performance': form.performance.data,
                'location': form.location.data,
                'record_date': form.record_date.data,
                'made_in_competition': form.made_in_competition.data,
                'approved': True,
                'approved_by': current_user.id
            }
            try:
                PersonalBest.create(**data)
                flash('Personal best added successfully', 'success')
                return redirect(url_for('admin.personal_bests_list'))
            except Exception as e:
                flash(f'Error adding personal best: {str(e)}', 'danger')

        return render_template('admin/records/add_pb.html', form=form)

    @bp.route('/personal-bests/<int:pb_id>/approve', methods=['POST'])
    @technical_delegate_required
    def personal_best_approve(pb_id):
        try:
            PersonalBest.approve(pb_id, current_user.id)
            flash('Personal best approved successfully', 'success')
        except Exception as e:
            flash(f'Error approving personal best: {str(e)}', 'danger')
        return redirect(url_for('admin.personal_bests_list'))

    @bp.route('/personal-bests/<int:pb_id>/delete', methods=['POST'])
    @technical_delegate_required
    def personal_best_delete(pb_id):
        try:
            PersonalBest.delete(pb_id)
            flash('Personal best deleted successfully', 'success')
        except Exception as e:
            flash(f'Error deleting personal best: {str(e)}', 'danger')
        return redirect(url_for('admin.personal_bests_list'))

    @bp.route('/personal-bests/approve-all', methods=['POST'])
    @technical_delegate_required
    def personal_bests_approve_all():
        try:
            count = PersonalBest.approve_all(current_user.id)
            flash(f'{count} personal bests approved successfully', 'success')
        except Exception as e:
            flash(f'Error approving personal bests: {str(e)}', 'danger')
        return redirect(url_for('admin.personal_bests_list'))

    @bp.route('/personal-bests/delete-pending', methods=['POST'])
    @technical_delegate_required
    def personal_bests_delete_pending():
        try:
            count = PersonalBest.delete_all_pending()
            flash(f'{count} pending personal bests deleted successfully', 'success')
        except Exception as e:
            flash(f'Error deleting pending personal bests: {str(e)}', 'danger')
        return redirect(url_for('admin.personal_bests_list'))

    @bp.route('/games/<int:game_id>/check-records', methods=['POST'])
    @technical_delegate_required
    def check_game_records(game_id):
        try:
            game = Game.get_by_id(game_id)
            if not game:
                return jsonify({'error': 'Game not found'}), 404

            results = Result.get_all(game_id=game_id)
            if not results:
                return jsonify({'error': 'No results found for this game'}), 400

            # Process each result for records and personal bests
            records_found = 0
            pbs_found = 0

            for result in results:
                athlete = Athlete.get_by_sdms(result['athlete_sdms'])
                if athlete:
                    # Get the athlete's class that matches the game
                    athlete_class = get_matching_class(athlete, game)
                    if athlete_class:
                        created_records, created_pbs = check_for_records_and_pbs_improved(result, athlete, game,
                                                                                          athlete_class)
                        records_found += created_records
                        pbs_found += created_pbs

            message = f'Check completed: {records_found} records and {pbs_found} personal bests found'
            return jsonify({'success': True, 'message': message})

        except Exception as e:
            print(f"Error checking records for game {game_id}: {e}")
            return jsonify({'error': str(e)}), 500


def get_matching_class(athlete, game):
    """Get the athlete's class that matches the game classes"""
    if not athlete or not athlete.get('class'):
        return None

    athlete_classes = [c.strip() for c in athlete['class'].split(',') if c.strip()]
    game_classes = [c.strip() for c in game['classes'].split(',') if c.strip()]

    # Return the first matching class
    for athlete_class in athlete_classes:
        if athlete_class in game_classes:
            return athlete_class

    # If no match, return the first athlete class (for backwards compatibility)
    return athlete_classes[0] if athlete_classes else None


def check_for_records_and_pbs_improved(result, athlete, game, athlete_class):
    """Improved function to check for records and personal bests with multi-class support"""
    if not game.get('official'):
        return 0, 0

    performance_value = result['value']
    if performance_value in Config.get_result_special_values():
        return 0, 0

    try:
        performance_float = float(performance_value)
    except (ValueError, TypeError):
        return 0, 0

    event = game['event']
    records_created = 0
    pbs_created = 0

    # Check for World Record
    if check_and_create_wr(athlete, event, athlete_class, performance_value, performance_float, game):
        records_created += 1

    # Check for Area Record
    if athlete.get('region_code') and check_and_create_ar(athlete, event, athlete_class, performance_value,
                                                          performance_float, game):
        records_created += 1

    # Check for Personal Best
    if check_and_create_pb(athlete, event, athlete_class, performance_value, performance_float, game):
        pbs_created += 1

    return records_created, pbs_created


from database.config_manager import ConfigManager
from flask_login import current_user


def check_and_create_wr(athlete, event, athlete_class, performance_value, performance_float, game):
    """Check and create World Record if applicable"""
    # Check existing approved WR
    existing_wr = WorldRecord.check_existing_record(event, athlete_class, 'WR')

    # Check pending WR
    pending_wr = WorldRecord.get_pending_for_event_class(event, athlete_class, 'WR')

    is_new_record = False

    if not existing_wr or performance_float > float(existing_wr['performance']):
        if not pending_wr or performance_float > float(pending_wr['performance']):
            is_new_record = True
        elif pending_wr:
            # Delete the inferior pending record
            WorldRecord.delete(pending_wr['id'])
            is_new_record = True

    if is_new_record:
        # Check if auto-approval is enabled - CORRECTION ICI
        auto_approve = ConfigManager.get_config('auto_approve_records', 'false') == 'true'

        WorldRecord.create(
            sdms=athlete['sdms'],
            event=event,
            athlete_class=athlete_class,
            performance=performance_value,
            location='Tunis, Tunisia',
            npc=athlete['npc'],
            region_code=athlete.get('region_code'),
            record_date=date.today(),
            record_type='WR',
            made_in_competition=True,
            competition_id=game['id'],
            approved=auto_approve,
            approved_by=current_user.id if auto_approve else None
        )
        return True

    return False


def check_and_create_ar(athlete, event, athlete_class, performance_value, performance_float, game):
    """Check and create Area Record if applicable"""
    region_code = athlete.get('region_code')
    if not region_code:
        return False

    # Check existing approved AR for this region
    existing_ar = WorldRecord.check_existing_record(event, athlete_class, 'AR', athlete['npc'])

    # Check pending AR for this region
    pending_ar = WorldRecord.get_pending_for_event_class_region(event, athlete_class, 'AR', region_code)

    is_new_record = False

    if not existing_ar or performance_float > float(existing_ar['performance']):
        if not pending_ar or performance_float > float(pending_ar['performance']):
            is_new_record = True
        elif pending_ar:
            # Delete the inferior pending record
            WorldRecord.delete(pending_ar['id'])
            is_new_record = True

    if is_new_record:
        # Check if auto-approval is enabled - CORRECTION ICI
        auto_approve = ConfigManager.get_config('auto_approve_records', 'false') == 'true'

        WorldRecord.create(
            sdms=athlete['sdms'],
            event=event,
            athlete_class=athlete_class,
            performance=performance_value,
            location='Tunis, Tunisia',
            npc=athlete['npc'],
            region_code=region_code,
            record_date=date.today(),
            record_type='AR',
            made_in_competition=True,
            competition_id=game['id'],
            approved=auto_approve,
            approved_by=current_user.id if auto_approve else None
        )
        return True

    return False


def check_and_create_pb(athlete, event, athlete_class, performance_value, performance_float, game):
    """Check and create Personal Best if applicable"""
    # Check existing approved PB
    existing_pb = PersonalBest.check_existing_pb(athlete['sdms'], event, athlete_class)

    # Check pending PB
    pending_pb = PersonalBest.get_pending_for_athlete(athlete['sdms'], event, athlete_class)

    is_new_pb = False

    if not existing_pb or performance_float > float(existing_pb['performance']):
        if not pending_pb or performance_float > float(pending_pb['performance']):
            is_new_pb = True
        elif pending_pb:
            # Delete the inferior pending PB
            PersonalBest.delete(pending_pb['id'])
            is_new_pb = True

    if is_new_pb:
        # Check if auto-approval is enabled - CORRECTION ICI
        auto_approve = ConfigManager.get_config('auto_approve_personal_bests', 'false') == 'true'

        PersonalBest.create(
            sdms=athlete['sdms'],
            event=event,
            athlete_class=athlete_class,
            performance=performance_value,
            location='Tunis, Tunisia',
            record_date=date.today(),
            made_in_competition=True,
            competition_id=game['id'],
            approved=auto_approve,
            approved_by=current_user.id if auto_approve else None
        )
        return True

    return False