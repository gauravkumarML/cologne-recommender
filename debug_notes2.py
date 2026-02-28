import asyncio
import nodriver as uc

async def debug_two():
    browser = await uc.start()
    page = await browser.get('about:blank')
    url = "https://www.parfumo.com/Perfumes/Tom_Ford/Tuscan_Leather"
    print(f"Loading {url}...")
    await page.get(url)
    await page.sleep(5)
    
    html = await page.get_content()
    with open("debug_tuscan.html", "w") as f:
        f.write(html)
        
    await browser.stop()

if __name__ == "__main__":
    uc.loop().run_until_complete(debug_two())
