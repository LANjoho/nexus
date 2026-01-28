import sqlite3
from pathlib import Path


class Database:
    def __init__(self, db_path="clinic.db"):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._initialize_schema()

    def _initialize_schema(self):
        schema_path = Path(__file__).parent / "schema.sql"

        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()

        self.conn.executescript(schema_sql)
        self.conn.commit()

    def fetch_one(self, query, params=None):
        cursor = self.conn.cursor()
        cursor.execute(query, params or [])
        row = cursor.fetchone()
        return row[0] if row else None
    
    def fetch_all(self, query, params=None):
        cursor = self.conn.cursor()
        cursor.execute(query, params or [])
        return cursor.fetchall()
    
    def close(self):
        self.conn.close()
