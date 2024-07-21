This is a script used to sync the local changes I make to my files to the cloud using rclone.
Rclone normally syncs everything and not just the files that have been modified since last sync, which is where this program comes in.

In it I am using Python and PostgreSQL. Python for the logic and PSQL to keep a database with information about when files were last modified.
