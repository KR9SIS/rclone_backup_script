from subprocess import run, CalledProcessError
from datetime import datetime


class BackupPDriveWithRclone:
    def __init__(self) -> None:
        self.prev_statuses: dict[str, list[str]] = {}
        self.current_folders: set[str] = set()
        self.included_files: list[str] = []
        self.log_backup("Start")

        self.get_previous_statuses()
        self.get_current_folders()
        self.check_files()
        if self.included_files:
            self.call_rclone_sync()

        self.log_backup("End")

    def log_backup(self, status):
        with open("backup.log", "a") as log_file:
            log_file.write(f"{status} backup at {datetime.now()}\n")
            if status == "End":
                log_file.write("\n\n")

    def get_previous_statuses(self) -> dict[str, list[str]]:
        output = {}
        with open("last_modified.txt", "r") as mod_file:
            for line in mod_file:
                line = line.strip().split(", ")
                output[line[2]] = line
        self.prev_statuses = output

    def get_current_folders(self) -> set[str]:
        result = run(["ls"], capture_output=True, cwd="/home/kr9sis/PDrive", text=True)
        self.current_folders = set(result.stdout.split("\n")[:-1])

    def call_and_parse_du(self, filename: str):
        result = run(
            ["du", "-s", "--time", filename],
            capture_output=True,
            cwd="/home/kr9sis/PDrive",
            text=True,
        )
        return result.stdout.strip().split("\t")

    def check_files(self):
        update = False
        # Checking for modified or created files
        for file in self.current_folders:
            file_info = self.call_and_parse_du(file)
            filename = file_info[2]
            try:
                file_prev_status = self.prev_statuses[filename]
                if not file_prev_status[1] == file_info[1]:
                    raise NotImplementedError

            except KeyError or NotImplementedError:
                self.included_files.append(file)
                self.prev_statuses[filename] = file_info
                update = True

        # Checking for deleted files
        if len(self.current_folders) < len(self.prev_statuses):
            for file in self.prev_statuses:
                if file not in self.current_folders:
                    self.included_files.append(file)
                    self.prev_statuses[filename] = file_info
                    update = True

        return update

    def call_rclone_sync(self):
        source_path = "/home/kr9sis/PDrive/"
        destination_path = "KHS-PD:"

        with open("backup.log", "a") as log_file:
            log_file.write("\n")

        command = [
            "/usr/bin/rclone",
            "sync",
            source_path,
            destination_path,
            "-v",
            "--log-file",
            "/home/kr9sis/PDrive/backup_script/backup.log",
            "--dry-run",
            "--filter",
            "- **/.**",  # TODO Fix this filter
        ]
        for file in self.included_files:
            command.append("--filter")
            command.append(f"+ {file}")
            command.append("--filter")
            command.append(f"+ /{file}/**")

        try:
            run(
                command,
                check=True,
            )

        except CalledProcessError as e:
            with open("backup.log", "a") as log_file:
                log_file.write(
                    f"Error while syncing {file} to cloud.\nError Message:\n{e}"
                )

    def update_prev_statuses(prev_statuses: dict[str, list[str]]):
        with open("last_modified.txt", "w") as mod_file:
            for file_info in prev_statuses.values:
                file_info = ", ".join(file_info) + "\n"
                mod_file.write(file_info)


BackupPDriveWithRclone()
