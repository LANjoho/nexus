from datetime import datetime
from database.db import Database


class MetricsQueries:
    def __init__(self, db: Database):
        self.db = db

    def _time_filter(self, start=None, end=None):
        """
        Builds SQL WHERE clause for optional date filtering
        """
        clauses = []
        params = []

        if start:
            clauses.append("timestamp >= ?")
            params.append(start)

        if end:
            clauses.append("timestamp <= ?")
            params.append(end)

        where = ""
        if clauses:
            where = "WHERE " + " AND ".join(clauses)

        return where, params

    def _append_filter(self, base_where, extra_clause):
        """
        Safely appends an extra clause to a WHERE statement
        """
        if base_where:
            return f"{base_where} AND {extra_clause}"
        return f"WHERE {extra_clause}"

    def avg_transition_time(self, from_status, to_status, start=None, end=None):
        """
        Average time (in seconds) between two statuses
        """
        where, params = self._time_filter(start, end)

        # Append status filters safely
        where = self._append_filter(where, "curr.new_status = ?")
        where = self._append_filter(where, "next.new_status = ?")

        query = f"""
        SELECT AVG(
            strftime('%s', next.timestamp) - strftime('%s', curr.timestamp)
        ) AS avg_seconds
        FROM room_status_history curr
        JOIN room_status_history next
            ON curr.room_id = next.room_id
           AND next.id = (
                SELECT MIN(id)
                FROM room_status_history
                WHERE room_id = curr.room_id
                  AND id > curr.id
            )
        {where}
        """

        return self.db.fetch_one(query, params + [from_status, to_status])

    def avg_occupied_time(self, start=None, end=None):
        return self.avg_transition_time(
            "occupied",
            "needs_cleaning",
            start,
            end
        )

    def avg_cleaning_time(self, start=None, end=None):
        return self.avg_transition_time(
            "cleaning",
            "available",
            start,
            end
        )

    def total_turnovers(self, start=None, end=None):
        where, params = self._time_filter(start, end)

        # Always filter for turnovers
        where = self._append_filter(where, "new_status = 'needs_cleaning'")

        query = f"""
        SELECT COUNT(*) AS turnovers
        FROM room_status_history
        {where}
        """

        return self.db.fetch_one(query, params)

    def rooms_stuck_needing_cleaning(self, threshold_seconds=1800):
        """
        Rooms in needs_cleaning longer than threshold
        """
        query = """
        SELECT room_id,
               MAX(timestamp) AS since
        FROM room_status_history
        WHERE new_status = 'needs_cleaning'
        GROUP BY room_id
        HAVING strftime('%s','now') - strftime('%s', since) > ?
        """

        return self.db.fetch_all(query, [threshold_seconds])
