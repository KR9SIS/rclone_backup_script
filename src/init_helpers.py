"""Module housing the init helpers class"""

from datetime import datetime


class InitHelpers:
    """
    Class designed to implement helper funcitons for RCloneBackupScript class __init__ method
    """

    def get_total_time(self, start_time, end_time):
        """
        Calculates the difference in hours, minutes, and seconds between start_time and end_time
        """
        timedelta_tt = end_time - start_time
        total_seconds = timedelta_tt.total_seconds()
        h, remainder = divmod(total_seconds, 3600)
        m, s = divmod(remainder, 60)

        return (int(h), int(m), int(s))

    def write_start_end_times(self, backup_log, start_time=None):
        """
        Writes the start and end times to the backup_log
        """
        now = datetime.now()
        with open(backup_log, "a", encoding="utf-8") as log_file:
            if not start_time:
                msg = f"# Program started at {now.strftime("%Y-%m-%d %H:%M")} #"
                print(f"\n\n{"#"*len(msg)}\n{msg}", file=log_file)
                return now

            h, m, s = self.get_total_time(start_time, now)
            msg = f"# Program ended at {now.strftime("%Y-%m-%d %H:%M")}. Total time {h}:{m}:{s} #"

            print(f"\n{msg}\n{"#"*len(msg)}\n", file=log_file)

            return None

    def write_mod_files(self, backup_log, modified):
        """
        If there's less than 100 modified files, then it writes each to the file
        otherwise it writes an error message
        """
        with open(backup_log, "a", encoding="utf-8") as log_file:
            print("Files to be modified are:", file=log_file)
            if len(modified) < 100:
                _ = [print(file, file=log_file) for file in modified]
                print(file=log_file)
            else:
                print("Too many to list, maximum 100 files\n", file=log_file)

    def write_rclone_cmd(self, backup_log, local_directory, remote_directory, modified):
        """
        Creates the complete rclone command for the current run and prints it out
        for the user to sync files which couldn't be synced
        """
        with open(backup_log, "a", encoding="utf-8") as log_file:
            if len(modified) > 10000:
                print(
                    """
                    Sync was cancelled. Too many files, maximum 50 at a time.
                    Command creation was also cancelled, maximum 10000 files.
                    It is reccomended to sync entire local folder manually to reset.
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
                    [item for file in modified for item in ["--include", str(file)]]
                )
                cmd = ", ".join(cmd_list)

                print(
                    f"""Sync was cancelled. Too many files, maximum 50 at a time. \n
                    It is reccomended that you sync them manually yourself with the command
                    \n\n
                    {cmd}
                    \n
                    """,  # Create a list where you add "--include" and then the file from modified
                    file=log_file,
                )
