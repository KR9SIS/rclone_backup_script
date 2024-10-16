"""
rclone backup script for backing up local directory files
"""

from contextlib import closing
from pathlib import Path
from sqlite3 import connect

from db_ops import get_count_or_setup_db, write_db_mod_files
from dir_ops import get_modified_files
from rclone_ops import rclone_check_connection, rclone_sync


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
        self.stdout = True
        LOCAL_DIRECTORY = "/home/kr9sis/PDrive"
        REMOTE_DIRECTORY = "PDrive:"
        self.mod_times: dict[Path, str] = {}
        self.file_count = -99999
        self.cur_file = 0
        self.excluded_paths: list[str] = ["__pycache__"]
        # Dotfiles and synlinks are also excluded in get_files_in_cwd()

        file_dir = Path(__file__).resolve().parent
        self.error_log = file_dir / "error.log"
        self.db_file = file_dir / "RCloneBackupScript.db"

        if not rclone_check_connection(self, REMOTE_DIRECTORY):
            return

        with closing(connect(self.db_file)) as self.db_conn:
            setup = get_count_or_setup_db(self, LOCAL_DIRECTORY)
            self.mod_times = get_modified_files(self, cwd=Path(LOCAL_DIRECTORY))
            if setup is True:
                return  # Only sync if database existed

            write_db_mod_files(self)
            rclone_sync(self, LOCAL_DIRECTORY, REMOTE_DIRECTORY)


if __name__ == "__main__":
    try:
        RCloneBackupScript()
    except Exception as e:
        # Logging any unknown exceptions which might happen.
        # Because this program will be called automatically and without anyone watching stdout.
        with open("error.log", "a", encoding="utf-8") as err_file:
            print(e, file=err_file)
