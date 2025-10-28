#!/bin/bash

# Simple Copy Script for Svelte Integration
# Run this manually to copy files to server

echo "📤 Copying Svelte files to server..."

# Copy the built Svelte app
echo "📁 Copying Svelte frontend..."
scp -r /Users/javiddelossantos/Documents/Github/Strata/svelte-yard-sale/* javiddelossantos@10.1.2.165:/home/javiddelossantos/yard-sale-svelte/

# Copy the server integration script
echo "📄 Copying server integration script..."
scp /Users/javiddelossantos/Documents/Github/Strata/fast-api-test/integrate_svelte_server_prebuilt.sh javiddelossantos@10.1.2.165:/home/javiddelossantos/fast-api-test/

echo "✅ Files copied successfully!"
echo ""
echo "🚀 Next steps:"
echo "1. SSH to server: ssh javiddelossantos@10.1.2.165"
echo "2. Run: cd /home/javiddelossantos/fast-api-test"
echo "3. Run: chmod +x integrate_svelte_server_prebuilt.sh"
echo "4. Run: ./integrate_svelte_server_prebuilt.sh"
