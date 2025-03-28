"""
Script for backing up the entire PDrive folder
"""

from pathlib import Path
from subprocess import CalledProcessError, run

SOURCE = "/home/kr9sis/PDrive"
DESTINATION = "PDrive:"
FILTER_FILE = (
    "/home/kr9sis/PDrive/Code/Py/rclone_backup_script/repo/rclone_sync_filter.txt"
)


def sync_subdir(path: Path):
    """
    If path is directory, sync each individual subdirectories
    """
    if path.is_dir():
        for sub_path in path.iterdir():
            sync_dir(sub_path)
    else:
        print(path)


def sync_dir(path: Path):
    """
    Sync given directory
    """
    rel_path = path.relative_to(SOURCE)
    command = [
        "rclone",
        "sync",
        SOURCE,
        DESTINATION,
        "--filter-from",
        FILTER_FILE,
        "--filter",
        f"+ {rel_path}",
    ]

    print(" ".join(command), "\n")

    try:
        run(command, capture_output=False, timeout=25200, check=True)

    except (TimeoutError, CalledProcessError) as e:
        print(e)
        sync_subdir(path)


def main():
    """
    Start syncing SOURCE to DESTINATION
    """
    sync_dir(Path("/home/kr9sis/PDrive"))


if __name__ == "__main__":
    main()
