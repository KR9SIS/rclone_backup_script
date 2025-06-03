"""
Helper functions for the main function of the rclone backup script
"""

from datetime import datetime
from pathlib import Path
from sqlite3 import Connection


class VariableStorer:
    """
    Class to store the variables needed for the rclone backup script to run
    """

    def __init__(self, STDOUT: bool, CWD: Path) -> None:
        self.STDOUT: bool = STDOUT
        if self.STDOUT:
            print("Initializing VariableStorer")
        self.CWD = CWD
        self.LOCAL_DIR: str = "/home/kr9sis/PDrive"
        self.REMOTE_DIR: str = "PDrive:"
        self.mod_times: list[tuple[Path, str]] = []
        self.file_count: int = -99999
        self.cur_file: int = 0
        self.excluded_paths: set[str] = {
            "__pycache__",
            "node_modules",
            "firm_extract_NOBACKUP",
        }
        # Dotfiles and synlinks are also excluded in get_files_in_cwd()

        file_dir = Path(__file__).resolve().parent
        self.start_time: datetime = datetime.now()
        self.now: str = self.start_time.strftime("%Y-%m-%d %H:%M")

        self.run_log: Path = (
            file_dir
            / "logs"
            / f"{self.start_time.year % 100}_{self.start_time.month:02}_run.log"
        )
        self.err_log: Path = file_dir / "logs" / "error.log"
        self.db_file: Path = file_dir / "RCloneBackupScript.db"
        del file_dir

        self.db_conn: Connection


def write_start_end_times(
    var_storer: VariableStorer,
    now: datetime,
    start_time=None,
    error=False,
    RETRYING=False,
    COUNTING=False,
):
    from db_ops import log_start_end_times_db

    """
    Writes the start and end times to the run log
    """

    with open(
        var_storer.err_log if error else var_storer.run_log, "a", encoding="utf-8"
    ) as log_file:

        if not start_time:
            if RETRYING:
                msg = f"# Retry {now.strftime("%Y-%m-%d %H:%M")} #"
            elif COUNTING:
                 msg = f"# Count {now.strftime("%Y-%m-%d %H:%M")} #"
            else:
                msg = f"# Start {now.strftime("%Y-%m-%d %H:%M")} #"

            print(f"\n{"#"*len(msg)}\n{msg}", file=log_file)
            return
        
        # Get total time of script run
        timedelta_tt = now - start_time
        total_seconds = timedelta_tt.total_seconds()
        h, remainder = divmod(total_seconds, 3600)
        m, s = divmod(remainder, 60)

        msg = f"# End   {now.strftime("%Y-%m-%d %H:%M")} #"
        dur = f"# Time  {int(h)} h. {int(m)} m. {int(s)} s."

        if not error:
            log_start_end_times_db(
                var_storer,
                now.strftime("%Y-%m-%d %H:%M"),
                f"End Time, Duration {h} h. {m} m. {s} s.",
            )

        print(
            f"{msg}\n{dur}{" "*(len(msg)-len(dur)-1)}#\n{"#"*len(msg)}",
            file=log_file,
        )
