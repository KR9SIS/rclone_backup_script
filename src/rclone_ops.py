"""
Functions which interact with rclone
"""

from pathlib import Path
from subprocess import CalledProcessError, TimeoutExpired, run
from textwrap import dedent

from db_ops import get_num_synced_files, update_db_mod_file
from helpers import VariableStorer


def check_connection(var_storer: VariableStorer) -> bool:
    """
    Function to query the rclone connection and check if it's active
    If this function fails multiple times, then try running the command
    manually and if that fails, reset the authentication of 'rclone config'
    """
    try:
        if var_storer.STDOUT:
            print("Checking connection")
        _ = run(
            ["rclone", "lsd", var_storer.REMOTE_DIR],
            check=True,
            timeout=60,
            capture_output=True,
        )
        return True

    except (CalledProcessError, TimeoutExpired):
        with open(var_storer.run_log, "a", encoding="utf-8") as log_file:
            print(
                dedent("# Remote Connect Failed  #\n# Exiting Run            #"),
                file=log_file,
            )
        return False


def sync(var_storer: VariableStorer):
    """
    Sync modified files to Proton Drive
    """

    command = [
        "rclone",
        "sync",
        var_storer.LOCAL_DIR,
        var_storer.REMOTE_DIR,
        "-v",
        "--protondrive-replace-existing-draft=true",
    ]

    sync_fails: int = 0
    file_num = 0
    for file_path, mod_time in var_storer.mod_times:
        rel_file_path: Path = file_path.relative_to(var_storer.LOCAL_DIR)
        cmd_with_file = []
        cmd_with_file.extend(command)
        cmd_with_file.extend(["--include", str(rel_file_path)])

        try:
            run(cmd_with_file, check=True, timeout=36000)
            update_db_mod_file(var_storer, str(file_path), mod_time)

        except (CalledProcessError, TimeoutExpired) as e:
            sync_fails += 1
            print("\nFAILED ", end="")
            with open(var_storer.err_log, "a", encoding="utf-8") as err_file:
                print(f"\n{'*'*30}\n", file=err_file)
                print(e, file=err_file)

        if var_storer.STDOUT:
            file_num += 1
            percent = round((file_num / len(var_storer.mod_times)) * 100)
            print(f"Syncing file #{file_num}:\n{rel_file_path}\n")
            print(f"Total synced: {percent}%\n")

    if sync_fails:
        fails = f"Fails {sync_fails}"
        if len(fails) < 12:
            str_diff = 12 - len(fails)
            fails += " " * str_diff
        fails += "#"
        with open(var_storer.run_log, "a", encoding="utf-8") as log_file:
            print(dedent(fails), file=log_file)

    else:
        with open(var_storer.run_log, "a", encoding="utf-8") as log_file:
            synced = f"Synced {get_num_synced_files(var_storer)} "
            if len(synced) < 12:
                str_diff = 12 - len(synced)
                synced += " " * str_diff
            synced += "#"
            print(dedent(synced), file=log_file)
