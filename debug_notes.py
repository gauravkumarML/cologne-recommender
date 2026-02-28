import asyncio
import nodriver as uc
from bs4 import BeautifulSoup

async def debug_one():
    browser = await uc.start(headless=False)
    page = await browser.get('about:blank')
    
    url = "https://www.parfumo.com/Perfumes/Dior/dior-homme-2020-eau-de-toilette"
    print(f"Loading {url}...")
    
    await page.get(url)
    await page.sleep(5) # Let cloudflare pass
    
    html = await page.get_content()
    with open("debug_dior_homme.html", "w") as f:
        f.write(html)
        
    soup = BeautifulSoup(html, 'html.parser')
    
    # Try finding notes in different ways
    print("--- Searching for notes ---")
    
    # Look for the word "Notes" or similar headers
    for h in soup.find_all(['h2', 'h3', 'div']):
        if h.text and 'Fragrance Notes' in h.text:
            print(f"Found Fragrance Notes Header: {h}")
            # print parent or siblings
            
    print("Saved HTML to debug_dior_homme.html for manual inspection if needed.")
    
    await browser.stop()

if __name__ == "__main__":
    uc.loop().run_until_complete(debug_one())
