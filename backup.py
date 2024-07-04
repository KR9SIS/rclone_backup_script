from subprocess import run, CalledProcessError
from datetime import datetime


def log_backup(status):
    with open("backup.log", "a") as log_file:
        log_file.write(f"{status} backup at {datetime.now()}\n")
        if status == "End":
            log_file.write("\n\n")


def get_all_files_except_backup_script() -> set[str]:
    result = run(["ls"], capture_output=True, cwd="/home/kr9sis/PDrive")
    stdout_as_str = result.stdout.decode("utf-8")
    necessary_files = set(stdout_as_str.split("\n")[:-1])
    necessary_files.remove("backup_script")

    return necessary_files


def get_previous_statuses() -> dict[str, list[str]]:
    output = {}
    with open("last_modified.txt", "r") as mod_file:
        for line in mod_file:
            line = line.strip().split(", ")
            output[line[2]] = line
    return output


def call_and_parse_du(filename: str):
    result = run(
        ["du", "-s", "--time", filename], capture_output=True, cwd="/home/kr9sis/PDrive"
    )
    result = result.stdout.decode("utf-8")
    return result.strip().split("\t")


def call_rclone_sync(file):
    source_path = f"/home/kr9sis/PDrive/{file}"
    destination_path = f"KHS-PD:{file}"

    with open("backup.log", "a") as log_file:
        log_file.write("\n")
    try:
        run(
            [
                "/usr/bin/rclone",
                "sync",
                source_path,
                destination_path,
                "-v",
                "--log-file",
                "/home/kr9sis/PDrive/backup_script/backup.log",
            ],
            check=True,
            capture_output=True,
        )

    except CalledProcessError as e:
        with open("backup.log", "a") as log_file:
            log_file.write(f"Error while syncing {file} to cloud.\nError Message:\n{e}")


def delete_extras(prev_statuses: dict[str, list[str]], current_folders: set[str]):
    del_filenames = []
    for filename in prev_statuses:
        if filename not in current_folders:
            call_rclone_sync(filename)
            del_filenames.append(filename)

    for filename in del_filenames:
        prev_statuses.pop(filename)


def check_files(prev_statuses: dict[str, list[str]], current_folders: set[str]):
    update = False
    for file in current_folders:
        file_info = call_and_parse_du(file)
        filename = file_info[2]
        try:
            file_prev_status = prev_statuses[filename]
            if not file_prev_status[1] == file_info[1]:
                raise NotImplementedError

        except KeyError or NotImplementedError:
            call_rclone_sync(filename)
            prev_statuses[filename] = file_info
            update = True

    return update


def update_prev_statuses(prev_statuses: dict[str, list[str]]):
    with open("last_modified.txt", "w") as mod_file:
        for _, file_info in prev_statuses.items():
            file_info = ", ".join(file_info) + "\n"
            mod_file.write(file_info)


def main():
    log_backup("Start")
    prev_statuses = get_previous_statuses()
    current_folders = get_all_files_except_backup_script()
    add_update = del_update = False
    """
    if len(prev_statuses) > len(current_folders):
        delete_extras(prev_statuses, current_folders)
        del_update = True
    """
    add_update = check_files(prev_statuses, current_folders)
    if add_update or del_update:
        update_prev_statuses(prev_statuses)
    else:
        with open("backup.log", "a") as log_file:
            log_file.write("No sync needed\n")

    log_backup("End")


main()
