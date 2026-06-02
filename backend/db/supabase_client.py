import os
import sqlite3
import uuid
from dotenv import load_dotenv

load_dotenv()

# We keep these for env compatibility check but don't strictly require cloud supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

class MockTable:
    def __init__(self, db_path: str, table_name: str):
        self.db_path = db_path
        self.table_name = table_name
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                id TEXT PRIMARY KEY,
                title TEXT,
                type TEXT,
                content TEXT,
                source_url TEXT,
                updated_at TEXT
            )
        """)
        conn.commit()
        conn.close()

    def insert(self, data):
        class InsertBuilder:
            def __init__(self, table, d):
                self.table = table
                self.data = d
                
            def execute(self):
                conn = sqlite3.connect(self.table.db_path)
                cursor = conn.cursor()
                items = self.data if isinstance(self.data, list) else [self.data]
                inserted_items = []
                for item in items:
                    item_id = item.get("id") or str(uuid.uuid4())
                    cursor.execute(f"""
                        INSERT OR REPLACE INTO {self.table.table_name} (id, title, type, content, source_url, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        item_id,
                        item.get("title"),
                        item.get("type"),
                        item.get("content"),
                        item.get("source_url"),
                        item.get("updated_at")
                    ))
                    item_copy = dict(item)
                    item_copy["id"] = item_id
                    inserted_items.append(item_copy)
                conn.commit()
                conn.close()
                
                class ExecuteResult:
                    def __init__(self, d):
                        self.data = d
                return ExecuteResult(inserted_items)
                
        return InsertBuilder(self, data)

    def select(self, query: str = "*"):
        # We simply support chaining
        return self

    def eq(self, column: str, value):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(f"SELECT * FROM {self.table_name} WHERE {column} = ?", (value,))
        rows = cursor.fetchall()
        conn.close()
        
        data = [dict(row) for row in rows]
        
        class ExecuteResult:
            def __init__(self, d):
                self.data = d
                
        class ChainResult:
            def execute(self):
                return ExecuteResult(data)
                
        return ChainResult()

class MockSupabaseClient:
    def __init__(self, db_path: str = "local_supabase.db"):
        # Make path absolute relative to db package parent directory
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.db_path = os.path.join(base_dir, db_path)

    def table(self, table_name: str) -> MockTable:
        return MockTable(self.db_path, table_name)

def get_supabase_client():
    return MockSupabaseClient()
