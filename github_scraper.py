import time
import pprint
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os

load_dotenv()  # Load variables from .env into environment

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    return webdriver.Chrome(options=options)

def navigate_to_tab(driver, username, tab):
    url = f"https://github.com/{username}?tab={tab}"
    driver.get(url)
    time.sleep(2)

def scrape_overview(driver, username):
    driver.get(f"https://github.com/{username}")
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    profile_data = {}

    profile_data['Name'] = soup.find('span', class_='p-name').get_text(strip=True) if soup.find('span', class_='p-name') else ''
    profile_data['Bio'] = soup.find('div', class_='p-note').get_text(strip=True) if soup.find('div', class_='p-note') else ''
    profile_data['Location'] = soup.find('span', class_='p-label').get_text(strip=True) if soup.find('span', class_='p-label') else ''
    profile_data['Followers'] = soup.find('a', href=f"/{username}?tab=followers").find('span').get_text(strip=True) if soup.find('a', href=f"/{username}?tab=followers") else ''
    profile_data['Following'] = soup.find('a', href=f"/{username}?tab=following").find('span').get_text(strip=True) if soup.find('a', href=f"/{username}?tab=following") else ''
    profile_data['Stars'] = soup.find('a', href=f"/{username}?tab=stars").find('span').get_text(strip=True) if soup.find('a', href=f"/{username}?tab=stars") else ''

    pinned_repos = []
    pinned_items = soup.find_all('span', class_='repo')
    for repo in pinned_items:
        pinned_repos.append(repo.get_text(strip=True))
    profile_data['Pinned Repositories'] = pinned_repos

    return profile_data

def scrape_repositories(driver, username):
    repositories = []
    page = 1
    while True:
        navigate_to_tab(driver, username, f"repositories&page={page}")
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        repo_list = soup.find_all('li', itemprop='owns')
        if not repo_list:
            break
        for repo in repo_list:
            repo_name = repo.find('a', itemprop='name codeRepository').get_text(strip=True)
            repo_desc = repo.find('p', itemprop='description').get_text(strip=True) if repo.find('p', itemprop='description') else ''
            repo_lang = repo.find('span', itemprop='programmingLanguage').get_text(strip=True) if repo.find('span', itemprop='programmingLanguage') else ''
            repositories.append({
                'Name': repo_name,
                'Description': repo_desc,
                'Language': repo_lang
            })
        page += 1
    return repositories

def scrape_projects(driver, username):
    projects = []
    navigate_to_tab(driver, username, "projects")
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    project_items = soup.find_all('div', class_='project-card')
    for project in project_items:
        title = project.find('a', class_='h4').get_text(strip=True)
        desc = project.find('p', class_='text-gray').get_text(strip=True) if project.find('p', class_='text-gray') else ''
        projects.append({
            'Title': title,
            'Description': desc
        })
    return projects

def scrape_packages(driver, username):
    packages = []
    navigate_to_tab(driver, username, "packages")
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    package_items = soup.find_all('div', class_='package')
    for package in package_items:
        name = package.find('h4').get_text(strip=True)
        desc = package.find('p').get_text(strip=True) if package.find('p') else ''
        packages.append({
            'Name': name,
            'Description': desc
        })
    return packages

def scrape_follow(driver, username, follow_type):
    users = []
    page = 1
    while True:
        navigate_to_tab(driver, username, f"{follow_type}&page={page}")
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        user_items = soup.find_all('span', class_='Link--secondary')
        if not user_items:
            break
        for user in user_items:
            users.append(user.get_text(strip=True))
        page += 1
    return len(users)

def scrape_readme(driver, username):
    raw_url = f"https://raw.githubusercontent.com/{username}/{username}/main/README.md"
    try:
        response = requests.get(raw_url)
        if response.status_code == 200:
            return response.text.strip()
        else:
            return ""
    except Exception:
        return ""

def scrape_contributions(driver, username):
    driver.get(f"https://github.com/{username}")
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    contrib_text = soup.find('h2', class_='f4 text-normal mb-2')
    return contrib_text.get_text(strip=True) if contrib_text else "Contribution data not found."

def summarize_with_openai(overview, repositories, projects, packages, followers, following, contributions, readme_content, OPENROUTER_API_KEY):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""
You are a GitHub profile analysis assistant. Based on the following GitHub profile data, generate a professional, structured summary.

**Overview**:
{overview}

**Repositories** (sample):
{repositories[:5]}

**Projects**:
{projects[:3]}

**Packages**:
{packages[:3]}

**Followers**: {followers}
**Following**: {following}
**Contributions**: {contributions}

**README.md** (if present):
{readme_content[:1000]}

Summarize under these headings:
1. Overview
2. Technical Skills, Tools, and Frameworks
3. Notable Projects or Work
4. Git Activity and Consistency
5. Important Keywords or Focus Areas (e.g., Web Dev, AI, DevOps)
Use a professional tone and avoid generic filler.
"""

    data = {
        "model": "openai/gpt-4",
        "messages": [
            {"role": "system", "content": "You are a GitHub profile summarizer."},
            {"role": "user", "content": prompt}
        ]
    }

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content'].strip()
        else:
            return f"❌ Failed to summarize profile (Status: {response.status_code})"
    except Exception as e:
        return f"❌ Error during summarization: {str(e)}"

def scrape_github_profile(username):
    driver = init_driver()
    try:
        overview = scrape_overview(driver, username)
        repositories = scrape_repositories(driver, username)
        projects = scrape_projects(driver, username)
        packages = scrape_packages(driver, username)
        followers = scrape_follow(driver, username, "followers")
        following = scrape_follow(driver, username, "following")
        contributions = scrape_contributions(driver, username)
        readme = scrape_readme(driver, username)

        return summarize_with_openai(
            overview, repositories, projects, packages,
            followers, following, contributions, readme, OPENROUTER_API_KEY
        )
    finally:
        driver.quit()

