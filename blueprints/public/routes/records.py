from flask import render_template, request
from database.models import WorldRecord, Region


def register_routes(bp):
    @bp.route('/records')
    def records():
        search = request.args.get('search', '')

        all_records = WorldRecord.get_all_with_competition_details(approved_only=True)

        regions = Region.get_all()

        if search:
            filtered_records = []
            search_lower = search.lower()

            for r in all_records:
                if (
                        (r.get('firstname') and search_lower in r['firstname'].lower()) or
                        (r.get('lastname') and search_lower in r['lastname'].lower()) or
                        (r.get('event') and search_lower in r['event'].lower()) or
                        (r.get('npc') and search_lower in r['npc'].lower())
                ):
                    filtered_records.append(r)

            all_records = filtered_records

        world_records = [r for r in all_records if r['record_type'] == 'WR']

        region_records = {}
        for region in regions:
            region_records[region['code']] = [
                r for r in all_records
                if r['record_type'] == 'AR' and r.get('region_code') == region['code']
            ]

        return render_template(
            'public/records.html',
            world_records=world_records,
            region_records=region_records,
            regions=regions,
            search=search
        )