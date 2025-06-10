def register_routes(bp):
    from . import auth_routes, dashboard, users, athletes, games
    from . import results, startlists, records, config, registrations, medals, heat_groups
    auth_routes.register_routes(bp)
    dashboard.register_routes(bp)
    users.register_routes(bp)
    athletes.register_routes(bp)
    games.register_routes(bp)
    results.register_routes(bp)
    startlists.register_routes(bp)
    records.register_routes(bp)
    config.register_routes(bp)
    registrations.register_routes(bp)
    medals.register_routes(bp)
    heat_groups.register_heat_routes(bp)
