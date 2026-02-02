from database.db import Database
from controllers.metrics_controller import MetricsController

db = Database()
metrics = MetricsController(db)

summary = metrics.get_summary()

print(summary)
