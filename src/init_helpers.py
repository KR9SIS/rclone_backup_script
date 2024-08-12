"""Module housing the init helpers class"""

from datetime import datetime


class InitHelpers:
    """
    Class designed to implement helper funcitons for RCloneBackupScript class __init__ method
    """

    def __init__(self, main_self):
        self.main = main_self

    def get_total_time(self, start_time, end_time):
        """
        Calculates the difference in hours, minutes, and seconds between start_time and end_time
        """
        timedelta_tt = end_time - start_time
        total_seconds = timedelta_tt.total_seconds()
        h, remainder = divmod(total_seconds, 3600)
        m, s = divmod(remainder, 60)

        return (int(h), int(m), int(s))

    def write_start_end_times(self, start_time=None):
        """
        Writes the start and end times to the backup_log
        """
        now = datetime.now()
        with open(self.main.backup_log, "a", encoding="utf-8") as log_file:
            if not start_time:
                msg = f"# Program started at {now.strftime("%Y-%m-%d %H:%M")} #"
                print(f"{"#"*len(msg)}\n{msg}", file=log_file)
                return now

            h, m, s = self.get_total_time(start_time, now)
            msg = f"# Program ended at {now.strftime("%Y-%m-%d %H:%M")} #"
            dur = f"# Total time {h} h. {m} m. {s} s."

            print(
                f"{msg}\n{dur}{" "*(len(msg)-len(dur)-1)}#\n{"#"*len(msg)}\n\n",
                file=log_file,
            )

            return None

    def filter_mod_files(self, db_file):
        """
        Filters out items in dirs_to_exclude and files_to_exclude
        """
        dirs_to_exclude = "__pycache__"
        files_to_exclude = (self.main.backup_log, db_file)
        # backup_log and DB file are being changed as the program runs
        # so they will never sync correctly
        return {
            filename: mod_time
            for filename, mod_time in self.main.modified.items()
            if not any(part in dirs_to_exclude for part in filename.parts)
            and filename not in files_to_exclude
        }

    def write_mod_files(self):
        """
        If there's less than 100 modified files, then it writes each to the file
        otherwise it writes an error message
        """
        with open(self.main.backup_log, "a", encoding="utf-8") as log_file:
            print("Files to be modified are:", file=log_file)
            if len(self.main.modified) < 100:
                _ = [print(file, file=log_file) for file in self.main.modified]
                print(file=log_file)
            else:
                print("Too many to list, maximum 100 files\n", file=log_file)

    def write_rclone_cmd(self, local_directory, remote_directory):
        """
        Creates the complete rclone command for the current run and prints it out
        for the user to sync files which couldn't be synced
        """
        with open(self.main.backup_log, "a", encoding="utf-8") as log_file:
            if len(self.main.modified) > 10000:
                print(
                    """
                    Sync was cancelled. Too many files, maximum 50 at a time.\n
                    Command creation was also cancelled, maximum 10000 files.\n
                    It is reccomended to sync entire local folder manually to reset.\n
                    """,
                    file=log_file,
                )
            else:
                cmd_list = [
                    "rclone",
                    "sync",
                    local_directory,
                    remote_directory,
                    "-v",
                    "--log-file",
                    "/home/kr9sis/PDrive/Code/Py/rclone_backup_script/src/backup.log",
                    "--protondrive-replace-existing-draft=true",
                ]
                cmd_list.extend(
                    [
                        item
                        for file in self.main.modified
                        for item in ["--include", str(file)]
                    ]
                )
                cmd = ", ".join(cmd_list)

                print(
                    f"""Sync was cancelled. Too many files, maximum 50 at a time. \n
                    It is reccomended that you sync them manually yourself with the command
                    \n\n
                    {cmd}
                    \n
                    """,
                    file=log_file,
                )
