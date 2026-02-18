from database.db import Database


class MetricsQueries:
    def __init__(self, db: Database):
        self.db = db

    def _visit_time_filter(self, start=None, end=None):       
        """
        Builds SQL WHERE clause for optional date filtering on visit windows.
        """
        clauses = []
        params = []

        if start:
            clauses.append("v.start_time >= ?")
            params.append(start)

        if end:
            clauses.append("(v.end_time IS NOT NULL AND v.end_time <= ?)")
            params.append(end)

        where = ""
        if clauses:
            where = "WHERE " + " AND ".join(clauses)

        return where, params

    def _avg_transition_within_visit(self, from_status, to_status, start=None, end=None):
        where, params = self._visit_time_filter(start, end)
        
        query = f"""
        SELECT AVG(strftime('%s', to_ts) - strftime('%s', from_ts))
        FROM (
            SELECT
                v.id,
                (
                    SELECT MIN(hf.timestamp)
                    FROM room_status_history hf
                    WHERE hf.room_id = v.room_id
                      AND hf.new_status = ?
                      AND hf.timestamp >= v.start_time
                      AND (v.end_time IS NULL OR hf.timestamp <= v.end_time)
                ) AS from_ts,
                (
                    SELECT MIN(ht.timestamp)
                    FROM room_status_history ht
                    WHERE ht.room_id = v.room_id
                      AND ht.new_status = ?
                      AND ht.timestamp >= v.start_time
                      AND (v.end_time IS NULL OR ht.timestamp <= v.end_time)
                ) AS to_ts
            FROM visits v
            {where}
        ) visit_durations
        WHERE from_ts IS NOT NULL
          AND to_ts IS NOT NULL
          AND to_ts > from_ts
        """

        return self.db.fetch_one(query, [from_status, to_status, *params])
    
    def avg_wait_time(self, start=None, end=None):
        return self._avg_transition_within_visit(
            from_status='waiting',
            to_status='seeing_provider',
            start=start,
            end=end,
        )

    def avg_provider_time(self, start=None, end=None):
        return self._avg_transition_within_visit(
            from_status='seeing_provider',
            to_status='needs_cleaning',
            start=start,
            end=end,
        )

    def avg_cleaning_time(self, start=None, end=None):
        return self._avg_transition_within_visit(
            from_status='cleaning',
            to_status='available',
            start=start,
            end=end,
        )


    def total_turnovers(self, start=None, end=None):
        where, params = self._visit_time_filter(start, end)

        query = f"""
        SELECT COUNT(*) AS turnovers
        FROM visits v
        {where}
        """

        return self.db.fetch_one(query, params)

    def rooms_stuck_needing_cleaning(self, threshold_seconds=1800):
        """
        Rooms in needs_cleaning longer than threshold
        """
        query = """
        SELECT r.id
        FROM rooms r
        JOIN (
            SELECT room_id, MAX(timestamp) AS since
            FROM room_status_history
            WHERE new_status = 'needs_cleaning'
            GROUP BY room_id
        ) latest_nc ON latest_nc.room_id = r.id
        WHERE r.status = 'needs_cleaning'
          AND strftime('%s','now','localtime') - strftime('%s', latest_nc.since) > ?
        ORDER BY r.id
        """

        rows = self.db.fetch_all(query, [threshold_seconds])
        return [row[0] for row in rows]
