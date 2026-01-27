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

    def close(self):
        self.conn.close()
