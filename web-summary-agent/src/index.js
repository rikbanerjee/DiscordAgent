import 'dotenv/config';
import { createBot } from './bot.js';
import { initSummarizer } from './summarizer.js';

// ---------------------------------------------------------------------------
// Validate required environment variables
// ---------------------------------------------------------------------------
const required = ['DISCORD_TOKEN', 'GEMINI_API_KEY'];
const missing = required.filter((k) => !process.env[k]);
if (missing.length) {
  console.error(`Missing required environment variables: ${missing.join(', ')}`);
  console.error('Copy .env.example to .env and fill in the values.');
  process.exit(1);
}

// ---------------------------------------------------------------------------
// Bootstrap
// ---------------------------------------------------------------------------
initSummarizer(process.env.GEMINI_API_KEY);

const bot = createBot();

bot.login(process.env.DISCORD_TOKEN).catch((err) => {
  console.error('Failed to login to Discord:', err.message);
  process.exit(1);
});

// Graceful shutdown
for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => {
    console.log(`Received ${signal}, shutting down…`);
    bot.destroy();
    process.exit(0);
  });
}
