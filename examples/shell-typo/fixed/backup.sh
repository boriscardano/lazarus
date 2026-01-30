#!/bin/bash
set -e

# Daily Backup Script
# Backs up important directories to a backup location
# This is the FIXED version with typos corrected.

BACKUP_DIR="/tmp/backup-$(date +%Y%m%d)"
SOURCE_DIRS=("./data" "./config" "./logs")

echo "Starting backup process..."  # Fixed: 'echoo' -> 'echo'
echo "Backup directory: $BACKUP_DIR"  # Fixed: 'echoo' -> 'echo'

# Create backup directory
mkdir -p "$BACKUP_DIR"  # Fixed: 'mkdri' -> 'mkdir'

# Create sample directories if they don't exist (for demo)
for dir in "${SOURCE_DIRS[@]}"; do
    mkdir -p "$dir"
    echo "Sample data" > "$dir/sample.txt"
done

# Perform backup
for dir in "${SOURCE_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "Backing up $dir..."
        cp -r "$dir" "$BACKUP_DIR/"
    else
        echo "Warning: $dir does not exist, skipping..."
    fi
done

echo "Backup completed successfully!"
echo "Files backed up to: $BACKUP_DIR"

# List backup contents
ls -lh "$BACKUP_DIR"
