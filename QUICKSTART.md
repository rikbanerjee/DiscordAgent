# Quick Start Guide - Job Agent Bot

Get your Discord Job Agent Bot running in 5 minutes!

## Step 1: Get API Keys (5 minutes)

### Discord Bot Token

1. Go to https://discord.com/developers/applications
2. Click "New Application" → Name it (e.g., "Job Agent")
3. Go to "Bot" tab → Click "Add Bot"
4. **IMPORTANT**: Scroll down to "Privileged Gateway Intents"
   - ✅ Enable "MESSAGE CONTENT INTENT"
5. Click "Reset Token" → Copy the token
6. Save it somewhere safe!

### Invite Bot to Your Server

1. Go to "OAuth2" → "URL Generator"
2. Select scopes:
   - ✅ `bot`
3. Select bot permissions:
   - ✅ Send Messages
   - ✅ Embed Links
   - ✅ Read Message History
   - ✅ Use Slash Commands
4. Copy the generated URL
5. Open in browser → Select your server → Authorize

### Google Gemini API Key

1. Go to https://aistudio.google.com/app/apikey
2. Click "Create API Key"
3. Copy the key
4. Save it!

## Step 2: Setup on Linux Box (2 minutes)

### Transfer Files

```bash
# Option 1: Git clone (if using git)
git clone <your-repo-url>
cd DiscordAgent

# Option 2: SCP from your Mac
scp -r /path/to/DiscordAgent your-user@linux-box:/home/your-user/
```

### Run Installation

```bash
cd DiscordAgent
./install.sh
```

Follow the prompts! The script will:
- Create virtual environment
- Install dependencies
- Create .env template
- Set up logging
- (Optional) Configure systemd

## Step 3: Configure Environment (1 minute)

Edit the `.env` file:

```bash
nano .env
```

Replace with your actual keys:

```env
TOKEN=YOUR_ACTUAL_DISCORD_TOKEN_HERE
GEMINI_API_KEY=YOUR_ACTUAL_GEMINI_KEY_HERE
```

Save and exit (Ctrl+X, Y, Enter)

## Step 4: Start the Bot (30 seconds)

### Option A: Manual Start (for testing)

```bash
source venv/bin/activate
python job_agent_bot.py
```

You should see:
```
✅ Logged in as YourBotName
✅ Job Agent Bot is ready!
```

### Option B: systemd Service (for production)

```bash
sudo systemctl start job-agent-bot
sudo systemctl status job-agent-bot  # Check it's running
```

## Step 5: Test in Discord (1 minute)

Go to your Discord server and try:

```
!help
```

You should see the help embed!

Try analyzing a job:
```
!linkedin https://www.linkedin.com/jobs/view/3823456789
```

## Common Issues

### Bot doesn't respond

**Check MESSAGE CONTENT INTENT:**
- Go to Discord Developer Portal
- Your App → Bot → Privileged Gateway Intents
- Enable "MESSAGE CONTENT INTENT"
- Restart the bot

### "Invalid Token" error

**Double-check your .env file:**
```bash
cat .env
```
Make sure there are no extra spaces or quotes around the token.

### Scraping fails

**Try different LinkedIn URLs:**
- Make sure the URL is public (not behind login)
- Try a different job posting
- Wait a few minutes (rate limiting)

## Quick Commands Reference

| Command | What it does |
|---------|--------------|
| `!help` | Show help |
| `!linkedin <url>` | Analyze job posting |
| `!job <company>` | Find jobs at company |
| `!ping` | Check if bot is alive |

## Useful Management Commands

```bash
# Start bot
sudo systemctl start job-agent-bot

# Stop bot
sudo systemctl stop job-agent-bot

# Restart bot
sudo systemctl restart job-agent-bot

# Check status
sudo systemctl status job-agent-bot

# View logs (live)
sudo journalctl -u job-agent-bot -f

# View recent logs
sudo journalctl -u job-agent-bot -n 50

# Enable auto-start on boot
sudo systemctl enable job-agent-bot

# Disable auto-start
sudo systemctl disable job-agent-bot
```

## Next Steps

- ✅ Bot is running!
- 📖 Read full documentation: `README_JOB_AGENT.md`
- 🎨 Customize bot status/presence in `job_agent_bot.py`
- 📊 Monitor logs for issues
- 🚀 Share with friends!

## Getting Help

If something isn't working:

1. **Check logs first:**
   ```bash
   sudo journalctl -u job-agent-bot -n 50
   ```

2. **Test manually:**
   ```bash
   source venv/bin/activate
   python job_agent_bot.py
   ```
   This shows errors directly!

3. **Verify API keys:**
   - Discord: Test bot token is valid
   - Gemini: Check quota at https://aistudio.google.com

4. **Check permissions:**
   - Bot has "Send Messages" permission in Discord
   - Bot can read messages in the channel

---

**You're all set! Happy job hunting! 🎉**
