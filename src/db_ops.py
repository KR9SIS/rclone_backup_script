"""
Operations pertaining to the sqlite database
"""

from datetime import datetime
from sqlite3 import OperationalError


def get_count_or_setup_db(self, LOCAL_DIRECTORY) -> bool:
    """
    Function to set up SQLite database if it doesn't exist
    and grab all files which failed to sync last time program was run
    """
    try:
        # Check if database is already set up
        self.file_count = self.db_conn.execute(
            "SELECT COUNT(file_path) FROM Times"
        ).fetchone()[0]
        return False

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
                date TEXT PRIMARY KEY
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

        self.db_conn.commit()

        return True


def write_db_mod_files(self):
    """
    Writes mod files to database to keep track of which files were modified
    """
    self.now = datetime.now().strftime("%Y-%m-%d %H:%M")
    file_data = [(self.now, str(file_path), 0) for file_path in self.mod_times]

    if self.stdout:
        print("\nModified files:")
        _ = [print(file_path) for file_path in self.mod_times]
        print()

    self.db_conn.execute(
        """
        INSERT OR IGNORE INTO Dates (date) VALUES (?)
        """,
        (self.now,),
    )

    self.db_conn.executemany(
        """
        INSERT INTO Log (date, file_path, synced) VALUES (?, ?, ?)
        """,
        file_data,
    )

    self.db_conn.commit()


def update_db_mod_file(self, file_path: str, modification_time: str):
    """
    Function which updates the sync status and modification_time for a specific file path
    """
    self.db_conn.execute(
        """
        UPDATE Log
        SET synced = ?
        WHERE date = ? AND file_path = ?
        """,
        (1, self.now, file_path),
    )

    self.db_conn.execute(
        """
        UPDATE Times
        SET modification_time = ?
        WHERE file_path = ?
        """,
        (modification_time, file_path),
    )
    self.db_conn.commit()
