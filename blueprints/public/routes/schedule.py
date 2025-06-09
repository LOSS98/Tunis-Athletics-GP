from flask import render_template, request
from database.models import Game
from config import Config


def register_routes(bp):
    @bp.route('/schedule')
    def schedule():
        day_filter = request.args.get('day', '')
        event_filter = request.args.get('event', '')

        # Get all games
        games = Game.get_with_status()

        # Apply filters
        if day_filter:
            games = [g for g in games if str(g['day']) == day_filter]

        if event_filter:
            games = [g for g in games if event_filter.lower() in g['event'].lower()]

        # Sort by day and time
        games.sort(key=lambda x: (x['day'], x['time']))

        # Get unique days and events for filters
        all_games = Game.get_with_status()
        days = sorted(list(set([g['day'] for g in all_games])))
        events = sorted(list(set([g['event'] for g in all_games])))

        return render_template('public/schedule.html',
                               games=games,
                               days=days,
                               events=events,
                               day_filter=day_filter,
                               event_filter=event_filter)

    @bp.route('/schedule/day/<int:day>')
    def schedule_day(day):
        """Schedule for a specific day"""
        games = Game.get_with_status()
        day_games = [g for g in games if g['day'] == day]
        day_games.sort(key=lambda x: x['time'])

        return render_template('public/schedule_day.html',
                               games=day_games,
                               day=day)