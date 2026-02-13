# Discord Job Agent Bot - Architecture

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           Discord Platform                          │
│                                                                       │
│  User Types:  !linkedin https://linkedin.com/jobs/view/123         │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                │ Discord API
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│                    Your Linux Box (24/7)                            │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                 job_agent_bot.py                            │   │
│  │                 (Main Discord Bot)                          │   │
│  │                                                             │   │
│  │  • Command Parser                                           │   │
│  │  • Event Handlers                                           │   │
│  │  • Error Management                                         │   │
│  │  • Message Routing                                          │   │
│  └────────┬──────────────────────────┬─────────────────────────┘   │
│           │                          │                              │
│           │                          │                              │
│  ┌────────▼───────────┐    ┌────────▼──────────┐                  │
│  │  Scrapers Module   │    │   Utils Module     │                  │
│  │                    │    │                    │                  │
│  │ LinkedInScraper    │    │  JobAnalyzer       │                  │
│  │ • scrape_job()     │    │  • analyze_job()   │                  │
│  │ • extract_*()      │    │  • compare_jobs()  │                  │
│  │ • search_company() │    │  • extract_skills()│                  │
│  │                    │    │                    │                  │
│  │ CompanyScraper     │    │  DiscordFormatter  │                  │
│  │ • search_info()    │    │  • create_embeds() │                  │
│  │ • scrape_careers() │    │  • format_analysis()│                  │
│  └────────┬───────────┘    └────────┬───────────┘                  │
│           │                         │                              │
└───────────┼─────────────────────────┼──────────────────────────────┘
            │                         │
            │                         │
┌───────────▼────────────┐ ┌──────────▼──────────────┐
│   LinkedIn.com         │ │  Google Gemini AI       │
│                        │ │                         │
│  • Job Postings        │ │  • Job Analysis         │
│  • Company Pages       │ │  • Skill Extraction     │
│  • Search Results      │ │  • Insights Generation  │
└────────────────────────┘ └─────────────────────────┘
```

## Data Flow

### 1. LinkedIn Job Analysis Flow

```
User Input: !linkedin https://linkedin.com/jobs/view/123
                    ↓
        ┌───────────────────────┐
        │  Discord Bot Receives │
        │  Command & URL        │
        └───────────┬───────────┘
                    ↓
        ┌───────────────────────┐
        │  Validate URL         │
        │  Extract Job ID       │
        └───────────┬───────────┘
                    ↓
        ┌───────────────────────┐
        │  LinkedInScraper      │
        │  • HTTP Request       │
        │  • Parse HTML         │
        │  • Extract Fields     │
        └───────────┬───────────┘
                    ↓
              Job Data Dict
              {title, company,
               location, desc...}
                    ↓
        ┌───────────────────────┐
        │  JobAnalyzer          │
        │  • Create Prompt      │
        │  • Call Gemini API    │
        │  • Parse Response     │
        └───────────┬───────────┘
                    ↓
            Analysis Dict
            {summary, skills,
             salary, insights...}
                    ↓
        ┌───────────────────────┐
        │  DiscordFormatter     │
        │  • Create Embeds      │
        │  • Format Fields      │
        │  • Apply Colors       │
        └───────────┬───────────┘
                    ↓
        ┌───────────────────────┐
        │  Send to Discord      │
        │  • Job Overview Embed │
        │  • Analysis Embed     │
        └───────────────────────┘
                    ↓
          User Sees Results
```

### 2. Company Search Flow

```
User Input: !job Google
        ↓
┌──────────────────┐
│ Parse Company    │
│ Name             │
└────────┬─────────┘
         ↓
┌──────────────────┐
│ LinkedIn Search  │
│ • Build URL      │
│ • Scrape Results │
└────────┬─────────┘
         ↓
┌──────────────────┐
│ Parse Job Cards  │
│ • Title          │
│ • Company        │
│ • Location       │
│ • URL            │
└────────┬─────────┘
         ↓
