"""
Operations pertaining to the sqlite database
"""

from pathlib import Path
from sqlite3 import OperationalError
from helpers import VariableStorer


def get_count_or_setup_db(var_storer: VariableStorer) -> bool:
    """
    Function to set up SQLite database if it doesn't exist
    and grab all files which failed to sync last time program was run
    """
    try:
        # Check if database is already set up
        var_storer.file_count = var_storer.db_conn.execute(
            "SELECT COUNT(file_path) FROM Times"
        ).fetchone()[0]
        return False

    except OperationalError:
        # If not, then set it up
        var_storer.db_conn.execute("PRAGMA foreign_keys = ON;")
        var_storer.db_conn.execute("DROP TABLE IF EXISTS Times;")
        var_storer.db_conn.execute("DROP TABLE IF EXISTS Folders;")

        var_storer.db_conn.execute(
            """
            CREATE TABLE Folders (
                folder_path TEXT PRIMARY KEY
            );
            """
        )

        var_storer.db_conn.execute(
            """
            INSERT INTO Folders (folder_path)
            VALUES (?);
            """,
            (var_storer.LOCAL_DIR,),
        )

        var_storer.db_conn.execute(
            """
            CREATE TABLE Times (
                parent_path TEXT,
                file_path TEXT PRIMARY KEY,
                modification_time TEXT NOT NULL,
                FOREIGN KEY (parent_path) REFERENCES Folders (folder_path)
            );
            """
        )

        var_storer.db_conn.execute(
            """
            CREATE TABLE Dates (
                date TEXT PRIMARY KEY
            );
            """
        )
        var_storer.db_conn.execute(
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

        var_storer.db_conn.execute(
            """
            CREATE INDEX idx_log_file_path_synced_date
            ON Log(file_path, synced, date);
            """
        )

        var_storer.db_conn.commit()

        with open(var_storer.run_log, "a", encoding="utf-8") as log_file:
            print(
                f"# Database created{' '*7}#\n# Syncing future changes #\n{'#'*26}",
                file=log_file,
            )

        return True


def log_start_end_times_db(var_storer: VariableStorer, time: str, msg: str):
    """
    Logs the start and end times of the program when program runs
    """
    var_storer.db_conn.execute(
        """
        INSERT INTO Log (date, file_path, synced) VALUES (?, ?, 1)
        """,
        (time, msg),
    )


def write_db_mod_files(var_storer: VariableStorer):
    """
    Writes mod files to database to keep track of which files were modified
    and writes the number of modified files to the run log
    """
    file_data = [
        (var_storer.now, str(file_path[0]), 0) for file_path in var_storer.mod_times
    ]

    if var_storer.STDOUT:
        print("\nModified files:")
        _ = [print(file_path[0]) for file_path in var_storer.mod_times]
        print()

    var_storer.db_conn.execute(
        """
        INSERT OR IGNORE INTO Dates (date) VALUES (?)
        """,
        (var_storer.now,),
    )

    var_storer.db_conn.executemany(
        """
        INSERT INTO Log (date, file_path, synced) VALUES (?, ?, ?)
        """,
        file_data,
    )

    var_storer.db_conn.commit()

    with open(var_storer.run_log, "a", encoding="utf-8") as log_file:
        mod_nums = f"# Files {len(var_storer.mod_times)} "
        if len(mod_nums) < 13:
            str_diff = 13 - len(mod_nums)
            mod_nums += " " * str_diff
        print(mod_nums, file=log_file, end="")


def update_db_mod_file(
    var_storer: VariableStorer, file_path: str, modification_time: str
):
    """
    Function which updates the sync status and modification_time for a specific file path
    """
    var_storer.db_conn.execute(
        """
        UPDATE Log
        SET synced = ?
        WHERE date = ? AND file_path = ?
        """,
        (1, var_storer.now, file_path),
    )

    var_storer.db_conn.execute(
        """
        UPDATE Times
        SET modification_time = ?
        WHERE file_path = ?
        """,
        (modification_time, file_path),
    )
    var_storer.db_conn.commit()


def get_num_synced_files(var_storer: VariableStorer) -> int:
    """
    Counts the number of files which synced this run and returns it
    :return: The number of files which successfully synced this time around
    """
    ret = var_storer.db_conn.execute(
        """
        SELECT COUNT(file_path) FROM Log
        WHERE date = ?
            AND synced = 1
            AND file_path NOT LIKE 'Start Time, PID: %'
            AND file_path NOT LIKE 'End Time, Duration %'
        """,
        (var_storer.now,),
    ).fetchone()[0]

    return ret if ret else 0


def get_fails(var_storer: VariableStorer) -> list[tuple[Path, str]]:
    """
    Gets all failed syncs from db and tries to returns them
    """
    ret = var_storer.db_conn.execute(
        """
        SELECT * FROM Log AS l1
        WHERE l1.synced = 0
        AND NOT EXISTS (
            SELECT 1
            FROM Log AS l2
            WHERE l2.file_path = l1.file_path
            AND l2.synced = 1
            AND l2.date > l1.date
        )
        """
    ).fetchall()

    return [(Path(file_path), mod_time) for mod_time, file_path, _ in ret]
