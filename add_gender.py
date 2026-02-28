import sqlite3

def add_gender_column():
    conn = sqlite3.connect("colognes.db")
    cursor = conn.cursor()
    
    # Check if gender column already exists
    cursor.execute("PRAGMA table_info(colognes)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if "gender" not in columns:
        print("Adding 'gender' column...")
        cursor.execute("ALTER TABLE colognes ADD COLUMN gender TEXT DEFAULT 'Unisex'")
    else:
        print("'gender' column already exists.")
        
    cursor.execute("SELECT id, name FROM colognes")
    rows = cursor.fetchall()
    
    update_count = 0
    for row in rows:
        cid, name = row
        name_lower = name.lower()
        
        # Naive keyword matching for gender since we didn't scrape it
        if any(word in name_lower for word in ['pour homme', ' men', 'man', 'boy', 'him']):
            gender = 'Male'
        elif any(word in name_lower for word in ['pour femme', 'women', 'woman', 'girl', 'her', 'mademoiselle', 'donna']):
            gender = 'Female'
        else:
            gender = 'Unisex'
            
        cursor.execute("UPDATE colognes SET gender = ? WHERE id = ?", (gender, cid))
        update_count += 1
        
    conn.commit()
    conn.close()
    print(f"Updated {update_count} colognes with inferred gender.")

if __name__ == "__main__":
    add_gender_column()
