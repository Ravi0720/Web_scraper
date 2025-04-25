import requests
from bs4 import BeautifulSoup
import time
import random
import re
from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import logging
import cv2
import numpy as np
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# SQLite database setup
Base = declarative_base()
engine = create_engine('sqlite:///crime_data.db')
Session = sessionmaker(bind=engine)

class CrimeData(Base):
    __tablename__ = 'crime_data'
    id = Column(Integer, primary_key=True)
    source = Column(String)
    url = Column(String)
    criminal_name = Column(String)
    crime_date = Column(String)
    crime_story = Column(Text)
    fetch_date = Column(String)

Base.metadata.create_all(engine)

# Mock criminal database (for identification)
MOCK_CRIMINAL_DB = {
    "John Doe": {"aliases": ["Johnny D", "J. Doe"], "history": "Robbery, 2019", "image_hash": "mock_hash_123"},
    "Jane Smith": {"aliases": ["J. Smith"], "history": "Assault, 2020", "image_hash": "mock_hash_456"},
    "Alice Brown": {"aliases": ["A. Brown"], "history": "Theft, 2021", "image_hash": "mock_hash_789"},
}

# User agents for rotation
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0'
]

# FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class IdentifyRequest(BaseModel):
    name: str = None

class CrimeoMeterRequest(BaseModel):
    lat: float
    lon: float
    start_date: str
    end_date: str
    distance: str = "1mi"

# WebScraper class
class WebScraper:
    def __init__(self, delay=2):
        self.delay = delay
        self.data = []

    def get_headers(self):
        return {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive'
        }

    def fetch_page(self, url):
        try:
            response = requests.get(url, headers=self.get_headers(), timeout=10)
            response.raise_for_status()
            logging.info(f"Successfully fetched: {url}")
            return response.text
        except requests.RequestException as e:
            logging.error(f"Failed to fetch {url}: {e}")
            return None

    def extract_criminal_info(self, text):
        name_pattern = r'\b[A-Z][a-z]+ [A-Z][a-z]+\b'
        names = re.findall(name_pattern, text)
        exclude_names = {'United States', 'New York', 'Los Angeles', 'Police Department'}
        names = [name for name in names if name not in exclude_names and len(name.split()) == 2]

        date_pattern = r'(?:\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\b|\b\d{4}-\d{2}-\d{2}\b)'
        dates = re.findall(date_pattern, text)

        crime_keywords = r'crime|murder|theft|assault|robbery|arrest|convict|kill|attack'
        sentences = re.split(r'[.!?]\s+', text)
        crime_sentences = [s for s in sentences if re.search(crime_keywords, s, re.I)]

        return names, dates, crime_sentences

    def parse_news_page(self, html, url, source):
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)

        names, dates, crime_sentences = self.extract_criminal_info(text)
        if not names or not dates or not crime_sentences:
            return None

        criminal_name = names[0] if names else "Unknown"
        crime_date = dates[0] if dates else "Unknown"
        crime_story = " ".join(crime_sentences[:2]) if crime_sentences else "No story available"

        return {
            "source": source,
            "url": url,
            "criminal_name": criminal_name,
            "crime_date": crime_date,
            "crime_story": crime_story,
            "fetch_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    def fetch_crimeometer_data(self, lat, lon, start_date, end_date, distance="1mi"):
        api_key = "YOUR_CRIMEOMETER_API_KEY"
        url = f"https://api.crimeometer.com/v2/crime-incidents?lat={lat}&lon={lon}&datetime_ini={start_date}&datetime_end={end_date}&distance={distance}"
        headers = {"x-api-key": api_key}
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            logging.info(f"Successfully fetched CrimeoMeter data for lat={lat}, lon={lon}")
            return data
        except requests.RequestException as e:
            logging.error(f"Failed to fetch CrimeoMeter data: {e}")
            return None

    def fetch_reliable_data(self):
        session = Session()
        self.data = []

        news_sources = [
            {"name": "CNN", "url": "https://www.cnn.com/us/crime"},
            {"name": "BBC", "url": "https://www.bbc.com/news/topics/c77jz3mdmx9t/crime"},
            {"name": "The Guardian", "url": "https://www.theguardian.com/uk/crime"}
        ]

        for source in news_sources:
            logging.info(f"Fetching data from: {source['name']} ({source['url']})")
            html = self.fetch_page(source['url'])
            if html:
                page_data = self.parse_news_page(html, source['url'], source['name'])
                if page_data:
                    self.data.append(page_data)

                    db_entry = CrimeData(
                        source=page_data['source'],
                        url=page_data['url'],
                        criminal_name=page_data['criminal_name'],
                        crime_date=page_data['crime_date'],
                        crime_story=page_data['crime_story'],
                        fetch_date=page_data['fetch_date']
                    )
                    session.add(db_entry)
                    session.commit()
            time.sleep(self.delay)

        self.save_to_file()
        session.close()

    def identify_criminal_by_image(self, image_file):
        try:
            image_path = "temp_image.jpg"
            with open(image_path, 'wb') as f:
                f.write(image_file.file.read())
            
            img = cv2.imread(image_path)
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)

            results = []
            for i, (x, y, w, h) in enumerate(faces):
                image_hash = f"mock_hash_{(i % 3) + 1}"
                match_found = False
                for name, info in MOCK_CRIMINAL_DB.items():
                    if info.get("image_hash") == image_hash:
                        results.append({"name": name, "details": info})
                        match_found = True
                        break
                if not match_found:
                    results.append({"name": "Unknown", "details": f"No match found for face {i+1}"})
            if not results:
                results.append({"name": "No Faces", "details": "No faces detected in the image"})
            return results
        except Exception as e:
            logging.error(f"Error in image identification: {e}")
            return [{"name": "Error", "details": str(e)}]
        finally:
            if os.path.exists(image_path):
                os.remove(image_path)

    def identify_criminal_by_name(self, name):
        name = name.strip().lower()
        for known_name, info in MOCK_CRIMINAL_DB.items():
            if name == known_name.lower() or any(alias.lower() == name for alias in info.get("aliases", [])):
                return {"name": known_name, "details": info}
        return {"name": "Unknown", "details": "No match found"}

    def save_to_file(self, filename='scraped_data.txt'):
        with open(filename, 'w', encoding='utf-8') as f:
            for page_data in self.data:
                f.write(f"Source: {page_data['source']}\n")
                f.write(f"URL: {page_data['url']}\n")
                f.write(f"Criminal Name: {page_data['criminal_name']}\n")
                f.write(f"Crime Date: {page_data['crime_date']}\n")
                f.write(f"Crime Story: {page_data['crime_story']}\n")
                f.write(f"Fetched On: {page_data['fetch_date']}\n")
                f.write("\n" + "="*50 + "\n")

