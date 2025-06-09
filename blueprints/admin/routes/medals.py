from flask import render_template, request, redirect, url_for, flash, jsonify
from database.models import Medal, Result
from database.models.npc import NPC
from ..auth import admin_required


def register_routes(bp):
    @bp.route('/medals')
    @admin_required
    def medals_list():
        medals = Medal.get_all()
        npcs = NPC.get_all()
        return render_template('admin/medals/list.html', medals=medals, npcs=npcs)

    @bp.route('/medals/calculate', methods=['POST'])
    @admin_required
    def medals_calculate():
        try:
            Medal.calculate_from_results()
            flash('Medals calculated successfully from official results', 'success')
        except Exception as e:
            flash(f'Error calculating medals: {str(e)}', 'danger')
        return redirect(url_for('admin.medals_list'))

    @bp.route('/medals/update', methods=['POST'])
    @admin_required
    def medals_update():
        try:
            npc_code = request.form.get('npc_code')
            gold = int(request.form.get('gold', 0))
            silver = int(request.form.get('silver', 0))
            bronze = int(request.form.get('bronze', 0))

            Medal.update_manual(npc_code, gold, silver, bronze)
            flash(f'Medals updated for {npc_code}', 'success')
        except Exception as e:
            flash(f'Error updating medals: {str(e)}', 'danger')
        return redirect(url_for('admin.medals_list'))

    @bp.route('/medals/<npc_code>/delete', methods=['POST'])
    @admin_required
    def medals_delete(npc_code):
        try:
            Medal.delete_by_npc(npc_code)
            flash(f'Medals deleted for {npc_code}', 'success')
        except Exception as e:
            flash(f'Error deleting medals: {str(e)}', 'danger')
        return redirect(url_for('admin.medals_list'))