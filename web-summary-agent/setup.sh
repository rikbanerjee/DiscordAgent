#!/usr/bin/env bash
set -euo pipefail

echo "=== Discord Web Summary Agent — Setup ==="
echo ""

# 1. Check Node.js
if ! command -v node &>/dev/null; then
  echo "ERROR: Node.js is not installed. Install Node.js 18+ and try again."
  exit 1
fi

NODE_VERSION=$(node -v | sed 's/v//' | cut -d. -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
  echo "ERROR: Node.js 18+ is required (found v$(node -v))."
  exit 1
fi
echo "Node.js $(node -v) found."

# 2. Install npm dependencies
echo "Installing dependencies..."
npm install

# 3. Install Chromium via Puppeteer if Chrome is not found
CHROME_BIN=""
for candidate in \
  /usr/bin/google-chrome-stable \
  /usr/bin/google-chrome \
  /usr/bin/chromium-browser \
  /usr/bin/chromium \
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"; do
  if [ -x "$candidate" ]; then
    CHROME_BIN="$candidate"
    break
  fi
done

if [ -z "$CHROME_BIN" ]; then
  echo ""
  echo "No Chrome/Chromium found on the system."
  echo "Installing Chromium via @puppeteer/browsers..."
  npx @puppeteer/browsers install chrome@stable --path ./chrome
  # Find the installed binary
  CHROME_BIN=$(find ./chrome -name "chrome" -o -name "google-chrome" | head -1)
  echo "Installed Chromium at: $CHROME_BIN"
fi

# 4. Create .env if it doesn't exist
if [ ! -f .env ]; then
  cp .env.example .env
  echo ""
  echo "Created .env file from .env.example."
  echo "Please edit .env and add your DISCORD_TOKEN and GEMINI_API_KEY."
else
  echo ".env already exists, skipping."
fi

# 5. Set CHROME_PATH in .env if we found/installed one
if [ -n "$CHROME_BIN" ]; then
  if ! grep -q "^CHROME_PATH=" .env 2>/dev/null; then
    echo "CHROME_PATH=$CHROME_BIN" >> .env
    echo "Set CHROME_PATH=$CHROME_BIN in .env"
  fi
fi

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit .env and fill in DISCORD_TOKEN and GEMINI_API_KEY"
echo "  2. Run:  npm start"
echo ""
