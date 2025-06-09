def register_routes(bp):
    from . import home, results, startlists, athletes, records, raza, schedule, medals
    home.register_routes(bp)
    results.register_routes(bp)
    startlists.register_routes(bp)
    athletes.register_routes(bp)
    records.register_routes(bp)
    raza.register_routes(bp)
    schedule.register_routes(bp)
    medals.register_routes(bp)
