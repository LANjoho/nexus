from database.metrics_queries import MetricsQueries
from utils.time_format import seconds_to_mmss

class MetricsController:
    def __init__(self, db):
        self.metrics = MetricsQueries(db)
        
    def get_summary(self, start=None, end=None):
        """
        Returns high-level metrics summary.
        start/end: ISO timestamps or None (all time)
        """
        
        avg_occupied = self.metrics.avg_occupied_time(start, end)
        avg_cleaning = self.metrics.avg_cleaning_time(start, end)
        turnovers = self.metrics.total_turnovers(start, end)
        stuck_rooms = self.metrics.rooms_stuck_needing_cleaning()
        
        return {
            "avg_occupied": seconds_to_mmss(avg_occupied),
            "avg_cleaning": seconds_to_mmss(avg_cleaning),
            "turnovers": turnovers,
            "stuck_rooms": stuck_rooms,
        }