"""
AI-powered job analysis using Gemini
"""

import google.generativeai as genai
import logging
from typing import Dict, Optional
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JobAnalyzer:
    """Analyze job postings using Gemini AI"""

    def __init__(self, api_key: str):
        """
        Initialize the job analyzer

        Args:
            api_key: Gemini API key
        """
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')

    def analyze_job(self, job_data: Dict) -> Optional[Dict]:
        """
        Analyze a job posting and extract structured insights

        Args:
            job_data: Dictionary containing job information

        Returns:
            Dictionary with analysis results
        """
        try:
            logger.info(f"Analyzing job: {job_data.get('title', 'Unknown')}")

            prompt = self._create_analysis_prompt(job_data)
            response = self.model.generate_content(prompt)

            # Parse the response
            analysis = self._parse_analysis_response(response.text)
            analysis['raw_data'] = job_data

            logger.info("Job analysis completed successfully")
            return analysis

        except Exception as e:
            logger.error(f"Error analyzing job: {e}")
            return {
                'error': str(e),
                'raw_data': job_data,
                'summary': 'Analysis failed - showing raw data only'
            }

    def _create_analysis_prompt(self, job_data: Dict) -> str:
        """Create a structured prompt for Gemini"""

        prompt = f"""You are an expert career advisor and job market analyst. Analyze the following job posting and provide detailed, actionable insights.

JOB POSTING DETAILS:
---
Title: {job_data.get('title', 'N/A')}
Company: {job_data.get('company', 'N/A')}
Location: {job_data.get('location', 'N/A')}
Employment Type: {job_data.get('employment_type', 'N/A')}
Seniority Level: {job_data.get('seniority_level', 'N/A')}
Industries: {job_data.get('industries', 'N/A')}

DESCRIPTION:
{job_data.get('description', 'N/A')}
---

Please provide a comprehensive analysis with the following structure:

1. **ROLE SUMMARY** (2-3 sentences)
   - What this role actually does
   - Key responsibilities

2. **REQUIRED SKILLS** (List top 5-8 most important technical skills)
   - Format: Skill name - Brief context

3. **PREFERRED QUALIFICATIONS**
   - Years of experience
   - Education requirements
   - Certifications or special requirements

4. **KEY TECHNOLOGIES & TOOLS**
   - Programming languages
   - Frameworks/Libraries
   - Tools and platforms

5. **SALARY ESTIMATE**
   - Estimated salary range (if US-based, use USD)
   - Base this on: job title, seniority, location, and company
   - Note: Mark as "estimate" and mention it varies by experience

6. **CAREER INSIGHTS**
   - Growth potential
   - Industry trends
   - What makes this role attractive or challenging

7. **RED FLAGS / GREEN FLAGS**
   - Positive aspects (green flags)
   - Potential concerns (red flags)

8. **APPLICATION TIPS**
   - What to emphasize in your application
   - Skills to highlight
   - Questions to ask during interview

Format your response in clean markdown with clear headers and bullet points. Be concise but insightful.
"""
        return prompt

    def _parse_analysis_response(self, response_text: str) -> Dict:
        """
        Parse Gemini's response into structured format

        Args:
            response_text: Raw text from Gemini

        Returns:
            Dictionary with parsed analysis
        """
        return {
            'full_analysis': response_text,
            'summary': self._extract_summary(response_text),
        }

    def _extract_summary(self, text: str) -> str:
        """Extract a brief summary from the analysis"""
        lines = text.split('\n')
        # Get first few meaningful lines
        summary_lines = []
        for line in lines[:10]:
            line = line.strip()
            if line and not line.startswith('#') and len(line) > 20:
                summary_lines.append(line)
                if len(summary_lines) >= 3:
                    break

        return ' '.join(summary_lines) if summary_lines else text[:200] + '...'

    def compare_jobs(self, jobs: list) -> Optional[str]:
        """
        Compare multiple job postings

        Args:
            jobs: List of job data dictionaries

        Returns:
            Comparison analysis text
        """
        try:
            if not jobs or len(jobs) < 2:
                return "Need at least 2 jobs to compare"

            prompt = f"""Compare the following {len(jobs)} job postings and help the user decide which might be best:

"""
            for i, job in enumerate(jobs[:3], 1):  # Limit to 3 for MVP
                prompt += f"""
JOB {i}:
Title: {job.get('title', 'N/A')}
Company: {job.get('company', 'N/A')}
Location: {job.get('location', 'N/A')}
---
"""

            prompt += """
Please provide:
1. Quick comparison of roles, companies, and locations
2. Which job might offer better career growth
3. Which might have better work-life balance
4. Recommendation based on typical career priorities

Keep it concise and actionable.
"""

            response = self.model.generate_content(prompt)
            return response.text

        except Exception as e:
            logger.error(f"Error comparing jobs: {e}")
            return f"Error comparing jobs: {str(e)}"

    def extract_skills(self, job_description: str) -> list:
        """
        Extract skills from job description

        Args:
            job_description: Job description text

        Returns:
            List of skills
        """
        try:
            prompt = f"""Extract all technical skills, tools, and technologies mentioned in this job description. Return ONLY a comma-separated list of skills, nothing else.

Job Description:
{job_description[:2000]}  # Limit length

Example output: Python, AWS, Docker, Kubernetes, React, PostgreSQL
"""

            response = self.model.generate_content(prompt)
            skills_text = response.text.strip()

            # Parse comma-separated skills
            skills = [s.strip() for s in skills_text.split(',')]
            return skills[:15]  # Limit to top 15

        except Exception as e:
            logger.error(f"Error extracting skills: {e}")
            return []
