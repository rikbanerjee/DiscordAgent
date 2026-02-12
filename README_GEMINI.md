# Discord Link Sharing Agent

A Discord bot that extracts content from shared URLs (LinkedIn, Substack, any website) and uses Google's Gemini API to summarize, research, draft articles, or extract code insights. Think of it as your personal, self-hosted research assistant controlled entirely through Discord.

## Features

- **Auto URL Detection** — Paste a link and get an instant summary
- **Multiple Processing Modes** — Summarize, deep research, article drafting, code insights
- **Site-Aware Extraction** — Tuned for LinkedIn, Substack, and general websites
- **Follow-Up Questions** — Ask questions about the last shared link in any channel
- **General Chat** — Falls back to Gemini chat when no URL is involved
- **Message Splitting** — Handles Discord's 2000-character limit automatically

## Setup

### 1. Get Your API Keys

**Discord Bot Token:**
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application or select existing
3. Go to "Bot" section and get your token
4. Enable "Message Content Intent" under Privileged Gateway Intents

**Gemini API Key:**
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Click "Get API Key" or "Create API Key"
3. Copy your API key

### 2. Configure Environment Variables

Add to your `.env` file:

```
TOKEN=your_discord_bot_token_here
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Bot

```bash
# Link sharing agent (recommended)
python discord_link_agent.py

# Original simple Gemini chat bot
python discord_only_gemini.py
```

## Commands

| Command | Description |
|---|---|
| Just paste a URL | Auto-summarize the page |
| `!summarize <url>` | Quick summary with key points |
| `!research <url>` | Deep analysis — thesis, evidence, takeaways |
| `!article <url>` | Draft an original article from the content |
| `!code <url>` | Extract technical/code insights |
| `!extract <url>` | Show raw extracted text (no AI processing) |
| `!help` | Show all commands |
| `!status` | Show cached content for the current channel |

### Follow-Up Questions

After sharing a URL, just type a regular message (no URL) and the bot will answer using the cached content from the last link you shared in that channel.

```
You:  https://example.com/some-article
Bot:  [Summary of the article...]

You:  What were the key statistics mentioned?
Bot:  [Answers using the cached article content...]

You:  Can you draft a tweet thread from this?
Bot:  [Uses the article to draft tweets...]
```

### Adding Context to Commands

You can add extra instructions after the URL:

```
!article https://example.com/post focus on the AI implications
!code https://example.com/tutorial use Python instead of JavaScript
!research https://example.com/paper compare with transformer architectures
```

## Architecture

```
discord_link_agent.py
  |
  |-- URL Detection (regex)
  |-- Content Fetching (aiohttp)
  |-- Site-Specific Extraction (BeautifulSoup)
  |     |-- LinkedIn extractor
  |     |-- Substack extractor
  |     |-- General extractor
  |-- Gemini Processing (prompt engineering per command)
  |-- Per-Channel Content Cache (follow-up questions)
  |-- Discord Message Handling (splitting, typing indicators)
```

## Supported Sites

| Site | Notes |
|---|---|
| **Substack** | Full article extraction works well |
| **LinkedIn** | Limited — LinkedIn blocks most scrapers. Public posts with meta descriptions will work; login-walled content won't |
| **Medium** | Works for non-paywalled articles |
| **Blogs/News** | General extraction works for most sites |
| **Documentation** | Technical docs extract cleanly |

**Limitations:**
- JavaScript-rendered content (SPAs) won't be extracted — the bot fetches raw HTML
- Login-walled or paywalled content will be incomplete
- Very large pages are truncated to 50,000 characters

## Files

| File | Purpose |
|---|---|
| `discord_link_agent.py` | Main link sharing agent bot |
| `discord_only_gemini.py` | Original simple Gemini chat bot |
| `discord_only.py` | Basic Discord bot template |
| `requirements.txt` | Python dependencies |

## Troubleshooting

**Bot says "couldn't extract meaningful text content":**
- The page may require JavaScript to render (SPAs, React apps)
- The page may require login/authentication
- Try `!extract <url>` to see what raw HTML is available

**LinkedIn content is minimal:**
- LinkedIn aggressively blocks scrapers. You'll typically get only the meta description
- For better results, copy-paste the post text into Discord and ask Gemini to process it directly

**Timeout errors:**
- The default fetch timeout is 30 seconds — very slow sites may fail
- Retry the command or check if the site is accessible from your Linux box

## Security

- Never commit your `.env` file to version control
- The bot fetches URLs from the public internet — only share links you trust
- Content is cached in memory only and cleared when the bot restarts
