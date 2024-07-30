#!/home/kr9sis/PDrive/Code/Py/rclone_backup_script/.venv/bin/python
"""
modules contains the class RCloneBackupScript which
when instanciated will sync all files from a given
directory that have been modified.
By using rclone to connect to the repo
"""
from contextlib import closing
from datetime import datetime
from pathlib import Path
from sqlite3 import OperationalError, connect
from subprocess import PIPE, CalledProcessError, TimeoutExpired, run


class RCloneBackupScript:
    """
    Script to check if files in a local directory have been modified and if so
    then send them and their modifications to a remote at PDrive:
    """

    def __init__(self) -> None:
        # Script setup
        local_directory = "/home/kr9sis/PDrive"
        remote_directory = "PDrive:"
        self.modified: set[Path] = set()
        self.failed_syncs: list[tuple[str]] = []

        file_dir = Path(__file__).resolve().parent
        self.backup_log = file_dir / "backup.log"
        db_file = file_dir / "FileModifyTimes.db"

        init_helpers = self.InitHelpers()
        start_time = init_helpers.write_start_end_times(self.backup_log)

        # Script logic
        with closing(connect(db_file)) as self.conn:
            self.check_or_setup_database(local_directory)
            self.get_modified_files(cwd=Path(local_directory))

            # backup_log and DB file are being changed as the program runs
            # so they will never sync correctly
            self.modified.remove(self.backup_log)
            self.modified.remove(db_file)
            init_helpers.write_mod_files(self.backup_log, self.modified)

            if len(self.modified) < 50:
                self.rclone_sync(local_directory, remote_directory)
                if self.failed_syncs:
                    self.update_failed_syncs_table()

        if 50 < len(self.modified):
            init_helpers.write_rclone_cmd(
                self.backup_log, local_directory, remote_directory, self.modified
            )
        init_helpers.write_start_end_times(self.backup_log, start_time)

    class InitHelpers:
        """
        Class designed to implement helper funcitons for RCloneBackupScript class __init__ method
        """

        def get_total_time(self, start_time, end_time):
            """
            Calculates the difference in hours, minutes, and seconds between start_time and end_time
            """
            timedelta_tt = end_time - start_time
            total_seconds = timedelta_tt.total_seconds()
            h, remainder = divmod(total_seconds, 3600)
            m, s = divmod(remainder, 60)

            return (h, m, s)

        def write_start_end_times(self, backup_log, start_time=None):
            """
            Writes the start and end times to the backup_log
            """
            now = datetime.now()
            with open(backup_log, "a", encoding="utf-8") as log_file:
                if not start_time:
                    msg = f"# Program started at {now.strftime("%Y-%m-%d %H:%M")} #"
                    print(f"\n\n{"#"*len(msg)}\n{msg}", file=log_file)
                    return now

                h, m, s = self.get_total_time(start_time, now)
                msg = f"""
                    # Program ended at {now.strftime("%Y-%m-%d %H:%M")}. Total time {h}:{m}:{s} #
                    """

                print(f"\n{msg}\n{"#"*len(msg)}\n", file=log_file)

                return None

        def write_mod_files(self, backup_log, modified):
            """
            If there's less than 100 modified files, then it writes each to the file
            otherwise it writes an error message
            """
            with open(backup_log, "a", encoding="utf-8") as log_file:
                print("Files to be modified are:", file=log_file)
                if len(modified) < 100:
                    _ = [print(file, file=log_file) for file in modified]
                    print(file=log_file)
                else:
                    print("Too many to list, maximum 100 files\n", file=log_file)

        def write_rclone_cmd(
            self, backup_log, local_directory, remote_directory, modified
        ):
            """
            Creates the complete rclone command for the current run and prints it out
            for the user to sync files which couldn't be synced
            """
            cmd_list = [
                "rclone",
                "sync",
                local_directory,
                remote_directory,
                "-v",
                "--log-file",
                "/home/kr9sis/PDrive/Code/Py/rclone_backup_script/src/backup.log",
                "--protondrive-replace-existing-draft=true",
            ]
            cmd_list.extend([item for file in modified for item in ["--include", file]])
            cmd = ", ".join(cmd_list)

            with open(backup_log, "a", encoding="utf-8") as log_file:
                print(
                    f"""Sync was cancelled. Too many files, maximum 50 at a time. \n
                    It is reccomended that you sync them manually yourself with the command
                    \n\n
                    {cmd}
                    \n
                    """,  # Create a list where you add "--include" and then the file from modified
                    file=log_file,
                )

    def check_or_setup_database(self, local_directory):
        """
        Function to set up SQLite database if it doesn't exist
        and grab all files which failed to sync last time program was run
        """
        try:
            # Check if database is already set up
            failed_syncs = self.conn.execute("SELECT * FROM FailedSyncs").fetchall()
            self.conn.execute("DELETE FROM FailedSyncs")
            self.conn.commit()
            self.modified.union({Path(file[0]) for file in failed_syncs})

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
                    file_path TEXT PRIMARY KEY
                );
                """
            )

            self.conn.commit()

    def get_files_in_cwd(self, cwd: str) -> str:
        """
        Function to get all files within the current working directory
        and their modification time and return a str containing that
        information sorted with most recent modification first
        """
        du_cmd = ["du", "--time", "--all", "--max-depth=1", cwd]
        sort_cmd = ["sort", "-k2", "-r"]
        try:
            du_out = run(du_cmd, check=True, timeout=10, stdout=PIPE)
            sort_out = run(
                sort_cmd, check=True, timeout=10, input=du_out.stdout, stdout=PIPE
            )
            return sort_out.stdout.decode("utf-8")

        except CalledProcessError as e:
            print(f"CWD:\n{cwd}\nError occured with getting files command\nError:\n{e}")
            return ""
        except TimeoutExpired as e:
            print(f"CWD:\n{cwd}\nError occured with getting files command\nError:\n{e}")
            return ""

    def create_files_dict(self, files_str, cwd: Path) -> dict[Path, str]:
        """
        Takes in the files string and turns it into a dictionary
        where the file paths are keys and mod times are values
        """
        files_str = files_str.strip()
        files_str = files_str.split("\n")
        files = {}
        for file in files_str:
            file = file.split("\t")[1:3]

            file_path = Path(file[1])
            mod_time = file[0]

            if file[1] == str(cwd) or file_path.name.startswith("."):
                continue
            files[file_path] = mod_time

        return files

    def create_db_files_dict(self, cwd: Path) -> dict[Path, str]:
        """
        Gets the files from the DB and turns them into a dictionary
        where the file paths are keys and mod times are values
        """
        db_files = self.conn.execute(
            """
            SELECT file_path, modification_time
            FROM Times
            WHERE parent_path = ?;
            """,
            (str(cwd),),
        ).fetchall()

        return {Path(item[0]): item[1] for item in db_files}

    def add_or_del_from_db(self, files, db_files):
        """
        Clean up difference between local directory and database
        """
        local_files: set[Path] = set(files)
        cloud_files: set[Path] = set(db_files)

        diff = local_files.symmetric_difference(cloud_files)
        self.modified = self.modified.union(diff)
        for file in diff:
            if file not in cloud_files:  # File was created locally
                parent_dir = file.parent
                if file.is_dir():
                    self.conn.execute(
                        """
                        INSERT INTO Folders(folder_path)
                        VALUES(?);
                        """,
                        (str(file),),
                    )
                    self.conn.execute(
                        """
                        INSERT INTO Times(parent_path, file_path, modification_time)
                        VALUES(?,?,?);
                        """,
                        (str(parent_dir), str(file), files[file]),
                    )
                else:
                    self.conn.execute(
                        """
                        INSERT INTO Times(parent_path, file_path, modification_time)
                        VALUES(?,?,?);
                        """,
                        (str(parent_dir), str(file), files[file]),
                    )

                db_files[file] = "0000-00-00 00:00"

            elif file not in local_files:  # File was deleted locally
                self.conn.execute(
                    """
                    DELETE FROM Times 
                    WHERE parent_path=?;
                    """,
                    (str(file),),
                )

                self.conn.execute(
                    """
                    DELETE FROM Folders
                    WHERE folder_path=?;
                    """,
                    (str(file),),
                )
                self.conn.execute(
                    """
                    DELETE FROM Times
                    WHERE file_path=?;
                    """,
                    (str(file),),
                )

                files[file] = "0000-00-00 00:00"

        self.conn.commit()

    def check_if_modified(self, files: dict[Path, str], db_files: dict[Path, str]):
        """
        Check the given files and see if they have been
        modified or not if they have been then either check its
        subdirectories or log the file as modified
        """

        for file, modification_time in files.items():
            if modification_time != db_files[file]:
                if file.is_dir():
                    self.get_modified_files(file)
                elif file.is_file():
                    self.modified.add(file)
                self.conn.execute(
                    """
                    UPDATE Times SET modification_time = ?
                    WHERE file_path = ?
                    """,
                    (modification_time, str(file)),
                )
            else:
                break

        self.conn.commit()

    def get_modified_files(self, cwd: Path):
        """
        Recursively checks the cwd and every subdirectory within it
        """
        files = self.get_files_in_cwd(str(cwd))
        if not files:
            return

        files = self.create_files_dict(files, cwd)
        db_files = self.create_db_files_dict(cwd)

        if len(files) != len(db_files):
            self.add_or_del_from_db(files, db_files)

        self.check_if_modified(files, db_files)

    def rclone_sync(self, source_path, destination_path):
        """
        Sync modified files to Proton Drive
        """
        command = [
            "rclone",
            "sync",
            source_path,
            destination_path,
            "-v",
            "--log-file",
            "/home/kr9sis/PDrive/Code/Py/rclone_backup_script/src/backup.log",
            "--protondrive-replace-existing-draft=true",
        ]

        for file, file_num in zip(self.modified, range(1, len(self.modified))):
            file = file.relative_to("/home/kr9sis/PDrive")
            cmd_with_file = []
            cmd_with_file.extend(command)
            cmd_with_file.extend(["--include", str(file)])

            with open(self.backup_log, "a", encoding="utf-8") as log_file:
                print(
                    f"""
                    Syncing file #{file_num}:\n{file}\n
                    Total synced: {file_num // len(self.modified)}%
                    """,
                    file=log_file,
                )

            with open(self.backup_log, "a", encoding="utf-8") as log_file:
                try:
                    run(cmd_with_file, check=True, timeout=600)
                except CalledProcessError as e:
                    print(
                        f"""
                        Error occured with syncing file\n
                        {file}\nError:\n{e}\n
                        File will be added to FailedSyncs table
                        """,
                        file=log_file,
                    )
                    self.failed_syncs.append((str(file),))
                except TimeoutExpired as e:
                    print(
                        f"""
                        Error occured with syncing file\n
                        {file}\nError:\n{e}\n
                        File will be added to FailedSyncs table
                        """,
                        file=log_file,
                    )
                    self.failed_syncs.append((str(file),))

    def update_failed_syncs_table(self):
        """
        Add all files which failed to sync to the DB
        for retrival and a retry next time the script is run
        """
        self.conn.executemany(
            """
            INSERT INTO FailedSyncs (file_path)
            VALUES (?);
            """,
            self.failed_syncs,
        )
        self.conn.commit()

        with open(self.backup_log, "a", encoding="utf-8") as log_file:
            print("Files which failed to sync", file=log_file)
            _ = [print(file, file=log_file) for file in self.failed_syncs]


if __name__ == "__main__":
    RCloneBackupScript()
