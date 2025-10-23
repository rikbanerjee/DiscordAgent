from dotenv import load_dotenv
import os
import discord
import google.generativeai as genai


load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

# Initialize Gemini model (2.0 Flash-Lite - optimized for cost efficiency and low latency)
model = genai.GenerativeModel('gemini-2.0-flash-lite')

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    print(f'Gemini Flash API is ready!')
    

@client.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == client.user:
        return
    
    # Ignore empty messages
    if not message.content.strip():
        return
    
    print(f'Received message from {message.author}: {message.content}')
    
    try:
        # Send typing indicator while processing
        async with message.channel.typing():
            # Call Gemini API to generate response
            response = await discord.utils.maybe_coroutine(
                model.generate_content, message.content
            )
            
            # Get the response text
            reply = response.text
            
            # Discord has a 2000 character limit per message
            if len(reply) > 2000:
                # Split into multiple messages if needed
                chunks = [reply[i:i+2000] for i in range(0, len(reply), 2000)]
                for chunk in chunks:
                    await message.channel.send(chunk)
            else:
                await message.channel.send(reply)
            
            print(f'Sent response: {reply[:100]}...')
    
    except Exception as e:
        error_msg = f'Sorry, I encountered an error: {str(e)}'
        await message.channel.send(error_msg)
        print(f'Error: {e}')

client.run(os.getenv('TOKEN'))