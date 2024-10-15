"""
Functions which interact with rclone
"""

from datetime import datetime
from subprocess import CalledProcessError, TimeoutExpired, run


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

    file_num = 0
    for file_path in self.mod_times:
        rel_file_path = file_path.relative_to(SOURCE_PATH)
        cmd_with_file = []
        cmd_with_file.extend(command)
        cmd_with_file.extend(["--include", str(rel_file_path)])

        _ = (
            print(f"Syncing file #{file_num}:\n{rel_file_path}\n")
            if self.stdout is True
            else None
        )

        with open(self.error_log, "a", encoding="utf-8") as log_file:
            try:
                run(cmd_with_file, check=True, timeout=600)
                self.update_db_mod_time(file_path, self.mod_times[file_path])

            except CalledProcessError as e:
                print(
                    f"""
                    Error occured with syncing file\n
                    {rel_file_path}\nError:\n{e}\n
                    File mod time will not be updated this run
                    """,
                    file=log_file,
                )
            except TimeoutExpired as e:
                print(
                    f"""
                    Error occured with syncing file\n
                    {rel_file_path}\nError:\n{e}\n
                    File mod time will not be updated this run
                    """,
                    file=log_file,
                )

            file_num += 1
            percent = round((file_num / len(self.mod_times)) * 100)
            _ = print(f"Total synced: {percent}%\n") if self.stdout is True else None


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
