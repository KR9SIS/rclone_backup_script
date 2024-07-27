"""
modules docstring
"""

import sys  # TODO: Remove when program works
from contextlib import closing
from os.path import isdir, isfile
from sqlite3 import OperationalError, connect
from subprocess import CalledProcessError, TimeoutExpired, run


class RCloneBackupScript:
    """
    Script to check if files in a local directory have been modified and if so
    then send them and their modifications to a remote at PDrive:
    """

    def __init__(self) -> None:
        # Script setup
        local_directory = "/home/kr9sis/PDrive/Code/Py/rclone_backup_script/"
        remote_directory = "PDrive:"
        self.modified: set[str] = set()

        # Script logic
        with closing(connect("FileModifyTimes.db", autocommit=False)) as self.conn:
            self.check_or_setup_database()
            self.get_modified_files(cwd=local_directory)
            # self.rclone_sync(local_directory, remote_directory) #TODO: Uncomment
            # self.update_mod_times_in_db()
            # self.backup_log_to_git() #TODO: Uncomment

    def check_or_setup_database(self):
        """
        Function to set up SQLite database if it doesn't exist
        """
        try:
            # Check if database is already set up
            self.conn.execute("SELECT BackupNum FROM BackupNum")

        except OperationalError:
            # If not, then set it up
            self.conn.execute("PRAGMA foreign_keys = ON;")
            self.conn.execute("DROP TABLE IF EXISTS BackupNum;")
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
                CREATE TABLE BackupNum (
                    num_key TEXT PRIMARY KEY,
                    backup_num INTEGER
                );
                """
            )

            self.conn.execute(
                """
                INSERT INTO BackupNum (num_key, backup_num)
                VALUES (?, ?)
                """,
                ("numkey", 0),
            )

            self.conn.commit()

    def get_files_in_cwd(self, cwd) -> str:
        """
        Get all files within CWD and all subdirectories
        """
        try:
            files = run(
                ["ls", "-lt", "--time-style=+'%Y-%m-%d %H:%M'", f"{cwd}"],
                check=True,
                timeout=10,
                capture_output=True,
            )
            files = files.stdout.decode("utf-8")

        except CalledProcessError as exc:
            print(
                f"""
                Process returned unsuccessful return code.\n
                Code: {exc.returncode} \nException: {exc}\n
                Error: {exc.stderr}\n
                CWD {cwd}
                """
            )
            files = ""

        except TimeoutExpired as exc:
            print(f"Process timed out\nException: {exc}")
            raise exc

        return files

    def add_or_del_from_db(self, files, db_files):
        """
        Clean up difference between local directory and database
        """
        local_files: set[str] = set(files)
        cloud_files: set[str] = set(db_files)

        diff = local_files.symmetric_difference(cloud_files)
        self.modified = self.modified.union(diff)
        for file in diff:
            if file not in cloud_files:  # File was created locally
                index = file.rfind("/", 0, -1)
                parent_dir = file[0 : index + 1]
                if isdir(file):
                    self.conn.execute(
                        """
                        INSERT INTO Folders(folder_path)
                        VALUES(?);
                        """,
                        (file,),
                    )
                    self.conn.execute(
                        """
                        INSERT INTO Times(parent_path, file_path, modification_time)
                        VALUES(?,?,?);
                        """,
                        (parent_dir, file, files[file]),
                    )
                else:
                    self.conn.execute(
                        """INSERT INTO Times(parent_path, file_path, modification_time)
                        VALUES(?,?,?);""",
                        (parent_dir, file, files[file]),
                    )

                db_files[file] = "0000-00-00 00:00"

            elif file not in local_files:  # File was deleted locally
                if file[-1] == "/":
                    self.conn.execute(
                        """
                        DELETE FROM Times 
                        WHERE parent_path=?;
                        """,
                        (file,),
                    )

                    self.conn.execute(
                        """
                        DELETE FROM Folders
                        WHERE folder_path=?;
                        """,
                        (file,),
                    )
                else:
                    self.conn.execute(
                        """
                        DELETE FROM Times
                        WHERE file_path=?;
                        """,
                        (file,),
                    )

                files[file] = "0000-00-00 00:00"

        self.conn.commit()

    def check_if_modified(self, cwd: str, files):
        """
        Check the given files and see if they have been
        modified or not if they have been then either check its
        subdirectories or log the file as modified
        """
        files = files.strip()
        files = files.split("\n")
        tmp = {}
        for file in files:
            if len(file) > 50:
                file = file.split()
                key = cwd + " ".join(file[7:])
                if isdir(key):
                    key += "/"
                values = " ".join(file[5:7]).strip("'")
                tmp[key] = values

        files = tmp
        del tmp

        db_files = self.conn.execute(
            """
            SELECT file_path, modification_time
            FROM Times
            WHERE parent_path = ?;
            """,
            (cwd,),
        ).fetchall()

        db_files = dict(db_files)

        if len(files) != len(db_files):
            self.add_or_del_from_db(files, db_files)

        for file, modification_time in files.items():
            if modification_time != db_files[file]:
                if isdir(file):
                    self.get_modified_files(file)
                elif isfile(file):
                    self.modified.add(file)
            else:
                break

    def get_modified_files(self, cwd: str):
        """
        Recursively checks the cwd and every subdirectory within it
        """
        print(f"In {cwd}")
        files = self.get_files_in_cwd(cwd)
        if not files:
            return

        self.check_if_modified(cwd, files)

    def rclone_sync(self, source_path, destination_path):
        """
        Sync modified files to Proton Drive
        """
        command = [
            "/usr/bin/rclone",
            "sync",
            source_path,
            destination_path,
            "-v",
            "--log-file",
            "/home/kr9sis/PDrive/Code/Py/rclone_backup_script/backup.log",
            "--dry-run",
        ]
        for file in self.modified:
            file = file[19:]
            command.append("--include")
            command.append(file)
        try:
            run(command, check=True, timeout=1800)
        except CalledProcessError as e:
            print(e.stderr.decode("utf-8"), "\n")
            print(e.returncode, "\n")
            sys.exit()  # TODO: Remove after fix

    def update_mod_times_in_db(self):
        """
        Update the database mod times to their current version
        """
        counter = 1
        for file in self.modified:
            if file[-1] != "/":
                print(f"File {counter} of {len(self.modified)}")
                try:
                    cmd_out = run(
                        ["du", "--time", f"{file}"],
                        check=True,
                        capture_output=True,
                        timeout=10,
                    )
                    cmd_out = cmd_out.stdout.decode("utf-8")
                    mod_time = cmd_out.split("\t")[1]
                except CalledProcessError as e:
                    if e.returncode == 2:
                        # File was modified locally so it is in the DB but not the local filesystem
                        continue

                    raise e
                    # Should never go here, but if it does then I want to stop the program

                self.conn.execute(
                    """
                    UPDATE Times
                    SET modification_time = ?
                    WHERE file_path = ?;
                    """,
                    (mod_time, file),
                )
                counter += 1

        self.conn.commit()

    def backup_log_to_git(self):
        """
        Every 10 runs, the log files will be backed up to github
        """
        backup_num = self.conn.execute(
            """
            SELECT backup_num from BackupNum
            WHERE num_key = ?;
            """,
            ("numkey",),
        ).fetchone()

        backup_num = backup_num[0]
        if backup_num % 10 == 0:
            run(
                [
                    "git",
                    "add",
                    "/home/kr9sis/PDrive/Code/Py/rclone_backup_script/backup.log",
                ],
                check=True,
                timeout=10,
            )
            run(
                [
                    "git",
                    "commit",
                    f"-m Backup #{backup_num} made, syncing to github",
                ],
                check=True,
                timeout=10,
            )
            run(
                ["git", "push"],
                check=True,
                timeout=10,
            )
        backup_num += 1
        self.conn.execute(
            """
            UPDATE BackupNum
            SET backup_num = ?
            WHERE num_key = ?
            """,
            (backup_num, "numkey"),
        )
        self.conn.commit()


if __name__ == "__main__":
    RCloneBackupScript()
