import sqlite3

DB_PATH = "colognes_basenotes.db"

def add_review_texts_column():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE colognes ADD COLUMN review_texts TEXT DEFAULT '[]'")
        print("Successfully added review_texts column to colognes_basenotes.db")
    except sqlite3.OperationalError as e:
        print(f"OperationalError: {e} (Column might already exist)")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    add_review_texts_column()
