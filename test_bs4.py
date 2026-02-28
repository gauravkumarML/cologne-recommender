from bs4 import BeautifulSoup
import json

def test_parse_dir():
    with open('basenotes_dir.html', 'r') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
    
    links = []
    cards = soup.find_all('a', class_='xbn_card')
    for card in cards:
        href = card.get('href')
        if href and href.startswith('/fragrances/'):
            links.append('https://basenotes.com' + href)
    
    print(f"Found {len(links)} fragrance links. First 3: {links[:3]}")

def test_parse_item():
    with open('basenotes_item.html', 'r') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
    
    # Extract Name & Brand
    name_elem = soup.find('span', class_='h1_fragname')
    name = name_elem.text.strip() if name_elem else "Unknown Name"
    
    brand_elem = soup.find('span', class_='h1_house')
    brand = brand_elem.text.strip() if brand_elem else "Unknown Brand"
    
    # Extract Notes
    notes_list = []
    notes_container = soup.find('ul', class_='fragrancenotes')
    if notes_container:
        # Find all deeply nested li or simply text inside the uls
        # Basenotes structure usually: <ul ...> <li> <h3>Head</h3> <ul> <li>notes</li> </ul> </li> </ul>
        inner_uls = notes_container.find_all('ul')
        if inner_uls:
            for ul in inner_uls:
                for li in ul.find_all('li'):
                    text = li.text.strip()
                    # Splitting by comma if there's a comma-separated list
                    items = [x.strip() for x in text.split(',')]
                    notes_list.extend(items)
        else:
            # Fallback for simple structures without head/heart/base
            for li in notes_container.find_all('li'):
                text = li.text.strip()
                items = [x.strip() for x in text.split(',')]
                notes_list.extend(items)
                
    # Remove empty
    notes_list = [n for n in notes_list if n]
    
    # Extract Reviews
    pos_reviews, neu_reviews, neg_reviews = 0, 0, 0
    review_links = soup.find_all('a')
    for link in review_links:
        href = link.get('href', '')
        text_parts = link.text.strip().split()
        if not text_parts:
            continue
            
        if 'reviews/positive/' in href and "Positive" in link.text:
            if text_parts[0].isdigit(): pos_reviews = int(text_parts[0])
        elif 'reviews/neutral/' in href and "Neutral" in link.text:
            if text_parts[0].isdigit(): neu_reviews = int(text_parts[0])
        elif 'reviews/negative/' in href and "Negative" in link.text:
            if text_parts[0].isdigit(): neg_reviews = int(text_parts[0])

    review_texts = []
    for div in soup.find_all('div', class_='fragreview'):
        text = div.get_text(separator=' ', strip=True)
        if text:
            review_texts.append(text)

    data = {
        "name": name,
        "brand": brand,
        "notes": notes_list,
        "reviews": {
            "positive": pos_reviews,
            "neutral": neu_reviews,
            "negative": neg_reviews,
            "texts": review_texts[:3]
        }
    }
    print(json.dumps(data, indent=2))

if __name__ == "__main__":
    print("--- Directory ---")
    test_parse_dir()
    print("--- Item ---")
    test_parse_item()
