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

from db_ops import get_count_or_setup_db, log_start_end_times_db, write_db_mod_files
from dir_ops import get_modified_files
from rclone_ops import check_connection, check_log_n_db_eq, sync


class RCloneBackupScript:
    """
    Script to check if files in a local directory have been modified and if so
    then send them and their modifications to a remote at PDrive:
    1. Check connection
    2. Get or setup database connection
    3. Recursively get modified files from local directory
        - Filter out unneeded files
    5. Sync modified files
        - Filter out unneeded modified files
        - If sync was successfull then update modification time in DB
    """

    def __init__(self) -> None:
        try:
            self.stdout = False  # WARN: Make sure stdout is false
            LOCAL_DIRECTORY = "/home/kr9sis/PDrive"
            REMOTE_DIRECTORY = "PDrive:"
            self.mod_times: list[tuple[Path, str]] = []
            self.file_count = -99999
            self.cur_file = 0
            self.excluded_paths: set[str] = {
                "__pycache__",
                "node_modules",
                "firm_extract_NOBACKUP",
            }
            # Dotfiles and synlinks are also excluded in get_files_in_cwd()

            file_dir = Path(__file__).resolve().parent
            self.start_time = datetime.now()
            self.run_log = (
                file_dir
                / "logs"
                / f"{self.start_time.year % 100}_{self.start_time.month:02}_run.log"
            )
            self.db_file = file_dir / "RCloneBackupScript.db"

            self.write_start_end_times(self.start_time, self.run_log)
            self.now: str = self.start_time.strftime("%Y-%m-%d %H:%M")

            with closing(connect(self.db_file)) as self.db_conn:
                log_start_end_times_db(self, self.now, f"Start Time, PID: {getpid()}")

                if not check_connection(self, REMOTE_DIRECTORY):
                    self.write_start_end_times(
                        datetime.now(), self.run_log, start_time=self.start_time
                    )
                    return
                new_db = get_count_or_setup_db(self, LOCAL_DIRECTORY)
                self.mod_times = get_modified_files(self, cwd=Path(LOCAL_DIRECTORY))

                if new_db is True:
                    self.write_start_end_times(
                        datetime.now(), self.run_log, start_time=self.start_time
                    )
                    return  # Only sync if database existed to get around syncing thousands of files

                if len(self.mod_times) == 2:
                    dest = REMOTE_DIRECTORY + str(
                        Path.cwd().relative_to(LOCAL_DIRECTORY)
                    )
                    if check_log_n_db_eq(self, dest):
                        self.write_start_end_times(
                            datetime.now(), self.run_log, start_time=self.start_time
                        )
                        return  # Only sync files if they are different

                if len(self.mod_times) > 200:
                    # Only sync 200 files at a time
                    self.mod_times = self.mod_times[:200]

                write_db_mod_files(self)
                sync(self, LOCAL_DIRECTORY, REMOTE_DIRECTORY)

                self.write_start_end_times(
                    datetime.now(), self.run_log, start_time=self.start_time
                )
                self.db_conn.commit()

        except (Exception, IntegrityError, OperationalError) as exc:
            # Logging any unknown exceptions which might happen.
            # Because this program will be called automatically and without anyone watching stdout.
            with closing(connect(self.db_file)) as self.db_conn:
                with open(self.run_log, "a", encoding="utf-8") as run_log:
                    print(f"\n  {exc}\n", file=run_log)

                end_time = datetime.now()
                self.write_start_end_times(
                    end_time, self.run_log, start_time=self.start_time
                )

                err_log = Path(__file__).resolve().parent / "logs" / "error.log"
                self.write_start_end_times(self.start_time, err_log)
                basicConfig(
                    filename=err_log,
                    filemode="a",
                    format="\n%(asctime)s - %(levelname)s - %(message)s",
                    level=ERROR,
                )
                error(format_exc())
                self.write_start_end_times(
                    end_time, err_log, start_time=self.start_time
                )
                self.db_conn.commit()

    def __get_total_time(self, start_time, end_time):
        """
        Calculates the difference in hours, minutes, and seconds between start_time and end_time
        """
        timedelta_tt = end_time - start_time
        total_seconds = timedelta_tt.total_seconds()
        h, remainder = divmod(total_seconds, 3600)
        m, s = divmod(remainder, 60)

        return (int(h), int(m), int(s))

    def write_start_end_times(self, now, file, start_time=None):
        """
        Writes the start and end times to the run log
        """

        with open(file, "a", encoding="utf-8") as log_file:
            if not start_time:
                msg = f"# Start {now.strftime("%Y-%m-%d %H:%M")} #"
                print(f"\n{"#"*len(msg)}\n{msg}", file=log_file)
                return

            h, m, s = self.__get_total_time(start_time, now)
            msg = f"# End   {now.strftime("%Y-%m-%d %H:%M")} #"
            dur = f"# Time  {h} h. {m} m. {s} s."

            if file == self.run_log:
                log_start_end_times_db(
                    self,
                    now.strftime("%Y-%m-%d %H:%M"),
                    f"End Time, Duration {h} h. {m} m. {s} s.",
                )

            print(
                f"{msg}\n{dur}{" "*(len(msg)-len(dur)-1)}#\n{"#"*len(msg)}",
                file=log_file,
            )


if __name__ == "__main__":
    RCloneBackupScript()
