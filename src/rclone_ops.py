"""
Functions which interact with rclone
"""

from datetime import datetime
from pathlib import Path
from subprocess import CalledProcessError, TimeoutExpired, run
from textwrap import dedent

from db_ops import get_num_synced_files, update_db_mod_file


def rclone_check_connection(self, DESTINATION_PATH) -> bool:
    """Function to query the rclone connection and check if it's active"""
    try:
        _ = run(
            ["rclone", "lsd", DESTINATION_PATH],
            check=True,
            timeout=60,
            capture_output=True,
        )
        return True

    except (CalledProcessError, TimeoutExpired):
        with open(self.run_log, "a", encoding="utf-8") as log_file:
            print(
                dedent("# Remote Connect Failed  #\n# Exiting Run            #"),
                file=log_file,
            )
        return False


def rclone_sync(self, SOURCE_PATH: str, DESTINATION_PATH: str):
    """
    Sync modified files to Proton Drive
    """

    command = [
        "rclone",
        "sync",
        SOURCE_PATH,
        DESTINATION_PATH,
        "-v",
        "--protondrive-replace-existing-draft=true",
    ]

    sync_fails: int = 0
    file_num = 0
    for file_path in self.mod_times:
        rel_file_path = file_path.relative_to(SOURCE_PATH)
        cmd_with_file = []
        cmd_with_file.extend(command)
        cmd_with_file.extend(["--include", str(rel_file_path)])
        if self.stdout:
            file_num += 1
            percent = round((file_num / len(self.mod_times)) * 100)
            print(f"Total synced: {percent}%\n")
            print(f"Syncing file #{file_num}:\n{rel_file_path}\n")

        try:
            run(cmd_with_file, check=True, timeout=600)
            update_db_mod_file(self, str(file_path), self.mod_times[file_path])

        except (CalledProcessError, TimeoutExpired):
            sync_fails += 1

    if sync_fails:
        fails = f"Fails {sync_fails}"
        if len(fails) < 12:
            str_diff = 12 - len(fails)
            fails += " " * str_diff
        fails += "#"
        with open(self.run_log, "a", encoding="utf-8") as log_file:
            print(dedent(fails), file=log_file)

    else:
        with open(self.run_log, "a", encoding="utf-8") as log_file:
            synced = f"Synced {get_num_synced_files(self)} "
            if len(synced) < 12:
                str_diff = 12 - len(synced)
                synced += " " * str_diff
            synced += "#"
            print(dedent(synced), file=log_file)
