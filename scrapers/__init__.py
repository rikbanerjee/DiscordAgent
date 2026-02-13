"""
Scrapers package for job information extraction
"""

from .linkedin_scraper import LinkedInScraper
from .company_scraper import CompanyScraper

__all__ = ['LinkedInScraper', 'CompanyScraper']
