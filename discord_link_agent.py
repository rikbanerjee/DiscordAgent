"""
Discord Link Sharing Agent
- Detects URLs in messages and extracts web content
- Uses Gemini to summarize, research, generate articles, or extract code insights
- Supports LinkedIn, Substack, and general websites
- Maintains per-channel content cache for follow-up questions
"""

from dotenv import load_dotenv
import os
import re
import json
import asyncio
from collections import defaultdict
from urllib.parse import urlparse

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

# Per-channel cache of the last extracted content for follow-up questions
# Maps channel_id -> {"url": str, "title": str, "content": str}
channel_context = {}

# Regex to find URLs in messages
URL_PATTERN = re.compile(
    r'https?://[^\s<>\"\')\]}>]+', re.IGNORECASE
)

HELP_TEXT = """**Link Agent Commands**

**Auto-detect:** Just paste a URL and I'll summarize it.

**Explicit commands:**
`!summarize <url>` — Quick summary of the page
`!research <url>` — Deep analysis with key takeaways
`!article <url>` — Draft an article based on the content
`!code <url>` — Extract code-relevant insights and ideas
`!extract <url>` — Show the raw extracted text (no AI processing)

**Follow-up:** After processing a link, just send a message (no URL) and I'll answer using the last extracted content in this channel.

`!help` — Show this message
`!status` — Show cached content info for this channel
"""

# Headers that help with fetching content from various sites
REQUEST_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}


async def fetch_url(url: str) -> dict:
    """Fetch a URL and extract text content. Returns dict with title, content, url."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()

    try:
        async with aiohttp.ClientSession(headers=REQUEST_HEADERS) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30),
                                   allow_redirects=True, ssl=False) as resp:
                if resp.status != 200:
                    return {
                        'url': url,
                        'title': '',
                        'content': f'Failed to fetch URL (HTTP {resp.status})',
                        'error': True,
                    }
                html = await resp.text()
    except asyncio.TimeoutError:
        return {'url': url, 'title': '', 'content': 'Request timed out', 'error': True}
    except Exception as e:
        return {'url': url, 'title': '', 'content': f'Fetch error: {e}', 'error': True}

    soup = BeautifulSoup(html, 'html.parser')

    # Remove script, style, nav, footer, header elements
    for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside',
                     'noscript', 'iframe', 'svg']):
        tag.decompose()

    title = ''
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    # Site-specific extraction
    if 'linkedin.com' in domain:
        content = _extract_linkedin(soup)
    elif 'substack.com' in domain or _is_substack(soup):
        content = _extract_substack(soup)
    else:
        content = _extract_general(soup)

    # Truncate very long content to stay within Gemini context limits
    max_chars = 50000
    if len(content) > max_chars:
        content = content[:max_chars] + '\n\n[Content truncated...]'

    return {'url': url, 'title': title, 'content': content, 'error': False}


def _is_substack(soup: BeautifulSoup) -> bool:
    """Detect if a page is a Substack post even on custom domains."""
    meta = soup.find('meta', attrs={'property': 'article:publisher'})
    if meta and 'substack' in (meta.get('content', '') or '').lower():
        return True
    # Check for substack-specific classes
    if soup.find(class_=re.compile(r'post-content|subtitle.*class', re.I)):
        return True
    return False


def _extract_linkedin(soup: BeautifulSoup) -> str:
    """Extract content from LinkedIn pages. LinkedIn often blocks scrapers,
    so we do our best with what's available in the HTML."""
    # Try to get article content
    article = soup.find('article') or soup.find(class_=re.compile(r'article|post-content', re.I))
    if article:
        return article.get_text(separator='\n', strip=True)

    # Try meta description and og tags as fallback (LinkedIn often has these)
    parts = []
    for meta_name in ['description', 'og:description', 'og:title', 'twitter:description']:
        meta = soup.find('meta', attrs={'property': meta_name}) or \
               soup.find('meta', attrs={'name': meta_name})
        if meta and meta.get('content'):
            parts.append(meta['content'].strip())

    if parts:
        return '\n\n'.join(dict.fromkeys(parts))  # dedupe while preserving order

    # Last resort: get all visible text
    return _extract_general(soup)


def _extract_substack(soup: BeautifulSoup) -> str:
    """Extract article content from Substack posts."""
    # Substack uses .body.markup for post content
    body = soup.find(class_='body markup') or soup.find(class_='post-content') or \
           soup.find('article')
    if body:
        return body.get_text(separator='\n', strip=True)
    return _extract_general(soup)


def _extract_general(soup: BeautifulSoup) -> str:
    """General-purpose content extraction."""
    # Try article or main content first
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
    # Clean up excessive blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text


def extract_command_and_url(text: str) -> tuple:
    """Parse a message into (command, url, extra_text).
    Returns (None, None, text) if no command found.
    """
    text = text.strip()
    commands = ['!summarize', '!research', '!article', '!code', '!extract']

    for cmd in commands:
        if text.lower().startswith(cmd):
            remainder = text[len(cmd):].strip()
            urls = URL_PATTERN.findall(remainder)
            url = urls[0] if urls else None
            extra = URL_PATTERN.sub('', remainder).strip()
            return (cmd.lstrip('!'), url, extra)

    # No explicit command — check for bare URLs
    urls = URL_PATTERN.findall(text)
    if urls:
        extra = URL_PATTERN.sub('', text).strip()
        return ('summarize', urls[0], extra)

    return (None, None, text)


