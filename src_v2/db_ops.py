"""
Operations pertaining to the sqlite database
"""

from datetime import datetime
from sqlite3 import OperationalError


def get_count_or_setup_db(self, LOCAL_DIRECTORY):
    """
    Function to set up SQLite database if it doesn't exist
    and grab all files which failed to sync last time program was run
    """
    try:
        # Check if database is already set up
        self.file_count = self.db_conn.execute(
            "SELECT COUNT(file_path) FROM Times"
        ).fetchone()[0]

    except OperationalError:
        # If not, then set it up
        self.db_conn.execute("PRAGMA foreign_keys = ON;")
        self.db_conn.execute("DROP TABLE IF EXISTS Times;")
        self.db_conn.execute("DROP TABLE IF EXISTS Folders;")

        self.db_conn.execute(
            """
            CREATE TABLE Folders (
                folder_path TEXT PRIMARY KEY
            );
            """
        )

        self.db_conn.execute(
            """
            INSERT INTO Folders (folder_path)
            VALUES (?);
            """,
            (LOCAL_DIRECTORY,),
        )

        self.db_conn.execute(
            """
            CREATE TABLE Times (
                parent_path TEXT,
                file_path TEXT PRIMARY KEY,
                modification_time TEXT NOT NULL,
                FOREIGN KEY (parent_path) REFERENCES Folders (folder_path)
            );
            """
        )

        self.db_conn.execute(
            """
            CREATE TABLE Dates (
                date TEXT PRIMARY KEY,
                file_count INTEGER DEFAULT 0 CHECK (file_count >= 0)
            );
            """
        )
        self.db_conn.execute(
            """
            CREATE TABLE Log (
                date TEXT,
                file_path TEXT,
                synced INTEGER CHECK (synced IN (0, 1)),
                PRIMARY KEY (date, file_path),
                FOREIGN KEY (date) REFERENCES Dates (date),
                FOREIGN KEY (file_path) REFERENCES Times (file_path)
            );
            """
        )


def write_mod_files(self):
    """
    Writes mod files to database to keep track of which files were modified
    """
    now = datetime.now().strftime("%Y-%m-%d")
    file_data = [(now, str(filename), 0) for filename in self.mod_times]
    file_count = len(file_data)

    self.db_conn.execute(
        """
        INSERT INTO Dates (date, file_count) VALUES (?, ?)
        ON CONFLICT (date) DO UPDATE SET file_count = file_count + ?
        """,
        (now, file_count, file_count),
    )

    self.db_conn.executemany(
        """
        INSERT INTO Log (date, file_path, synced) VALUES (?, ?, ?)
        """,
        file_data,
    )


def update_db_mod_file(self, filename, modification_time):
    """
    Function which updates the sync status and modification_time for a specific file path
    """
    now = datetime.now().strftime("%Y-%m-%d")
    self.db_conn.execute(
        """
        UPDATE Log
        SET synced = ?
        WHERE date = ? AND file_path = ?
        """,
        (1, now, filename),
    )

    self.db_conn.execute(
        """
        UPDATE Times
        SET modification_time = ?
        WHERE file_path = ?
        """,
        (modification_time, filename),
    )
