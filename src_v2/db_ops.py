"""
Operations pertaining to the sqlite database
"""

from sqlite3 import OperationalError


def get_count_or_setup_db(self, LOCAL_DIRECTORY):
    """
    Function to set up SQLite database if it doesn't exist
    and grab all files which failed to sync last time program was run
    """
    try:
        # Check if database is already set up
        self.file_count = self.conn.execute(
            "SELECT COUNT(file_path) FROM Times"
        ).fetchone()[0]

    except OperationalError:
        # If not, then set it up
        self.conn.execute("PRAGMA foreign_keys = ON;")
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
            (LOCAL_DIRECTORY,),
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
            CREATE TABLE Dates (
                date TEXT PRIMARY KEY
                file_count INTEGER CHECK(file_count >= 0)
            );
            """
        )
        self.conn.execute(
            """
            CREATE TABLE log,
            date TEXT,
            filename
            """
        )

        self.conn.commit()
