"""
Class to recursively go through every file in a directory and all it's subdirectories
extracting their modification times.
"""

from datetime import datetime
from pathlib import Path
from subprocess import CalledProcessError, TimeoutExpired, run
from textwrap import dedent

from helpers import VariableStorer


def __get_files_in_cwd(var_storer, cwd: Path) -> list[tuple[str, str]]:
    """
    Function to get all files within the current working directory
    and their modification time and return a str containing that
    information sorted with most recent modification first
    """
    ret = []
    for file in cwd.iterdir():
        if (
            file.name.startswith(".")
            or file.is_symlink()
            or any(excluded in str(file) for excluded in var_storer.excluded_paths)
        ):
            # Get rid of all dotfiles, symlinks and explicitly excluded files defined in main.py
            continue

        stat_cmd = ["stat", "-c", "%n %y", str(file)]
        try:
            stat_out = run(stat_cmd, check=True, timeout=10, capture_output=True)
            stat_out = stat_out.stdout.decode("utf-8")
            mod_time = stat_out[-36:-7]
            filename = stat_out[:-37]
            ret.append((filename, mod_time))

        except (CalledProcessError, TimeoutExpired) as e:
            with open(var_storer.run_log, "a", encoding="utf-8") as log_file:
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
    return ret


def __create_db_files_list(var_storer, cwd: Path) -> list[tuple[Path, str]]:
    """
    Gets the files from the DB and turns them into a
    list of tuples containing file paths and mod times
    """
    db_files = var_storer.db_conn.execute(
        """
            SELECT file_path, modification_time
            FROM Times
            WHERE parent_path = ?;
            """,
        (str(cwd),),
    ).fetchall()

    return [(Path(db_f_tup[0]), db_f_tup[1]) for db_f_tup in db_files]


def __add_or_del_from_db(
    var_storer, files: list[tuple[Path, str]], db_files: list[tuple[Path, str]]
):
    """
    Clean up difference between local directory and database
    """
    local_files: set[Path] = {Path(file_tup[0]) for file_tup in files}
    cloud_files: set[Path] = {Path(file_tup[0]) for file_tup in db_files}

    diff = local_files.symmetric_difference(cloud_files)

    for file in diff:
        if file not in cloud_files:  # File was created locally
            parent_dir = file.parent
            mod_time = next(
                (file_tup[1] for file_tup in files if file_tup[0] == file), None
            )
            if file.is_dir():
                var_storer.db_conn.execute(
                    """
                        INSERT INTO Folders(folder_path)
                        VALUES(?);
                        """,
                    (str(file),),
                )
                var_storer.db_conn.execute(
                    """
                        INSERT INTO Times(parent_path, file_path, modification_time)
                        VALUES(?,?,?);
                        """,
                    (str(parent_dir), str(file), mod_time),
                )
            else:
                var_storer.db_conn.execute(
                    """
                        INSERT INTO Times(parent_path, file_path, modification_time)
                        VALUES(?,?,?);
                        """,
                    (str(parent_dir), str(file), mod_time),
                )

                var_storer.mod_times.append((file, mod_time))

        elif file not in local_files:  # File was deleted locally
            mod_time = next(
                (file_tup[1] for file_tup in db_files if file_tup[0] == file), None
            )

            var_storer.db_conn.execute(
                """
                    DELETE FROM Times 
                    WHERE parent_path=?;
                    """,
                (str(file),),
            )

            var_storer.db_conn.execute(
                """
                    DELETE FROM Folders
                    WHERE folder_path=?;
                    """,
                (str(file),),
            )
            var_storer.db_conn.execute(
                """
                    DELETE FROM Times
                    WHERE file_path=?;
                    """,
                (str(file),),
            )

            if file.is_file:
                var_storer.mod_times.append((file, mod_time))


def __check_if_modified(
    var_storer, files: list[tuple[Path, str]], db_files: list[tuple[Path, str]]
):
    """
    Check the given files and see if they have been
    modified or not if they have been then either check its
    subdirectories or log the file as modified
    """

    for file_data in files:
        file, _ = file_data
        if file.is_dir():
            get_modified_files(var_storer, file)

        elif (
            file.is_file()
            and file_data not in db_files
            and file_data not in var_storer.mod_times
        ):
            var_storer.mod_times.append(file_data)

        var_storer.cur_file += 1


def get_modified_files(var_storer: VariableStorer, cwd: Path):
    """
    Recursively checks the cwd and every subdirectory within it
    """
    if var_storer.STDOUT:
        if var_storer.file_count != -99999:
            percent = round((var_storer.cur_file / var_storer.file_count) * 100)
            print(f"{percent}%", end=" ")
        print(f"In {cwd}")

    files = __get_files_in_cwd(var_storer, cwd)
    if not files:
        return var_storer.mod_times

    files = [(Path(f_tup[0]), f_tup[1]) for f_tup in files]
    db_files = __create_db_files_list(var_storer, cwd)

    if len(files) != len(db_files) or files != db_files:
        __add_or_del_from_db(var_storer, files, db_files)

    __check_if_modified(var_storer, files, db_files)

    return var_storer.mod_times
