#!/home/kr9sis/PDrive/Code/Py/rclone_backup_script/.venv/bin/python
"""
modules contains the class RCloneBackupScript which
when instanciated will sync all files from a given
directory that have been modified.
By using rclone to connect to the repo
"""

from contextlib import closing
from pathlib import Path
from sqlite3 import connect
from subprocess import CalledProcessError, TimeoutExpired, run

from check_or_setup_db import check_or_setup_database
from init_helpers import InitHelpers
from rclone_sync import rclone_sync, update_failed_syncs_table


class RCloneBackupScript:
    """
    Script to check if files in a local directory have been modified and if so
    then send them and their modifications to a remote at PDrive:
    """

    def __init__(self) -> None:
        # Script setup
        local_directory = "/home/kr9sis/PDrive"
        remote_directory = "PDrive:"
        self.modified: dict[Path, str] = {}
        self.failed_syncs: list[tuple[str]] = []

        file_dir = Path(__file__).resolve().parent
        self.backup_log = file_dir / "backup.log"
        db_file = file_dir / "FileModifyTimes.db"

        init_helpers = InitHelpers()
        start_time = init_helpers.write_start_end_times(self.backup_log)

        # Script logic
        with closing(connect(db_file)) as self.conn:
            self.modified.update(check_or_setup_database(local_directory, self.conn))
            self.get_modified_files(cwd=Path(local_directory))

            # backup_log and DB file are being changed as the program runs
            # so they will never sync correctly
            self.modified.pop(self.backup_log, None)
            self.modified.pop(db_file, None)
            init_helpers.write_mod_files(self.backup_log, self.modified)

            if len(self.modified) < 50:
                rclone_sync(self, local_directory, remote_directory)
                if self.failed_syncs:
                    update_failed_syncs_table(self)

        if 50 <= len(self.modified):
            init_helpers.write_rclone_cmd(
                self.backup_log, local_directory, remote_directory, self.modified
            )
        init_helpers.write_start_end_times(self.backup_log, start_time)

    def get_files_in_cwd(self, cwd) -> list[str]:
        """
        Function to get all files within the current working directory
        and their modification time and return a str containing that
        information sorted with most recent modification first
        """

        with open(self.backup_log, "a", encoding="utf-8") as log_file:
            ret = []
            for file in cwd.iterdir():
                if file.name.startswith("."):
                    continue  # Get rid of all dotfiles
                stat_cmd = ["stat", "-c", "%n %y", str(file)]
                try:
                    stat_out = run(
                        stat_cmd, check=True, timeout=10, capture_output=True
                    )
                    stat_out = stat_out.stdout.decode("utf-8")

                except CalledProcessError as e:
                    print(
                        f"CWD:\n{cwd}\nError occured with getting files command\nError:\n{e}",
                        file=log_file,
                    )
                    stat_out = ""

                except TimeoutExpired as e:
                    print(
                        f"CWD:\n{cwd}\nError occured with getting files command\nError:\n{e}",
                        file=log_file,
                    )
                    stat_out = ""

                mod_time = stat_out[-36:-7]
                filename = stat_out[:-37]
                print(f"{filename} : {mod_time}")
                ret.append((filename, mod_time))

        return ret

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
                self.modified[file] = files[file]
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

                self.modified[file] = db_files[file]
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
                    self.modified[file] = modification_time
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
        print(f"In {cwd}")
        files = self.get_files_in_cwd(cwd)
        if not files:
            return

        files = {Path(file[0]): file[1] for file in files}
        db_files = self.create_db_files_dict(cwd)

        if len(files) != len(db_files):
            self.add_or_del_from_db(files, db_files)

        self.check_if_modified(files, db_files)


if __name__ == "__main__":
    RCloneBackupScript()
