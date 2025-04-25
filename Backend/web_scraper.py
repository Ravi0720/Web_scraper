import requests
from bs4 import BeautifulSoup
import time
import random
import re
from urllib.parse import urljoin
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import logging
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# SQLite database setup
Base = declarative_base()
engine = create_engine('sqlite:///crime_data.db')
Session = sessionmaker(bind=engine)

class CrimeData(Base):
    __tablename__ = 'crime_data'
    id = Column(Integer, primary_key=True)
    website = Column(String)
    url = Column(String)
    headings = Column(Text)
    tables = Column(Text)
    incidents = Column(Text)
    dataset_links = Column(Text)

Base.metadata.create_all(engine)

# User agents for rotation
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0'
]

# FastAPI app
app = FastAPI()

# Pydantic model for request
class ScrapeRequest(BaseModel):
    urls: List[str]
    max_pages_per_site: int = 5

class WebScraper:
    def __init__(self, delay=2):
        self.delay = delay
        self.visited_urls = set()

    def get_headers(self):
        return {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive'
        }

    def fetch_page(self, url, use_selenium=False):
        if use_selenium:
            try:
                options = Options()
                options.add_argument('--headless')
                driver = webdriver.Chrome(options=options)
                driver.get(url)
                time.sleep(3)
                html = driver.page_source
                logging.info(f"Successfully fetched with Selenium: {url}")
                return html
            except Exception as e:
                logging.error(f"Failed to fetch {url} with Selenium: {e}")
                return None
            finally:
                driver.quit()
        else:
            try:
                response = requests.get(url, headers=self.get_headers(), timeout=10)
                response.raise_for_status()
                logging.info(f"Successfully fetched: {url}")
                return response.text
            except requests.RequestException as e:
                logging.error(f"Failed to fetch {url}: {e}")
                return None

    def parse_page(self, html, url):
        if not html:
            return {}

        soup = BeautifulSoup(html, 'html.parser')
        page_data = {}

        # Extract tables
        tables = soup.find_all('table')
        page_data['tables'] = [str(table) for table in tables if table.get_text().strip()]

        # Extract incidents
        incidents = soup.find_all('div', class_=re.compile('crime|incident'))
        page_data['incidents'] = [inc.get_text().strip() for inc in incidents if inc.get_text().strip()]

        # Extract headings
        headings = soup.find_all(['h1', 'h2', 'h3'])
        page_data['headings'] = [h.get_text().strip() for h in headings if h.get_text().strip()]

        # Extract dataset links
        links = soup.find_all('a', href=re.compile(r'\.(csv|json|pdf)'))
        page_data['dataset_links'] = [urljoin(url, link['href']) for link in links]

        return page_data

    def scrape(self, urls, max_pages_per_site=5):
        session = Session()
        for base_url in urls:
            logging.info(f"Starting scrape for: {base_url}")
            urls_to_visit = [base_url]
            pages_scraped = 0

            while urls_to_visit and pages_scraped < max_pages_per_site:
                url = urls_to_visit.pop(0)
                if url in self.visited_urls:
                    continue

                self.visited_urls.add(url)
                logging.info(f"Scraping: {url}")

                # Use selenium for specific sites
                use_selenium = any(site in url for site in ['crimemapping.com', 'spotcrime.com'])
                html = self.fetch_page(url, use_selenium=use_selenium)
                if html:
                    page_data = self.parse_page(html, url)
                    page_data['url'] = url
                    page_data['website'] = base_url

                    # Save to database
                    db_entry = CrimeData(
                        website=base_url,
                        url=url,
                        headings='; '.join(page_data.get('headings', [])),
                        tables='; '.join(page_data.get('tables', [])),
                        incidents='; '.join(page_data.get('incidents', [])),
                        dataset_links='; '.join(page_data.get('dataset_links', []))
                    )
                    session.add(db_entry)
                    session.commit()

                    # Find new URLs to visit
                    for link in page_data.get('dataset_links', []):
                        if link.startswith(base_url) and link not in self.visited_urls:
                            urls_to_visit.append(link)

                    pages_scraped += 1
                    time.sleep(self.delay)

        session.close()

# API endpoints
@app.post("/scrape")
async def scrape_websites(request: ScrapeRequest):
    scraper = WebScraper()
    try:
        scraper.scrape(request.urls, request.max_pages_per_site)
        return {"status": "Scraping completed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/data")
async def get_data():
    session = Session()
    try:
        data = session.query(CrimeData).all()
        return [{
            "website": d.website,
            "url": d.url,
            "headings": d.headings.split('; ') if d.headings else [],
            "tables": d.tables.split('; ') if d.tables else [],
            "incidents": d.incidents.split('; ') if d.incidents else [],
            "dataset_links": d.dataset_links.split('; ') if d.dataset_links else []
        } for d in data]
    finally:
        session.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)