┌──────────────────┐
│ Format as Embed  │
│ • Job List       │
│ • Clickable URLs │
└────────┬─────────┘
         ↓
    Send to Discord
```

## Module Details

### job_agent_bot.py (Main Bot)

**Responsibilities:**
- Discord connection management
- Command registration and routing
- Event handling
- Error management
- User interaction flow

**Key Functions:**
- `on_ready()` - Bot startup
- `on_message()` - Message handling
- `linkedin_command()` - Analyze LinkedIn job
- `job_command()` - Company search
- `help_command()` - Show help

**Dependencies:**
- discord.py - Bot framework
- scrapers - Data collection
- utils - Analysis & formatting

### scrapers/linkedin_scraper.py

**Responsibilities:**
- HTTP requests to LinkedIn
- HTML parsing
- Data extraction
- Rate limiting
- Error handling

**Key Functions:**
- `scrape_job(url)` - Main scraping function
- `extract_job_id(url)` - URL parsing
- `_extract_title()` - Title extraction
- `_extract_description()` - Description parsing
- `search_company_jobs()` - Company search

**Techniques:**
- Multiple CSS selector fallbacks
- Regex for flexible parsing
- User-Agent rotation
- Polite scraping (delays)

### scrapers/company_scraper.py

**Responsibilities:**
- Fallback when LinkedIn fails
- Generic career page scraping
- Company information

**Key Functions:**
- `search_company_info()` - Company lookup
- `scrape_careers_page()` - Career page scraping

### utils/ai_analyzer.py

**Responsibilities:**
- Gemini AI integration
- Prompt engineering
- Response parsing
- Structured analysis

**Key Functions:**
- `analyze_job()` - Main analysis
- `_create_analysis_prompt()` - Prompt creation
- `compare_jobs()` - Job comparison
- `extract_skills()` - Skill extraction

**Analysis Sections:**
1. Role Summary
2. Required Skills
3. Preferred Qualifications
4. Key Technologies
5. Salary Estimate
6. Career Insights
7. Red/Green Flags
8. Application Tips

### utils/formatters.py

**Responsibilities:**
- Discord embed creation
- Message formatting
- Color coding
- Content chunking

**Key Functions:**
- `create_job_embed()` - Job overview
- `create_analysis_embed()` - Detailed analysis
- `create_help_embed()` - Help message
- `create_job_list_embed()` - Job list
- `split_message()` - Content chunking

**Embed Types:**
- Job Overview (blue)
- Analysis (gold)
- Error (red)
- Help (blue)
- Job List (blue)

## Configuration

### Environment Variables (.env)

```
TOKEN=<discord_bot_token>
GEMINI_API_KEY=<google_gemini_api_key>
```

### Dependencies (requirements.txt)

```
discord.py>=2.3.0      # Discord bot framework
google-generativeai    # Gemini AI SDK
requests>=2.31.0       # HTTP library
beautifulsoup4>=4.12.0 # HTML parser
lxml>=4.9.0           # XML parser
python-dotenv>=1.0.0   # Env management
aiohttp>=3.9.0        # Async HTTP
```

## Deployment Architecture

### systemd Service

```
┌─────────────────────────────────┐
│      systemd (init system)      │
│                                 │
│  • Auto-start on boot           │
│  • Auto-restart on crash        │
│  • Resource management          │
│  • Logging                      │
└────────────┬────────────────────┘
             │
             │ Manages
             ↓
┌─────────────────────────────────┐
│   job-agent-bot.service         │
│                                 │
│  WorkingDirectory=/path/to/bot  │
│  ExecStart=python bot.py        │
│  Restart=always                 │
└────────────┬────────────────────┘
             │
             │ Runs
             ↓
┌─────────────────────────────────┐
│   Python Virtual Environment    │
│                                 │
│  /path/to/venv/bin/python       │
│  + all dependencies             │
└────────────┬────────────────────┘
             │
             │ Executes
             ↓
