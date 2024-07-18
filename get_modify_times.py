from subprocess import run, CalledProcessError, TimeoutExpired
from os.path import isfile, isdir
import psycopg


def get_modified_times(CWD: str):
    try:
        process_output = run(
            ["du", "--time", "--all"],
            check=True,
            timeout=10,
            capture_output=True,
            cwd=CWD,
        )
        files_mod_times = process_output.stdout.decode("utf-8")

    except CalledProcessError as exc:
        print(
            f"du process returned unsuccessful return code.\nCode: {exc.returncode} \nException: {exc}"
        )

    except TimeoutExpired as exc:
        print(f"du process timed out\nException: {exc}")

    del process_output

    tmp: list[str] = files_mod_times.strip().split("\n")

    files_mod_times: list[str] = []
    dirs_mod_times: list[str] = []
    for file in tmp:
        file = file.split("\t")[1:]
        if file[1].find("/.") > 0:  # Check if file is dotfile
            file = "DELETED"
        else:
            file[1] = file[1].replace("./", CWD, 1)
            if isfile(file[1]):
                files_mod_times.append(file)
            elif isdir(file[1]):
                file[1] = file[1] + "/"
                file[1] = file[1].replace("./", CWD, 1)
                dirs_mod_times.append(file)

    del tmp

    with psycopg.connect("dbname=FileModifyTimes user=postgres") as conn:
        with conn.cursor() as cur:
            # Reset DB
            try:
                cur.execute(
                    """
                     DROP TABLE IF EXISTS Times;
                     DROP TABLE IF EXISTS Folders;

                     CREATE TABLE Folders(
                         folder_path VARCHAR(255) PRIMARY KEY
                     );

                     CREATE TABLE Times(
                         folder_path VARCHAR(255),
                         file_path VARCHAR(255) NOT NULL,
                         modification_time CHAR(16) NOT NULL,
                         FOREIGN KEY (folder_path) REFERENCES Folders(folder_path)

                     );
                     """
                )
            except Exception as e:
                print(f"Exception \n{e} \noccured in Drop Tables")
                conn.rollback()

            for file in dirs_mod_times:
                try:
                    # index = file[1].rfind("/", 0, -1)
                    # parent_dir = file[1][0 : index + 1]

                    # cur.execute(
                    #    "SELECT 1 FROM Folders WHERE folder_path = %s", (parent_dir,)
                    # )
                    # if cur.fetchone() is None:
                    cur.execute(
                        "INSERT INTO Folders (folder_path) VALUES (%s)",
                        (file[1],),
                    )

                except Exception as e:
                    print(
                        f"Exception \n{e}\noccured in Insert Into Folders when trying to insert\n{file[1]}"
                    )
                """
                try:
                    index = file[1].rfind("/", 0, -1)
                    parent_dir = file[1][0 : index + 1]
                    # if file[1] != CWD:
                    cur.execute(
                        "INSERT INTO Times (folder_path, file_path, modification_time) VALUES (%s, %s, %s)",
                        (parent_dir, file[1], file[0]),
                    )
                except Exception as e:
                    print(
                        f"Exception \n{e} \noccured in Insert Into Folders when trying to insert \nfolder_path: {parent_dir}, \nfile_path: {file[1]} \nand modification time: {file[0]}"
                    )
                    conn.rollback()
                """
            for file in files_mod_times:
                try:
                    index = file[1].rfind("/")
                    parent_dir = file[1][0 : index + 1]

                    cur.execute(
                        "INSERT INTO Times (folder_path, file_path, modification_time) VALUES (%s, %s, %s)",
                        (parent_dir, file[1], file[0]),
                    )
                except Exception as e:
                    print(
                        f"Exception:\n{e}\noccured in Insert Into Folders when trying to insert  \nfolder_path: {parent_dir}, \nfile_path: {file[1]} \nand modification time: {file[0]}"
                    )
                    conn.rollback()

            conn.commit()


cwd = "/home/kr9sis/PDrive/"
get_modified_times(cwd)
