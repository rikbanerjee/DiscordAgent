import { Client, GatewayIntentBits, EmbedBuilder } from 'discord.js';
import { scrapePage } from './scraper.js';
import { summarize } from './summarizer.js';

// Regex that matches http(s) URLs in a message
const URL_REGEX = /https?:\/\/[^\s<>)"']+/gi;

/**
 * Create and configure the Discord bot.
 * Returns the Client instance (call client.login(token) to start).
 */
export function createBot() {
  const client = new Client({
    intents: [
      GatewayIntentBits.Guilds,
      GatewayIntentBits.GuildMessages,
      GatewayIntentBits.MessageContent,
    ],
  });

  client.once('ready', () => {
    console.log(`Logged in as ${client.user.tag}`);
    client.user.setActivity('for URLs | !summary', { type: 3 }); // "Watching for URLs"
  });

  client.on('messageCreate', async (message) => {
    // Ignore bots and DMs
    if (message.author.bot) return;
    if (!message.guild) return;

    // !help command
    if (message.content.trim() === '!help') {
      return sendHelp(message);
    }

    // !ping command
    if (message.content.trim() === '!ping') {
      return message.reply(`Pong! Latency: ${client.ws.ping}ms`);
    }

    // !summary <url> command
    if (message.content.startsWith('!summary ')) {
      const url = message.content.slice('!summary '.length).trim();
      if (!isValidUrl(url)) {
        return message.reply('Please provide a valid URL. Example: `!summary https://example.com`');
      }
      return handleUrl(message, url);
    }

    // Auto-detect: if the message contains a URL (and nothing else significant), summarize it
    if (process.env.AUTO_SUMMARIZE === 'true') {
      const urls = message.content.match(URL_REGEX);
      if (urls && urls.length === 1) {
        // Only auto-summarize if the message is mostly just a URL
        const textWithoutUrl = message.content.replace(URL_REGEX, '').trim();
        if (textWithoutUrl.length < 30) {
          return handleUrl(message, urls[0]);
        }
      }
    }
  });

  return client;
}

// ---------------------------------------------------------------------------
// Handlers
// ---------------------------------------------------------------------------

async function handleUrl(message, url) {
  let statusMsg;
  try {
    statusMsg = await message.reply('Fetching and reading page...');
    await message.channel.sendTyping();

    // Scrape
    const pageData = await scrapePage(url);

    await statusMsg.edit('Generating summary...');
    await message.channel.sendTyping();

    // Summarize
    const summaryText = await summarize(pageData);

    // Build embed
    const embed = new EmbedBuilder()
      .setTitle(truncate(pageData.title, 256))
      .setURL(pageData.url)
      .setDescription(truncate(summaryText, 4096))
      .setColor(getSiteColor(pageData.siteName))
      .setFooter({ text: `Source: ${pageData.siteName}` })
      .setTimestamp();

    await statusMsg.edit({ content: null, embeds: [embed] });
  } catch (err) {
    console.error('Error processing URL:', err);
    const errorMsg = `Failed to summarize <${url}>: ${err.message}`;
    if (statusMsg) {
      await statusMsg.edit(errorMsg).catch(() => {});
    } else {
      await message.reply(errorMsg).catch(() => {});
    }
  }
}

function sendHelp(message) {
  const embed = new EmbedBuilder()
    .setTitle('Web Summary Bot — Help')
    .setColor(0x5865f2)
    .setDescription(
      'I read web pages using a real browser and give you a summary powered by AI.'
    )
    .addFields(
      {
        name: 'Commands',
        value: [
          '`!summary <url>` — Summarize any web page',
          '`!ping` — Check bot latency',
          '`!help` — Show this message',
        ].join('\n'),
      },
      {
        name: 'Supported Sites',
        value:
          'Reddit, Substack, Medium, X/Twitter, Hacker News, GitHub, and any general web page.',
      },
      {
        name: 'Auto-Summarize',
        value:
          'When enabled (`AUTO_SUMMARIZE=true`), the bot will automatically summarize any message that is just a URL.',
      }
    )
    .setFooter({ text: 'Powered by Puppeteer + Gemini AI' });

  return message.reply({ embeds: [embed] });
}

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------

function isValidUrl(str) {
  try {
    const u = new URL(str);
    return u.protocol === 'http:' || u.protocol === 'https:';
  } catch {
    return false;
  }
}

function truncate(str, max) {
  if (!str) return '';
  return str.length > max ? str.slice(0, max - 3) + '...' : str;
}

/** Return a color based on the site name. */
function getSiteColor(siteName) {
  const name = (siteName || '').toLowerCase();
  if (name.includes('reddit')) return 0xff4500;
  if (name.includes('substack')) return 0xff6719;
  if (name.includes('twitter') || name.includes('x')) return 0x1da1f2;
  if (name.includes('medium')) return 0x00ab6c;
  if (name.includes('hacker news')) return 0xff6600;
  if (name.includes('github')) return 0x333333;
  return 0x5865f2; // Discord blurple
}
