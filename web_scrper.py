import requests
from bs4 import BeautifulSoup
import time
import random
import re
from urllib.parse import urljoin
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# List of user agents for rotation to avoid detection
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0'
]

class WebScraper:
    def __init__(self, base_url, delay=2):
        """
        Initialize the scraper with a base URL and delay between requests.
        
        Args:
            base_url (str): The starting URL to scrape.
            delay (int): Seconds to wait between requests to avoid being blocked.
        """
        self.base_url = base_url
        self.delay = delay
        self.visited_urls = set()
        self.data = []

    def get_headers(self):
        """Return headers with a random user agent."""
        return {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive'
        }

    def fetch_page(self, url):
        """Fetch the content of a URL."""
        try:
            response = requests.get(url, headers=self.get_headers(), timeout=10)
            response.raise_for_status()
            logging.info(f"Successfully fetched: {url}")
            return response.text
        except requests.RequestException as e:
            logging.error(f"Failed to fetch {url}: {e}")
            return None

    def parse_page(self, html, url):
        """Parse HTML content and extract data."""
        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        page_data = {}

        # Example: Extract all text from paragraphs
        paragraphs = soup.find_all('p')
        page_data['text'] = [p.get_text().strip() for p in paragraphs if p.get_text().strip()]

        # Example: Extract all links
        links = soup.find_all('a', href=True)
        page_data['links'] = [urljoin(url, link['href']) for link in links]

        # Example: Extract specific data (e.g., emails)
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, html)
        page_data['emails'] = list(set(emails))  # Remove duplicates

        return page_data

    def scrape(self, max_pages=10):
        """Scrape data from the website up to max_pages."""
        urls_to_visit = [self.base_url]
        pages_scraped = 0

        while urls_to_visit and pages_scraped < max_pages:
            url = urls_to_visit.pop(0)
            if url in self.visited_urls:
                continue

            self.visited_urls.add(url)
            logging.info(f"Scraping: {url}")

            html = self.fetch_page(url)
            if html:
                page_data = self.parse_page(html, url)
                page_data['url'] = url
                self.data.append(page_data)

                # Find new URLs to visit (only those within the same domain)
                for link in page_data.get('links', []):
                    if link.startswith(self.base_url) and link not in self.visited_urls:
                        urls_to_visit.append(link)

                pages_scraped += 1
                time.sleep(self.delay)  # Respectful delay

        return self.data

    def save_data(self, filename='scraped_data.txt'):
        """Save scraped data to a file."""
        with open(filename, 'w', encoding='utf-8') as f:
            for page_data in self.data:
                f.write(f"URL: {page_data['url']}\n")
                f.write("Text:\n")
                for text in page_data.get('text', []):
                    f.write(f"  {text}\n")
                f.write("Emails:\n")
                for email in page_data.get('emails', []):
                    f.write(f"  {email}\n")
                f.write("Links:\n")
                for link in page_data.get('links', []):
                    f.write(f"  {link}\n")
                f.write("\n" + "="*50 + "\n")

def main():
    # Example usage
    target_url = input("Enter the website URL to scrape (e.g., https://example.com): ").strip()
    if not target_url.startswith(('http://', 'https://')):
        target_url = 'https://' + target_url

    scraper = WebScraper(base_url=target_url, delay=2)
    scraped_data = scraper.scrape(max_pages=5)
    scraper.save_data()

    logging.info(f"Scraping complete. Data saved to scraped_data.txt")
    print("Scraping complete. Check scraped_data.txt for results.")

if __name__ == "__main__":
    main()