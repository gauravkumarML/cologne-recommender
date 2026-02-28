import sqlite3
import os

DB_PATH = "colognes.db"

def check_status():
    if not os.path.exists(DB_PATH):
        print("Database does not exist yet.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get total count
    cursor.execute("SELECT COUNT(*) FROM colognes")
    total_colognes = cursor.fetchone()[0]

    print("=======================================")
    print(f"📊 DATABASE STATUS: {total_colognes} Colognes Saved")
    print("=======================================")

    if total_colognes > 0:
        print("\nFive Most Recently Added:")
        cursor.execute("SELECT brand, name FROM colognes ORDER BY id DESC LIMIT 5")
        for brand, name in cursor.fetchall():
            print(f" - {brand}: {name}")
            
    conn.close()

if __name__ == "__main__":
    check_status()
