"""
rclone backup script for backing up local directory files
"""

from contextlib import closing
from datetime import datetime
from logging import ERROR, basicConfig, error
from os import getpid
from pathlib import Path
from sqlite3 import IntegrityError, OperationalError, connect
from traceback import format_exc
from argparse import ArgumentParser

from db_ops import (
    get_count_or_setup_db,
    get_fails,
    log_start_end_times_db,
    write_db_mod_files,
)
from dir_ops import get_modified_files
from helpers import VariableStorer, write_start_end_times
from rclone_ops import check_connection, sync


def main(STDOUT: bool, CWD: Path, RETRY_FAILS: bool, COUNT_MODF: bool):
    """
    Main function for the rclone backup script
    """
    if not isinstance(STDOUT, bool):
        raise TypeError("STDOUT must be of type bool")
    if not isinstance(RETRY_FAILS, bool):
        raise TypeError("RETRY_FAILs must be of type bool")
    if not isinstance(COUNT_MODF, bool):
        raise TypeError("COUNT_MODE must be of type bool")
    if not isinstance(CWD, Path) or not CWD.exists():
        raise TypeError("CWD must be of type path and exist")

    var_storer = VariableStorer(STDOUT, CWD)
    try:
        write_start_end_times(var_storer, var_storer.start_time, RETRYING=RETRY_FAILS, COUNTING=COUNT_MODF)

        with closing(connect(var_storer.db_file)) as var_storer.db_conn:
            if not check_connection(var_storer):
                write_start_end_times(
                    var_storer,
                    datetime.now(),
                    start_time=var_storer.start_time,
                )
                return

            new_db = get_count_or_setup_db(var_storer)
            log_start_end_times_db(
                var_storer, var_storer.now, f"Start Time, PID: {getpid()}"
            )

            if RETRY_FAILS:
                if STDOUT:
                    print("Retrying fails")
                var_storer.mod_times = get_fails(var_storer)
            else:
                var_storer.mod_times = get_modified_files(var_storer, var_storer.CWD)

            if COUNT_MODF:
                if STDOUT:
                    print(f"\n{len(var_storer.mod_times)} modified files")
                with open(var_storer.run_log, "a", encoding="utf-8") as run_log:
                    msg = f"# Files {len(var_storer.mod_times):<7}{'Exiting':<10}#"
                    print(msg, file=run_log)
                write_start_end_times(
                    var_storer,
                    datetime.now(),
                    start_time=var_storer.start_time,
                )
                return

            if new_db is True:
                if STDOUT:
                    print("New database detected, sync cancelled")
                write_start_end_times(
                    var_storer,
                    datetime.now(),
                    start_time=var_storer.start_time,
                )
                return  # Only sync if database existed to get around syncing thousands of files

            if not RETRY_FAILS and len(var_storer.mod_times) == 3:
                with open(var_storer.run_log, "a", encoding="utf-8") as run_log:
                    print("# Files 0    Exiting     #", file=run_log)
                write_start_end_times(
                    var_storer,
                    datetime.now(),
                    start_time=var_storer.start_time,
                )
                return  # Only sync files if they are different

            elif len(var_storer.mod_times) > 200:
                if STDOUT:
                    print(f"{len(var_storer.mod_times)} modified files\nModified files list will be truncated down to 200")
                # Only sync 200 files at a time
                var_storer.mod_times = var_storer.mod_times[:200]

            write_db_mod_files(var_storer)
            sync(var_storer)
            write_start_end_times(
                var_storer,
                datetime.now(),
                start_time=var_storer.start_time,
            )
            var_storer.db_conn.commit()

    except (Exception, IntegrityError, OperationalError) as exc:
        pass
        # Logging any unknown exceptions which might happen.
        # Because this program will be called automatically and without anyone watching stdout.
        with closing(connect(var_storer.db_file)) as var_storer.db_conn:
            with open(var_storer.run_log, "a", encoding="utf-8") as run_log:
                print(f"\n  {exc}\n", file=run_log)

            end_time = datetime.now()
            write_start_end_times(
                var_storer,
                end_time,
                start_time=var_storer.start_time,
            )

            write_start_end_times(
                var_storer, var_storer.start_time, RETRYING=RETRY_FAILS, error=True
            )
            basicConfig(
                filename=var_storer.err_log,
                filemode="a",
                format="\n%(asctime)s - %(levelname)s - %(message)s",
                level=ERROR,
            )
            error(format_exc())
            write_start_end_times(
                var_storer,
                end_time,
                start_time=var_storer.start_time,
                error=True,
            )
            var_storer.db_conn.commit()


if __name__ == "__main__":
    parser = ArgumentParser(prog="RCloneBackupScript")
    parser.add_argument(
        "-v",
        "--stdout",
        help="Print output to standard out",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "-p",
        "--cwd",
        type=Path,
        help="Chose where to look for files to sync",
        default="/home/kr9sis/PDrive/",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-r",
        "--retry_fails",
        help="Retry files which failed to sync",
        action="store_true",
        default=False,
    )
    group.add_argument(
        "-c",
        "--count",
        help="Count how many files are modified and need to be synced",
        action="store_true",
        default=False,
    )
    args = parser.parse_args()

    main(args.stdout, args.cwd, args.retry_fails, args.count)
