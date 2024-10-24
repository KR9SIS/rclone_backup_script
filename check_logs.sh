#!/bin/sh
echo "All logged files:"
echo "date|file_path|synced"
sqlite3 src/RCloneBackupScript.db <<EOF
SELECT * FROM Log;
EOF
echo "\nFiles which did not sync:"
echo "date|file_path|synced"
sqlite3 src/RCloneBackupScript.db <<EOF
SELECT * FROM Log WHERE synced = 0;
EOF
