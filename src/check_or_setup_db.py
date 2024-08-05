from pathlib import Path
from sqlite3 import OperationalError


def check_or_setup_database(local_directory, conn):
    """
    Function to set up SQLite database if it doesn't exist
    and grab all files which failed to sync last time program was run
    """
    try:
        # Check if database is already set up
        failed_syncs = conn.execute("SELECT * FROM FailedSyncs").fetchall()
        conn.execute("DELETE FROM FailedSyncs")
        conn.commit()
        return {Path(file[0][0]): file[0][1] for file in failed_syncs}

    except OperationalError:
        # If not, then set it up
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("DROP TABLE IF EXISTS FailedSyncs")
        conn.execute("DROP TABLE IF EXISTS Times;")
        conn.execute("DROP TABLE IF EXISTS Folders;")

        conn.execute(
            """
            CREATE TABLE Folders (
                folder_path TEXT PRIMARY KEY
            );
            """
        )

        conn.execute(
            """
            INSERT INTO Folders (folder_path)
            VALUES (?);
            """,
            (local_directory,),
        )

        conn.execute(
            """
            CREATE TABLE Times (
                parent_path TEXT,
                file_path TEXT PRIMARY KEY,
                modification_time TEXT NOT NULL,
                FOREIGN KEY (parent_path) REFERENCES Folders (folder_path)
            );
            """
        )

        conn.execute(
            """
            CREATE TABLE FailedSyncs (
                file_path TEXT PRIMARY KEY,
                modification_time TEXT NOT NULL
            );
            """
        )

        conn.commit()
        return {}
