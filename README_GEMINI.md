# Discord Link Sharing Agent

A self-hosted Discord bot that extracts content from shared URLs — newsletters, LinkedIn posts, Substack, blogs, any website — and uses Google's Gemini Flash API to summarize, research, draft articles, track trends, and analyze brand perception. Your personal research assistant, fully controlled from Discord.

## Features

- **Auto URL Detection** — Paste a link and get an instant summary
- **Newsletter-Aware Extraction** — Tuned extractors for Substack, Beehiiv, Ghost, Mailchimp, ConvertKit, Buttondown, Medium, and more
- **Multiple Processing Modes** — Summarize, deep research, article drafting, code insights, newsletter breakdown
- **Content Library** — Persistent named collections that survive bot restarts
- **Trend Research** — Analyze trends across multiple collected sources on any topic
- **Brand Perception** — Sentiment and positioning analysis across your collected content
- **Follow-Up Questions** — Ask questions about the last shared link in any channel
- **General Chat** — Falls back to Gemini chat when no URL is involved

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

Optional: set a custom data directory for the content library (defaults to `./agent_data`):
```
AGENT_DATA_DIR=/path/to/your/data
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

### URL Processing

| Command | Description |
|---|---|
| Just paste a URL | Auto-summarize the page |
| `!summarize <url>` | Quick summary with key points |
| `!research <url>` | Deep analysis — thesis, evidence, takeaways |
| `!article <url>` | Draft an original article from the content |
| `!code <url>` | Extract technical/code insights |
| `!extract <url>` | Show raw extracted text (no AI processing) |
| `!newsletter <url>` | Newsletter-specific breakdown: sections, insights, resources |

### Trend & Brand Analysis

| Command | Description |
|---|---|
| `!trend <topic>` | Analyze trends across all collected content matching the topic |
| `!brand <brand_name>` | Brand perception analysis across all collected content |
| `!brand <brand_name> <url>` | Analyze how a specific page portrays a brand |

### Content Library

| Command | Description |
|---|---|
| `!collect <name> <url>` | Fetch a URL and save its content to a named collection |
| `!library` | List all collections |
| `!library <name>` | Show contents of a specific collection |
| `!analyze <name>` | Deep cross-source analysis of an entire collection |
| `!clear <name>` | Delete a collection |

### Utility

| Command | Description |
|---|---|
| `!history` | Show recently fetched URLs (last 15) |
| `!status` | Show cached content info for this channel |
| `!help` | Show all commands |

## Workflows

### Reading Newsletters

Paste a newsletter URL and the bot auto-detects the platform and extracts content cleanly:

```
You:  https://newsletter.example.com/p/this-weeks-ai-roundup
Bot:  [Summary of the newsletter...]

You:  What tools did they recommend?
Bot:  [Answers from the cached newsletter content...]
```

Use `!newsletter` for a structured breakdown with sections, resources, and takeaways:
```
!newsletter https://newsletter.example.com/p/this-weeks-ai-roundup
```

### Building a Research Collection

Collect multiple articles on a topic over time:

```
!collect ai-agents https://blog.example.com/autonomous-agents
!collect ai-agents https://newsletter.example.com/p/agent-frameworks
!collect ai-agents https://example.com/2024/agent-benchmarks
```

Then analyze them together:
```
!analyze ai-agents
```

Or look for trends:
```
!trend autonomous agents
```

### Brand Perception Tracking

Collect articles mentioning a brand:
```
!collect openai-coverage https://techcrunch.com/openai-announcement
!collect openai-coverage https://newsletter.example.com/p/openai-review
!collect openai-coverage https://blog.example.com/openai-vs-competitors
```

Run brand analysis:
```
!brand OpenAI
```

Or analyze a single article's take on a brand:
```
!brand OpenAI https://example.com/openai-critique
```

### Adding Context to Commands

Append extra instructions after the URL:

```
!article https://example.com/post focus on the AI implications
!code https://example.com/tutorial use Python instead of JavaScript
!research https://example.com/paper compare with transformer architectures
!newsletter https://example.com/weekly focus on the startup funding section
```

## Architecture

```
discord_link_agent.py
  |
  |-- URL Detection (regex)
  |-- Content Fetching (aiohttp, async)
  |-- Platform Detection (domain + HTML heuristics)
  |-- Site-Specific Extractors (BeautifulSoup)
  |     |-- Substack, Beehiiv, Ghost, Mailchimp
  |     |-- ConvertKit, Buttondown, Medium
  |     |-- LinkedIn (meta-tag fallback)
  |     |-- General (article/main/body)
  |-- Metadata Extraction (author, date, description)
  |-- Persistent Content Library (JSON on disk)
  |     |-- Named collections
  |     |-- Fetch history (last 200)
  |-- Gemini Processing
  |     |-- Single-URL prompts (summarize, research, article, code, newsletter)
  |     |-- Multi-source prompts (trend analysis, brand perception, collection analysis)
  |-- Per-Channel Context Cache (follow-up questions)
  |-- Discord Message Handling (splitting, typing indicators)
```

## Supported Platforms

| Platform | Detection | Notes |
|---|---|---|
| **Substack** | Domain + HTML meta | Full article extraction, custom domains supported |
| **Beehiiv** | Domain + data attributes | Post body extraction |
| **Ghost** | Domain + generator meta | `gh-content` class extraction |
| **Mailchimp** | Domain + template IDs | Campaign archive extraction |
| **ConvertKit / Kit** | Domain + classes | Broadcast content extraction |
| **Buttondown** | Domain + classes | Email body extraction |
| **Medium** | Domain | Article extraction (non-paywalled) |
| **LinkedIn** | Domain | Limited — meta description fallback |
| **General websites** | Fallback | article > main > body heuristic |

## Data Storage

The content library is stored as JSON at `./agent_data/content_library.json` (or wherever `AGENT_DATA_DIR` points). It contains:

- **Collections** — named groups of full content, each with URL, title, platform, metadata, and full text
- **History** — last 200 fetched URLs with content previews (500 chars each)

The library persists across bot restarts. The per-channel context cache (for follow-up questions) is in-memory only.

## Limitations

- JavaScript-rendered content (SPAs) won't be extracted — the bot fetches raw HTML
- Login-walled or paywalled content will be incomplete
- Very large pages are truncated to 50,000 characters
- LinkedIn aggressively blocks scrapers — you'll typically get only meta descriptions
- Trend and brand analysis quality depends on having enough collected content

## Files

| File | Purpose |
|---|---|
| `discord_link_agent.py` | Main link sharing agent bot |
| `discord_only_gemini.py` | Original simple Gemini chat bot |
| `discord_only.py` | Basic Discord bot template |
| `requirements.txt` | Python dependencies |
| `agent_data/` | Persistent content library (gitignored) |

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

**Trend/brand analysis says "no content found":**
- You need to collect content first using `!collect <name> <url>`
- The search is keyword-based — make sure your topic/brand name appears in the titles or content

## Security

- Never commit your `.env` file to version control
- The bot fetches URLs from the public internet — only share links you trust
- The content library stores extracted text on disk — keep your `agent_data/` directory secure
- `.env` and `agent_data/` are both gitignored by default
