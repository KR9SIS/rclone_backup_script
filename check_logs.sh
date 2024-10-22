#!/bin/sh
sqlite3 src/RCloneBackupScript.db <<EOF
SELECT * FROM Log;
EOF

