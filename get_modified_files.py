from subprocess import run, CalledProcessError, TimeoutExpired
from os.path import isfile, isdir
import psycopg


def check_if_modified(cwd: str, modified: list):
    try:
        files = run(
            ["ls", "-t", "-1", "-F", f"{cwd}"],
            check=True,
            timeout=10,
            capture_output=True,
        )
        files = files.stdout.decode("utf-8")

    except CalledProcessError as exc:
        print(
            f"Process returned unsuccessful return code.\nCode: {exc.returncode} \nException: {exc}"
        )

    except TimeoutExpired as exc:
        print(f"Process timed out\nException: {exc}")

    if not files:
        return
    else:
        files = files.strip().split("\n")

        for file in files:
            # TODO check if file was modified
            # if file in mod_files # make mod_files a set

            if isdir(file):
                check_if_modified(cwd + file, modified)
            elif isfile(file):
                modified.append(cwd + file)

    return


cwd = "/home/kr9sis/PDrive/Code/Py/rclone_backup_script/"
modified = []
check_if_modified(cwd, modified)
print(modified)
