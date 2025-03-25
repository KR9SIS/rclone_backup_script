"""
Script for backing up the entire PDrive folder
"""

from io import TextIOWrapper
from pathlib import Path
from subprocess import CalledProcessError, run


def sync_dir(path: str, filter_file: str, out_file: TextIOWrapper, indent: int = 0):
    """
    Calls rclone with the PDrive + the given path
    """
    print("#", " " * indent, f"{path}:")
    try:
        ret = run(
            [
                "rclone",
                "sync",
                f"~/PDrive{path}",
                f"PDrive:{path}",
                f"--filter-from {filter_file}",
            ],
            check=True,
            timeout=10800,  # 3 hours
            capture_output=True,
        )

        if ret.stderr:
            print(" " * indent, ret.stderr, file=out_file)
            cwd = Path(path)
            if cwd.is_dir():
                for sub_path in cwd.iterdir():
                    sync_dir(str(sub_path), filter_file, out_file, indent + 1)

        if ret.stdout:
            print(" " * indent, ret.stdout, file=out_file)

    except (TimeoutError, CalledProcessError) as e:
        print(" " * indent, e, file=out_file)
        cwd = Path(path)
        if cwd.is_dir():
            for sub_path in cwd.iterdir():
                sync_dir(str(sub_path), filter_file, out_file, indent + 1)


def main():
    """
    Calls sync_dir
    """
    with open("full_backup_out.md", "w", encoding="utf-8") as out_file:
        sync_dir(
            "/", str(Path(__file__).parent.joinpath("rclone_sync_filter")), out_file
        )


if __name__ == "__main__":
    main()
