import asyncio
import json
import random
import os
import nodriver as uc
from bs4 import BeautifulSoup
import database

async def scrape_cologne_details(page, url):
    data = {"url": url, "brand": "Unknown", "name": "Unknown", "notes": []}
    
    try:
        await page.get(url)
        # Random sleep for jitter and Cloudflare processing
        await page.sleep(random.uniform(4, 7))
        
        html = await page.get_content()
        soup = BeautifulSoup(html, 'html.parser')
        
        # 1. Name & Brand
        brand_elem = soup.select_one('span[itemprop="brand"] span[itemprop="name"]')
        if brand_elem:
            data['brand'] = brand_elem.text.strip()
            
        h1_elem = soup.find('h1', itemprop='name')
        if h1_elem and h1_elem.contents:
            data['name'] = h1_elem.contents[0].strip()
            
        # 2. Fragrance Notes
        notes_div = soup.find('div', class_='nb_n')
        if notes_div:
            imgs = notes_div.find_all('img')
            for img in imgs:
                if 'alt' in img.attrs and img['alt']:
                    data['notes'].append(img['alt'].strip())
                    
    except Exception as e:
        print(f"Failed to scrape {url}: {e}")
        
    return data

async def run_list_scraper(url_list_path: str):
    database.init_db()
    
    if not os.path.exists(url_list_path):
        print(f"Error: {url_list_path} not found.")
        return
        
    with open(url_list_path, 'r') as f:
        urls = json.load(f)
    
    # Filter pending urls
    pending_urls = [u for u in urls if not database.get_cologne_by_url(u)]
    print(f"Remaining URLs to scrape: {len(pending_urls)}")
    
    chunk_size = 15
    for i in range(0, len(pending_urls), chunk_size):
        chunk = pending_urls[i:i+chunk_size]
        print(f"--- Processing chunk {i//chunk_size + 1} of {(len(pending_urls)//chunk_size) + 1} ---")
        
        browser = None
        try:
            # We run sequentially and visible (headless=False)
            browser = await uc.start(headless=False)
            page = await browser.get('about:blank')
            
            for url in chunk:
                if database.get_cologne_by_url(url):
                    continue
                    
                print(f"Scraping: {url}")
                data = await scrape_cologne_details(page, url)
                
                if data and data.get("name") != "Unknown":
                    database.save_cologne_data(
                        name=data['name'],
                        brand=data['brand'],
                        url=data['url'],
                        notes_list=data['notes']
                    )
                    print(f"Saved: {data['brand']} - {data['name']}")
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
    uc.loop().run_until_complete(run_list_scraper("cologne_urls.json"))
