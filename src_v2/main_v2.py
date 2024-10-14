"""
1. Check connection
2. Get or setup database
3. Get modified files
4. Filter out unneeded modified files
5. Sync modified files
    - If sync was successfull then update modification time in DB
"""

from contextlib import closing
from pathlib import Path
from sqlite3 import connect
from subprocess import CalledProcessError, TimeoutExpired, run

from db_ops import get_count_or_setup_db
from rclone_ops import rclone_check_connection


class RCloneBackupScript:
    """
    Script to check if files in a local directory have been modified and if so
    then send them and their modifications to a remote at PDrive:
    """

    def __init__(self) -> None:
        LOCAL_DIRECTORY = "/home/kr9sis/PDrive"
        REMOTE_DIRECTORY = "PDrive:"
        self.mod_times: dict[Path, str] = {}
        self.file_count = -99999
        self.cur_file = 0

        file_dir = Path(__file__).resolve().parent
        self.backup_log = file_dir / "backup.log"
        db_file = file_dir / "RCloneBackupScript.db"

        if rclone_check_connection(self, REMOTE_DIRECTORY):
            with closing(connect(db_file)) as self.db_conn:
                get_count_or_setup_db(self, LOCAL_DIRECTORY)
                self.get_modified_files(cwd=Path(LOCAL_DIRECTORY))

    def get_files_in_cwd(self, cwd: Path) -> list[str]:
        """
        Function to get all files within the current working directory
        and their modification time and return a str containing that
        information sorted with most recent modification first
        """
        # TODO: FINISH GOING OVER THIS FUNCTION BEFORE PORTING OVER OTHER FUNCTIONS
        # TODO: CHECK OUT dedent FROM Minni_Vinna

        with open(self.backup_log, "a", encoding="utf-8") as log_file:
            ret = []
            for file in cwd.iterdir():
                if file.name.startswith(".") or file.is_symlink():
                    continue  # Get rid of all dotfiles

                stat_cmd = ["stat", "-c", "%n %y", str(file)]
                try:
                    stat_out = run(
                        stat_cmd, check=True, timeout=10, capture_output=True
                    )
                    stat_out = stat_out.stdout.decode("utf-8")

                except CalledProcessError as e:
                    print(
                        f"CWD:\n{cwd}\nError occured with getting files command\nError:\n{e}",
                        file=log_file,
                    )
                    stat_out = ""

                except TimeoutExpired as e:
                    print(
                        f"CWD:\n{cwd}\nError occured with getting files command\nError:\n{e}",
                        file=log_file,
                    )
                    stat_out = ""

                mod_time = stat_out[-36:-7]
                filename = stat_out[:-37]
                ret.append((filename, mod_time))

        return ret

    def get_modified_files(self, cwd: Path):
        """
        Recursively checks the cwd and every subdirectory within it
        """
        if self.file_count != -99999:
            percent = round((self.cur_file / self.file_count) * 100)
            print(f"{percent}%", end=" ")
        print(f"In {cwd}")

        files = self.get_files_in_cwd(cwd)
        if not files:
            return

        files = {Path(file[0]): file[1] for file in files}
        db_files = self.create_db_files_dict(cwd)

        if len(files) != len(db_files) or files != db_files:
            self.add_or_del_from_db(files, db_files)

        self.check_if_modified(files, db_files)
