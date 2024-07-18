-- ALTER SEQUENCE times_id_seq RESTART WITH 1;
DROP TABLE IF EXISTS Times;
DROP TABLE IF EXISTS Folders;

CREATE TABLE Folders(
    folder_path VARCHAR(255) PRIMARY KEY
);

CREATE TABLE Times(
    --ID SERIAL PRIMARY KEY,
    folder_path VARCHAR(255),
    file_path VARCHAR(255) NOT NULL,
    modification_time CHAR(16) NOT NULL,
    FOREIGN KEY (folder_path) REFERENCES Folders(folder_path)

);

INSERT INTO Folders(folder_path) VALUES('/parent/');
INSERT INTO Folders(folder_path) VALUES('/parent/child/');

INSERT INTO Times(folder_path, file_path, modification_time) VALUES('/parent/', 'parent/child/', '2024-06-17 13:32');
INSERT INTO Times(folder_path, file_path, modification_time) VALUES('/parent/child/', '/parent/child/1', '2024-06-17 13:32');
INSERT INTO Times(folder_path, file_path, modification_time) VALUES('/parent/child/', '/parent/child/2', '2024-06-17 13:32');
INSERT INTO Times(folder_path, file_path, modification_time) VALUES('/parent/child/', '/parent/child/3', '2024-06-17 13:32');

SELECT * FROM Folders
SELECT * FROM Times WHERE Times.folder_path = '/parent/child/'


SELECT * FROM Times
WHERE folder_path = '/home/kr9sis/PDrive/Code/Py/';

SELECT * FROM Times
WHERE folder_path = '/home/kr9sis/PDrive/Barnabókinn mín/'

SELECT * FROM Folders;
SELECT * FROM Times;