"""
Script to rerun failed documents
"""

from contextlib import closing
from datetime import datetime
from os import getpid
from pathlib import Path
from sqlite3 import connect

from db_ops import get_fails, log_start_end_times_db, write_db_mod_files
from rclone_ops import check_connection, sync


class RetrySyncs:
    """
    1. write start time to log file
    2. Check rclone connection
    3. grab the filenames that didn't sync
    4. write file count to log file
    5. try syncing them
    6. write synced count or fail count to log file
    7. write end time to log file
    """

    def __init__(self) -> None:
        self.stdout = True
        self.mod_times: list[tuple[Path, str]] = []
        self.file_count = -99999
        self.cur_file = 0

        file_dir = Path(__file__).resolve().parent
        self.start_time = datetime.now()
        self.run_log = (
            file_dir
            / "logs"
            / f"{self.start_time.year % 100}_{self.start_time.month:02}_run.log"
        )
        self.err_log = file_dir / "logs" / "error.log"
        self.db_file = file_dir / "RCloneBackupScript.db"

        self.write_start_end_times(self.start_time, self.run_log)
        self.now: str = self.start_time.strftime("%Y-%m-%d %H:%M")

        LOCAL_DIRECTORY = "/home/kr9sis/PDrive"
        REMOTE_DIRECTORY = "PDrive:"

        with closing(connect(self.db_file)) as self.db_conn:
            log_start_end_times_db(self, self.now, f"Start Time, PID: {getpid()}")

            if not check_connection(self, REMOTE_DIRECTORY):
                self.write_start_end_times(
                    datetime.now(), self.run_log, start_time=self.start_time
                )
                return

            self.mod_times = get_fails(self)

            write_db_mod_files(self)
            sync(self, LOCAL_DIRECTORY, REMOTE_DIRECTORY)
            self.write_start_end_times(
                datetime.now(), self.run_log, start_time=self.start_time
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
                msg = f"# Retry {now.strftime("%Y-%m-%d %H:%M")} #"
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
    RetrySyncs()
