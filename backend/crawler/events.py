import requests
from bs4 import BeautifulSoup
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.schema import ExtractedContent

def scrape_events_page(url: str = "https://vitap.ac.in/events/") -> list[ExtractedContent]:
    try:
        response = requests.get(url, timeout=10)
        # Proceed even if it's 404 for MVP testing as we are stubbing
        if response.status_code != 200:
            print(f"Status code {response.status_code} for {url}. Attempting to parse anyway or returning empty.")
            
        soup = BeautifulSoup(response.content, 'html.parser')
        
        events = []
        event_elements = soup.find_all('div', class_=lambda x: x and 'event' in x.lower())
        
        for el in event_elements:
            title_el = el.find(['h3', 'h4'])
            event_name = title_el.get_text(strip=True) if title_el else "Unknown Event"
            description = el.get_text(separator=' ', strip=True)
            
            events.append(ExtractedContent(
                title=f"Event: {event_name}",
                type="event",
                content=description,
                source_url=url,
                updated_at=datetime.now().isoformat()
            ))
            
        return events
    except Exception as e:
        print(f"Error scraping events: {e}")
        return []

if __name__ == "__main__":
    events_data = scrape_events_page()
    print(f"Found {len(events_data)} events.")
