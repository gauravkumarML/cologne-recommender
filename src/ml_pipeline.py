import sqlite3
import json
import os
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "colognes_basenotes.db")
INDEX_PATH = os.path.join(BASE_DIR, "data", "cologne_index.faiss")
MAPPING_PATH = os.path.join(BASE_DIR, "data", "cologne_mapping.json")
MODEL_NAME = 'all-MiniLM-L6-v2'

def load_data_from_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    

    query = '''
    SELECT c.id, c.name, c.brand, GROUP_CONCAT(n.name, ', ')
    FROM colognes c
    LEFT JOIN cologne_notes cn ON c.id = cn.cologne_id
    LEFT JOIN notes n ON cn.note_id = n.id
    GROUP BY c.id
    '''
    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()
    
    colognes = []
    for row in results:
        c_id, name, brand, notes_str = row
        notes = notes_str.split(', ') if notes_str else []
        colognes.append({
            "id": c_id,
            "name": name,
            "brand": brand,
            "notes": notes
        })
    return colognes

def build_index():
    print("pulling data from db...")
    colognes = load_data_from_db()
    
    if not colognes:
        print("db is empty, stopping")
        return
        
    print(f"found {len(colognes)} items, prepping text...")
    
    texts = []
    mapping = {}
    
    for i, item in enumerate(colognes):

        notes_text = ", ".join(item['notes'])
        text = f"{item['name']} features notes of {notes_text}."
        texts.append(text)
        mapping[i] = item['id']
        
    print(f"firing up model {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)
    
    print("crunching text into vectors...")
    embeddings = model.encode(texts, show_progress_bar=True)
    

    embeddings = np.array(embeddings).astype('float32')
    dimension = embeddings.shape[1]
    
    print(f"building faiss index with dimension {dimension}")
    index = faiss.IndexFlatIP(dimension)
    

    faiss.normalize_L2(embeddings)
    index.add(embeddings)
    
    print(f"saving index to {INDEX_PATH}")
    faiss.write_index(index, INDEX_PATH)
    
    print(f"saving mapping to {MAPPING_PATH}")
    with open(MAPPING_PATH, 'w') as f:
        json.dump(mapping, f)
        
    print("all done")

def search_similar(cologne_id: int, top_k: int = 5):
    if not os.path.exists(INDEX_PATH) or not os.path.exists(MAPPING_PATH):
        print("missing index/mapping, run build_index first")
        return []
        
    index = faiss.read_index(INDEX_PATH)
    with open(MAPPING_PATH, 'r') as f:
        mapping = {int(k): v for k, v in json.load(f).items()}
        

    reverse_mapping = {v: k for k, v in mapping.items()}
    if cologne_id not in reverse_mapping:
        print(f"id {cologne_id} is missing from the index")
        return []
        
    faiss_id = reverse_mapping[cologne_id]
    

    try:
        vector = index.reconstruct(faiss_id)
    except Exception as e:
        print(f"failed to grab vector: {e}")
        return []
        

    query_vector = np.array([vector]).astype('float32')
    
    distances, indices = index.search(query_vector, top_k + 1)
    
    results = []

    for i in range(1, len(indices[0])):
        idx = indices[0][i]
        dist = distances[0][i]
        db_id = mapping.get(idx)
        if db_id:
             results.append({"db_id": db_id, "distance": float(dist)})
             
    return results

def search_raw_text(query: str, index, model, top_k: int = 5):
    embedding = model.encode([query])
    embedding = np.array(embedding).astype('float32')

    faiss.normalize_L2(embedding)
    
    distances, indices = index.search(embedding, top_k)
    return distances, indices

def add_cologne(cologne_data, index, model, mapping):
    notes_text = ", ".join(cologne_data.get('notes', []))
    text = f"{cologne_data.get('name', '')} features notes of {notes_text}."
    

    embedding = model.encode([text])
    embedding = np.array(embedding).astype('float32')
    faiss.normalize_L2(embedding)
    

    index.add(embedding)
    

    new_faiss_id = index.ntotal - 1
    mapping[new_faiss_id] = cologne_data['id']
    

    faiss.write_index(index, INDEX_PATH)
    with open(MAPPING_PATH, 'w') as f:
        json.dump(mapping, f)
        
    print(f"added {cologne_data.get('name')} to the index")

if __name__ == "__main__":
    build_index()
    

    colognes = load_data_from_db()
    if colognes:
        first_id = colognes[0]['id']
        print(f"\ntesting a search for {colognes[0]['name']}")
        similar = search_similar(first_id, top_k=3)
        for s in similar:
            c = next(c for c in colognes if c['id'] == s['db_id'])
            print(f"- {c['brand']} {c['name']} (Distance: {s['distance']:.4f})")
