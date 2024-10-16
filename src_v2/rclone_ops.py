"""
Functions which interact with rclone
"""

from datetime import datetime
from pathlib import Path
from subprocess import CalledProcessError, TimeoutExpired, run

from db_ops import update_db_mod_file


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
        with open(self.error_log, "a", encoding="utf-8") as log_file:
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            print(
                f"\n{now}\nConnection could not be established to remote, exiting run\n",
                file=log_file,
            )
        return False


def rclone_sync(self, SOURCE_PATH: str, DESTINATION_PATH: str):
    """
    Sync modified files to Proton Drive
    """

    def sync_func(self, file_num: int, file_path: Path) -> int:
        rel_file_path = file_path.relative_to(SOURCE_PATH)
        cmd_with_file = []
        cmd_with_file.extend(command)
        cmd_with_file.extend(["--include", str(rel_file_path)])
        _ = (
            print(f"Syncing file #{file_num}:\n{rel_file_path}\n")
            if self.stdout is True
            else None
        )
        try:
            run(cmd_with_file, check=True, timeout=600)
            update_db_mod_file(self, str(file_path), self.mod_times[file_path])

        except CalledProcessError as e:
            with open(self.error_log, "a", encoding="utf-8") as log_file:
                print(
                    f"""
                    Error occured with syncing file\n
                    {rel_file_path}\nError:\n{e}\n
                    File mod time will not be updated this run
                    """,
                    file=log_file,
                )
        except TimeoutExpired as e:
            with open(self.error_log, "a", encoding="utf-8") as log_file:
                print(
                    f"""
                    Error occured with syncing file\n
                    {rel_file_path}\nError:\n{e}\n
                    File mod time will not be updated this run
                    """,
                    file=log_file,
                )
        if self.stdout:
            file_num += 1
            percent = round((file_num / len(self.mod_times)) * 100)
            print(f"Total synced: {percent}%\n")

        return file_num

    command = [
        "rclone",
        "sync",
        SOURCE_PATH,
        DESTINATION_PATH,
        "-v",
        "--protondrive-replace-existing-draft=true",
    ]

    self.excluded_paths.extend(["RCloneBackupScript.db"])
    # Make sure the database file is the last to go to minimize dataloss, since it is edited at runtime

    file_num = 0
    for file_path in self.mod_times:
        if any(excluded in str(file_path) for excluded in self.excluded_paths):
            continue
        file_num = sync_func(self, file_num, file_path)

    file_num = sync_func(self, file_num, self.db_file)
