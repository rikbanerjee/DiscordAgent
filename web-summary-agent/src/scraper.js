import puppeteer from 'puppeteer-core';

const DEFAULT_TIMEOUT = 30_000;
const USER_AGENT =
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36';

/** Resolve a Chrome/Chromium executable path. */
function getChromePath() {
  if (process.env.CHROME_PATH) return process.env.CHROME_PATH;

  const candidates = [
    '/usr/bin/google-chrome-stable',
    '/usr/bin/google-chrome',
    '/usr/bin/chromium-browser',
    '/usr/bin/chromium',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
  ];

  // In practice we rely on CHROME_PATH; the fallback list is a convenience.
  return candidates[0];
}

/**
 * Launch a headless Chromium browser, navigate to `url`, and return the
 * extracted page content tailored to the site type.
 *
 * Returns { title, content, url, siteName }
 */
export async function scrapePage(url) {
  const browser = await puppeteer.launch({
    executablePath: getChromePath(),
    headless: true,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-gpu',
      '--disable-extensions',
      '--disable-background-networking',
      '--disable-sync',
      '--no-first-run',
    ],
  });

  try {
    const page = await browser.newPage();
    await page.setUserAgent(USER_AGENT);
    await page.setViewport({ width: 1280, height: 900 });

    // Block images, fonts, and media to speed up loading
    await page.setRequestInterception(true);
    page.on('request', (req) => {
      const type = req.resourceType();
      if (['image', 'font', 'media', 'stylesheet'].includes(type)) {
        req.abort();
      } else {
        req.continue();
      }
    });

    await page.goto(url, {
      waitUntil: 'networkidle2',
      timeout: DEFAULT_TIMEOUT,
    });

    // Determine which extraction strategy to use
    const hostname = new URL(url).hostname.replace('www.', '');

    let result;
    if (hostname.includes('reddit.com')) {
      result = await extractReddit(page, url);
    } else if (hostname.includes('substack.com') || hostname.includes('.substack.')) {
      result = await extractSubstack(page, url);
    } else if (hostname.includes('twitter.com') || hostname.includes('x.com')) {
      result = await extractTwitter(page, url);
    } else if (hostname.includes('medium.com')) {
      result = await extractMedium(page, url);
    } else if (hostname.includes('news.ycombinator.com')) {
      result = await extractHackerNews(page, url);
    } else if (hostname.includes('github.com')) {
      result = await extractGitHub(page, url);
    } else {
      result = await extractGeneric(page, url);
    }

    return result;
  } finally {
    await browser.close();
  }
}

// ---------------------------------------------------------------------------
// Site-specific extractors
// ---------------------------------------------------------------------------

async function extractReddit(page, url) {
  // Wait for content to render (old or new Reddit)
  await page.waitForSelector(
    'shreddit-post, .Post, .thing, [data-testid="post-container"], .expando',
    { timeout: 10_000 }
  ).catch(() => {});

  return page.evaluate(() => {
    const title =
      document.querySelector('h1')?.innerText ||
      document.querySelector('[data-testid="post-title"]')?.innerText ||
      document.querySelector('.title a')?.innerText ||
      document.title;

    // Post body (self-text)
    const postBody =
      document.querySelector('[data-testid="post-content"]')?.innerText ||
      document.querySelector('.expando .md')?.innerText ||
      document.querySelector('[slot="text-body"]')?.innerText ||
      '';

    // Collect top comments
    const commentEls = document.querySelectorAll(
      'shreddit-comment [slot="comment"], .Comment .RichTextJSON-root, .comment .md'
    );
    const comments = [];
    for (const el of commentEls) {
      const text = el.innerText?.trim();
      if (text && text.length > 10) comments.push(text);
      if (comments.length >= 15) break;
    }

    const subreddit =
      document.querySelector('[data-testid="subreddit-name"]')?.innerText ||
      document.querySelector('.subreddit')?.innerText ||
      '';

    let content = '';
    if (postBody) content += `Post:\n${postBody}\n\n`;
    if (comments.length) content += `Top Comments:\n${comments.map((c, i) => `${i + 1}. ${c}`).join('\n\n')}`;

    return {
      title,
      content: content || document.body.innerText.slice(0, 12000),
      url: window.location.href,
      siteName: `Reddit${subreddit ? ' – ' + subreddit : ''}`,
    };
  });
}

async function extractSubstack(page, url) {
  await page.waitForSelector('.post-content, .body, article', { timeout: 10_000 }).catch(() => {});

  return page.evaluate(() => {
    const title =
      document.querySelector('h1.post-title')?.innerText ||
      document.querySelector('h1')?.innerText ||
      document.title;

    const subtitle =
      document.querySelector('h3.subtitle')?.innerText ||
      document.querySelector('.subtitle')?.innerText ||
      '';

    const author =
      document.querySelector('.author-name')?.innerText ||
      document.querySelector('[data-testid="authoring-info"] a')?.innerText ||
      '';

    const body =
      document.querySelector('.post-content')?.innerText ||
      document.querySelector('.body.markup')?.innerText ||
      document.querySelector('article')?.innerText ||
      document.body.innerText.slice(0, 12000);

    let content = '';
    if (subtitle) content += `Subtitle: ${subtitle}\n`;
    if (author) content += `Author: ${author}\n\n`;
    content += body;

    return {
      title,
      content,
      url: window.location.href,
      siteName: 'Substack',
    };
  });
}

