from database.metrics_queries import MetricsQueries
from utils.time_format import seconds_to_mmss



class MetricsController:
    def __init__(self, db):
        self.db = db
        self.metrics = MetricsQueries(db)
        
    def get_summary(self, start=None, end=None):
        """
        Returns high-level metrics summary.
        start/end: ISO timestamps or None (all time)
        """
        avg_wait = self.metrics.avg_wait_time(start, end)
        avg_provider = self.metrics.avg_provider_time(start, end)
        #avg_occupied = self.metrics.avg_occupied_time(start, end)
        avg_cleaning = self.metrics.avg_cleaning_time(start, end)
        turnovers = self.metrics.total_turnovers(start, end)
        stuck_rooms = self.metrics.rooms_stuck_needing_cleaning()
        
        return {
            "avg_wait": seconds_to_mmss(avg_wait),
            "avg_provider": seconds_to_mmss(avg_provider),
            "avg_cleaning": seconds_to_mmss(avg_cleaning),
            "turnovers": turnovers,
            "stuck_rooms": stuck_rooms,
        }