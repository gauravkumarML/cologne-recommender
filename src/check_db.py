import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "colognes_basenotes.db")

def check_status():
    if not os.path.exists(DB_PATH):
        print("db missing")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    

    cursor.execute("SELECT COUNT(*) FROM colognes")
    total_colognes = cursor.fetchone()[0]

    print(f"saved {total_colognes} colognes")

    if total_colognes > 0:
        print("\nlatest 5:")
        cursor.execute("SELECT brand, name FROM colognes ORDER BY id DESC LIMIT 5")
        for brand, name in cursor.fetchall():
            print(f" - {brand}: {name}")
            
    conn.close()

if __name__ == "__main__":
    check_status()