async function extractTwitter(page, url) {
  await page.waitForSelector('[data-testid="tweetText"]', { timeout: 10_000 }).catch(() => {});

  return page.evaluate(() => {
    const tweets = document.querySelectorAll('[data-testid="tweetText"]');
    const texts = [];
    for (const t of tweets) {
      const text = t.innerText?.trim();
      if (text) texts.push(text);
      if (texts.length >= 20) break;
    }

    const author =
      document.querySelector('[data-testid="User-Name"]')?.innerText || '';

    const title = author ? `Tweet by ${author}` : document.title;

    return {
      title,
      content: texts.join('\n\n---\n\n') || document.body.innerText.slice(0, 12000),
      url: window.location.href,
      siteName: 'X / Twitter',
    };
  });
}

async function extractMedium(page, url) {
  await page.waitForSelector('article', { timeout: 10_000 }).catch(() => {});

  return page.evaluate(() => {
    const title =
      document.querySelector('h1')?.innerText || document.title;

    const article =
      document.querySelector('article')?.innerText ||
      document.body.innerText.slice(0, 12000);

    const author =
      document.querySelector('[data-testid="authorName"]')?.innerText ||
      document.querySelector('a[rel="author"]')?.innerText ||
      '';

    let content = '';
    if (author) content += `Author: ${author}\n\n`;
    content += article;

    return {
      title,
      content,
      url: window.location.href,
      siteName: 'Medium',
    };
  });
}

async function extractHackerNews(page, url) {
  return page.evaluate(() => {
    const title =
      document.querySelector('.titleline a')?.innerText || document.title;

    const storyUrl = document.querySelector('.titleline a')?.href || '';

    const commentEls = document.querySelectorAll('.commtext');
    const comments = [];
    for (const el of commentEls) {
      const text = el.innerText?.trim();
      if (text && text.length > 10) comments.push(text);
      if (comments.length >= 20) break;
    }

    let content = `Story: ${title}\n`;
    if (storyUrl) content += `Link: ${storyUrl}\n\n`;
    if (comments.length) {
      content += `Top Comments:\n${comments.map((c, i) => `${i + 1}. ${c}`).join('\n\n')}`;
    }

    return {
      title,
      content: content || document.body.innerText.slice(0, 12000),
      url: window.location.href,
      siteName: 'Hacker News',
    };
  });
}

async function extractGitHub(page, url) {
  await page.waitForSelector('.markdown-body, .repository-content, .Box-body', {
    timeout: 10_000,
  }).catch(() => {});

  return page.evaluate(() => {
    const title = document.title;

    // README content
    const readme =
      document.querySelector('#readme .markdown-body')?.innerText || '';

    // Repo description
    const description =
      document.querySelector('[itemprop="about"]')?.innerText ||
      document.querySelector('.f4.my-3')?.innerText ||
      '';

    // Issue or PR body
    const issueBody =
      document.querySelector('.js-comment-body')?.innerText || '';

    let content = '';
    if (description) content += `Description: ${description}\n\n`;
    if (issueBody) content += `Body:\n${issueBody}\n\n`;
    if (readme) content += `README:\n${readme}`;

    return {
      title,
      content: content || document.body.innerText.slice(0, 12000),
      url: window.location.href,
      siteName: 'GitHub',
    };
  });
}

async function extractGeneric(page, url) {
  // Try to identify article content using common selectors, fall back to body
  return page.evaluate(() => {
    const title = document.title;

    // Try article / main content selectors first
    const selectors = [
      'article',
      '[role="main"]',
      'main',
      '.post-content',
      '.entry-content',
      '.article-body',
      '.story-body',
      '#content',
      '.content',
    ];

    let body = '';
    for (const sel of selectors) {
      const el = document.querySelector(sel);
      if (el && el.innerText.length > 200) {
        body = el.innerText;
        break;
      }
    }

    if (!body) {
      // Remove nav, header, footer, sidebar noise
      const clone = document.body.cloneNode(true);
      for (const tag of clone.querySelectorAll(
        'nav, header, footer, aside, .sidebar, .nav, .menu, .ad, .advertisement, script, style, noscript'
      )) {
        tag.remove();
      }
      body = clone.innerText;
    }

    // Get meta description as supplementary info
    const metaDesc =
      document.querySelector('meta[name="description"]')?.content ||
      document.querySelector('meta[property="og:description"]')?.content ||
      '';

    const siteName =
      document.querySelector('meta[property="og:site_name"]')?.content || '';

    let content = '';
    if (metaDesc) content += `Description: ${metaDesc}\n\n`;
    content += body;

    return {
      title,
      content: content.slice(0, 15000),
      url: window.location.href,
      siteName: siteName || new URL(window.location.href).hostname,
    };
  });
}
