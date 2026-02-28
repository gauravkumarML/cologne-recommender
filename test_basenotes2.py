import asyncio
import nodriver as uc

async def test_basenotes2():
    browser = await uc.start()
    page = await browser.get('about:blank')
    
    item_url = "https://basenotes.com/fragrances/aventus-by-creed.26131702"
    print(f"Loading item: {item_url}")
    await page.get(item_url)
    await page.sleep(5)
    
    item_html = await page.get_content()
    with open("basenotes_item.html", "w") as f:
        f.write(item_html)
        
    print("Saved item HTML to basenotes_item.html")
        
    await browser.stop()

if __name__ == "__main__":
    uc.loop().run_until_complete(test_basenotes2())
