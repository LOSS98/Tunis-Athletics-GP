from flask import render_template, request
from database.models import Result
def register_routes(bp):
    @bp.route('/records')
    def records():
        search = request.args.get('search', '')
        records = Result.get_records()
        if search:
            records = [r for r in records if
                      search.lower() in r['firstname'].lower() or
                      search.lower() in r['lastname'].lower() or
                      search.lower() in r['npc'].lower() or
                      search.lower() in r['event'].lower() or
                      search.lower() in r['record'].lower()]
        return render_template('public/records.html', records=records, search=search)
