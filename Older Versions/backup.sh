#!/bin/bash

log_with_timestamp(){
echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> /home/kr9sis/backup.log
}

log_with_timestamp "Running rclone copy"

#/usr/bin/rclone copy /home/kr9sis/PDrive KHS-PD: --exclude /home/kr9sis/PDrive/backup.sh --exclude /home/kr9sis/PDrive/backup.log --protondrive-2fa=000000 --dry-run --no-console >> /home/kr9sis/script.log 2>&1

log_with_timestamp "Completed rclone copy"
