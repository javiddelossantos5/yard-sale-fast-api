#!/bin/bash

# Copy all necessary files to server
# Run this from your local machine

echo "📤 Copying Docker files to server..."

# Copy all files
scp -r /Users/javiddelossantos/Documents/Github/Strata/fast-api-test/* javiddelossantos@10.1.2.165:/home/javiddelossantos/fast-api-test/

echo "✅ Files copied successfully!"
echo ""
echo "Now SSH to your server and run:"
echo "ssh javiddelossantos@10.1.2.165"
echo "cd /home/javiddelossantos/fast-api-test"
echo "chmod +x quick_deploy.sh"
echo "./quick_deploy.sh"
