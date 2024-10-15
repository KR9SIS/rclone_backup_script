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

from db_ops import get_count_or_setup_db
from dir_ops import get_modified_files
from rclone_ops import rclone_check_connection


class RCloneBackupScript:
    """
    Script to check if files in a local directory have been modified and if so
    then send them and their modifications to a remote at PDrive:
    """

    def __init__(self) -> None:
        self.stdout = False
        LOCAL_DIRECTORY = "/home/kr9sis/PDrive"
        REMOTE_DIRECTORY = "PDrive:"
        self.mod_times: dict[Path, str] = {}
        self.file_count = -99999
        self.cur_file = 0

        file_dir = Path(__file__).resolve().parent
        self.error_log = file_dir / "error.log"
        db_file = file_dir / "RCloneBackupScript.db"

        if rclone_check_connection(self, REMOTE_DIRECTORY):
            with closing(connect(db_file)) as self.db_conn:
                get_count_or_setup_db(self, LOCAL_DIRECTORY)
                get_modified_files(self, cwd=Path(LOCAL_DIRECTORY))
