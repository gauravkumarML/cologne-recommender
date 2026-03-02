import sqlite3
import asyncio
import os
import random
from bs4 import BeautifulSoup
import nodriver as uc

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "colognes_basenotes.db")

async def scrape_missing_notes(page, url):
    notes = []
    try:
        # Crucial: set a strict timeout so a single bad URL redirect loop doesn't hang the worker
        await asyncio.wait_for(page.get(url), timeout=15.0)
        
        # Jitter to avoid bot detection triggering
        await asyncio.sleep(random.uniform(5, 8))
        
        # Try to dismiss the consent popup
        try:
            btns = await page.find_elements('.fc-button')
            if btns:
                for btn in btns:
                    text_val = await btn.get_text()
                    if text_val == 'Consent':
                        await btn.click()
                        await asyncio.sleep(2)
                        break
        except:
            pass
            
        html = await page.get_content()
        soup = BeautifulSoup(html, 'html.parser')
        
        notes_container = soup.find('ul', class_='fragrancenotes')
        if notes_container:
            text = notes_container.get_text(separator=',')
            extracted = [x.strip() for x in text.split(',') if x.strip()]
            notes.extend(extracted)
        return notes, True # Success
        print(f"  -> Timeout loading page.")
        return [], False
    except Exception as e:
        print(f"  -> Browser error: {str(e)[:100]}")
        return [], False

async def patch_missing_colognes():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT c.id, c.name, c.url 
        FROM colognes c 
        LEFT JOIN cologne_notes cn ON c.id = cn.cologne_id 
        WHERE cn.note_id IS NULL
    ''')
    missing = cursor.fetchall()
    
    print(f"Found {len(missing)} colognes completely missing notes.")
    print("NOTE: The first few colognes in this queue (e.g. Tana by Tana, Good Girl) GENUINELY have no notes on their website pages. Please let the script run and it will catch the ones that do!")
    
    if not missing:
        conn.close()
        return
        
    # Start the browser with robust arguments to prevent WebSocket crashes
    browser = await uc.start(
        headless=False,
        browser_args=[
            '--disable-web-security', 
            '--disable-features=IsolateOrigins,site-per-process', 
            '--no-sandbox', 
            '--disable-dev-shm-usage'
        ]
    )
    
    page = await browser.get('about:blank')
    success_count = 0
    
    try:
        for i, (c_id, name, url) in enumerate(missing):
            print(f"[{i+1}/{len(missing)}] Healing {name}...")
            
            notes, success = await scrape_missing_notes(page, url)
            
            if notes:
                for note in notes:
                    cursor.execute("INSERT OR IGNORE INTO notes (name) VALUES (?)", (note,))
                    cursor.execute("SELECT id FROM notes WHERE name = ?", (note,))
                    res = cursor.fetchone()
                    if res:
                        note_id = res[0]
                        cursor.execute("INSERT OR IGNORE INTO cologne_notes (cologne_id, note_id) VALUES (?, ?)", (c_id, note_id))
                
                conn.commit()
                print(f"  -> Added {len(notes)} notes: {', '.join(notes)}")
                success_count += 1
            elif success:
                print("  -> Page genuinely has no notes listed.")
            
            # Restart browser every 50 to clear memory and prevent websocket crashes
            if (i + 1) % 50 == 0:
                print("--- Deep cleaning browser memory to prevent crash ---")
                try:
                    browser.stop()
                except:
                    pass
                await asyncio.sleep(5)
                browser = await uc.start(
                    headless=False,
                    browser_args=[
                        '--disable-web-security', 
                        '--disable-features=IsolateOrigins,site-per-process', 
                        '--no-sandbox', 
                        '--disable-dev-shm-usage'
                    ]
                )
                page = await browser.get('about:blank')
                
    except Exception as e:
        print(f"Fatal patch error: {e}")
    finally:
        try:
            browser.stop()
        except:
            pass
        conn.close()
        print(f"Patch complete. Recovered notes for {success_count} fragrances.")

if __name__ == "__main__":
    uc.loop().run_until_complete(patch_missing_colognes())
