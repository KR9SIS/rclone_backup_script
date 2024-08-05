"""
Module Docstring
"""

from subprocess import CalledProcessError, TimeoutExpired, run


def rclone_sync(self, source_path, destination_path):
    """
    Sync modified files to Proton Drive
    """
    command = [
        "rclone",
        "sync",
        source_path,
        destination_path,
        "-v",
        "--log-file",
        "/home/kr9sis/PDrive/Code/Py/rclone_backup_script/src/backup.log",
        "--protondrive-replace-existing-draft=true",
    ]

    for file, file_num in zip(self.modified, range(1, len(self.modified) + 1)):
        file = file.relative_to("/home/kr9sis/PDrive")
        cmd_with_file = []
        cmd_with_file.extend(command)
        cmd_with_file.extend(["--include", str(file)])

        with open(self.backup_log, "a", encoding="utf-8") as log_file:
            print(
                f"Syncing file #{file_num}:\n{file}\n",
                file=log_file,
            )

        with open(self.backup_log, "a", encoding="utf-8") as log_file:
            try:
                run(cmd_with_file, check=True, timeout=600)
            except CalledProcessError as e:
                print(
                    f"""
                    Error occured with syncing file\n
                    {file}\nError:\n{e}\n
                    File will be added to FailedSyncs table
                    """,
                    file=log_file,
                )
                self.failed_syncs.append((str(file),))
            except TimeoutExpired as e:
                print(
                    f"""
                    Error occured with syncing file\n
                    {file}\nError:\n{e}\n
                    File will be added to FailedSyncs table
                    """,
                    file=log_file,
                )
                self.failed_syncs.append((str(file),))

            percent = round((file_num / len(self.modified)) * 100)
            print(f"Total synced: {percent}%\n", file=log_file)


def update_failed_syncs_table(self):
    """
    Add all files which failed to sync to the DB
    for retrival and a retry next time the script is run
    """
    self.conn.executemany(
        """
        INSERT INTO FailedSyncs (file_path)
        VALUES (?);
        """,
        self.failed_syncs,
    )
    self.conn.commit()

    with open(self.backup_log, "a", encoding="utf-8") as log_file:
        print("Files which failed to sync", file=log_file)
        _ = [print(file, file=log_file) for file in self.failed_syncs]
