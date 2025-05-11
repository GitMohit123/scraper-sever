import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()  # Load variables from .env into environment

LI_AT_COOKIE = os.getenv("LI_AT_COOKIE")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

def get_rendered_html_with_cookie(url, li_at_cookie):
    options = uc.ChromeOptions()
    options.add_argument("--headless=new")
    driver = uc.Chrome(options=options)

    driver.get("https://www.linkedin.com")
    driver.delete_all_cookies()
    driver.add_cookie({"name": "li_at", "value": li_at_cookie, "domain": ".linkedin.com"})
    driver.get(url)
    time.sleep(5)

    html = driver.page_source
    driver.quit()
    return html


def extract_full_visible_text(html):
    soup = BeautifulSoup(html, "html.parser")

    # Prefer content inside <main> tag if present
    main_content = soup.find("main")
    if main_content:
        text = main_content.get_text(separator="\n", strip=True)
    else:
        text = soup.get_text(separator="\n", strip=True)

    # Basic cleanup
    lines = text.splitlines()
    cleaned = "\n".join(line for line in lines if len(line.strip()) > 0 and not line.strip().startswith("LinkedIn"))
    return cleaned


def summarize_with_openrouter(full_text):
    prompt = f"""
You are provided with raw, unstructured text scraped from a candidate's LinkedIn profile. Your task is to extract, analyze, and rewrite this into a structured, multi-paragraph professional summary that accurately reflects the individual’s career, experience, skills, projects, certifications, and domain exposure.

**IMPORTANT GUIDELINES**:
1. **Critically assess and neutralize** any self-promotional, exaggerated, or boastful language. LinkedIn profiles often contain unverified claims; your job is to filter out such content and only retain statements that are **specific, verifiable, or logically credible**.
2. **Every achievement, skill, or claim about capability must be backed by context or evidence** in the original text. If no proof or context is present (e.g., outcomes, responsibilities, tools used, impact), **do not inflate it into a strong claim**.
3. Use a **smart, experienced, recruiter-like lens** to evaluate the candidate’s professional background. Summarize what they have done, in which domains, using which tools/methods, and for what business objectives.
4. Ensure the response is **multi-paragraph**, structured with the following sections:  
   - **Professional Summary**: High-level overview of the candidate’s background, roles, and overall expertise.  
   - **Work Experience**: Detailed timeline or summary of past roles, responsibilities, and actual scope of work.  
   - **Projects**: Highlight meaningful project work, real deliverables, and technologies used (only if projects are mentioned explicitly).  
   - **Skills and Tools**: Only list skills that are reflected by concrete evidence in roles or projects. Avoid vague listing.  
   - **Certifications & Education**: Mention only if present in text, and indicate relevance to current domain.  
   - **Domains & Industry Exposure**: Identify the industries or business areas the candidate has worked in (e.g., fintech, retail, healthcare, SaaS).

5. The tone must be **neutral, detailed, and analytical**. This is an internal professional record used for job-role fit evaluation and background assessment.

6. Avoid generic filler statements like “passionate about learning” or “strong leadership skills” unless the text provides **specific and contextual proof** of such claims (e.g., mentoring, team management examples).

Your goal is to create an **accurate, comprehensive, and trustworthy profile summary** that can be used in a hiring pipeline as a factual reference.

**Input: (Raw LinkedIn Profile Text):**  
{full_text[:3500]}
"""
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    body = {
        "model": "openai/gpt-4",
        "messages": [
            {"role": "system", "content": "You are a professional LinkedIn profile summarizer."},
            {"role": "user", "content": prompt}
        ]
    }

    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=body)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def scrape_linkedin_profile(profile_url):
    html = get_rendered_html_with_cookie(profile_url, LI_AT_COOKIE)
    full_text = extract_full_visible_text(html)
    return summarize_with_openrouter(full_text)
