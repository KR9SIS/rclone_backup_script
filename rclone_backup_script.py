"""
modules docstring
"""

import sys  # TODO: Remove when program works
from os.path import isdir, isfile
from subprocess import CalledProcessError, TimeoutExpired, run

from psycopg import connect


class RCloneBackupScript:
    """
    Script to check if files in a local directory have been modified and if so
    then send them and their modifications to a remote at PDrive:
    """

    def __init__(self) -> None:
        print("Entered Init")
        local_directory = "/home/kr9sis/PDrive/"
        remote_directory = "PDrive:"
        self.modified: set[str] = set()
        with connect("dbname=FileModifyTimes user=postgres") as self.conn:
            print("Entering get_modified_files")
            self.get_modified_files(cwd=local_directory)
            print("Entering rclone_sync")
            self.rclone_sync(
                source_path=local_directory, destination_path=remote_directory
            )
            print("Entering update_mod_times_in_db")
            self.update_mod_times_in_db()
            print("Entering backup_log_to_git")
            self.backup_log_to_git()

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
                f"Process returned unsuccessful return code.\nCode: {exc.returncode} \nException: {exc}\nError: {exc.stderr}\nCWD {cwd}"
            )

        except TimeoutExpired as exc:
            print(f"Process timed out\nException: {exc}")

        return files

    def add_or_del_from_db(self, files, db_files):
        """
        Clean up difference between local directory and database
        """
        local_files: set[str] = set(files)
        cloud_files: set[str] = set(db_files)

        diff = local_files.symmetric_difference(cloud_files)
        self.modified = self.modified.union(diff)
        with self.conn.cursor() as cur:
            for file in diff:
                if file not in cloud_files:  # File was created locally
                    index = file.rfind("/", 0, -1)
                    parent_dir = file[0 : index + 1]
                    if isdir(file):
                        cur.execute(
                            """
                            INSERT INTO Folders(folder_path)
                            VALUES(%s);
                            """,
                            (file,),
                        )
                        cur.execute(
                            """
                            INSERT INTO Times(parent_path, file_path, modification_time)
                            VALUES(%s, %s, %s);
                            """,
                            (parent_dir, file, "0000-00-00 00:00"),
                        )
                    else:
                        cur.execute(
                            """INSERT INTO Times(parent_path, file_path, modification_time)
                            VALUES(%s, %s, %s);""",
                            (parent_dir, file, "0000-00-00 00:00"),
                        )

                    db_files[file] = "0000-00-00 00:00"

                elif file not in local_files:  # File was deleted locally
                    if file[-1] == "/":
                        cur.execute(
                            """
                            DELETE FROM Times
                            WHERE parent_path=%s;
                            """,
                            (file,),
                        )

                        cur.execute(
                            """
                            DELETE FROM Folders
                            WHERE folder_path=%s;
                            """,
                            (file,),
                        )
                    else:
                        cur.execute(
                            """
                            DELETE FROM Times
                            WHERE file_path=%s;
                            """,
                            (file,),
                        )

                    files[file] = "0000-00-00 00:00"

            self.conn.commit()

    def check_if_modified(self, cwd: str, files: str):
        """
        Check the given files and see if they have been
        modified or not if they have been then either check its
        subdirectories or log the file as modified
        """
        files = files.strip().split("\n")
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

        with self.conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    SELECT file_path, modification_time
                    FROM Times
                    WHERE parent_path = %s;
                    """,
                    (cwd,),
                )
                db_files = cur.fetchall()
            except Exception as e:
                print(
                    f"\n\n Exception occured when getting {cwd} content form DB\nException:\n{e}"
                )

        db_files = {key: value for key, value in db_files}

        if len(files) != len(db_files):
            self.add_or_del_from_db(files, db_files)

        for file in files:
            if files[file] != db_files[file]:
                if isdir(file):
                    self.get_modified_files(file)
                elif isfile(file):
                    self.modified.add(file)
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
            sys.exit()

    def update_mod_times_in_db(self):
        """
        Update the database mod times to their current version
        """
        with self.conn.cursor() as cur:
            for file in self.modified:
                try:
                    mod_time = run(
                        ["ls", "-lt", "--time-style=+'%Y-%m-%d %H:%M'", f"{file}"],
                        check=True,
                        capture_output=True,
                        timeout=10,
                    )
                    mod_time = mod_time.stdout.decode("utf-8")
                    mod_time = " ".join(mod_time.split(" ")[5:7]).strip("'")
                except CalledProcessError as e:
                    if (
                        e.returncode == 2
                    ):  # File was modified locally so it is in the DB but not the local filesystem
                        continue

                    raise CalledProcessError  # Should never go here, but if it does then I want to stop the program

                cur.execute(
                    """
                    UPDATE Times
                    SET modification_time = %s
                    WHERE file_path = %s;
                    """,
                    (mod_time, file),
                )

    def backup_log_to_git(self):
        """
        Every 10 runs, the log files will be backed up to github
        """
        with self.conn.cursor() as cur:
            backup_num = cur.execute(
                """
                SELECT nextval('BackupNum');
                """
            ).fetchall()

        backup_num = backup_num[0][0]
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
                    "-m" f"Backup #{backup_num} made, syncing to github",
                ],
                check=True,
                timeout=10,
            )
            run(
                ["git", "push"],
                check=True,
                timeout=10,
            )


if __name__ == "__main__":
    RCloneBackupScript()