# API endpoints
@app.get("/")
async def root():
    return {"message": "Welcome to the Crime Data Scraper API. Use POST /fetch-data to retrieve data or POST /identify/image to identify criminals."}

@app.get("/favicon.ico")
async def favicon():
    return {"message": "No favicon available"}

@app.post("/fetch-data")
async def fetch_data():
    logging.info("Received request to fetch reliable data")
    scraper = WebScraper()
    try:
        scraper.fetch_reliable_data()
        return {"status": "Data fetch completed"}
    except Exception as e:
        logging.error("Data fetch error: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/data")
async def get_data():
    logging.info("Received request for /data endpoint")
    session = Session()
    try:
        data = session.query(CrimeData).all()
        return [{
            "source": d.source,
            "url": d.url,
            "criminal_name": d.criminal_name,
            "crime_date": d.crime_date,
            "crime_story": d.crime_story,
            "fetch_date": d.fetch_date
        } for d in data]
    finally:
        session.close()

@app.post("/fetch-crimeometer")
async def fetch_crimeometer(request: CrimeoMeterRequest):
    logging.info("Received CrimeoMeter request for lat=%s, lon=%s", request.lat, request.lon)
    scraper = WebScraper()
    try:
        data = scraper.fetch_crimeometer_data(
            request.lat, request.lon, request.start_date, request.end_date, request.distance
        )
        if not data:
            raise HTTPException(status_code=500, detail="Failed to fetch CrimeoMeter data")
        session = Session()
        for incident in data.get("incidents", []):
            db_entry = CrimeData(
                source="crimeometer.com",
                url=f"lat={request.lat},lon={request.lon}",
                criminal_name="Unknown",
                crime_date=incident.get("datetime", "Unknown"),
                crime_story=f"{incident.get('incident_type', 'Crime')} reported at {incident.get('location', 'unknown location')}",
                fetch_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
            session.add(db_entry)
        session.commit()
        session.close()
        return {"status": "CrimeoMeter data fetched", "data": data}
    except Exception as e:
        logging.error("CrimeoMeter fetch error: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/identify/image")
async def identify_by_image(image: UploadFile = File(...)):
    logging.info("Received image for identification")
    scraper = WebScraper()
    results = scraper.identify_criminal_by_image(image)
    return {"identifications": results}

@app.post("/identify/name")
async def identify_by_name(request: IdentifyRequest):
    logging.info("Received name for identification: %s", request.name)
    scraper = WebScraper()
    result = scraper.identify_criminal_by_name(request.name)
    return {"identification": result}

if __name__ == "__main__":
    logging.info("Starting FastAPI server on port 8000")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)