def build_prompt(command: str, content_data: dict, extra: str = '') -> str:
    """Build the Gemini prompt based on command type."""
    title = content_data.get('title', '')
    content = content_data.get('content', '')
    url = content_data.get('url', '')

    header = f"Source: {url}"
    if title:
        header += f"\nTitle: {title}"
    header += f"\n\nExtracted content:\n{content}"

    if command == 'summarize':
        return (
            f"{header}\n\n"
            "Provide a clear, concise summary of this content. "
            "Include the key points, main argument or topic, and any notable details. "
            "Format with bullet points where appropriate."
        )
    elif command == 'research':
        return (
            f"{header}\n\n"
            "Perform a deep analysis of this content:\n"
            "1. Main thesis or topic\n"
            "2. Key arguments and supporting evidence\n"
            "3. Notable quotes or data points\n"
            "4. Strengths and weaknesses of the arguments\n"
            "5. Related topics worth exploring further\n"
            "6. Key takeaways\n"
            f"{f'Additional context: {extra}' if extra else ''}"
        )
    elif command == 'article':
        return (
            f"{header}\n\n"
            "Using this content as source material, draft an original article. "
            "The article should:\n"
            "- Have a compelling headline\n"
            "- Synthesize the key ideas into a coherent narrative\n"
            "- Add context and analysis\n"
            "- Be well-structured with clear sections\n"
            "- Be roughly 500-800 words\n"
            f"{f'Article direction: {extra}' if extra else ''}"
        )
    elif command == 'code':
        return (
            f"{header}\n\n"
            "Analyze this content from a software engineering perspective:\n"
            "1. Identify any technical concepts, tools, or frameworks mentioned\n"
            "2. Suggest code implementations or projects inspired by the content\n"
            "3. If code snippets are present, explain and improve them\n"
            "4. Propose automation or tooling ideas based on the content\n"
            f"{f'Focus area: {extra}' if extra else ''}"
        )

    return content  # fallback


async def process_with_gemini(prompt: str) -> str:
    """Send prompt to Gemini and return the response text."""
    response = await discord.utils.maybe_coroutine(
        model.generate_content, prompt
    )
    return response.text


async def send_long_message(channel, text: str):
    """Send a message, splitting into chunks if over Discord's 2000 char limit."""
    if len(text) <= 2000:
        await channel.send(text)
        return

    # Try to split on newlines near the limit
    chunks = []
    while text:
        if len(text) <= 2000:
            chunks.append(text)
            break
        # Find a good split point
        split_at = text.rfind('\n', 0, 2000)
        if split_at == -1 or split_at < 1000:
            split_at = 2000
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip('\n')

    for chunk in chunks:
        await channel.send(chunk)


@client.event
async def on_ready():
    print(f'Link Agent logged in as {client.user}')
    print(f'Gemini API ready | Watching for URLs...')


@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if not message.content.strip():
        return

    text = message.content.strip()

    # Handle !help
    if text.lower() == '!help':
        await message.channel.send(HELP_TEXT)
        return

    # Handle !status
    if text.lower() == '!status':
        ctx = channel_context.get(message.channel.id)
        if ctx:
            title_display = ctx['title'] or '(no title)'
            content_len = len(ctx['content'])
            await message.channel.send(
                f"**Cached content for this channel:**\n"
                f"URL: {ctx['url']}\n"
                f"Title: {title_display}\n"
                f"Content length: {content_len:,} characters"
            )
        else:
            await message.channel.send("No cached content for this channel yet. Share a URL to get started.")
        return

    command, url, extra = extract_command_and_url(text)

    # If there's a URL, fetch and process it
    if url:
        print(f'[{message.author}] {command} -> {url}')

        async with message.channel.typing():
            # Fetch content
            content_data = await fetch_url(url)

            if content_data.get('error'):
                await message.channel.send(
                    f"Could not fetch content from <{url}>:\n{content_data['content']}"
                )
                return

            if not content_data['content'].strip():
                await message.channel.send(
                    f"Fetched <{url}> but couldn't extract meaningful text content. "
                    f"The page may require JavaScript or authentication."
                )
                return

            # Cache the content for follow-ups
            channel_context[message.channel.id] = content_data

            # For !extract, just show the raw content
            if command == 'extract':
                title = content_data['title'] or '(no title)'
                response_text = (
                    f"**Extracted from:** {url}\n"
                    f"**Title:** {title}\n"
                    f"**Content length:** {len(content_data['content']):,} chars\n\n"
                    f"{content_data['content'][:3500]}"
                )
                if len(content_data['content']) > 3500:
                    response_text += "\n\n*[Truncated for display — full content cached for follow-up questions]*"
                await send_long_message(message.channel, response_text)
                return

            # Process with Gemini
            prompt = build_prompt(command, content_data, extra)
            try:
                result = await process_with_gemini(prompt)
                header = f"**{command.title()}** — {content_data['title'] or url}\n\n"
                await send_long_message(message.channel, header + result)
            except Exception as e:
                await message.channel.send(f"Gemini error: {e}")
                print(f'Gemini error: {e}')
        return

    # No URL found — check if this is a follow-up question using cached content
    ctx = channel_context.get(message.channel.id)
    if ctx and command is None:
        print(f'[{message.author}] Follow-up question on {ctx["url"]}')
        async with message.channel.typing():
            prompt = (
                f"Previously extracted content from {ctx['url']}:\n"
                f"Title: {ctx['title']}\n\n"
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
                print(f'Gemini error: {e}')
        return

    # No URL and no cached context — pass through to Gemini as general chat
    print(f'[{message.author}] General chat: {text[:80]}')
    async with message.channel.typing():
        try:
            result = await process_with_gemini(text)
            await send_long_message(message.channel, result)
        except Exception as e:
            await message.channel.send(f"Gemini error: {e}")
            print(f'Gemini error: {e}')


client.run(os.getenv('TOKEN'))
