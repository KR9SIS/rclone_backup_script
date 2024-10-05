"""
Module docstring
"""

from pathlib import Path
from sqlite3 import OperationalError


def check_or_setup_database(self, local_directory):
    """
    Function to set up SQLite database if it doesn't exist
    and grab all files which failed to sync last time program was run
    """
    try:
        # Check if database is already set up
        failed_syncs = self.conn.execute(
            "SELECT file_path, modification_time FROM FailedSyncs WHERE synced = 0"
        ).fetchall()
        self.file_count = self.conn.execute(
            "SELECT COUNT(file_path) FROM Times"
        ).fetchone()[0]
        self.retried_syncs.union(set(failed_syncs))
        self.modified.update({Path(file[0]): file[1] for file in failed_syncs})

    except OperationalError:
        # If not, then set it up
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self.conn.execute("DROP TABLE IF EXISTS FailedSyncs")
        self.conn.execute("DROP TABLE IF EXISTS Times;")
        self.conn.execute("DROP TABLE IF EXISTS Folders;")

        self.conn.execute(
            """
            CREATE TABLE Folders (
                folder_path TEXT PRIMARY KEY
            );
            """
        )

        self.conn.execute(
            """
            INSERT INTO Folders (folder_path)
            VALUES (?);
            """,
            (local_directory,),
        )

        self.conn.execute(
            """
            CREATE TABLE Times (
                parent_path TEXT,
                file_path TEXT PRIMARY KEY,
                modification_time TEXT NOT NULL,
                FOREIGN KEY (parent_path) REFERENCES Folders (folder_path)
            );
            """
        )

        self.conn.execute(
            """
            CREATE TABLE FailedSyncs (
                file_path TEXT PRIMARY KEY,
                modification_time TEXT NOT NULL,
                synced INTEGER NOT NULL,
                occurance DEFAULT 0,
                FOREIGN KEY (file_path) REFERENCES Times (file_path)
            );
            """
        )

        self.conn.execute(
            """
            CREATE TABLE UserSpecs (
                username TEXT PRIMARY KEY,
                local_directory TEXT,
                remote_directory TEXT
            );
            """
        )

        self.conn.execute(
            """
            CREATE TABLE CurrentUser (
                id INTEGER PRIMARY KEY CHECK (id = 0),
                username TEXT,
                FOREIGN KEY (username) REFERENCES UserSpecs (username)
            );
            """
        )

        self.conn.commit()
