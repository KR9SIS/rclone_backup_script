from subprocess import run, CalledProcessError, TimeoutExpired
from os.path import isfile, isdir
from psycopg import connect


class RCloneBackupScript:
    def __init__(self) -> None:
        local_directory = "/home/kr9sis/PDrive/"
        remote_directory = "PDrive:"
        self.modified: set[str] = set()
        with connect("dbname=FileModifyTimes user=postgres") as self.conn:
            self.get_modified_files(cwd=local_directory)
            self.rclone_sync(
                source_path=local_directory, destination_path=remote_directory
            )
            self.update_mod_times_in_db()
            self.backup_log_to_git()
        ""

    def get_files_in_cwd(self, cwd) -> str:
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
        local_files: set[str] = {val for val in files}
        cloud_files: set[str] = {val for val in db_files}

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

    def check_if_modified(self, cwd: str, files: str) -> None:
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
                ""

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
            else:
                break

        return

    def get_modified_files(self, cwd: str):
        files = self.get_files_in_cwd(cwd)
        if not files:
            return
        else:
            self.check_if_modified(cwd, files)

    def rclone_sync(self, source_path, destination_path):
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
            command.append("--include")
            command.append(file)

        run(command, check=True, timeout=1800)

    def update_mod_times_in_db(self):
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
                    else:
                        raise Exception  # Should never go here, but if it does then I want to stop the program
                cur.execute(
                    """
                    UPDATE Times
                    SET modification_time = %s
                    WHERE file_path = %s;
                    """,
                    (mod_time, file),
                )

    def backup_log_to_git(self):
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
            run(["git", "push"])

        ""


RCloneBackupScript()
