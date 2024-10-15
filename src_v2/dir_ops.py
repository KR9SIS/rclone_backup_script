"""
Class to recursively go through every file in a directory and all it's subdirectories
extracting their modification times.
"""

from datetime import datetime
from pathlib import Path
from subprocess import CalledProcessError, TimeoutExpired, run
from textwrap import dedent


def get_files_in_cwd(self, cwd: Path) -> list[tuple[str]]:
    """
    Function to get all files within the current working directory
    and their modification time and return a str containing that
    information sorted with most recent modification first
    """
    with open(self.error_log, "a", encoding="utf-8") as log_file:
        ret = []
        for file in cwd.iterdir():
            if file.name.startswith(".") or file.is_symlink():
                continue  # Get rid of all dotfiles and symlinks

            stat_cmd = ["stat", "-c", "%n %y", str(file)]
            try:
                stat_out = run(stat_cmd, check=True, timeout=10, capture_output=True)
                stat_out = stat_out.stdout.decode("utf-8")

            except CalledProcessError as e:
                now = datetime.now().strftime("%Y-%m-%d %H:%M")
                print(
                    dedent(
                        f"""
                        \n{now}\nError occured with stat command
                        \nCurrent working Directory:\n{cwd}
                        \nCommand:\n{stat_cmd}\nError:\n{e}
                        """
                    ),
                    file=log_file,
                )
                stat_out = ""

            except TimeoutExpired as e:
                now = datetime.now().strftime("%Y-%m-%d %H:%M")
                print(
                    dedent(
                        f"""
                        \n{now}\nError occured with stat command
                        \nCurrent working Directory:\n{cwd}
                        \nCommand:\n{stat_cmd}\nError:\n{e}
                        """
                    ),
                    file=log_file,
                )
                stat_out = ""

            if stat_out:
                mod_time = stat_out[-36:-7]
                filename = stat_out[:-37]
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

    return {Path(db_f_tup[0]): db_f_tup[1] for db_f_tup in db_files}


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
            self.mod_times[file] = files[file]
            # Make sure mod time is different so the file will be synced
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

            self.mod_times[file] = db_files[file]

            # Make sure mod time is different so the file will be synced
            files[file] = "0000-00-00 00:00"

    self.conn.commit()


def check_if_modified(self, files: dict[Path, str], db_files: dict[Path, str]):
    """
    Check the given files and see if they have been
    modified or not if they have been then either check its
    subdirectories or log the file as modified
    """

    for file, modification_time in files.items():
        if file.is_dir():
            self.get_modified_files(file)

        if file.is_file() and modification_time != db_files[file]:
            self.mod_times[file] = modification_time
        self.cur_file += 1


def get_modified_files(self, cwd: Path):
    """
    Recursively checks the cwd and every subdirectory within it
    """
    if self.stdout:
        if self.file_count != -99999:
            percent = round((self.cur_file / self.file_count) * 100)
            print(f"{percent}%", end=" ")
        print(f"In {cwd}")

    files = self.get_files_in_cwd(cwd)
    if not files:
        return self.mod_times

    files = {Path(f_tup[0]): f_tup[1] for f_tup in files}
    db_files = self.create_db_files_dict(cwd)

    if len(files) != len(db_files) or files != db_files:
        self.add_or_del_from_db(files, db_files)

    self.check_if_modified(files, db_files)

    return self.mod_times
