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
        # "--log-file",
        # "/home/kr9sis/PDrive/Code/Py/rclone_backup_script/src/backup.log",
        "--protondrive-replace-existing-draft=true",
    ]
    file_num = 0
    for file_path in self.modified:
        file_path = file_path.relative_to("/home/kr9sis/PDrive")
        cmd_with_file = []
        cmd_with_file.extend(command)
        cmd_with_file.extend(["--include", str(file_path)])

        with open(self.backup_log, "a", encoding="utf-8") as log_file:
            print(
                f"Syncing file #{file_num}:\n{file_path}\n",
            )

        with open(self.backup_log, "a", encoding="utf-8") as log_file:
            try:
                run(cmd_with_file, check=True, timeout=600)
            except CalledProcessError as e:
                print(
                    f"""
                    Error occured with syncing file\n
                    {file_path}\nError:\n{e}\n
                    File will be added to FailedSyncs table
                    """,
                    file=log_file,
                )
                self.failed_syncs.add(str(file_path))
            except TimeoutExpired as e:
                print(
                    f"""
                    Error occured with syncing file\n
                    {file_path}\nError:\n{e}\n
                    File will be added to FailedSyncs table
                    """,
                    file=log_file,
                )
                self.failed_syncs.add(str(file_path))

            file_num += 1
            percent = round((file_num / len(self.modified)) * 100)
            print(f"Total synced: {percent}%\n")


# BUG: Unnecisary function
def update_failed_syncs_table(self):
    """
    Add all files which failed to sync to the DB
    for retrival and a retry next time the script is run
    """
    self.conn.executemany(
        """
        INSERT INTO FailedSyncs (file_path, modification_time, synced)
        VALUES (?, ?, 1)
        ON CONFLICT (file_path)
        DO
            UPDATE
            SET
                modification_time = excluded.modification_time,
                synced = excluded.synced,
                occurrence = occurrence + 1;
        """,
        self.failed_syncs,
    )

    failed_syncs = {item[0] for item in self.failed_syncs}
    compl_syncs = [
        (synced, 1) for synced in self.retried_syncs if synced not in failed_syncs
    ]

    self.conn.executemany(
        """
        UPDATE FailedSyncs
        SET synced = 1
        WHERE file_path = ?
        """,
        compl_syncs,
    )

    self.conn.commit()

    with open(self.backup_log, "a", encoding="utf-8") as log_file:
        print("Files which failed to sync", file=log_file)
        _ = [print(file, file=log_file) for file in self.failed_syncs]


def rclone_check_connection(self, destination_path) -> bool:
    """Function to query the rclone connection and check if it's active"""
    try:
        _ = run(
            ["rclone", "lsd", destination_path],
            check=True,
            timeout=60,
            capture_output=True,
        )
        return True
    except (CalledProcessError, TimeoutExpired):
        with open(self.backup_log, "a", encoding="utf-8") as log_file:
            print(
                "Connection could not be established to remote, exiting run\n",
                file=log_file,
            )
        return False
