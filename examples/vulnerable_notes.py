import sqlite3
import os

class NotesApp:
    def __init__(self, base_dir="/tmp/system_root/var/notes", db_path=":memory:"):
        self.base_dir = base_dir
        # Keep a persistent connection open so the in-memory DB stays alive
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        """Initializes the database table and standard testing data."""
        c = self.conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY, owner TEXT, content TEXT)")
        
        # Seed standard data for behaviour testing
        c.execute("SELECT COUNT(*) FROM notes")
        if c.fetchone()[0] == 0:
            c.execute("INSERT INTO notes (owner, content) VALUES ('alice', 'Grocery list: milk, eggs.')")
            self.conn.commit()

    def seed_secret(self, flag: str):
        """Called ONLY by the harness server_runner to plant the IDOR flag."""
        c = self.conn.cursor()
        c.execute("INSERT INTO notes (owner, content) VALUES ('admin', ?)", (flag,))
        self.conn.commit()

    def get_note(self, note_id: int, requesting_user: str) -> str:
        """
        VULNERABILITY 1: IDOR
        Fails to check if requesting_user matches the owner column.
        """
        c = self.conn.cursor()
        c.execute("SELECT content FROM notes WHERE id=?", (note_id,))
        row = c.fetchone()
        
        if row:
            return row[0]
        return "Note not found."

    def read_attachment(self, filename: str) -> str:
        """
        VULNERABILITY 2: Path Traversal
        Fails to sanitize the input before opening the file.
        """
        filepath = os.path.join(self.base_dir, filename)
        
        try:
            with open(filepath, 'r') as f:
                return f.read()
        except Exception:
            return "File not found."