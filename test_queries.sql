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


SELECT '/home/kr9sis/PDrive/Code/Py/' FROM Times
LIMIT 30;

SELECT T.*
FROM Times T
RIGHT JOIN Folders F ON F.folder_path = T.folder_path;

WHERE F.folder_path = '/home/kr9sis/PDrive/Barnabókinn mín';


SELECT * FROM Times
WHERE folder_path LIKE '/home/kr9sis/PDrive/Code/Py/%'
AND folder_path NOT LIKE '/home/kr9sis/PDrive/Code/Py/%/%';

SELECT * FROM Times
WHERE folder_path = '/home/kr9sis/PDrive/Barnabókinn mín/'

SELECT * FROM Folders;
SELECT * FROM Times;