import asyncio
import nodriver as uc

async def test_basenotes():
    browser = await uc.start()
    page = await browser.get('about:blank')
    
    dir_url = "https://basenotes.com/directory/?search=&type=all"
    print(f"Loading directory: {dir_url}")
    await page.get(dir_url)
    
    # Wait for Cloudflare or page render
    await page.sleep(10)
    
    html = await page.get_content()
    with open("basenotes_dir.html", "w") as f:
        f.write(html)
        
    print("Saved directory HTML to basenotes_dir.html")
    
    # Let's see if we can jump to a popular item (e.g. Aventus)
    item_url = "https://basenotes.com/fragrances/aventus-by-creed.26131650"
    print(f"Loading item: {item_url}")
    await page.get(item_url)
    await page.sleep(5)
    
    item_html = await page.get_content()
    with open("basenotes_item.html", "w") as f:
        f.write(item_html)
        
    print("Saved item HTML to basenotes_item.html")
        
    await browser.stop()

if __name__ == "__main__":
    uc.loop().run_until_complete(test_basenotes())
