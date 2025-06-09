# blueprints/admin/routes/records.py
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user
from ..auth import admin_required, technical_delegate_required, loc_required
from ..forms import WorldRecordForm, PersonalBestForm
from database.models import WorldRecord, PersonalBest, Athlete, Region
from config import Config
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
                'npc': athlete['npc'],
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
def check_for_records_and_pbs(result, athlete, game):
    if not game.get('official'):
        return
    performance_value = result['value']
    if performance_value in Config.get_result_special_values():
        return
    try:
        performance_float = float(performance_value)
    except (ValueError, TypeError):
        return
    event = game['event']
    athlete_class = athlete['class']
    existing_wr = WorldRecord.check_existing_record(event, athlete_class, 'WR')
    if not existing_wr or performance_float > float(existing_wr['performance']):
        WorldRecord.create(
            sdms=athlete['sdms'],
            event=event,
            athlete_class=athlete_class,
            performance=performance_value,
            location='Tunis, Tunisia',
            npc=athlete['npc'],
            region_code=athlete['region_code'],
            record_date='CURRENT_DATE',
            record_type='WR',
            made_in_competition=True,
            competition_id=game['id'],
            approved=False
        )
    if athlete['region_code']:
        existing_ar = WorldRecord.check_existing_record(event, athlete_class, 'AR', athlete['region_code'])
        if not existing_ar or performance_float > float(existing_ar['performance']):
            WorldRecord.create(
                sdms=athlete['sdms'],
                event=event,
                athlete_class=athlete_class,
                performance=performance_value,
                location='Tunis, Tunisia',
                npc=athlete['npc'],
                region_code=athlete['region_code'],
                record_date='CURRENT_DATE',
                record_type='AR',
                made_in_competition=True,
                competition_id=game['id'],
                approved=False
            )
    existing_pb = PersonalBest.check_existing_pb(athlete['sdms'], event, athlete_class)
    if not existing_pb or performance_float > float(existing_pb['performance']):
        PersonalBest.create(
            sdms=athlete['sdms'],
            event=event,
            athlete_class=athlete_class,
            performance=performance_value,
            location='Tunis, Tunisia',
            npc=athlete['npc'],
            record_date='CURRENT_DATE',
            made_in_competition=True,
            competition_id=game['id'],
            approved=False
        )