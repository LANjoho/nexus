from database.db import Database
from database.metrics_queries import MetricsQueries

db = Database()
metrics = MetricsQueries(db)

print("Avg occupied time:", metrics.avg_occupied_time())
print("Avg cleaning time:", metrics.avg_cleaning_time())
print("Total turnovers:", metrics.total_turnovers())
print("Rooms stuck:", metrics.rooms_stuck_needing_cleaning())
