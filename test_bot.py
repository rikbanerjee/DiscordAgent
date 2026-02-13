#!/usr/bin/env python3
"""
Test script for Job Agent Bot
Run this to verify all components are working before deployment
"""

import sys
import os
from dotenv import load_dotenv

def test_imports():
    """Test that all required packages are installed"""
    print("Testing imports...")
    try:
        import discord
        print("  ✅ discord.py")
        import google.generativeai as genai
        print("  ✅ google-generativeai")
        import requests
        print("  ✅ requests")
        from bs4 import BeautifulSoup
        print("  ✅ beautifulsoup4")
        import aiohttp
        print("  ✅ aiohttp")
        return True
    except ImportError as e:
        print(f"  ❌ Missing package: {e}")
        print("\nRun: pip install -r requirements.txt")
        return False


def test_env_file():
    """Test that .env file exists and has required keys"""
    print("\nTesting .env file...")

    if not os.path.exists('.env'):
        print("  ❌ .env file not found!")
        print("\nCreate .env file with:")
        print("  TOKEN=your_discord_token")
        print("  GEMINI_API_KEY=your_gemini_key")
        return False

    load_dotenv()

    token = os.getenv('TOKEN')
    gemini_key = os.getenv('GEMINI_API_KEY')

    if not token:
        print("  ❌ TOKEN not found in .env")
        return False
    else:
        print(f"  ✅ TOKEN found (length: {len(token)})")

    if not gemini_key:
        print("  ❌ GEMINI_API_KEY not found in .env")
        return False
    else:
        print(f"  ✅ GEMINI_API_KEY found (length: {len(gemini_key)})")

    return True


def test_modules():
    """Test that custom modules can be imported"""
    print("\nTesting custom modules...")
    try:
        from scrapers import LinkedInScraper, CompanyScraper
        print("  ✅ scrapers module")

        from utils import JobAnalyzer, DiscordFormatter
        print("  ✅ utils module")

        return True
    except ImportError as e:
        print(f"  ❌ Error importing custom modules: {e}")
        return False


def test_scraper():
    """Test LinkedIn scraper with a sample URL"""
    print("\nTesting LinkedIn scraper...")
    try:
        from scrapers import LinkedInScraper
        scraper = LinkedInScraper()

        # Test URL extraction
        test_url = "https://www.linkedin.com/jobs/view/1234567890"
        job_id = scraper.extract_job_id(test_url)

        if job_id == "1234567890":
            print("  ✅ URL parsing works")
            return True
        else:
            print(f"  ❌ URL parsing failed (got: {job_id})")
            return False

    except Exception as e:
        print(f"  ❌ Scraper test failed: {e}")
        return False


def test_ai_analyzer():
    """Test AI analyzer initialization"""
    print("\nTesting AI analyzer...")
    try:
        load_dotenv()
        api_key = os.getenv('GEMINI_API_KEY')

        if not api_key:
            print("  ⚠️  Skipping (no GEMINI_API_KEY)")
            return True

        from utils import JobAnalyzer
        analyzer = JobAnalyzer(api_key)
        print("  ✅ AI analyzer initialized")

        # Note: We don't test actual API calls to avoid using quota
        print("  ℹ️  Skipping live API test (to save quota)")
        return True

    except Exception as e:
        print(f"  ❌ AI analyzer test failed: {e}")
        return False


def test_discord_formatter():
    """Test Discord formatter"""
    print("\nTesting Discord formatter...")
    try:
        from utils import DiscordFormatter
        import discord

        formatter = DiscordFormatter()

        # Test job embed creation
        sample_job = {
            'title': 'Test Job',
            'company': 'Test Company',
            'location': 'Test Location',
            'url': 'https://example.com'
        }

        embed = formatter.create_job_embed(sample_job)

        if isinstance(embed, discord.Embed):
            print("  ✅ Job embed creation works")
        else:
            print("  ❌ Job embed creation failed")
            return False

        # Test help embed
        help_embed = formatter.create_help_embed()
        if isinstance(help_embed, discord.Embed):
            print("  ✅ Help embed creation works")
        else:
            print("  ❌ Help embed creation failed")
            return False

        return True

    except Exception as e:
        print(f"  ❌ Formatter test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 50)
    print("Job Agent Bot - Component Tests")
    print("=" * 50)

    tests = [
        test_imports,
        test_env_file,
        test_modules,
        test_scraper,
        test_ai_analyzer,
        test_discord_formatter,
    ]

    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"\n❌ Test failed with exception: {e}")
            results.append(False)

    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)

    passed = sum(results)
    total = len(results)

    print(f"\nPassed: {passed}/{total}")

    if all(results):
        print("\n✅ All tests passed! Bot is ready to run.")
        print("\nNext steps:")
        print("  1. Run: python job_agent_bot.py")
        print("  2. Test in Discord with: !help")
        return 0
    else:
        print("\n❌ Some tests failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("  - Install dependencies: pip install -r requirements.txt")
        print("  - Create .env file with your API keys")
        print("  - Ensure you're in the correct directory")
        return 1


if __name__ == '__main__':
    sys.exit(main())
