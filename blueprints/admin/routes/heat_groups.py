from flask import render_template, request, redirect, url_for, flash, jsonify
from ..auth import admin_required, loc_required
from database.models.heat_group import HeatGroup
from database.models.game import Game


def register_heat_routes(bp):
    @bp.route('/heat-groups')
    @loc_required
    def heat_groups_list():
        heat_groups = HeatGroup.get_all()
        for hg in heat_groups:
            hg['games'] = HeatGroup.get_games(hg['id'])
        return render_template('admin/heat_groups/list.html', heat_groups=heat_groups)

    @bp.route('/heat-groups/create', methods=['POST'])
    @loc_required
    def heat_group_create():
        name = request.form.get('name')
        event = request.form.get('event')
        genders = request.form.get('genders')
        classes = request.form.get('classes')
        day = request.form.get('day')

        heat_group_id = HeatGroup.create(name, event, genders, classes, int(day))
        if heat_group_id:
            flash('Heat group created successfully', 'success')
        else:
            flash('Error creating heat group', 'danger')

        return redirect(url_for('admin.heat_groups_list'))

    @bp.route('/games/<int:game_id>/add-to-heat', methods=['POST'])
    @loc_required
    def add_game_to_heat(game_id):
        data = request.get_json()
        heat_group_id = data.get('heat_group_id')
        heat_number = data.get('heat_number')

        if heat_group_id == 'new':
            name = data.get('name')
            game = Game.get_by_id(game_id)
            heat_group_id = HeatGroup.create(name, game['event'], game['genders'], game['classes'], game['day'])
            heat_number = 1

        success = Game.add_to_heat_group(game_id, heat_group_id, heat_number)
        return jsonify({'success': success})

    @bp.route('/games/<int:game_id>/remove-from-heat', methods=['POST'])
    @loc_required
    def remove_game_from_heat(game_id):
        success = Game.remove_from_heat_group(game_id)
        return jsonify({'success': success})

    @bp.route('/heat-groups/<int:heat_group_id>/rank', methods=['POST'])
    @admin_required
    def rank_heat_group(heat_group_id):
        success = HeatGroup.rank_combined_results(heat_group_id)
        return jsonify({'success': success})

    @bp.route('/heat-groups/<int:heat_group_id>/delete', methods=['POST'])
    @loc_required
    def delete_heat_group(heat_group_id):
        HeatGroup.delete(heat_group_id)
        flash('Heat group deleted successfully', 'success')
        return redirect(url_for('admin.heat_groups_list'))

    @bp.route('/api/heat-groups')
    @admin_required
    def api_heat_groups():
        heat_groups = HeatGroup.get_all()
        return jsonify(heat_groups)