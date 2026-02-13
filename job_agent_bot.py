"""
Discord Job Agent Bot - MVP
Analyzes job postings from LinkedIn and provides AI-powered insights
"""

from dotenv import load_dotenv
import os
import discord
from discord.ext import commands
import logging
import asyncio
import re

from scrapers import LinkedInScraper, CompanyScraper
from utils import JobAnalyzer, DiscordFormatter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Verify required environment variables
DISCORD_TOKEN = os.getenv('TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN not found in environment variables")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")

# Initialize bot with command prefix
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# Initialize scrapers and analyzers
linkedin_scraper = LinkedInScraper()
company_scraper = CompanyScraper()
job_analyzer = JobAnalyzer(GEMINI_API_KEY)
formatter = DiscordFormatter()


@bot.event
async def on_ready():
    """Called when the bot is ready"""
    logger.info(f'✅ Logged in as {bot.user.name} (ID: {bot.user.id})')
    logger.info(f'✅ Connected to {len(bot.guilds)} server(s)')
    logger.info('✅ Job Agent Bot is ready!')

    # Set bot status
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="for !help | Job postings"
        )
    )


@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(
            "❌ Unknown command! Use `!help` to see available commands.",
            delete_after=10
        )
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            f"❌ Missing required argument: `{error.param.name}`. Use `!help` for usage examples.",
            delete_after=10
        )
    else:
        logger.error(f"Command error: {error}")
        await ctx.send(
            "❌ An error occurred while processing your command. Please try again.",
            delete_after=10
        )


@bot.command(name='help')
async def help_command(ctx):
    """Show help message"""
    embed = formatter.create_help_embed()
    await ctx.send(embed=embed)


@bot.command(name='linkedin', aliases=['li', 'link'])
async def linkedin_command(ctx, url: str = None):
    """
    Analyze a LinkedIn job posting

    Usage: !linkedin <url>
    Example: !linkedin https://www.linkedin.com/jobs/view/1234567890
    """
    if not url:
        await ctx.send(
            "❌ Please provide a LinkedIn job URL.\nUsage: `!linkedin <url>`",
            delete_after=15
        )
        return

    # Validate URL
    if 'linkedin.com/jobs' not in url:
        await ctx.send(
            "❌ Please provide a valid LinkedIn job URL (must contain 'linkedin.com/jobs')",
            delete_after=15
        )
        return

    # Send processing message
    processing_msg = await ctx.send("🔍 Scraping LinkedIn job posting...")

    try:
        # Show typing indicator
        async with ctx.typing():
            # Scrape the job
            job_data = await asyncio.to_thread(linkedin_scraper.scrape_job, url)

            if not job_data:
                await processing_msg.edit(content="❌ Failed to scrape job posting. The URL might be invalid or LinkedIn is blocking requests.")
                return

            await processing_msg.edit(content="🤖 Analyzing job with AI...")

            # Analyze with AI
            analysis = await asyncio.to_thread(job_analyzer.analyze_job, job_data)

            await processing_msg.delete()

            # Send job overview embed
            job_embed = formatter.create_job_embed(job_data, analysis)
            await ctx.send(embed=job_embed)

            # Send detailed analysis in a separate embed
            if analysis and not analysis.get('error'):
                analysis_embed = formatter.create_analysis_embed(analysis)
                await ctx.send(embed=analysis_embed)
            else:
                # Send description as fallback
                description = job_data.get('description', 'No description available')
                chunks = formatter.split_message(f"**Job Description:**\n{description}")

                for chunk in chunks[:2]:  # Limit to 2 chunks for MVP
                    await ctx.send(chunk)

    except Exception as e:
        logger.error(f"Error in linkedin command: {e}")
        await processing_msg.edit(
            content=f"❌ An error occurred: {str(e)}\nPlease try again or use a different URL."
        )


@bot.command(name='job', aliases=['jobs', 'company'])
async def job_command(ctx, *, company_name: str = None):
    """
    Search for jobs at a company

    Usage: !job <company name>
    Example: !job Google
    """
    if not company_name:
        await ctx.send(
            "❌ Please provide a company name.\nUsage: `!job <company name>`",
            delete_after=15
        )
        return

    # Send processing message
    processing_msg = await ctx.send(f"🔍 Searching for jobs at {company_name}...")

    try:
        async with ctx.typing():
            # Search for jobs
            jobs = await asyncio.to_thread(
                linkedin_scraper.search_company_jobs,
                company_name,
                limit=5
            )

            await processing_msg.delete()

            if not jobs:
                # Fallback to company scraper for suggestions
                company_info = await asyncio.to_thread(
                    company_scraper.search_company_info,
                    company_name
                )

                embed = discord.Embed(
                    title=f"🔍 Jobs at {company_name}",
                    description=f"No jobs found via automated search.\n\n**Suggestions:**",
                    color=discord.Color.orange()
                )

                if company_info and company_info.get('suggestions'):
                    suggestions = '\n'.join([f"• {s}" for s in company_info['suggestions']])
                    embed.add_field(name="Try these:", value=suggestions, inline=False)

                await ctx.send(embed=embed)
                return

            # Send job list embed
            jobs_embed = formatter.create_job_list_embed(jobs, company_name)
            await ctx.send(embed=jobs_embed)

            # Optionally send a note about detailed analysis
            await ctx.send(
                "💡 **Tip:** Use `!linkedin <url>` with a specific job link for detailed AI analysis!",
                delete_after=30
            )

    except Exception as e:
        logger.error(f"Error in job command: {e}")
        await processing_msg.edit(
            content=f"❌ An error occurred while searching: {str(e)}"
        )


@bot.command(name='ping')
async def ping_command(ctx):
    """Check if bot is responsive"""
    latency = round(bot.latency * 1000)
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Bot is online and responsive.\nLatency: {latency}ms",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)


@bot.command(name='about', aliases=['info'])
async def about_command(ctx):
    """Show information about the bot"""
    embed = discord.Embed(
        title="🤖 Job Agent Bot",
        description="AI-powered job posting analyzer running on your Linux box",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="Features",
        value="• Scrape LinkedIn job postings\n• AI-powered analysis with Gemini\n• Company job search\n• Detailed insights and recommendations",
        inline=False
    )

    embed.add_field(
        name="Technology Stack",
        value="• Python 3.x\n• Discord.py\n• Google Gemini AI\n• BeautifulSoup4\n• Requests",
        inline=False
    )

    embed.add_field(
        name="Commands",
        value="Use `!help` to see all available commands",
        inline=False
    )

    embed.set_footer(text=f"Running on {len(bot.guilds)} server(s)")

    await ctx.send(embed=embed)


@bot.event
async def on_message(message):
    """
    Handle messages
    Automatically detect LinkedIn URLs in messages
    """
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return

    # Process commands first
    await bot.process_commands(message)

    # Auto-detect LinkedIn URLs in messages (if not a command)
    if not message.content.startswith('!'):
        linkedin_url_pattern = r'https?://(?:www\.)?linkedin\.com/jobs/view/\d+'
        urls = re.findall(linkedin_url_pattern, message.content)

        if urls:
            # Only process the first URL found
            url = urls[0]
            await message.channel.send(
                f"👀 Detected LinkedIn job URL! Analyzing...\n💡 Tip: Use `!linkedin {url}` for explicit commands"
            )

            # Create a mock context to reuse linkedin_command logic
            ctx = await bot.get_context(message)
            await linkedin_command(ctx, url)


def main():
    """Main entry point"""
    try:
        logger.info("🚀 Starting Job Agent Bot...")
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        raise


if __name__ == '__main__':
    main()