┌─────────────────────────────────┐
│     job_agent_bot.py            │
│                                 │
│  Discord Bot Process (24/7)     │
└─────────────────────────────────┘
```

### Logging

```
Application Logs
      ↓
┌───────────────────────────────┐
│  Python logging module         │
└────────┬──────────────────────┘
         │
         ↓
┌────────────────────────────────┐
│  systemd journal               │
│  (journalctl)                  │
└────────┬───────────────────────┘
         │
         ↓
┌────────────────────────────────┐
│  /var/log/job-agent-bot/       │
│  • output.log                  │
│  • error.log                   │
└────────────────────────────────┘
```

## Security Considerations

### API Keys
- Stored in `.env` file
- Not committed to git
- Environment variable isolation
- No hardcoding

### Web Scraping
- Respectful rate limiting
- User-Agent headers
- Public data only
- No authentication bypass

### Discord Bot
- Proper permission scoping
- Input validation
- Error message sanitization
- No execution of user code

### systemd Security
- `NoNewPrivileges=true`
- `PrivateTmp=true`
- User isolation
- Resource limits

## Error Handling

```
Try: Execute Operation
  ↓
Catch: Exception Occurred
  ↓
┌──────────────────────┐
│ Log Error Details    │
└──────┬───────────────┘
       ↓
┌──────────────────────┐
│ Create User-Friendly │
│ Error Message        │
└──────┬───────────────┘
       ↓
┌──────────────────────┐
│ Send to Discord      │
│ (with error embed)   │
└──────┬───────────────┘
       ↓
┌──────────────────────┐
│ Continue Running     │
│ (don't crash)        │
└──────────────────────┘
```

## Performance Characteristics

### Latency
- Command parsing: <100ms
- LinkedIn scraping: 2-5s
- Gemini analysis: 3-7s
- Discord message send: <500ms
- **Total time**: 5-15 seconds per analysis

### Throughput
- Single bot instance
- Async I/O for concurrency
- No request queuing (MVP)
- Rate limited by LinkedIn

### Resource Usage
- Memory: ~50-100MB
- CPU: <5% (idle), ~20% (processing)
- Network: Minimal (text only)
- Disk: Logs only (~10MB/day)

## Scalability Considerations

### Current Limitations
- Single bot instance
- No caching
- No database
- LinkedIn rate limiting

### Future Scaling
- Redis for caching
- PostgreSQL for job storage
- Multiple bot shards
- Load balancing
- CDN for responses

## Monitoring & Observability

### Logs
```bash
# Application logs
sudo journalctl -u job-agent-bot -f

# Error logs
tail -f /var/log/job-agent-bot/error.log

# Output logs
tail -f /var/log/job-agent-bot/output.log
```

### Status Checks
```bash
# Service status
sudo systemctl status job-agent-bot

# Bot ping
# In Discord: !ping
```

### Metrics (Future)
- Commands per minute
- Success/failure rates
- Response times
- API quota usage

## Technology Choices Rationale

| Technology | Why Chosen | Alternatives |
|------------|-----------|--------------|
| **discord.py** | Mature, well-documented, async | discord.js (Node.js) |
| **Gemini** | Fast, cost-effective, good quality | GPT-4, Claude |
| **BeautifulSoup** | Simple, reliable, sufficient for MVP | Selenium, Scrapy |
| **systemd** | Standard on Linux, robust | supervisord, pm2 |
| **Python 3** | Easy prototyping, rich libraries | Node.js, Go |

## Maintenance Tasks

### Regular
- Monitor logs for errors
- Check Gemini API quota
- Verify bot uptime
- Test with new LinkedIn URLs

### Periodic
- Update dependencies
- Review and improve prompts
- Add new features
- Optimize scraping selectors

### As Needed
- Fix breaking changes (LinkedIn HTML)
- Handle API changes (Discord, Gemini)
- Increase rate limits
- Add caching

---

**Architecture Version**: 1.0 (MVP)
**Last Updated**: 2026-02-10
**Status**: Production Ready
