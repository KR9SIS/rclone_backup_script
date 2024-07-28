#!/home/kr9sis/PDrive/Code/Py/rclone_backup_script/.venv/bin/python
"""
modules docstring
"""
from contextlib import closing
from pathlib import Path
from sqlite3 import OperationalError, connect
from subprocess import PIPE, CalledProcessError, TimeoutExpired, run

from rclone_python import rclone

# from subprocess import CalledProcessError, TimeoutExpired, run, PIPE


class RCloneBackupScript:
    """
    Script to check if files in a local directory have been modified and if so
    then send them and their modifications to a remote at PDrive:
    """

    def __init__(self) -> None:
        # Script setup
        local_directory = "/home/kr9sis/PDrive"
        # remote_directory = "PDrive:"
        self.modified: set[Path] = set()

        # Script logic
        with closing(connect("FileModifyTimes.db")) as self.conn:
            self.check_or_setup_database(local_directory)
            self.get_modified_files(cwd=Path(local_directory))
            # self.rclone_sync(local_directory, remote_directory)
            ""

    def check_or_setup_database(self, local_directory):
        """
        Function to set up SQLite database if it doesn't exist
        """
        try:
            # Check if database is already set up
            self.conn.execute(
                """
                SELECT folder_path FROM Folders
                WHERE folder_path = ?
                """,
                ("/home/kr9sis/PDrive",),
            )

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

    def check_if_modified(self, cwd: Path, files):
        """
        Check the given files and see if they have been
        modified or not if they have been then either check its
        subdirectories or log the file as modified
        """
        files = files.strip()
        files = files.split("\n")
        tmp = {}
        for file in files:
            file = file.split("\t")[1:3]

            file_path = Path(file[1])
            mod_time = file[0]

            if file[1] == str(cwd) or file_path.name.startswith("."):
                continue
            tmp[file_path] = mod_time

        files = tmp
        del tmp

        db_files = self.conn.execute(
            """
            SELECT file_path, modification_time
            FROM Times
            WHERE parent_path = ?;
            """,
            (str(cwd),),
        ).fetchall()

        db_files = {Path(item[0]): item[1] for item in db_files}

        if len(files) != len(db_files):
            self.add_or_del_from_db(files, db_files)

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

        self.check_if_modified(cwd, files)

    def rclone_sync(self, source_path, destination_path):
        """
        Sync modified files to Proton Drive
        """
        arguments = [
            "--dry-run",
            "-v",
            "--log-file",
            "/home/kr9sis/PDrive/Code/Py/rclone_backup_script/backup.log",
        ]

        for file in self.modified:
            file = file.relative_to("/home/kr9sis/PDrive")
            arguments.append("--include")
            arguments.append(str(file))

        rclone.sync(
            source_path,
            destination_path,
            show_progress=True,
            args=arguments,
        )


if __name__ == "__main__":
    RCloneBackupScript()
