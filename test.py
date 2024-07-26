"""Docstring"""

from sqlite3 import OperationalError, connect


def check_or_setup_database():
    """
    Function to set up SQLite database if it doesn't exist
    """
    try:
        conn = connect("file:test_db.db?mode=rw", uri=True)
        conn.close()
    except OperationalError:
        conn_new = connect("test_db", autocommit=False)
        with conn_new:
            conn_new.execute("PRAGMA foreign_keys = ON;")
            conn_new.execute("DROP TABLE IF EXISTS BACKUPNUM;")
            conn_new.execute("DROP TABLE IF EXISTS TIMES;")
            conn_new.execute("DROP TABLE IF EXISTS FOLDERS;")

            conn_new.execute(
                """
                CREATE TABLE FOLDERS (
                    FOLDER_PATH TEXT PRIMARY KEY
                );
                """
            )

            conn_new.execute(
                """
                CREATE TABLE TIMES (
                    PARENT_PATH TEXT,
                    FILE_PATH TEXT PRIMARY KEY,
                    MODIFICATION_TIME TEXT NOT NULL,
                    FOREIGN KEY (PARENT_PATH) REFERENCES FOLDERS (FOLDER_PATH)
                );
                """
            )

            conn_new.execute(
                """
                CREATE TABLE BACKUPNUM (
                    NUMKEY TEXT PRIMARY KEY,
                    BACKUPNUM INTEGER
                );
                """
            )

            conn_new.execute(
                """
                INSERT INTO BACKUPNUM (NUMKEY, BACKUPNUM)
                VALUES (?, ?)
                """,
                ("numkey", 0),
            )
        conn_new.close()


conn = connect("test_db", autocommit=False)
with conn:
    cur = conn.execute("SELECT name FROM sqlite_master")
    print(cur.fetchall())
    cur = conn.execute("SELECT BACKUPNUM FROM BACKUPNUM WHERE NUMKEY = ?", ("numkey",))
    print(cur.fetchall())
