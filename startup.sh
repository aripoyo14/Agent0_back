#!/bin/bash
echo "Starting startup.sh script"
echo "Current directory: $(pwd)"
echo "Listing files in current directory:"
ls -la

cd /home/site/wwwroot
echo "Changed to /home/site/wwwroot"
echo "Current directory: $(pwd)"
echo "Listing files in /home/site/wwwroot:"
ls -la

echo "Running python startup.py"
python startup.py 