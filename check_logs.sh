#!/bin/sh
echo "All logged files:"
echo "date|file_path|synced"
sqlite3 src/RCloneBackupScript.db <<EOF
SELECT * FROM Log;
EOF

echo "\nFiles which did not sync:"
echo "date|file_path|synced"
sqlite3 src/RCloneBackupScript.db <<EOF
SELECT *
FROM Log AS l1
WHERE l1.synced = 0
AND NOT EXISTS (
    SELECT 1
    FROM Log AS l2
    WHERE l2.file_path = l1.file_path
    AND l2.synced = 1
    AND l2.date > l1.date
);
EOF

echo "\nCount of files which did not sync:"
sqlite3 src/RCloneBackupScript.db <<EOF
SELECT COUNT(DISTINCT file_path)
FROM Log AS l1
WHERE l1.synced = 0
AND NOT EXISTS (
    SELECT 1
    FROM Log AS l2
    WHERE l2.file_path = l1.file_path
    AND l2.synced = 1
    AND l2.date > l1.date
);
EOF
