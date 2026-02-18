from database.db import Database
from database.metrics_queries import MetricsQueries
from utils.time_format import seconds_to_mmss



db = Database()
metrics = MetricsQueries(db)

print("Avg cleaning time:", seconds_to_mmss(metrics.avg_cleaning_time()))
print("Total turnovers:", metrics.total_turnovers())
print("Rooms stuck:", metrics.rooms_stuck_needing_cleaning())
