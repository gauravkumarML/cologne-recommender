import asyncio
import json
import random
import os
from bs4 import BeautifulSoup
import nodriver as uc
import database

# Ensure database is pointed properly
database.DB_PATH = "colognes_basenotes.db"

async def scrape_directory_pages(start_page=1, end_page=100):
    urls = []
    
    # Load existing if available
    if os.path.exists("basenotes_urls.json"):
        with open("basenotes_urls.json", "r") as f:
            urls = json.load(f)
            
    print(f"Loaded {len(urls)} existing URLs.")
            
    browser = await uc.start(headless=False)
    page = await browser.get('about:blank')
    
    try:
        for i in range(start_page, end_page + 1):
            url = f"https://basenotes.com/directory/?search=&type=all&page={i}"
            print(f"Scraping directory page {i}...")
            
            await page.get(url)
            await page.sleep(random.uniform(4, 7)) # Jitter to avoid blocks
            
            html = await page.get_content()
            soup = BeautifulSoup(html, 'html.parser')
            
            cards = soup.find_all('a', class_='xbn_card')
            page_links = []
            has_fragrance_cards = False
            
            for card in cards:
                href = card.get('href')
                if href and href.startswith('/fragrances/'):
                    has_fragrance_cards = True
                    full_link = 'https://basenotes.com' + href
                    if full_link not in urls:
                        page_links.append(full_link)
            
            if not has_fragrance_cards:
                print(f"Page {i} had no recognizable fragrance links. Stopping directory scrape.")
                break
                
            urls.extend(page_links)
            print(f"Found {len(page_links)} links on page {i}. Total: {len(urls)}")
            
            # Save progressively
            with open("basenotes_urls.json", "w") as f:
                json.dump(urls, f)
                
            # Random longer break
            if i % 10 == 0:
                print(f"Taking a longer break at page {i}...")
                await page.sleep(15)
                
    except Exception as e:
        print(f"Directory scraping failed on page {i}: {e}")
    finally:
        if browser:
            try:
                browser.stop()
            except Exception:
                pass
        
    return urls

async def scrape_cologne_details(page, url):
    data = {"url": url, "brand": "Unknown", "name": "Unknown", "notes": [], "gender": "Unisex", "reviews": {"positive": 0, "neutral": 0, "negative": 0, "texts": []}}
    
    try:
        await page.get(url)
        await page.sleep(random.uniform(3, 6))
        
        html = await page.get_content()
        soup = BeautifulSoup(html, 'html.parser')
        
        # Name
        name_elem = soup.find('span', class_='h1_fragname')
        if name_elem:
            data['name'] = name_elem.text.strip()
            
        # Gender inference from name (or icon)
        gender_icon = soup.find('i', class_='fa-genderless')
        if gender_icon:
            data['gender'] = 'Unisex'
        elif soup.find('i', class_='fa-mars'):
             data['gender'] = 'Male'
        elif soup.find('i', class_='fa-venus'):
             data['gender'] = 'Female'
             
        # Brand
        brand_elem = soup.find('span', class_='h1_house')
        if brand_elem:
            data['brand'] = brand_elem.text.strip()
            
        # Notes
        notes_container = soup.find('ul', class_='fragrancenotes')
        if notes_container:
            inner_uls = notes_container.find_all('ul')
            if inner_uls:
                for ul in inner_uls:
                    for li in ul.find_all('li'):
                        text = li.text.strip()
                        items = [x.strip() for x in text.split(',')]
                        data['notes'].extend(items)
            else:
                for li in notes_container.find_all('li'):
                    text = li.text.strip()
                    items = [x.strip() for x in text.split(',')]
                    data['notes'].extend(items)
                    
        # Clean empty notes
        data['notes'] = [n for n in data['notes'] if n]
        
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
                
        data['reviews'] = {"positive": pos_reviews, "neutral": neu_reviews, "negative": neg_reviews, "texts": review_texts[:3]}
        
    except Exception as e:
        print(f"Failed to scrape {url}: {e}")
        
    return data

async def run_details_scraper(chunk_size=20):
    database.DB_PATH = "colognes_basenotes.db"
    database.init_db()
    
    if not os.path.exists("basenotes_urls.json"):
        print("No basenotes_urls.json found. Run directory scraper first.")
        return
        
    with open("basenotes_urls.json", "r") as f:
        urls = json.load(f)
        
    # Exclude already processed
    pending_urls = [u for u in urls if not database.get_cologne_by_url(u)]
    print(f"Remaining URLs to extract details for: {len(pending_urls)}")
    
    for i in range(0, len(pending_urls), chunk_size):
        chunk = pending_urls[i:i+chunk_size]
        print(f"--- Processing chunk {i//chunk_size + 1} of {(len(pending_urls)//chunk_size) + 1} ---")
        
        browser = None
        try:
            browser = await uc.start(headless=False)
            page = await browser.get('about:blank')
            
            for url in chunk:
                if database.get_cologne_by_url(url):
                    continue
                    
                print(f"Scraping: {url}")
                data = await scrape_cologne_details(page, url)
                
                if data and data.get("name") != "Unknown":
                    # Note: save_cologne_data doesn't save gender in original implementation, but we added a script. 
                    # We will modify database.py to handle gender natively.
                    database.save_cologne_data(
                        name=data['name'],
                        brand=data['brand'],
                        url=data['url'],
                        notes_list=data['notes'],
                        gender=data['gender'],
                        pos_reviews=data['reviews']['positive'],
                        neu_reviews=data['reviews']['neutral'],
                        neg_reviews=data['reviews']['negative'],
                        review_texts=data['reviews']['texts']
                    )
                    has_notes = len(data['notes']) > 0
                    has_reviews = len(data['reviews']['texts'])
                    print(f"Saved: {data['brand']} - {data['name']} (Notes: {has_notes}, Review Summaries: +{data['reviews']['positive']} n{data['reviews']['neutral']} -{data['reviews']['negative']}, Text Reviews: {has_reviews})")
                else:
                    print(f"Failed to extract meaningful data from {url}")
                    
        except Exception as e:
            print(f"Chunk encountered an error: {e}")
        finally:
            if browser:
                try:
                    browser.stop()
                except Exception:
                    pass
                    
        print("Waiting 10 seconds before next chunk to cool down...")
        await asyncio.sleep(10)

if __name__ == "__main__":
    import sys
    
    # Simple CLI
    if len(sys.argv) > 1 and sys.argv[1] == "dir":
        print("Starting directory scraper...")
        uc.loop().run_until_complete(scrape_directory_pages(start_page=1, end_page=100))
    elif len(sys.argv) > 1 and sys.argv[1] == "details":
        print("Starting details scraper...")
        uc.loop().run_until_complete(run_details_scraper())
    else:
        print("Please specify 'dir' or 'details'. Example: python basenotes_crawler.py dir")
