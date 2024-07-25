-- ALTER SEQUENCE times_id_seq RESTART WITH 1;
DROP SEQUENCE BACKUPNUM;
DROP TABLE IF EXISTS TIMES;
DROP TABLE IF EXISTS FOLDERS;

CREATE TABLE FOLDERS (
    FOLDER_PATH VARCHAR(255) PRIMARY KEY
);

CREATE TABLE TIMES (
    PARENT_PATH VARCHAR(255),
    FILE_PATH VARCHAR(255) PRIMARY KEY,
    MODIFICATION_TIME CHAR(16) NOT NULL,
    FOREIGN KEY (PARENT_PATH) REFERENCES FOLDERS (FOLDER_PATH)

);

CREATE SEQUENCE BACKUPNUM START 1;

select *
from times
where modification_time = '0000-00-00 00:00'
;

select *
from times
where folder_path = '/home/kr9sis/PDrive/Barnabókinn mín/'

select *
from times
where
    parent_path
    = '/home/kr9sis/PDrive/School/MK/2019/Haust 2019/ALÞV2BA05/Viðfangsefni 8/'

select *
from folders
;
select *
from times
limit 30
;

select *
from times
where parent_path = '/home/kr9sis/PDrive/Code/Py/rclone_backup_script/Older Versions/'
;

select distinct parent_path
from times
;


