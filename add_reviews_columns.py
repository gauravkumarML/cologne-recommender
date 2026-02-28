import sqlite3

DB_PATH = "colognes_basenotes.db"

def add_reviews_columns():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE colognes ADD COLUMN positive_reviews INTEGER DEFAULT 0")
        cursor.execute("ALTER TABLE colognes ADD COLUMN neutral_reviews INTEGER DEFAULT 0")
        cursor.execute("ALTER TABLE colognes ADD COLUMN negative_reviews INTEGER DEFAULT 0")
        print("Successfully added review columns to colognes_basenotes.db")
    except sqlite3.OperationalError as e:
        print(f"OperationalError: {e} (Columns might already exist)")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    add_reviews_columns()
