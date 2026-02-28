import sqlite3
import os
import json

DB_PATH = "colognes.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create colognes table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS colognes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        brand TEXT NOT NULL,
        url TEXT UNIQUE NOT NULL,
        gender TEXT DEFAULT 'Unisex',
        positive_reviews INTEGER DEFAULT 0,
        neutral_reviews INTEGER DEFAULT 0,
        negative_reviews INTEGER DEFAULT 0,
        review_texts TEXT DEFAULT '[]'
    )
    ''')
    
    # Create notes table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )
    ''')
    
    # Create mapping table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS cologne_notes (
        cologne_id INTEGER,
        note_id INTEGER,
        FOREIGN KEY (cologne_id) REFERENCES colognes (id),
        FOREIGN KEY (note_id) REFERENCES notes (id),
        UNIQUE (cologne_id, note_id)
    )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized.")

def get_cologne_by_url(url: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, brand FROM colognes WHERE url = ?", (url,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {"id": result[0], "name": result[1], "brand": result[2], "url": url}
    return None

def save_cologne_data(name, brand, url, notes_list, gender="Unisex", pos_reviews=0, neu_reviews=0, neg_reviews=0, review_texts=None):
    if review_texts is None:
        review_texts = []
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Insert or ignore cologne
        cursor.execute('''
        INSERT OR IGNORE INTO colognes (name, brand, url, gender, positive_reviews, neutral_reviews, negative_reviews, review_texts) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, brand, url, gender, pos_reviews, neu_reviews, neg_reviews, json.dumps(review_texts)))
        
        # Get cologne ID
        cursor.execute("SELECT id FROM colognes WHERE url = ?", (url,))
        result = cursor.fetchone()
        if not result:
             return
        cologne_id = result[0]
        
        # Insert notes and mappings
        for note in notes_list:
            # Insert or ignore note
            cursor.execute("INSERT OR IGNORE INTO notes (name) VALUES (?)", (note,))
            
            # Get note ID
            cursor.execute("SELECT id FROM notes WHERE name = ?", (note,))
            res = cursor.fetchone()
            if res:
                note_id = res[0]
                # Map them
                cursor.execute("INSERT OR IGNORE INTO cologne_notes (cologne_id, note_id) VALUES (?, ?)", (cologne_id, note_id))
        
        conn.commit()
    except Exception as e:
        print(f"Error saving data for {name}: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
