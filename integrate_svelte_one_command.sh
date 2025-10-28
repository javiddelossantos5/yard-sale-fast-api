#!/bin/bash

# One-Command Svelte Integration
# Run this from your local machine

echo "🎨 One-Command Svelte Integration"
echo "================================="

# Build Svelte app locally first
echo "🔨 Building Svelte app locally..."
cd /Users/javiddelossantos/Documents/Github/Strata/svelte-yard-sale
npm run build

if [ ! -d "build" ]; then
    echo "❌ Build failed - no build directory created"
    exit 1
fi

echo "✅ Svelte app built successfully!"

# Copy Svelte frontend to server
echo "📤 Copying Svelte frontend to server..."
scp -r /Users/javiddelossantos/Documents/Github/Strata/svelte-yard-sale/* javiddelossantos@10.1.2.165:/home/javiddelossantos/yard-sale-svelte/

# Copy server integration script
echo "📤 Copying server integration script..."
scp integrate_svelte_server.sh javiddelossantos@10.1.2.165:/home/javiddelossantos/fast-api-test/

# Run integration on server
echo "🚀 Running integration on server..."
ssh javiddelossantos@10.1.2.165 "cd /home/javiddelossantos/fast-api-test && chmod +x integrate_svelte_server.sh && ./integrate_svelte_server.sh"

echo ""
echo "🎉 Svelte Frontend Integration Complete!"
echo "=========================================="
echo "Your Svelte frontend is now integrated with Docker!"
echo "Visit: https://garage.javidscript.com/"
