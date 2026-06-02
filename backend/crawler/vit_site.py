import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.schema import ExtractedContent

def scrape_vit_page(url: str, page_type: str) -> ExtractedContent:
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer"]):
            script.extract()
            
        title = soup.title.string if soup.title else url
        
        # Extract text from main content
        text = soup.get_text(separator=' ', strip=True)
        
        # Basic chunking/cleaning
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return ExtractedContent(
            title=title.strip(),
            type=page_type,
            content=text,
            source_url=url,
            updated_at=datetime.now().isoformat()
        )
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None

def run_crawler():
    # Base URLs for testing the MVP
    urls_to_scrape = [
        ("https://vitap.ac.in/", "general"),
        ("https://vitap.ac.in/clubs-and-chapters/", "club"),
    ]
    
    results = []
    for url, page_type in urls_to_scrape:
        print(f"Scraping {url}...")
        data = scrape_vit_page(url, page_type)
        if data:
            results.append(data)
            
    return results

if __name__ == "__main__":
    extracted_data = run_crawler()
    print(f"Scraped {len(extracted_data)} pages.")
    if extracted_data:
        print(f"Sample from {extracted_data[0].title}: {extracted_data[0].content[:200]}...")
