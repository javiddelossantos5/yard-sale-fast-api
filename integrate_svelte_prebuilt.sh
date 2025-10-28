#!/bin/bash

# One-Command Svelte Integration (Pre-built approach)
# Run this from your local machine

echo "🎨 One-Command Svelte Integration (Pre-built)"
echo "============================================="

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
scp /Users/javiddelossantos/Documents/Github/Strata/fast-api-test/integrate_svelte_server_prebuilt.sh javiddelossantos@10.1.2.165:/home/javiddelossantos/fast-api-test/

# Run server integration
echo "🚀 Running server integration..."
ssh javiddelossantos@10.1.2.165 "cd /home/javiddelossantos/fast-api-test && chmod +x integrate_svelte_server_prebuilt.sh && ./integrate_svelte_server_prebuilt.sh"

echo ""
echo "🎉 Integration Complete!"
echo "========================"
echo "Your Svelte frontend should now be running at:"
echo "  🌐 https://garage.javidscript.com/"
echo ""
echo "If you see any issues, check the server logs:"
echo "  ssh javiddelossantos@10.1.2.165"
echo "  cd /home/javiddelossantos/fast-api-test"
echo "  docker-compose logs -f"
