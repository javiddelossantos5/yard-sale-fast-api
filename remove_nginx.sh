#!/bin/bash

# Complete Nginx Removal Script
# Run this on your server (10.1.2.165) to completely remove Nginx

set -e

echo "🚫 Complete Nginx Removal Script"
echo "================================"
echo ""

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    echo "❌ This script needs to be run as root or with sudo"
    echo "Please run: sudo ./remove_nginx.sh"
    exit 1
fi

echo "🔍 Step 1: Stopping Nginx service..."
systemctl stop nginx 2>/dev/null || echo "Nginx service not running"
systemctl disable nginx 2>/dev/null || echo "Nginx service not enabled"

echo "✅ Nginx service stopped and disabled"

echo ""
echo "🔍 Step 2: Removing Nginx packages..."
apt-get remove --purge nginx nginx-common nginx-core nginx-full nginx-light nginx-extras -y 2>/dev/null || echo "Nginx packages not found"

echo "✅ Nginx packages removed"

echo ""
echo "🔍 Step 3: Cleaning up configuration files..."
rm -rf /etc/nginx 2>/dev/null || echo "No /etc/nginx directory"
rm -rf /var/log/nginx 2>/dev/null || echo "No /var/log/nginx directory"
rm -rf /var/www/html 2>/dev/null || echo "No /var/www/html directory"
rm -rf /usr/share/nginx 2>/dev/null || echo "No /usr/share/nginx directory"

echo "✅ Configuration files cleaned up"

echo ""
echo "🔍 Step 4: Killing any remaining Nginx processes..."
pkill -f nginx 2>/dev/null || echo "No Nginx processes found"

echo "✅ Nginx processes killed"

echo ""
echo "🔍 Step 5: Removing Nginx from autostart..."
update-rc.d nginx remove 2>/dev/null || echo "Nginx not in autostart"

echo "✅ Nginx removed from autostart"

echo ""
echo "🔍 Step 6: Cleaning package cache..."
apt-get autoremove -y
apt-get autoclean

echo "✅ Package cache cleaned"

echo ""
echo "🎉 Nginx completely removed!"
echo "=========================="
echo ""
echo "✅ What's been removed:"
echo "  🚫 Nginx service (stopped & disabled)"
echo "  🚫 Nginx packages (purged)"
echo "  🚫 Configuration files (/etc/nginx)"
echo "  🚫 Log files (/var/log/nginx)"
echo "  🚫 Web root (/var/www/html)"
echo "  🚫 Nginx processes (killed)"
echo "  🚫 Autostart entries (removed)"
echo ""
echo "🔍 Verify removal:"
echo "  systemctl status nginx    # Should show 'not found'"
echo "  ps aux | grep nginx       # Should show no processes"
echo "  which nginx               # Should show 'not found'"
echo ""
echo "🚀 Now you can run your Docker setup without conflicts!"
echo "   Your services will be available at:"
echo "   🎨 Frontend: http://10.1.2.165:3000/"
echo "   🔧 Backend: http://10.1.2.165:8000/"
