"""
Generic Company Career Page Scraper
Fallback when LinkedIn scraping fails
"""

import requests
from bs4 import BeautifulSoup
import logging
from typing import Dict, Optional, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CompanyScraper:
    """Generic scraper for company career pages"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        })

    def search_company_info(self, company_name: str) -> Optional[Dict]:
        """
        Search for basic company information

        Args:
            company_name: Company name to search

        Returns:
            Dictionary with company info or None
        """
        try:
            logger.info(f"Searching company info for: {company_name}")

            # For MVP, we'll return a structured response
            # In production, you'd integrate with APIs like Clearbit, Google Custom Search, etc.

            return {
                'company_name': company_name,
                'status': 'info_limited',
                'message': f"For detailed job information about {company_name}, please provide a specific LinkedIn job URL.",
                'suggestions': [
                    f"Search LinkedIn for '{company_name} jobs'",
                    f"Visit {company_name.lower().replace(' ', '')}.com/careers",
                    "Use the !linkedin <url> command with a specific job posting"
                ]
            }

        except Exception as e:
            logger.error(f"Error searching company info: {e}")
            return None

    def scrape_careers_page(self, url: str) -> Optional[Dict]:
        """
        Scrape a company careers page

        Args:
            url: URL of the careers page

        Returns:
            Dictionary with careers page info
        """
        try:
            logger.info(f"Scraping careers page: {url}")

            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract basic information
            return {
                'url': url,
                'title': soup.find('title').get_text(strip=True) if soup.find('title') else 'Unknown',
                'content_preview': self._get_text_preview(soup),
            }

        except Exception as e:
            logger.error(f"Error scraping careers page: {e}")
            return None

    def _get_text_preview(self, soup: BeautifulSoup, max_length: int = 500) -> str:
        """Get a preview of page text content"""
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        text = soup.get_text(separator=' ', strip=True)
        text = ' '.join(text.split())  # Normalize whitespace

        if len(text) > max_length:
            return text[:max_length] + '...'
        return text
