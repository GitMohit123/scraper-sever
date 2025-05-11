from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from linkedin_scraper import scrape_linkedin_profile
from github_scraper import scrape_github_profile

app = FastAPI()

class LinkedInRequest(BaseModel):
    profile_url: str

class GitHubRequest(BaseModel):
    username: str

@app.post("/scrape/linkedin")
def scrape_linkedin(data: LinkedInRequest):
    try:
        summary = scrape_linkedin_profile(data.profile_url)
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/scrape/github")
def scrape_github(data: GitHubRequest):
    try:
        summary = scrape_github_profile(data.username)
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
