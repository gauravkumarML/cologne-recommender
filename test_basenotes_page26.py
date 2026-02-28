import asyncio
import nodriver as uc

async def test_page26():
    browser = await uc.start()
    page = await browser.get('about:blank')
    
    url = "https://basenotes.com/directory/?search=&type=all&page=26"
    print(f"Loading {url}...")
    await page.get(url)
    await page.sleep(10)
    
    html = await page.get_content()
    with open("basenotes_page26.html", "w") as f:
        f.write(html)
        
    print("Saved to basenotes_page26.html")
    try:
        browser.stop()
    except Exception:
        pass

if __name__ == "__main__":
    uc.loop().run_until_complete(test_page26())
