"""
Discord message formatting utilities
"""

import discord
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DiscordFormatter:
    """Format job data for Discord messages"""

    @staticmethod
    def create_job_embed(job_data: Dict, analysis: Optional[Dict] = None) -> discord.Embed:
        """
        Create a Discord embed for a job posting

        Args:
            job_data: Raw job data
            analysis: AI analysis results (optional)

        Returns:
            discord.Embed object
        """
        # Determine embed color based on seniority
        color_map = {
            'entry level': discord.Color.green(),
            'associate': discord.Color.blue(),
            'mid-senior level': discord.Color.purple(),
            'director': discord.Color.orange(),
            'executive': discord.Color.red(),
        }

        seniority = job_data.get('seniority_level', 'Not specified').lower()
        embed_color = color_map.get(seniority, discord.Color.blue())

        # Create embed
        embed = discord.Embed(
            title=job_data.get('title', 'Unknown Title'),
            url=job_data.get('url', ''),
            description=f"**{job_data.get('company', 'Unknown Company')}**",
            color=embed_color,
        )

        # Add fields
        if job_data.get('location'):
            embed.add_field(
                name="📍 Location",
                value=job_data['location'],
                inline=True
            )

        if job_data.get('employment_type'):
            embed.add_field(
                name="💼 Type",
                value=job_data['employment_type'],
                inline=True
            )

        if job_data.get('seniority_level'):
            embed.add_field(
                name="📊 Level",
                value=job_data['seniority_level'],
                inline=True
            )

        if job_data.get('industries'):
            embed.add_field(
                name="🏢 Industry",
                value=job_data['industries'],
                inline=False
            )

        # Add analysis summary if available
        if analysis and not analysis.get('error'):
            summary = analysis.get('summary', '')
            if summary:
                # Truncate if too long
                if len(summary) > 300:
                    summary = summary[:297] + '...'
                embed.add_field(
                    name="🤖 AI Quick Summary",
                    value=summary,
                    inline=False
                )

        # Add footer
        embed.set_footer(text="💡 Use reactions to navigate • Powered by Gemini AI")

        return embed

    @staticmethod
    def create_analysis_embed(analysis: Dict) -> discord.Embed:
        """
        Create a detailed analysis embed

        Args:
            analysis: AI analysis results

        Returns:
            discord.Embed object
        """
        if analysis.get('error'):
            embed = discord.Embed(
                title="⚠️ Analysis Error",
                description=f"Could not complete analysis: {analysis['error']}",
                color=discord.Color.red()
            )
            return embed

        # Create main analysis embed
        embed = discord.Embed(
            title="📊 Detailed Job Analysis",
            color=discord.Color.gold()
        )

        # The full analysis is in markdown format
        full_analysis = analysis.get('full_analysis', 'No analysis available')

        # Split analysis into chunks for Discord's field limits
        sections = DiscordFormatter._split_analysis(full_analysis)

        for i, section in enumerate(sections[:5]):  # Limit to 5 sections
            # Extract section title and content
            lines = section.split('\n', 1)
            title = lines[0].replace('#', '').strip()
            content = lines[1] if len(lines) > 1 else section

            # Truncate if needed (Discord field value limit is 1024 chars)
            if len(content) > 1024:
                content = content[:1021] + '...'

            embed.add_field(
                name=title,
                value=content,
                inline=False
            )

        embed.set_footer(text="💡 AI-generated analysis • Results may vary")

        return embed

    @staticmethod
    def _split_analysis(text: str) -> List[str]:
        """Split analysis text into sections based on headers"""
        import re

        # Split by markdown headers (## or **)
        sections = re.split(r'\n(?=#{1,2}\s|\*\*[A-Z])', text)

        # Clean up sections
        cleaned_sections = []
        for section in sections:
            section = section.strip()
            if section and len(section) > 10:
                cleaned_sections.append(section)

        return cleaned_sections

    @staticmethod
    def create_error_embed(error_message: str) -> discord.Embed:
        """Create an error message embed"""
        embed = discord.Embed(
            title="❌ Error",
            description=error_message,
            color=discord.Color.red()
        )
        return embed

    @staticmethod
    def create_help_embed() -> discord.Embed:
        """Create a help message embed"""
        embed = discord.Embed(
            title="🤖 Job Agent Commands",
            description="I help you analyze job postings and company information!",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="!linkedin <url>",
            value="Analyze a LinkedIn job posting\nExample: `!linkedin https://linkedin.com/jobs/view/123456`",
            inline=False
        )

        embed.add_field(
            name="!job <company>",
            value="Search for jobs at a company\nExample: `!job Google`",
            inline=False
        )

        embed.add_field(
            name="!help",
            value="Show this help message",
            inline=False
        )

        embed.add_field(
            name="💡 Tips",
            value="• Paste LinkedIn job URLs directly\n• For best results, use specific job posting links\n• Analysis takes 5-10 seconds",
            inline=False
        )

        embed.set_footer(text="Powered by Gemini AI • Running on your Linux box")

        return embed

    @staticmethod
    def create_job_list_embed(jobs: List[Dict], company: str = None) -> discord.Embed:
        """Create an embed listing multiple jobs"""
        embed = discord.Embed(
            title=f"🔍 Jobs at {company}" if company else "🔍 Job Search Results",
            color=discord.Color.blue()
        )

        if not jobs:
            embed.description = "No jobs found. Try a different search!"
            return embed

        for i, job in enumerate(jobs[:10], 1):  # Limit to 10 jobs
            title = job.get('title', 'Unknown')
            company_name = job.get('company', 'Unknown')
            location = job.get('location', 'Unknown')
            url = job.get('url', '')

            # Create clickable link if URL available
            if url:
                value = f"**{company_name}** • {location}\n[View Job]({url})"
            else:
                value = f"**{company_name}** • {location}"

            embed.add_field(
                name=f"{i}. {title}",
                value=value,
                inline=False
            )

        embed.set_footer(text=f"Showing {len(jobs)} results • Click links to view details")

        return embed

    @staticmethod
    def split_message(text: str, max_length: int = 2000) -> List[str]:
        """
        Split a long message into Discord-compatible chunks

        Args:
            text: Text to split
            max_length: Maximum length per chunk (default 2000 for Discord)

        Returns:
            List of text chunks
        """
        if len(text) <= max_length:
            return [text]

        chunks = []
        current_chunk = ""

        # Split by paragraphs first
        paragraphs = text.split('\n\n')

        for para in paragraphs:
            if len(current_chunk) + len(para) + 2 <= max_length:
                current_chunk += para + '\n\n'
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + '\n\n'

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks
