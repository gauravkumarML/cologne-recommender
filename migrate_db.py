import sqlite3

DB_PATH = "colognes.db"

def run_migrations():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    queries = [
        "ALTER TABLE colognes ADD COLUMN positive_reviews INTEGER DEFAULT 0",
        "ALTER TABLE colognes ADD COLUMN neutral_reviews INTEGER DEFAULT 0",
        "ALTER TABLE colognes ADD COLUMN negative_reviews INTEGER DEFAULT 0",
        "ALTER TABLE colognes ADD COLUMN review_texts TEXT DEFAULT '[]'"
    ]
    
    for query in queries:
        try:
            cursor.execute(query)
            print(f"Success: {query}")
        except sqlite3.OperationalError as e:
            print(f"Skipped: {query} -> {e}")
            
    conn.commit()
    conn.close()

if __name__ == "__main__":
    run_migrations()
