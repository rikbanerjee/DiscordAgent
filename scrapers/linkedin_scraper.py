"""
LinkedIn Job Scraper
Uses requests and BeautifulSoup for MVP - no authentication required
"""

import requests
from bs4 import BeautifulSoup
import re
import time
from typing import Dict, Optional, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LinkedInScraper:
    """Scraper for LinkedIn job postings"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Connection': 'keep-alive',
        })

    def extract_job_id(self, url: str) -> Optional[str]:
        """Extract job ID from LinkedIn URL"""
        patterns = [
            r'linkedin\.com/jobs/view/(\d+)',
            r'currentJobId=(\d+)',
            r'jobs-(\d+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def scrape_job(self, url: str) -> Optional[Dict]:
        """
        Scrape a LinkedIn job posting

        Args:
            url: LinkedIn job URL

        Returns:
            Dictionary with job details or None if failed
        """
        try:
            logger.info(f"Scraping LinkedIn job: {url}")

            # Add delay to be respectful
            time.sleep(2)

            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract job details
            job_data = {
                'url': url,
                'title': self._extract_title(soup),
                'company': self._extract_company(soup),
                'location': self._extract_location(soup),
                'description': self._extract_description(soup),
                'employment_type': self._extract_employment_type(soup),
                'seniority_level': self._extract_seniority(soup),
                'industries': self._extract_industries(soup),
            }

            logger.info(f"Successfully scraped: {job_data.get('title', 'Unknown')}")
            return job_data

        except requests.RequestException as e:
            logger.error(f"Error scraping LinkedIn job: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract job title"""
        selectors = [
            ('h1', {'class': re.compile(r'top-card-layout__title')}),
            ('h1', {'class': re.compile(r'topcard__title')}),
            ('h2', {'class': re.compile(r'top-card-layout__title')}),
        ]

        for tag, attrs in selectors:
            element = soup.find(tag, attrs)
            if element:
                return element.get_text(strip=True)

        # Fallback: try to find in meta tags
        meta_title = soup.find('meta', property='og:title')
        if meta_title:
            return meta_title.get('content', 'Unknown Title')

        return 'Unknown Title'

    def _extract_company(self, soup: BeautifulSoup) -> str:
        """Extract company name"""
        selectors = [
            ('a', {'class': re.compile(r'topcard__org-name-link')}),
            ('span', {'class': re.compile(r'topcard__flavor')}),
            ('div', {'class': re.compile(r'top-card-layout__card')}),
        ]

        for tag, attrs in selectors:
            element = soup.find(tag, attrs)
            if element:
                text = element.get_text(strip=True)
                # Clean up text
                text = re.sub(r'\s+', ' ', text)
                if text and len(text) > 0:
                    return text

        return 'Unknown Company'

    def _extract_location(self, soup: BeautifulSoup) -> str:
        """Extract job location"""
        selectors = [
            ('span', {'class': re.compile(r'topcard__flavor--bullet')}),
            ('span', {'class': re.compile(r'top-card-layout__location')}),
        ]

        for tag, attrs in selectors:
            element = soup.find(tag, attrs)
            if element:
                return element.get_text(strip=True)

        return 'Unknown Location'

    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract job description"""
        selectors = [
            ('div', {'class': re.compile(r'show-more-less-html__markup')}),
            ('div', {'class': re.compile(r'description__text')}),
            ('section', {'class': re.compile(r'description')}),
        ]

        for tag, attrs in selectors:
            element = soup.find(tag, attrs)
            if element:
                # Get text and clean it up
                text = element.get_text(separator='\n', strip=True)
                # Remove extra whitespace
                text = re.sub(r'\n\s*\n', '\n\n', text)
                return text

        return 'Description not available'

    def _extract_employment_type(self, soup: BeautifulSoup) -> str:
        """Extract employment type (Full-time, Part-time, etc.)"""
        criteria_list = soup.find('ul', {'class': re.compile(r'description__job-criteria-list')})
        if criteria_list:
            items = criteria_list.find_all('li')
            for item in items:
                header = item.find('h3')
                if header and 'Employment type' in header.get_text():
                    value = item.find('span')
                    if value:
                        return value.get_text(strip=True)
        return 'Not specified'

    def _extract_seniority(self, soup: BeautifulSoup) -> str:
        """Extract seniority level"""
        criteria_list = soup.find('ul', {'class': re.compile(r'description__job-criteria-list')})
        if criteria_list:
            items = criteria_list.find_all('li')
            for item in items:
                header = item.find('h3')
                if header and 'Seniority level' in header.get_text():
                    value = item.find('span')
                    if value:
                        return value.get_text(strip=True)
        return 'Not specified'

    def _extract_industries(self, soup: BeautifulSoup) -> str:
        """Extract industries"""
        criteria_list = soup.find('ul', {'class': re.compile(r'description__job-criteria-list')})
        if criteria_list:
            items = criteria_list.find_all('li')
            for item in items:
                header = item.find('h3')
                if header and 'Industries' in header.get_text():
                    value = item.find('span')
                    if value:
                        return value.get_text(strip=True)
        return 'Not specified'

    def search_company_jobs(self, company_name: str, limit: int = 5) -> List[Dict]:
        """
        Search for jobs at a specific company

        Args:
            company_name: Company name to search for
            limit: Maximum number of jobs to return

        Returns:
            List of job dictionaries
        """
        try:
            logger.info(f"Searching jobs for company: {company_name}")

            # Create search URL
            search_url = f"https://www.linkedin.com/jobs/search/?keywords={company_name.replace(' ', '%20')}"

            time.sleep(2)
            response = self.session.get(search_url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find job cards
            job_cards = soup.find_all('div', {'class': re.compile(r'base-card')}, limit=limit)

            jobs = []
            for card in job_cards:
                try:
                    title_elem = card.find('h3', {'class': re.compile(r'base-search-card__title')})
                    company_elem = card.find('h4', {'class': re.compile(r'base-search-card__subtitle')})
                    location_elem = card.find('span', {'class': re.compile(r'job-search-card__location')})
                    link_elem = card.find('a', {'class': re.compile(r'base-card__full-link')})

                    if title_elem and link_elem:
                        jobs.append({
                            'title': title_elem.get_text(strip=True),
                            'company': company_elem.get_text(strip=True) if company_elem else company_name,
                            'location': location_elem.get_text(strip=True) if location_elem else 'Unknown',
                            'url': link_elem.get('href'),
                        })
                except Exception as e:
                    logger.warning(f"Error parsing job card: {e}")
                    continue

            logger.info(f"Found {len(jobs)} jobs for {company_name}")
            return jobs

        except Exception as e:
            logger.error(f"Error searching company jobs: {e}")
            return []
