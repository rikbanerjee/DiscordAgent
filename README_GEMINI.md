# Discord Bot with Gemini Flash API

A Discord bot that uses Google's Gemini Flash 1.5 API to answer questions and respond to messages.

## Features

- 🤖 **AI-Powered Responses** - Uses Gemini Flash 2.0 Lite to generate intelligent responses
- 💬 **Natural Conversation** - Responds to all messages in channels the bot can access
- ⚡ **Fast Processing** - Shows typing indicator while generating responses
- 📝 **Long Responses** - Automatically splits responses over 2000 characters

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
python discord_only_gemini.py
```

## How It Works

1. Bot receives a message in Discord
2. Message is sent to Gemini Flash API
3. Gemini generates a response
4. Bot sends the response back to Discord

## Usage

Simply send any message in a channel where the bot is present, and it will respond using Gemini!

**Example:**
```
User: What is the capital of France?
Bot: The capital of France is Paris.

User: Explain quantum computing in simple terms
Bot: [Gemini's detailed explanation...]
```

## Notes

- The bot will respond to ALL messages in channels it can access (except its own)
- Responses longer than 2000 characters are automatically split into multiple messages
- The bot shows a "typing..." indicator while processing
- All interactions are logged to the console

## Troubleshooting

**ImportError: No module named 'google.generativeai'**
- Run: `pip install google-generativeai`

**API Key Error:**
- Verify your `GEMINI_API_KEY` is set correctly in `.env`
- Make sure your API key is valid and active

**Bot not responding:**
- Check that "Message Content Intent" is enabled in Discord Developer Portal
- Verify bot has permissions to read and send messages in the channel

## Security

⚠️ **Never commit your `.env` file to version control!**
- Add `.env` to your `.gitignore`
- Keep your API keys secret and secure

