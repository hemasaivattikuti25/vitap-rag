import requests
from bs4 import BeautifulSoup
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.schema import ExtractedContent

def scrape_clubs_page(url: str = "https://vitap.ac.in/clubs-and-chapters/") -> list[ExtractedContent]:
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        clubs = []
        # Find elements that look like club listings - assuming standard WP layout
        # (A real implementation would need the exact selectors for the VIT-AP site)
        club_elements = soup.find_all(['h3', 'h4'], class_=lambda x: x and 'title' in x)
        
        for el in club_elements:
            club_name = el.get_text(strip=True)
            parent = el.find_parent('div')
            description = parent.get_text(separator=' ', strip=True) if parent else club_name
            
            clubs.append(ExtractedContent(
                title=f"Club: {club_name}",
                type="club",
                content=description,
                source_url=url,
                updated_at=datetime.now().isoformat()
            ))
            
        return clubs
    except Exception as e:
        print(f"Error scraping clubs: {e}")
        return []

if __name__ == "__main__":
    clubs_data = scrape_clubs_page()
    print(f"Found {len(clubs_data)} clubs.")
