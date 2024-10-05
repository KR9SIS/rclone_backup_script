# RClone Backup Script

### Overview
This is a script used to sync the local changes I make to my files to the cloud using rclone.
Rclone normally syncs everything and not just the files that have been modified since last sync, which is where this program comes in.
In it I am using Python and SQLite. Python for the logic and SQLite to keep a database with information about when files were last modified.
All of the program code is confined within the src folder.

### Breaking down the program in steps:
1. It starts in main.py setting up the variables
2. Starts by logging at what time program excution started.
3. Calls rclone_check_connection() to make sure that the computer is online and can sync files before going through local storage and attempting sync. If the connection fails, then the program jumps to step 9.
4. Uses with closing from contextlib to create the database connection, ensuring it will be closed after use.
5. Calls check_or_setup_database() to try and QUERY the database by getting failed syncs from previous runs and if that's not possible set up the database.
6. Calls get_modified_files() to recursively iterate through the local directory and its subirectories.
	Within get_modified_files() I start by calling get_files_in_cwd() to iterate through files within the cwd, excluding dot files and using the linux _stat_ command get the file path and last modification date for each file before returning them as a dictionary.
	Then I call create_db_files_dict to query the database for all database files within the cwd and return a file path, modification time dictionary of them.
	If the dictionary created within the local directory and from the database aren't equal then I call add_or_del_from_db() which goes through the two dictionaries and adds any file found in the local directory to the database and removes any item not in the local directory from the database.
	It then calls check_if_modified() with the two dictionaries and iterates over the dictionary created from the local folder and checks if the modification times within the database match. If they don't then that file is added to self.modified. If the file path is a directory, then it calls get_modified_files() on that directory.
6. If there are any files to be synced then it calls rclone_sync()
	In rclone_sync() it first creates the base rclone command and then it iterates over every modified file and uses subprocess run to call rclone sync, to sync each file seperately. If a file fails to sync, then the program logs an error message and adds the file to the failed_syncs list.
7. Calls filter_mod_files() to remove the database file and backup log files since they might be modified during the run of the program. Along with \_\_pycharm\_\_ folders.
8. If there are any files wiithin the failed_syncs list after syncing or files within retried_syncs list from previous runs then update_failed_syncs_table() is called
	In update_failed_syncs_table() it starts by adding all files which failed to sync to the database, whereafter it checks if a file which previously failed, failed again or succeeded, and if it suceeded, then it modifies the database to reflect that. It then writes to the log file a list of files which failed to sync.
9. Finishes by logging at what time the program is finished and how long it took to run.

### Possible future implementations:
- SQLite Create, Read, Update, Delete class to replace multiline string SQL calls within the program.


