import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from bs4 import BeautifulSoup
import database

# Initialize stealth to reuse configurations
stealth = Stealth()

async def scrape_cologne_details(context, url: str):
    """Scrapes a single cologne page using an existing browser context."""
    page = await context.new_page()
    # Apply stealth
    await stealth.apply_stealth_async(page)
    
    data = {"url": url, "brand": "Unknown", "name": "Unknown", "notes": []}
    
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        # Small random pause to look human and bypass basic checks
        await asyncio.sleep(random.uniform(3, 6))
        
        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        # 1. Name & Brand
        brand_elem = soup.select_one('span[itemprop="brand"] span[itemprop="name"]')
        if brand_elem:
            data['brand'] = brand_elem.text.strip()
            
        h1_elem = soup.find('h1', itemprop='name')
        if h1_elem and h1_elem.contents:
            # First text node is typically the name
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
    finally:
        await page.close()
        
    return data

import random

async def scrape_with_semaphore(semaphore, context, url):
    """Wrapper to limit concurrency and add jitter."""
    async with semaphore:
        # Add random jitter (2 to 6 seconds) before jumping into the scrape
        jitter = random.uniform(2.0, 6.0)
        print(f"Jitter sleeping for {jitter:.2f}s before scraping: {url}")
        await asyncio.sleep(jitter)
        
        cologne_data = await scrape_cologne_details(context, url)
        
        if cologne_data['name'] != "Unknown":
            print(f"Saving -> {cologne_data['brand']} {cologne_data['name']} with {len(cologne_data['notes'])} notes")
            database.save_cologne_data(
                name=cologne_data['name'],
                brand=cologne_data['brand'],
                url=cologne_data['url'],
                notes_list=cologne_data['notes']
            )
        else:
            print(f"Skipping {url} due to incomplete data.")

async def crawl_brand(brand_url: str, limit: int = 50, max_concurrent: int = 3):
    print(f"Starting crawl for brand: {brand_url} with max concurrency {max_concurrent}")
    brand_slug = brand_url.split('/')[-1]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        
        page = await context.new_page()
        # Apply stealth
        await stealth.apply_stealth_async(page)
        
        try:
            await page.goto(brand_url, wait_until="domcontentloaded", timeout=45000)
            # Crucial: sleep to allow Cloudflare-like challenges to resolve
            await asyncio.sleep(10)
            
            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find all cologne links
            all_links = soup.find_all('a', href=True)
            cologne_links = set()
            brand_pat = f"/Perfumes/{brand_slug}/".lower()
            
            for a_tag in all_links:
                href = a_tag['href']
                lower_href = href.lower()
                
                # Check for either relative or absolute links to this brand's perfumes
                if brand_pat in lower_href or f"/{brand_slug.lower()}/" in lower_href:
                    # Filter out non-perfume pages
                    if not any(sub in lower_href for sub in ["/reviews", "/statements", "/prices", "/souks", "release_years", "/brands", "?v="]):
                        # Standardize to absolute
                        full_url = href if href.startswith("http") else f"https://www.parfumo.com{href}"
                        # Ensure it's deep enough to be a perfume page (at least 5 segments)
                        if len(full_url.split('/')) >= 6:
                            cologne_links.add(full_url)
            
            links_list = list(cologne_links)[:limit]
            print(f"Found {len(links_list)} colognes for {brand_slug}.")
            await page.close()
            
            # Create a semaphore to control concurrency
            semaphore = asyncio.Semaphore(max_concurrent)
            
            # Create concurrent tasks
            tasks = [scrape_with_semaphore(semaphore, context, link) for link in links_list]
            
            # Run tasks concurrently
            await asyncio.gather(*tasks)
            
        except Exception as e:
            print(f"Error crawling brand: {e}")
        finally:
            await browser.close()
            
if __name__ == "__main__":
    database.init_db()
    
    # Run a test crawl for Dior using concurrency
    asyncio.run(crawl_brand("https://www.parfumo.com/Perfumes/Dior", limit=10, max_concurrent=3))
