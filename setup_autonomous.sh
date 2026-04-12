#!/bin/bash
# Sentinel-Scanner Autonomous Setup Script
# This script helps set up the cron job for autonomous regulatory monitoring

echo "🛡️ Sentinel-Scanner Autonomous Setup"
echo "===================================="

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: Please run this script from the Sentinel-Scanner directory"
    exit 1
fi

# Get the absolute path
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAIN_SCRIPT="$SCRIPT_DIR/main.py"

echo "📍 Script location: $MAIN_SCRIPT"

# Check if cron is available
if ! command -v crontab &> /dev/null; then
    echo "❌ Error: crontab is not available on this system"
    exit 1
fi

echo ""
echo "⏰ Setting up daily cron job at 9:00 AM..."
echo "   This will run: $MAIN_SCRIPT"

# Add to crontab (create if doesn't exist)
(crontab -l 2>/dev/null; echo "0 9 * * * /usr/bin/python3 $MAIN_SCRIPT") | crontab -

if [ $? -eq 0 ]; then
    echo "✅ Cron job added successfully!"
    echo ""
    echo "📋 Current cron jobs:"
    crontab -l
    echo ""
    echo "🎯 Sentinel will now run autonomously every morning at 9:00 AM"
    echo "📱 Don't forget to set up Telegram notifications in .env for alerts!"
else
    echo "❌ Failed to add cron job. You may need to run 'crontab -e' manually:"
    echo "   Add this line: 0 9 * * * /usr/bin/python3 $MAIN_SCRIPT"
fi

echo ""
echo "🔧 Next steps:"
echo "1. Configure your API keys in .env"
echo "2. Set up Telegram notifications (optional)"
echo "3. Test manually: python3 main.py"
echo "4. Check logs tomorrow morning!"