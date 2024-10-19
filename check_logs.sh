#!/bin/sh
sqlite3 RCloneBackupScript.db <<EOF
SELECT * FROM Log;
EOF

