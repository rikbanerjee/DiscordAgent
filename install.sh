#!/bin/bash

# Installation script for Job Agent Bot on Linux
# Run this script on your Linux box to set up the bot

set -e  # Exit on error

echo "========================================"
echo "Job Agent Bot - Installation Script"
echo "========================================"
echo ""

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo "⚠️  Warning: This script is designed for Linux systems."
    echo "Current OS: $OSTYPE"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "📁 Working directory: $SCRIPT_DIR"
echo ""

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "✅ Found Python $PYTHON_VERSION"

# Create virtual environment
echo ""
echo "📦 Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo ""
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo "✅ Dependencies installed"

# Check .env file
echo ""
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found!"
    echo "Creating .env template..."
    cat > .env << 'EOF'
# Discord Bot Token
TOKEN=your_discord_bot_token_here

# Google Gemini API Key
GEMINI_API_KEY=your_gemini_api_key_here
EOF
    echo "✅ .env template created"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env file and add your API keys before running the bot!"
    echo "   - Get Discord token from: https://discord.com/developers/applications"
    echo "   - Get Gemini API key from: https://aistudio.google.com/app/apikey"
else
    echo "✅ .env file exists"
fi

# Create log directory
echo ""
echo "📝 Setting up logging..."
sudo mkdir -p /var/log/job-agent-bot
sudo chown $USER:$USER /var/log/job-agent-bot
echo "✅ Log directory created: /var/log/job-agent-bot"

# Setup systemd service
echo ""
read -p "📋 Do you want to set up systemd service (run bot on startup)? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Update service file with actual paths
    SERVICE_FILE="job-agent-bot.service"
    TEMP_SERVICE="/tmp/job-agent-bot.service"

    sed "s|YOUR_USERNAME|$USER|g" "$SERVICE_FILE" > "$TEMP_SERVICE"
    sed -i "s|/path/to/DiscordAgent|$SCRIPT_DIR|g" "$TEMP_SERVICE"
    sed -i "s|/path/to/venv|$SCRIPT_DIR/venv|g" "$TEMP_SERVICE"

    # Copy to systemd directory
    sudo cp "$TEMP_SERVICE" /etc/systemd/system/job-agent-bot.service
    sudo systemctl daemon-reload

    echo "✅ Systemd service installed"
    echo ""
    echo "To enable the service to start on boot:"
    echo "  sudo systemctl enable job-agent-bot"
    echo ""
    echo "To start the service now:"
    echo "  sudo systemctl start job-agent-bot"
    echo ""
    echo "To check service status:"
    echo "  sudo systemctl status job-agent-bot"
    echo ""
    echo "To view logs:"
    echo "  sudo journalctl -u job-agent-bot -f"
fi

echo ""
echo "========================================"
echo "✅ Installation Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your API keys"
echo "2. Test the bot: python job_agent_bot.py"
echo "3. (Optional) Enable systemd service for auto-start"
echo ""
echo "Commands:"
echo "  Start bot manually:  python job_agent_bot.py"
echo "  Start with systemd:  sudo systemctl start job-agent-bot"
echo "  View logs:           tail -f /var/log/job-agent-bot/output.log"
echo ""
echo "Discord commands (once bot is running):"
echo "  !help              - Show help"
echo "  !linkedin <url>    - Analyze job posting"
echo "  !job <company>     - Search company jobs"
echo ""
