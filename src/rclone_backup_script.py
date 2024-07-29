#!/home/kr9sis/PDrive/Code/Py/rclone_backup_script/.venv/bin/python
"""
modules docstring
"""
from contextlib import closing
from pathlib import Path
from sqlite3 import OperationalError, connect
from subprocess import PIPE, CalledProcessError, TimeoutExpired, run
from time import localtime, strftime


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

        with open(self.backup_log, "a", encoding="utf-8") as log_file:
            msg = f"# Program started at {strftime("%Y-%m-%d %H:%M", localtime())} #"
            print(f"\n\n{"#"*len(msg)}\n{msg}", file=log_file)

        # Script logic
        with closing(connect(db_file)) as self.conn:
            self.check_or_setup_database(local_directory)
            self.get_modified_files(cwd=Path(local_directory))

            # backup_log and DB file are being changed as the program runs
            # so they will never sync correctly
            self.modified.remove(self.backup_log)
            self.modified.remove(db_file)

            with open(self.backup_log, "a", encoding="utf-8") as log_file:
                print("Files to be modified are:", file=log_file)
                if len(self.modified) < 1000:
                    _ = [print(file, file=log_file) for file in self.modified]
                    print(file=log_file)
                else:
                    print("Too many to list, maximum 1000 files\n", file=log_file)

            self.rclone_sync(local_directory, remote_directory)
            if self.failed_syncs:
                self.update_failed_syncs_table()

        with open(self.backup_log, "a", encoding="utf-8") as log_file:
            msg = f"# Program ended at {strftime("%Y-%m-%d %H:%M", localtime())} #"
            print(f"\n{msg}\n{"#"*len(msg)}\n", file=log_file)

    def check_or_setup_database(self, local_directory):
        """
        Function to set up SQLite database if it doesn't exist
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
        Get's the files from the DB and turns them into a dictionary
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
        print(f"In {str(cwd)}")
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

        with open(self.backup_log, "a", encoding="utf-8") as log_file:
            for file in self.modified:
                file = file.relative_to("/home/kr9sis/PDrive")
                cmd_with_file = []
                cmd_with_file.extend(command)
                cmd_with_file.extend(["--include", str(file)])

                print("Syncing:\n{file}")
                try:
                    run(cmd_with_file, check=True, timeout=300)
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
