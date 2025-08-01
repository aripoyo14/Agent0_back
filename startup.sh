#!/bin/bash
echo "Starting startup.sh script"
echo "Current directory: $(pwd)"
echo "Listing files in current directory:"
ls -la

# 複数の可能な場所をチェック
echo "Checking possible paths:"
for path in "/home/site/wwwroot" "/tmp/8ddd10a63c8f7a1" "."; do
    echo "Checking path: $path"
    if [ -d "$path" ]; then
        echo "Path exists: $path"
        echo "Files in $path:"
        ls -la "$path" || echo "Error listing files in $path"
    else
        echo "Path does not exist: $path"
    fi
done

cd /home/site/wwwroot
echo "Changed to /home/site/wwwroot"
echo "Current directory: $(pwd)"
echo "Listing files in /home/site/wwwroot:"
ls -la

echo "Running python startup.py"
python startup.py 