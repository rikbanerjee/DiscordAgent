# Discord Job Agent Bot - MVP

AI-powered Discord bot that analyzes job postings from LinkedIn and provides detailed insights using Google Gemini AI.

## Features

- 🔍 **LinkedIn Job Scraping** - Extract job details from LinkedIn URLs
- 🤖 **AI-Powered Analysis** - Detailed insights using Gemini AI
- 📊 **Structured Information** - Salary estimates, required skills, career insights
- 🏢 **Company Job Search** - Find jobs at specific companies
- 💬 **Discord Integration** - Beautiful embeds and interactive commands
- 🚀 **Auto-deployment** - systemd service for 24/7 operation

## Architecture

```
DiscordAgent/
├── job_agent_bot.py          # Main bot application
├── scrapers/
│   ├── linkedin_scraper.py   # LinkedIn job scraping
│   └── company_scraper.py    # Company info scraping
├── utils/
│   ├── ai_analyzer.py        # Gemini AI analysis
│   └── formatters.py         # Discord message formatting
├── requirements.txt          # Python dependencies
├── .env                      # API keys (not in git)
├── install.sh               # Linux installation script
└── job-agent-bot.service    # systemd service file
```

## Prerequisites

### Required
- **Python 3.8+** - Programming language
- **Discord Bot Token** - Get from [Discord Developer Portal](https://discord.com/developers/applications)
- **Google Gemini API Key** - Get from [Google AI Studio](https://aistudio.google.com/app/apikey)

### For Linux Deployment
- **Linux system** (Ubuntu, Debian, CentOS, etc.)
- **systemd** (usually pre-installed)
- **sudo access** (for systemd service setup)

## Quick Start

### 1. Get Your API Keys

#### Discord Bot Token
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Go to "Bot" section
4. Click "Add Bot"
5. Under "TOKEN", click "Copy"
6. **Important**: Enable "MESSAGE CONTENT INTENT" under Privileged Gateway Intents

#### Google Gemini API Key
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Click "Create API Key"
3. Copy the generated key

### 2. Installation on Linux

```bash
# Clone or transfer the files to your Linux box
cd /path/to/DiscordAgent

# Run the installation script
./install.sh

# Edit .env file with your API keys
nano .env
```

Add your keys to `.env`:
```env
TOKEN=your_discord_bot_token_here
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Test the Bot

```bash
# Activate virtual environment
source venv/bin/activate

# Run the bot
python job_agent_bot.py
```

You should see:
```
✅ Logged in as YourBotName (ID: 123456789)
✅ Connected to 1 server(s)
✅ Job Agent Bot is ready!
```

### 4. Set Up Auto-Start (Optional)

```bash
# Enable service to start on boot
sudo systemctl enable job-agent-bot

# Start the service now
sudo systemctl start job-agent-bot

# Check status
sudo systemctl status job-agent-bot

# View live logs
sudo journalctl -u job-agent-bot -f
```

## Discord Commands

### Core Commands

| Command | Description | Example |
|---------|-------------|---------|
| `!help` | Show help message | `!help` |
| `!linkedin <url>` | Analyze a LinkedIn job posting | `!linkedin https://linkedin.com/jobs/view/1234567` |
| `!job <company>` | Search for jobs at a company | `!job Google` |
| `!ping` | Check if bot is online | `!ping` |
| `!about` | Show bot information | `!about` |

### Command Aliases

- `!li` or `!link` - Alias for `!linkedin`
- `!jobs` or `!company` - Alias for `!job`

### Auto-Detection

The bot automatically detects LinkedIn job URLs in messages and offers to analyze them!

Just paste a LinkedIn job URL in the chat:
```
https://www.linkedin.com/jobs/view/1234567890
```

## Usage Examples

### Example 1: Analyze a LinkedIn Job

**Discord:**
```
!linkedin https://www.linkedin.com/jobs/view/3823456789
```

**Bot Response:**
```
🔍 Scraping LinkedIn job posting...
🤖 Analyzing job with AI...

[Embed 1: Job Overview]
- Title, Company, Location
- Employment Type, Seniority Level
- Quick AI Summary

[Embed 2: Detailed Analysis]
- Role Summary
- Required Skills
- Salary Estimate
- Career Insights
- Red/Green Flags
- Application Tips
```

### Example 2: Search Company Jobs

**Discord:**
```
!job Amazon
```

**Bot Response:**
```
[Embed: Jobs at Amazon]
1. Software Development Engineer
   Amazon • Seattle, WA
   [View Job](url)

2. Senior Product Manager
   Amazon • San Francisco, CA
   [View Job](url)

💡 Tip: Use !linkedin <url> with a specific job link for detailed AI analysis!
```

### Example 3: Get Help

**Discord:**
```
!help
```

**Bot Response:**
```
[Embed: Job Agent Commands]
- Command list
- Usage examples
- Tips
```

## AI Analysis Features

The bot provides comprehensive analysis including:

### 1. **Role Summary**
- What the job actually entails
- Key responsibilities

### 2. **Required Skills**
- Top 5-8 most important technical skills
- Context for each skill

### 3. **Preferred Qualifications**
- Years of experience needed
- Education requirements
- Certifications

### 4. **Key Technologies & Tools**
- Programming languages
- Frameworks and libraries
- Tools and platforms

### 5. **Salary Estimate**
- Estimated salary range (based on AI analysis)
- Considers: title, seniority, location, company

### 6. **Career Insights**
- Growth potential
- Industry trends
- What makes this role attractive/challenging

### 7. **Red Flags / Green Flags**
- Positive aspects to consider
- Potential concerns to watch for

### 8. **Application Tips**
- What to emphasize in your application
- Skills to highlight
- Interview questions to prepare

## Technical Details

### Dependencies

- **discord.py** - Discord bot framework
- **google-generativeai** - Gemini AI SDK
- **requests** - HTTP library for web scraping
- **beautifulsoup4** - HTML parsing
- **python-dotenv** - Environment variable management

### Rate Limiting

The bot implements respectful scraping practices:
- 2-second delay between requests
- Proper User-Agent headers
- Fallback mechanisms when scraping fails

### LinkedIn Scraping

**Important Notes:**
- The MVP uses public LinkedIn pages (no authentication)
- LinkedIn may block aggressive scraping
- For production use, consider:
  - LinkedIn API (requires partnership)
  - Proxies/VPNs
  - More sophisticated scraping (Selenium, undetected-chromedriver)

### Error Handling

The bot handles:
- Invalid URLs
- Failed scraping attempts
- AI analysis errors
- Network timeouts
- Rate limiting

## Troubleshooting

### Bot doesn't respond to commands

1. Check bot is online: `!ping`
2. Verify MESSAGE CONTENT INTENT is enabled in Discord Developer Portal
3. Check bot has permissions in the channel

### Scraping fails

1. Verify the LinkedIn URL is public
2. Check your internet connection
3. LinkedIn may be rate-limiting - wait a few minutes
4. Try a different job URL

### AI analysis errors

1. Verify GEMINI_API_KEY in `.env` is correct
2. Check Gemini API quota at [Google AI Studio](https://aistudio.google.com)
3. Review logs: `tail -f /var/log/job-agent-bot/error.log`

### Service won't start

```bash
# Check service status
sudo systemctl status job-agent-bot

# View full logs
sudo journalctl -u job-agent-bot -n 50

# Check if .env file exists
ls -la .env

# Verify virtual environment
source venv/bin/activate
python job_agent_bot.py  # Test manually
```

## Logs

### View Logs

```bash
# Service logs (systemd)
sudo journalctl -u job-agent-bot -f

# Output log
tail -f /var/log/job-agent-bot/output.log

# Error log
tail -f /var/log/job-agent-bot/error.log
```

### Log Rotation

For production, set up logrotate:

```bash
sudo nano /etc/logrotate.d/job-agent-bot
```

```
/var/log/job-agent-bot/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    missingok
}
```

## Deployment Checklist

- [ ] Python 3.8+ installed
- [ ] Discord bot created and token copied
- [ ] Gemini API key obtained
- [ ] `.env` file configured with both tokens
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Bot tested manually (`python job_agent_bot.py`)
- [ ] Log directory created (`/var/log/job-agent-bot/`)
- [ ] systemd service installed (optional)
- [ ] Service enabled for auto-start (optional)
- [ ] Bot invited to Discord server with proper permissions

## Security Best Practices

1. **Never commit .env file** - Already in `.gitignore`
2. **Restrict log file permissions** - `chmod 750 /var/log/job-agent-bot/`
3. **Use systemd security features** - Already configured in service file
4. **Regenerate tokens** if accidentally exposed
5. **Monitor API usage** - Check Gemini API quotas regularly

## Limitations (MVP)

1. **LinkedIn Scraping**
   - Public pages only
   - No authentication
   - Subject to rate limiting
   - May break if LinkedIn changes HTML structure

2. **Company Search**
   - Limited to LinkedIn search results
   - No direct company API integration

3. **AI Analysis**
   - Depends on Gemini API availability
   - Subject to API quotas
   - Estimates (salary, etc.) are AI-generated, not guaranteed

## Future Enhancements

- [ ] Selenium-based scraping for better reliability
- [ ] LinkedIn API integration (requires partnership)
- [ ] Database to cache job postings
- [ ] User profiles and job preferences
- [ ] Job alerts and notifications
- [ ] Resume matching and scoring
- [ ] Multi-company comparison
- [ ] Glassdoor integration for salary data
- [ ] Company culture insights

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review logs for error messages
3. Verify all API keys are correct
4. Test with known-working LinkedIn URLs

## License

This is an MVP/educational project. Use responsibly and respect LinkedIn's Terms of Service.

---

**Built with ❤️ using Python, Discord.py, and Google Gemini AI**
