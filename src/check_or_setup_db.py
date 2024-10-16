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
        self.retried_syncs.union(
            set(
                self.conn.execute(
                    "SELECT file_path, modification_time FROM FailedSyncs WHERE synced = 0"
                ).fetchall()
            )
        )
        self.file_count = self.conn.execute(
            "SELECT COUNT(file_path) FROM Times"
        ).fetchone()[0]

        self.modified.update({Path(file[0]): file[1] for file in self.retried_syncs})

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
                occurrence DEFAULT 0,
                FOREIGN KEY (file_path) REFERENCES Times (file_path)
            );
            """
        )

        self.conn.commit()
