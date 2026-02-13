"""
Discord Link Sharing Agent
- Detects URLs in messages and extracts web content
- Newsletter-aware extraction (Substack, Beehiiv, Ghost, Mailchimp, ConvertKit, etc.)
- Uses Gemini to summarize, research, generate articles, or extract code insights
- Persistent content library with named collections
- Trend research across multiple sources
- Brand perception and sentiment analysis
- Maintains per-channel content cache for follow-up questions
"""

from dotenv import load_dotenv
import os
import re
import json
import asyncio
import time
from collections import defaultdict
from datetime import datetime, timezone
from urllib.parse import urlparse
from pathlib import Path

import discord
import google.generativeai as genai
import aiohttp
from bs4 import BeautifulSoup

load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-2.0-flash-lite')

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# ---------------------------------------------------------------------------
# Persistent storage
# ---------------------------------------------------------------------------
DATA_DIR = Path(os.getenv('AGENT_DATA_DIR', './agent_data'))
LIBRARY_FILE = DATA_DIR / 'content_library.json'


def _load_library() -> dict:
    """Load the persistent content library from disk."""
    if LIBRARY_FILE.exists():
        try:
            return json.loads(LIBRARY_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {'collections': {}, 'history': []}


def _save_library(lib: dict):
    """Persist the content library to disk."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LIBRARY_FILE.write_text(json.dumps(lib, indent=2, default=str))


# In-memory mirror — loaded once at startup, written on every mutation
content_library = _load_library()

# Per-channel cache: last extracted content for follow-up questions
# Maps channel_id -> {"url": str, "title": str, "content": str}
channel_context = {}

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
URL_PATTERN = re.compile(r'https?://[^\s<>\"\')\]}>]+', re.IGNORECASE)

REQUEST_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

HELP_TEXT = """**Link Agent Commands**

**URL Processing** — paste a URL or use a command:
`!summarize <url>` — Quick summary of the page
`!research <url>` — Deep analysis with key takeaways
`!article <url>` — Draft an article based on the content
`!code <url>` — Extract code-relevant insights and ideas
`!extract <url>` — Show the raw extracted text (no AI)
`!newsletter <url>` — Extract & summarize newsletter content

**Trend & Brand Analysis:**
`!trend <topic>` — Analyze trends from your collected content on a topic
`!brand <brand_name>` — Brand perception analysis across collected content
`!brand <brand_name> <url>` — Analyze how a specific page portrays a brand

**Content Library:**
`!collect <name> <url>` — Save a URL's content to a named collection
`!library` — List all collections
`!library <name>` — Show contents of a collection
`!analyze <name>` — Deep cross-source analysis of a collection
`!clear <name>` — Delete a collection

**Utility:**
`!history` — Show recently fetched URLs
`!status` — Cached content info for this channel
`!help` — Show this message

**Follow-up:** After any URL, just send a message to continue the conversation about it.
"""

# ---------------------------------------------------------------------------
# Newsletter platform detection
# ---------------------------------------------------------------------------
NEWSLETTER_PLATFORMS = {
    'substack.com': 'substack',
    'beehiiv.com': 'beehiiv',
    'ghost.io': 'ghost',
    'ghost.org': 'ghost',
    'mailchimp.com': 'mailchimp',
    'campaign-archive.com': 'mailchimp',
    'convertkit.com': 'convertkit',
    'kit.co': 'convertkit',
    'buttondown.email': 'buttondown',
    'revue.email': 'revue',
    'getrevue.co': 'revue',
    'paragraph.xyz': 'paragraph',
    'medium.com': 'medium',
    'reddit.com': 'reddit',
    'old.reddit.com': 'reddit',
    'www.reddit.com': 'reddit',
}


def _detect_platform(domain: str, soup: BeautifulSoup) -> str:
    """Detect the newsletter/content platform from domain or HTML hints."""
    domain_lower = domain.lower()
    for pattern, platform in NEWSLETTER_PLATFORMS.items():
        if pattern in domain_lower:
            return platform

    # HTML-based detection for custom domains
    # Substack
    meta = soup.find('meta', attrs={'property': 'article:publisher'})
    if meta and 'substack' in (meta.get('content', '') or '').lower():
        return 'substack'
    if soup.find(class_=re.compile(r'post-content.*available-content', re.I)):
        return 'substack'

    # Ghost
    ghost_meta = soup.find('meta', attrs={'name': 'generator'})
    if ghost_meta and 'ghost' in (ghost_meta.get('content', '') or '').lower():
        return 'ghost'

    # Beehiiv
    if soup.find(attrs={'data-testid': re.compile(r'beehiiv', re.I)}):
        return 'beehiiv'
    for s in soup.find_all('script', src=True):
        if 'beehiiv' in (s.get('src') or ''):
            return 'beehiiv'

    # Mailchimp archive
    if soup.find(id='templateBody') or soup.find(class_='mcnTextContent'):
        return 'mailchimp'

    return 'general'


# ---------------------------------------------------------------------------
# Content extractors
# ---------------------------------------------------------------------------
def _extract_metadata(soup: BeautifulSoup) -> dict:
    """Pull common metadata: author, date, description."""
    meta = {}
    for prop in ['author', 'article:author']:
        tag = soup.find('meta', attrs={'name': prop}) or soup.find('meta', attrs={'property': prop})
        if tag and tag.get('content'):
            meta['author'] = tag['content'].strip()
            break

    for prop in ['article:published_time', 'date', 'datePublished']:
        tag = soup.find('meta', attrs={'property': prop}) or soup.find('meta', attrs={'name': prop})
        if tag and tag.get('content'):
            meta['date'] = tag['content'].strip()
            break

    for prop in ['og:description', 'description', 'twitter:description']:
        tag = soup.find('meta', attrs={'property': prop}) or soup.find('meta', attrs={'name': prop})
        if tag and tag.get('content'):
            meta['description'] = tag['content'].strip()
            break

    return meta


def _extract_substack(soup: BeautifulSoup) -> str:
    body = (
        soup.find(class_='body markup') or
        soup.find(class_='available-content') or
        soup.find(class_='post-content') or
        soup.find('article')
    )
    if body:
        return body.get_text(separator='\n', strip=True)
    return _extract_general(soup)


def _extract_beehiiv(soup: BeautifulSoup) -> str:
    content = (
        soup.find(attrs={'data-testid': 'post-body'}) or
        soup.find(class_=re.compile(r'post-body|email-body', re.I)) or
        soup.find('article')
    )
    if content:
        return content.get_text(separator='\n', strip=True)
    return _extract_general(soup)


def _extract_ghost(soup: BeautifulSoup) -> str:
    content = (
        soup.find(class_='gh-content') or
        soup.find(class_='post-content') or
        soup.find(class_='article-content') or
        soup.find('article')
    )
    if content:
        return content.get_text(separator='\n', strip=True)
    return _extract_general(soup)


def _extract_mailchimp(soup: BeautifulSoup) -> str:
    content = (
        soup.find(id='templateBody') or
        soup.find(class_='mcnTextContent') or
        soup.find(id='bodyTable')
    )
    if content:
        return content.get_text(separator='\n', strip=True)
    return _extract_general(soup)


def _extract_convertkit(soup: BeautifulSoup) -> str:
    content = (
        soup.find(class_=re.compile(r'letter-body|broadcast-content|post-body', re.I)) or
        soup.find('article')
    )
    if content:
        return content.get_text(separator='\n', strip=True)
    return _extract_general(soup)


def _extract_buttondown(soup: BeautifulSoup) -> str:
    content = (
        soup.find(class_=re.compile(r'email-body|letter-body', re.I)) or
        soup.find('article')
    )
    if content:
        return content.get_text(separator='\n', strip=True)
    return _extract_general(soup)


def _extract_medium(soup: BeautifulSoup) -> str:
    content = (
        soup.find('article') or
        soup.find(class_=re.compile(r'postArticle-content', re.I))
    )
    if content:
        return content.get_text(separator='\n', strip=True)
    return _extract_general(soup)


def _extract_linkedin(soup: BeautifulSoup) -> str:
    article = soup.find('article') or soup.find(class_=re.compile(r'article|post-content', re.I))
    if article:
        return article.get_text(separator='\n', strip=True)

    parts = []
    for meta_name in ['description', 'og:description', 'og:title', 'twitter:description']:
        meta = soup.find('meta', attrs={'property': meta_name}) or \
               soup.find('meta', attrs={'name': meta_name})
        if meta and meta.get('content'):
            parts.append(meta['content'].strip())
    if parts:
        return '\n\n'.join(dict.fromkeys(parts))
    return _extract_general(soup)


def _extract_general(soup: BeautifulSoup) -> str:
    main = (
        soup.find('article') or
        soup.find('main') or
        soup.find(role='main') or
        soup.find(class_=re.compile(r'article|post|content|entry', re.I)) or
        soup.find('body')
    )
    if not main:
        main = soup
    text = main.get_text(separator='\n', strip=True)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text


PLATFORM_EXTRACTORS = {
    'substack': _extract_substack,
    'beehiiv': _extract_beehiiv,
    'ghost': _extract_ghost,
    'mailchimp': _extract_mailchimp,
    'convertkit': _extract_convertkit,
    'buttondown': _extract_buttondown,
    'revue': _extract_general,
    'paragraph': _extract_general,
    'medium': _extract_medium,
    'linkedin': _extract_linkedin,
    'reddit': _extract_general,  # Reddit uses a separate JSON fetch path
    'general': _extract_general,
}


# ---------------------------------------------------------------------------
# Reddit OAuth API + fallback scraping
# ---------------------------------------------------------------------------
REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID', '')
REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET', '')
REDDIT_USER_AGENT = 'DiscordLinkAgent/1.0 (by bot)'

# Cache the OAuth token so we don't re-auth on every request
_reddit_token: dict = {'access_token': '', 'expires_at': 0.0}


async def _reddit_get_token() -> str:
    """Get a Reddit OAuth2 access token using client_credentials grant.
    See https://github.com/reddit-archive/reddit/wiki/OAuth2#application-only-oauth"""
    now = time.time()
    if _reddit_token['access_token'] and now < _reddit_token['expires_at']:
        return _reddit_token['access_token']

    auth = aiohttp.BasicAuth(REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET)
    headers = {'User-Agent': REDDIT_USER_AGENT}
    data = {'grant_type': 'client_credentials'}

    async with aiohttp.ClientSession() as session:
        async with session.post(
            'https://www.reddit.com/api/v1/access_token',
            auth=auth, headers=headers, data=data,
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status != 200:
                raise RuntimeError(f'Reddit OAuth failed: HTTP {resp.status}')
            body = await resp.json()

    token = body.get('access_token', '')
    expires_in = body.get('expires_in', 3600)
    _reddit_token['access_token'] = token
    _reddit_token['expires_at'] = now + expires_in - 60  # refresh 60s early
    return token


def _reddit_api_path(url: str) -> str:
    """Extract the Reddit path (e.g. /r/python/comments/abc123/...) from a URL."""
    clean = re.sub(r'https?://(www\.|old\.|new\.)?reddit\.com', '', url)
    clean = clean.split('?')[0].rstrip('/')
    if clean.endswith('.json'):
        clean = clean[:-5]
    return clean or '/'


def _parse_reddit_json(data, url: str) -> dict:
    """Parse Reddit JSON API response into our standard content dict."""
    parts = []
    title = ''
    metadata = {}

    listings = data if isinstance(data, list) else [data]

    for listing in listings:
        if not isinstance(listing, dict) or 'data' not in listing:
            continue
        children = listing.get('data', {}).get('children', [])
        for child in children:
            kind = child.get('kind', '')
            cdata = child.get('data', {})

            if kind == 't3':  # Post
                title = cdata.get('title', '')
                author = cdata.get('author', '')
                subreddit = cdata.get('subreddit_name_prefixed', '')
                score = cdata.get('score', 0)
                created = cdata.get('created_utc', 0)

                metadata = {
                    'author': f"u/{author}",
                    'date': datetime.fromtimestamp(created, tz=timezone.utc).isoformat() if created else '',
                    'description': f"{subreddit} | Score: {score}",
                }

                parts.append(f"POST: {title}")
                parts.append(f"Author: u/{author} | {subreddit} | Score: {score}")
                selftext = cdata.get('selftext', '')
                if selftext:
                    parts.append(f"\n{selftext}")
                post_url = cdata.get('url', '')
                if post_url and post_url != url and 'reddit.com' not in post_url:
                    parts.append(f"\nLinked URL: {post_url}")
                parts.append('')

            elif kind == 't1':  # Comment
                cauthor = cdata.get('author', '[deleted]')
                cscore = cdata.get('score', 0)
                cbody = cdata.get('body', '')
                if cbody and cauthor != 'AutoModerator':
                    parts.append(f"[u/{cauthor} | {cscore} pts]")
                    parts.append(cbody)
                    parts.append('')

                    replies = cdata.get('replies', '')
                    if isinstance(replies, dict):
                        reply_children = replies.get('data', {}).get('children', [])
                        for reply in reply_children[:3]:
                            rdata = reply.get('data', {})
                            rauthor = rdata.get('author', '')
                            rbody = rdata.get('body', '')
                            rscore = rdata.get('score', 0)
                            if rbody and rauthor and rauthor != 'AutoModerator':
                                parts.append(f"  [u/{rauthor} | {rscore} pts]")
                                parts.append(f"  {rbody}")
                                parts.append('')

    content = '\n'.join(parts)
    return {'title': title, 'content': content, 'metadata': metadata}


def _reddit_to_old(url: str) -> str:
    """Rewrite any reddit URL to old.reddit.com."""
    return re.sub(r'https?://(www\.)?reddit\.com', 'https://old.reddit.com', url)


def _parse_reddit_html(html: str) -> dict:
    """Fallback: extract content from old.reddit.com HTML."""
    soup = BeautifulSoup(html, 'html.parser')

    for tag in soup(['script', 'style', 'nav', 'aside', 'noscript', 'iframe', 'svg']):
        tag.decompose()

    title = ''
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    parts = []

    post_title = soup.find('a', class_='title')
    if post_title:
        parts.append(f"POST: {post_title.get_text(strip=True)}")
        title = title or post_title.get_text(strip=True)

    usertext = soup.find(class_='usertext-body')
    if usertext:
        parts.append(usertext.get_text(separator='\n', strip=True))
        parts.append('')

    comments = soup.find_all(class_='comment')
    for comment in comments[:30]:
        author_tag = comment.find(class_='author')
        author = author_tag.get_text(strip=True) if author_tag else '[deleted]'
        body = comment.find(class_='usertext-body')
        if body and author != 'AutoModerator':
            score_tag = comment.find(class_='score')
            score = score_tag.get('title', '') if score_tag else ''
            parts.append(f"[u/{author}{f' | {score} pts' if score else ''}]")
            parts.append(body.get_text(separator='\n', strip=True))
            parts.append('')

    if not parts:
        main = soup.find(class_='sitetable') or soup.find(role='main') or soup.find('body')
        if main:
            parts.append(main.get_text(separator='\n', strip=True))

    metadata = {}
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if meta_desc and meta_desc.get('content'):
        metadata['description'] = meta_desc['content'].strip()

    content = '\n'.join(parts)
    content = re.sub(r'\n{3,}', '\n\n', content)
    return {'title': title, 'content': content, 'metadata': metadata}


def _reddit_result(url, title, content, metadata, error=False):
    if len(content) > 50000:
        content = content[:50000] + '\n\n[Content truncated...]'
    return {'url': url, 'title': title, 'content': content,
            'platform': 'reddit', 'metadata': metadata, 'error': error}


async def _fetch_reddit(url: str) -> dict:
    """Fetch a Reddit URL. Strategy order:
    1. Reddit OAuth API (oauth.reddit.com) — if REDDIT_CLIENT_ID is set
    2. old.reddit.com .json endpoint with browser UA
    3. old.reddit.com HTML scraping
    """

    # Strategy 1: Official Reddit OAuth API
    if REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET:
        try:
            token = await _reddit_get_token()
            api_path = _reddit_api_path(url)
            api_url = f'https://oauth.reddit.com{api_path}'
            headers = {
                'Authorization': f'Bearer {token}',
                'User-Agent': REDDIT_USER_AGENT,
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, headers=headers,
                                       timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        parsed = _parse_reddit_json(data, url)
                        if parsed['content'].strip():
                            return _reddit_result(url, parsed['title'],
                                                  parsed['content'], parsed['metadata'])
        except Exception:
            pass  # Fall through to unauthenticated methods

    # Strategy 2: old.reddit.com .json with browser UA
    json_path = _reddit_api_path(url)
    json_url = f'https://old.reddit.com{json_path}.json'
    try:
        async with aiohttp.ClientSession(headers=REQUEST_HEADERS) as session:
            async with session.get(json_url, timeout=aiohttp.ClientTimeout(total=30),
                                   allow_redirects=True, ssl=False) as resp:
                if resp.status == 200:
                    ct = resp.headers.get('Content-Type', '')
                    if 'json' in ct:
                        data = await resp.json()
                        parsed = _parse_reddit_json(data, url)
                        if parsed['content'].strip():
                            return _reddit_result(url, parsed['title'],
                                                  parsed['content'], parsed['metadata'])
    except Exception:
        pass  # Fall through to HTML

    # Strategy 3: old.reddit.com HTML scraping
    old_url = _reddit_to_old(url)
    try:
        async with aiohttp.ClientSession(headers=REQUEST_HEADERS) as session:
            async with session.get(old_url, timeout=aiohttp.ClientTimeout(total=30),
                                   allow_redirects=True, ssl=False) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    parsed = _parse_reddit_html(html)
                    if parsed['content'].strip():
                        return _reddit_result(url, parsed['title'],
                                              parsed['content'], parsed['metadata'])
                    return _reddit_result(
                        url, '', 'Fetched Reddit page but could not extract content. '
                        'The post may be deleted or require login.', {}, error=True)
                else:
                    return _reddit_result(
                        url, '', f'Reddit returned HTTP {resp.status}. '
                        'The post may be private, deleted, or Reddit is blocking requests.',
                        {}, error=True)
    except asyncio.TimeoutError:
        return _reddit_result(url, '', 'Reddit request timed out', {}, error=True)
    except Exception as e:
        return _reddit_result(url, '', f'Reddit fetch error: {e}', {}, error=True)


# ---------------------------------------------------------------------------
# Core fetch
# ---------------------------------------------------------------------------
def _is_reddit(domain: str) -> bool:
    return any(r in domain for r in ['reddit.com', 'redd.it'])


async def fetch_url(url: str) -> dict:
    """Fetch a URL, detect platform, extract content + metadata."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()

    # Reddit needs its own fetch path (JSON API) to avoid 503 blocks
    if _is_reddit(domain):
        return await _fetch_reddit(url)

    try:
        async with aiohttp.ClientSession(headers=REQUEST_HEADERS) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30),
                                   allow_redirects=True, ssl=False) as resp:
                if resp.status != 200:
                    return {
                        'url': url, 'title': '', 'content': f'HTTP {resp.status}',
                        'platform': '', 'metadata': {}, 'error': True,
                    }
                html = await resp.text()
    except asyncio.TimeoutError:
        return {'url': url, 'title': '', 'content': 'Request timed out',
                'platform': '', 'metadata': {}, 'error': True}
    except Exception as e:
        return {'url': url, 'title': '', 'content': f'Fetch error: {e}',
                'platform': '', 'metadata': {}, 'error': True}

    soup = BeautifulSoup(html, 'html.parser')

    # Strip non-content elements
    for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside',
                     'noscript', 'iframe', 'svg']):
        tag.decompose()

    title = ''
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    platform = 'linkedin' if 'linkedin.com' in domain else _detect_platform(domain, soup)
    extractor = PLATFORM_EXTRACTORS.get(platform, _extract_general)
    content = extractor(soup)
    metadata = _extract_metadata(soup)

    max_chars = 50000
    if len(content) > max_chars:
        content = content[:max_chars] + '\n\n[Content truncated...]'

    return {
        'url': url,
        'title': title,
        'content': content,
        'platform': platform,
        'metadata': metadata,
        'error': False,
    }


# ---------------------------------------------------------------------------
# Library helpers
# ---------------------------------------------------------------------------
def _add_to_history(data: dict):
    """Add fetched content to the global history."""
    entry = {
        'url': data['url'],
        'title': data['title'],
        'platform': data.get('platform', ''),
        'metadata': data.get('metadata', {}),
        'content_preview': data['content'][:500],
        'content_length': len(data['content']),
        'fetched_at': datetime.now(timezone.utc).isoformat(),
    }
    content_library['history'].append(entry)
    # Keep last 200 entries
    if len(content_library['history']) > 200:
        content_library['history'] = content_library['history'][-200:]
    _save_library(content_library)


def _add_to_collection(name: str, data: dict):
    """Add content to a named collection."""
    name = name.lower().strip()
    if name not in content_library['collections']:
        content_library['collections'][name] = []
    content_library['collections'][name].append({
        'url': data['url'],
        'title': data['title'],
        'platform': data.get('platform', ''),
        'metadata': data.get('metadata', {}),
        'content': data['content'],
        'fetched_at': datetime.now(timezone.utc).isoformat(),
    })
    _save_library(content_library)


# ---------------------------------------------------------------------------
# Command parsing
# ---------------------------------------------------------------------------
ALL_COMMANDS = [
    '!summarize', '!research', '!article', '!code', '!extract',
    '!newsletter', '!trend', '!brand', '!collect', '!library',
    '!analyze', '!clear', '!history', '!status', '!help',
]


def extract_command_and_url(text: str) -> tuple:
    """Parse a message into (command, url, extra_text).
    Returns (None, None, text) if no command found.
    """
    text = text.strip()
    url_commands = ['!summarize', '!research', '!article', '!code', '!extract', '!newsletter']

    for cmd in url_commands:
        if text.lower().startswith(cmd):
            remainder = text[len(cmd):].strip()
            urls = URL_PATTERN.findall(remainder)
            url = urls[0] if urls else None
            extra = URL_PATTERN.sub('', remainder).strip()
            return (cmd.lstrip('!'), url, extra)

    # Commands that may or may not have a URL
    for cmd in ['!brand', '!collect']:
        if text.lower().startswith(cmd):
            remainder = text[len(cmd):].strip()
            urls = URL_PATTERN.findall(remainder)
            url = urls[0] if urls else None
            extra = URL_PATTERN.sub('', remainder).strip()
            return (cmd.lstrip('!'), url, extra)

    # No-URL commands
    for cmd in ['!trend', '!library', '!analyze', '!clear', '!history']:
        if text.lower().startswith(cmd):
            remainder = text[len(cmd):].strip()
            return (cmd.lstrip('!'), None, remainder)

    # Bare URLs
    urls = URL_PATTERN.findall(text)
    if urls:
        extra = URL_PATTERN.sub('', text).strip()
        return ('summarize', urls[0], extra)

    return (None, None, text)


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------
def build_prompt(command: str, content_data: dict, extra: str = '') -> str:
    """Build the Gemini prompt for single-URL commands."""
    title = content_data.get('title', '')
    content = content_data.get('content', '')
    url = content_data.get('url', '')
    platform = content_data.get('platform', '')
    metadata = content_data.get('metadata', {})

    header = f"Source: {url}"
    if title:
        header += f"\nTitle: {title}"
    if platform and platform != 'general':
        header += f"\nPlatform: {platform}"
    if metadata.get('author'):
        header += f"\nAuthor: {metadata['author']}"
    if metadata.get('date'):
        header += f"\nPublished: {metadata['date']}"
    header += f"\n\nExtracted content:\n{content}"

    prompts = {
        'summarize': (
            f"{header}\n\n"
            "Provide a clear, concise summary of this content. "
            "Include the key points, main argument or topic, and any notable details. "
            "Format with bullet points where appropriate."
        ),
        'research': (
            f"{header}\n\n"
            "Perform a deep analysis of this content:\n"
            "1. Main thesis or topic\n"
            "2. Key arguments and supporting evidence\n"
            "3. Notable quotes or data points\n"
            "4. Strengths and weaknesses of the arguments\n"
            "5. Related topics worth exploring further\n"
            "6. Key takeaways\n"
            f"{f'Additional context: {extra}' if extra else ''}"
        ),
        'article': (
            f"{header}\n\n"
            "Using this content as source material, draft an original article. "
            "The article should:\n"
            "- Have a compelling headline\n"
            "- Synthesize the key ideas into a coherent narrative\n"
            "- Add context and analysis\n"
            "- Be well-structured with clear sections\n"
            "- Be roughly 500-800 words\n"
            f"{f'Article direction: {extra}' if extra else ''}"
        ),
        'code': (
            f"{header}\n\n"
            "Analyze this content from a software engineering perspective:\n"
            "1. Identify any technical concepts, tools, or frameworks mentioned\n"
            "2. Suggest code implementations or projects inspired by the content\n"
            "3. If code snippets are present, explain and improve them\n"
            "4. Propose automation or tooling ideas based on the content\n"
            f"{f'Focus area: {extra}' if extra else ''}"
        ),
        'newsletter': (
            f"{header}\n\n"
            "This is a newsletter. Analyze it as follows:\n"
            "1. **Newsletter overview** — what is the theme / edition about?\n"
            "2. **Key stories / sections** — bullet each distinct topic covered\n"
            "3. **Notable insights or opinions** — anything the author emphasizes\n"
            "4. **Links & resources mentioned** — list any notable references\n"
            "5. **Actionable takeaways** — what should a reader do with this info?\n"
            f"{f'Focus: {extra}' if extra else ''}"
        ),
    }
    return prompts.get(command, f"{header}\n\nSummarize this content.")


def build_trend_prompt(topic: str, sources: list) -> str:
    """Build a prompt for trend analysis across multiple sources."""
    parts = [f"Analyze trends on the topic: **{topic}**\n\nSources:\n"]
    for i, src in enumerate(sources, 1):
        parts.append(
            f"--- Source {i} ---\n"
            f"URL: {src.get('url', 'N/A')}\n"
            f"Title: {src.get('title', 'N/A')}\n"
            f"Date: {src.get('metadata', {}).get('date', 'N/A')}\n"
            f"Content:\n{src.get('content', src.get('content_preview', ''))[:8000]}\n\n"
        )
    parts.append(
        "\nBased on these sources, provide:\n"
        "1. **Emerging trends** — what patterns or directions are appearing?\n"
        "2. **Consensus views** — what do most sources agree on?\n"
        "3. **Contrarian takes** — any dissenting or unique perspectives?\n"
        "4. **Timeline / momentum** — are things accelerating, plateauing, or declining?\n"
        "5. **Gaps** — what's not being covered that should be?\n"
        "6. **Prediction** — where is this topic heading in the next 6-12 months?\n"
    )
    return ''.join(parts)


def build_brand_prompt(brand: str, sources: list) -> str:
    """Build a prompt for brand perception analysis."""
    parts = [f"Analyze brand perception for: **{brand}**\n\nSources:\n"]
    for i, src in enumerate(sources, 1):
        parts.append(
            f"--- Source {i} ---\n"
            f"URL: {src.get('url', 'N/A')}\n"
            f"Title: {src.get('title', 'N/A')}\n"
            f"Date: {src.get('metadata', {}).get('date', 'N/A')}\n"
            f"Content:\n{src.get('content', src.get('content_preview', ''))[:8000]}\n\n"
        )
    parts.append(
        f"\nProvide a brand perception analysis for **{brand}**:\n"
        "1. **Overall sentiment** — positive, negative, mixed? Give a 1-10 score\n"
        "2. **Key themes** — what topics/attributes are associated with this brand?\n"
        "3. **Strengths highlighted** — what do sources praise?\n"
        "4. **Weaknesses / criticisms** — what do sources criticize or question?\n"
        "5. **Competitive positioning** — how is the brand positioned vs. alternatives?\n"
        "6. **Audience perception** — who talks about it and how?\n"
        "7. **Trend direction** — is perception improving, declining, or stable?\n"
        "8. **Recommendations** — strategic suggestions based on the perception data\n"
    )
    return ''.join(parts)


# ---------------------------------------------------------------------------
# Gemini + Discord helpers
# ---------------------------------------------------------------------------
async def process_with_gemini(prompt: str) -> str:
    response = await discord.utils.maybe_coroutine(model.generate_content, prompt)
    return response.text


async def send_long_message(channel, text: str):
    if len(text) <= 2000:
        await channel.send(text)
        return
    chunks = []
    while text:
        if len(text) <= 2000:
            chunks.append(text)
            break
        split_at = text.rfind('\n', 0, 2000)
        if split_at == -1 or split_at < 1000:
            split_at = 2000
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip('\n')
    for chunk in chunks:
        await channel.send(chunk)


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------
@client.event
async def on_ready():
    collections_count = len(content_library.get('collections', {}))
    history_count = len(content_library.get('history', []))
    print(f'Link Agent logged in as {client.user}')
    print(f'Gemini API ready | Library: {collections_count} collections, {history_count} history entries')


@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if not message.content.strip():
        return

    text = message.content.strip()

    # --- Simple commands ------------------------------------------------
    if text.lower() == '!help':
        await message.channel.send(HELP_TEXT)
        return

    if text.lower() == '!status':
        ctx = channel_context.get(message.channel.id)
        if ctx:
            platform_tag = f" ({ctx.get('platform', 'general')})" if ctx.get('platform') else ''
            await message.channel.send(
                f"**Cached content for this channel:**\n"
                f"URL: {ctx['url']}{platform_tag}\n"
                f"Title: {ctx.get('title') or '(no title)'}\n"
                f"Content length: {len(ctx['content']):,} characters"
            )
        else:
            await message.channel.send("No cached content. Share a URL to get started.")
        return

    if text.lower().startswith('!history'):
        history = content_library.get('history', [])
        if not history:
            await message.channel.send("No fetch history yet.")
            return
        lines = ["**Recent fetch history** (newest first):\n"]
        for entry in reversed(history[-15:]):
            ts = entry.get('fetched_at', '')[:10]
            plat = f" [{entry.get('platform', '')}]" if entry.get('platform') else ''
            lines.append(f"- `{ts}` {entry.get('title', entry['url'])[:80]}{plat}")
        await send_long_message(message.channel, '\n'.join(lines))
        return

    # --- Parse command --------------------------------------------------
    command, url, extra = extract_command_and_url(text)

    # --- Library commands (no URL needed) --------------------------------
    if command == 'library':
        collections = content_library.get('collections', {})
        if extra:
            name = extra.lower().strip()
            coll = collections.get(name)
            if not coll:
                await message.channel.send(f"No collection named **{name}**. Use `!library` to list all.")
                return
            lines = [f"**Collection: {name}** ({len(coll)} items)\n"]
            for item in coll:
                ts = item.get('fetched_at', '')[:10]
                lines.append(f"- `{ts}` [{item.get('title') or 'Untitled'}]({item['url']})")
            await send_long_message(message.channel, '\n'.join(lines))
        else:
            if not collections:
                await message.channel.send("Library is empty. Use `!collect <name> <url>` to start building collections.")
                return
            lines = ["**Content Library:**\n"]
            for name, items in collections.items():
                lines.append(f"- **{name}** — {len(items)} items")
            lines.append(f"\nUse `!library <name>` to see details.")
            await message.channel.send('\n'.join(lines))
        return

    if command == 'clear':
        if not extra:
            await message.channel.send("Usage: `!clear <collection_name>`")
            return
        name = extra.lower().strip()
        if name in content_library.get('collections', {}):
            del content_library['collections'][name]
            _save_library(content_library)
            await message.channel.send(f"Deleted collection **{name}**.")
        else:
            await message.channel.send(f"No collection named **{name}**.")
        return

    # --- Trend analysis (uses library + history) --------------------------
    if command == 'trend':
        if not extra:
            await message.channel.send("Usage: `!trend <topic>`\nI'll search your collected content for relevant sources.")
            return
        topic = extra
        async with message.channel.typing():
            # Gather relevant sources from collections and history
            sources = []
            for name, items in content_library.get('collections', {}).items():
                for item in items:
                    text_blob = f"{item.get('title', '')} {item.get('content', '')[:2000]}".lower()
                    if topic.lower() in text_blob:
                        sources.append(item)
            # Also check history content previews
            for entry in content_library.get('history', []):
                text_blob = f"{entry.get('title', '')} {entry.get('content_preview', '')}".lower()
                if topic.lower() in text_blob and not any(s['url'] == entry['url'] for s in sources):
                    sources.append(entry)

            if not sources:
                await message.channel.send(
                    f"No content found related to **{topic}** in your library.\n"
                    f"Collect some URLs first with `!collect <name> <url>` or share URLs related to this topic."
                )
                return

            # Limit to 10 most recent sources
            sources = sources[-10:]
            prompt = build_trend_prompt(topic, sources)
            try:
                result = await process_with_gemini(prompt)
                header = f"**Trend Analysis: {topic}** ({len(sources)} sources)\n\n"
                await send_long_message(message.channel, header + result)
            except Exception as e:
                await message.channel.send(f"Gemini error: {e}")
        return

    # --- Brand perception ------------------------------------------------
    if command == 'brand':
        brand = extra
        if not brand and not url:
            await message.channel.send(
                "Usage:\n"
                "`!brand <brand_name>` — Analyze perception across all collected content\n"
                "`!brand <brand_name> <url>` — Analyze perception in a specific page"
            )
            return

        async with message.channel.typing():
            sources = []

            # If a URL was provided, fetch it and use as the sole source
            if url:
                content_data = await fetch_url(url)
                if content_data.get('error'):
                    await message.channel.send(f"Could not fetch <{url}>: {content_data['content']}")
                    return
                _add_to_history(content_data)
                channel_context[message.channel.id] = content_data
                sources.append(content_data)
            else:
                # Search library for brand mentions
                for name, items in content_library.get('collections', {}).items():
                    for item in items:
                        text_blob = f"{item.get('title', '')} {item.get('content', '')[:3000]}".lower()
                        if brand.lower() in text_blob:
                            sources.append(item)
                for entry in content_library.get('history', []):
                    text_blob = f"{entry.get('title', '')} {entry.get('content_preview', '')}".lower()
                    if brand.lower() in text_blob and not any(s['url'] == entry['url'] for s in sources):
                        sources.append(entry)

            if not sources:
                await message.channel.send(
                    f"No content found mentioning **{brand}**.\n"
                    f"Try `!brand {brand} <url>` with a specific URL, or collect more content first."
                )
                return

            sources = sources[-10:]
            prompt = build_brand_prompt(brand, sources)
            try:
                result = await process_with_gemini(prompt)
                header = f"**Brand Perception: {brand}** ({len(sources)} sources)\n\n"
                await send_long_message(message.channel, header + result)
            except Exception as e:
                await message.channel.send(f"Gemini error: {e}")
        return

    # --- Collect to library -----------------------------------------------
    if command == 'collect':
        if not extra or not url:
            await message.channel.send("Usage: `!collect <collection_name> <url>`")
            return
        collection_name = extra.split()[0].lower()
        async with message.channel.typing():
            content_data = await fetch_url(url)
            if content_data.get('error'):
                await message.channel.send(f"Could not fetch <{url}>: {content_data['content']}")
                return
            _add_to_history(content_data)
            _add_to_collection(collection_name, content_data)
            channel_context[message.channel.id] = content_data
            count = len(content_library['collections'][collection_name])
            platform_tag = f" [{content_data.get('platform', '')}]" if content_data.get('platform') else ''
            await message.channel.send(
                f"Added to **{collection_name}** (now {count} items){platform_tag}\n"
                f"Title: {content_data['title'] or '(no title)'}"
            )
        return

    # --- Analyze collection -----------------------------------------------
    if command == 'analyze':
        if not extra:
            await message.channel.send("Usage: `!analyze <collection_name>`")
            return
        name = extra.lower().strip()
        coll = content_library.get('collections', {}).get(name)
        if not coll:
            await message.channel.send(f"No collection named **{name}**.")
            return
        async with message.channel.typing():
            parts = [f"Deep analysis of collection: **{name}** ({len(coll)} sources)\n\nSources:\n"]
            for i, item in enumerate(coll, 1):
                parts.append(
                    f"--- Source {i} ---\n"
                    f"URL: {item['url']}\nTitle: {item.get('title', 'N/A')}\n"
                    f"Date: {item.get('metadata', {}).get('date', 'N/A')}\n"
                    f"Content:\n{item['content'][:8000]}\n\n"
                )
            parts.append(
                "\nProvide a comprehensive cross-source analysis:\n"
                "1. **Common themes** across all sources\n"
                "2. **Key insights** — the most important takeaways\n"
                "3. **Contradictions or debates** — where do sources disagree?\n"
                "4. **Trends** — what direction is the topic moving?\n"
                "5. **Gaps** — what's missing from this collection?\n"
                "6. **Synthesis** — tie it all together into a cohesive narrative\n"
                "7. **Next steps** — what should be researched or collected next?\n"
            )
            try:
                result = await process_with_gemini(''.join(parts))
                header = f"**Collection Analysis: {name}** ({len(coll)} sources)\n\n"
                await send_long_message(message.channel, header + result)
            except Exception as e:
                await message.channel.send(f"Gemini error: {e}")
        return

    # --- URL-based commands -----------------------------------------------
    if url:
        print(f'[{message.author}] {command} -> {url}')
        async with message.channel.typing():
            content_data = await fetch_url(url)

            if content_data.get('error'):
                await message.channel.send(f"Could not fetch <{url}>:\n{content_data['content']}")
                return

            if not content_data['content'].strip():
                await message.channel.send(
                    f"Fetched <{url}> but couldn't extract meaningful text. "
                    f"The page may require JavaScript or authentication."
                )
                return

            # Cache and record
            channel_context[message.channel.id] = content_data
            _add_to_history(content_data)

            platform_tag = f" [{content_data.get('platform', '')}]" if content_data.get('platform', '') != 'general' else ''

            # Raw extract
            if command == 'extract':
                title = content_data['title'] or '(no title)'
                response_text = (
                    f"**Extracted from:** {url}{platform_tag}\n"
                    f"**Title:** {title}\n"
                    f"**Content length:** {len(content_data['content']):,} chars\n\n"
                    f"{content_data['content'][:3500]}"
                )
                if len(content_data['content']) > 3500:
                    response_text += "\n\n*[Truncated — full content cached for follow-up questions]*"
                await send_long_message(message.channel, response_text)
                return

            # AI processing
            prompt = build_prompt(command, content_data, extra)
            try:
                result = await process_with_gemini(prompt)
                header = f"**{command.title()}** — {content_data['title'] or url}{platform_tag}\n\n"
                await send_long_message(message.channel, header + result)
            except Exception as e:
                await message.channel.send(f"Gemini error: {e}")
                print(f'Gemini error: {e}')
        return

    # --- Follow-up on cached content --------------------------------------
    ctx = channel_context.get(message.channel.id)
    if ctx and command is None:
        print(f'[{message.author}] Follow-up on {ctx["url"]}')
        async with message.channel.typing():
            prompt = (
                f"Previously extracted content from {ctx['url']}:\n"
                f"Title: {ctx.get('title', '')}\n"
                f"Platform: {ctx.get('platform', '')}\n\n"
                f"{ctx['content']}\n\n"
                f"User question: {text}\n\n"
                "Answer the user's question based on the extracted content above. "
                "If the question goes beyond the content, you may use your general knowledge "
                "but note what comes from the source vs. your own knowledge."
            )
            try:
                result = await process_with_gemini(prompt)
                await send_long_message(message.channel, result)
            except Exception as e:
                await message.channel.send(f"Gemini error: {e}")
        return

    # --- General chat fallback --------------------------------------------
    print(f'[{message.author}] General: {text[:80]}')
    async with message.channel.typing():
        try:
            result = await process_with_gemini(text)
            await send_long_message(message.channel, result)
        except Exception as e:
            await message.channel.send(f"Gemini error: {e}")


client.run(os.getenv('TOKEN'))
