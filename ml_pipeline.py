import sqlite3
import json
import os
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

DB_PATH = "colognes.db"
INDEX_PATH = "cologne_index.faiss"
MAPPING_PATH = "cologne_mapping.json"
MODEL_NAME = 'all-MiniLM-L6-v2' # Fast and efficient sentence transformer

def load_data_from_db():
    """Loads all colognes and their notes from the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Query to get colognes and their notes concatenated
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
    print("Loading data from database...")
    colognes = load_data_from_db()
    
    if not colognes:
        print("No colognes found in database. Exiting.")
        return
        
    print(f"Loaded {len(colognes)} colognes. Preparing text for embedding...")
    
    texts = []
    mapping = {}
    
    for i, item in enumerate(colognes):
        # De-weight the brand, rely strictly on olfactory profile
        notes_text = ", ".join(item['notes'])
        text = f"{item['name']} features notes of {notes_text}."
        texts.append(text)
        mapping[i] = item['id']
        
    print(f"Loading SentenceTransformer model: {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)
    
    print("Encoding texts into vectors...")
    embeddings = model.encode(texts, show_progress_bar=True)
    
    # Convert to float32 numpy array as FAISS expects this
    embeddings = np.array(embeddings).astype('float32')
    dimension = embeddings.shape[1]
    
    print(f"Building FAISS Index with dimension {dimension} using Inner Product...")
    index = faiss.IndexFlatIP(dimension)
    
    # Normalize vectors for cosine similarity (L2 norm)
    faiss.normalize_L2(embeddings)
    index.add(embeddings)
    
    print(f"Saving FAISS index to {INDEX_PATH}...")
    faiss.write_index(index, INDEX_PATH)
    
    print(f"Saving mapping to {MAPPING_PATH}...")
    with open(MAPPING_PATH, 'w') as f:
        json.dump(mapping, f)
        
    print("Indexing complete!")

def search_similar(cologne_id: int, top_k: int = 5):
    """Utility function to search for similar colognes given a DB id."""
    if not os.path.exists(INDEX_PATH) or not os.path.exists(MAPPING_PATH):
        print("Index or mapping not found. Run build_index() first.")
        return []
        
    index = faiss.read_index(INDEX_PATH)
    with open(MAPPING_PATH, 'r') as f:
        mapping = {int(k): v for k, v in json.load(f).items()}
        
    # Reverse mapping to find the faiss index id
    reverse_mapping = {v: k for k, v in mapping.items()}
    if cologne_id not in reverse_mapping:
        print(f"Cologne ID {cologne_id} not found in index.")
        return []
        
    faiss_id = reverse_mapping[cologne_id]
    
    # Get the embedding for this specific item directly from the faiss index
    # We must reconstruct the vector. Wait, IndexFlatL2 supports reconstruction.
    try:
        vector = index.reconstruct(faiss_id)
    except Exception as e:
        print(f"Cannot reconstruct vector: {e}")
        return []
        
    # Reshape for search
    query_vector = np.array([vector]).astype('float32')
    
    # Search
    distances, indices = index.search(query_vector, top_k + 1) # +1 because it matches itself
    
    results = []
    # Skip the first one because it's the queried item itself
    for i in range(1, len(indices[0])):
        idx = indices[0][i]
        dist = distances[0][i]
        db_id = mapping.get(idx)
        if db_id:
             results.append({"db_id": db_id, "distance": float(dist)})
             
    return results

def search_raw_text(query: str, index, model, top_k: int = 5):
    """Embeds a single text query, normalizes it, and passes it to index.search()"""
    embedding = model.encode([query])
    embedding = np.array(embedding).astype('float32')
    # Must normalize query for inner product / cosine similarity
    faiss.normalize_L2(embedding)
    
    distances, indices = index.search(embedding, top_k)
    return distances, indices

def add_cologne(cologne_data, index, model, mapping):
    """
    Appends a single new embedding to the existing FAISS index in memory 
    and updates the JSON mapping without rebuilding the entire index.
    cologne_data should be a dict like: {'id': 999, 'name': '...", 'notes': ['...']}
    """
    notes_text = ", ".join(cologne_data.get('notes', []))
    text = f"{cologne_data.get('name', '')} features notes of {notes_text}."
    
    # Embed and normalize
    embedding = model.encode([text])
    embedding = np.array(embedding).astype('float32')
    faiss.normalize_L2(embedding)
    
    # Add to index
    index.add(embedding)
    
    # Update mapping
    new_faiss_id = index.ntotal - 1
    mapping[new_faiss_id] = cologne_data['id']
    
    # Save back to disk
    faiss.write_index(index, INDEX_PATH)
    with open(MAPPING_PATH, 'w') as f:
        json.dump(mapping, f)
        
    print(f"Successfully added {cologne_data.get('name')} to index and updated mapping.")

if __name__ == "__main__":
    build_index()
    
    # Test search on the first cologne
    colognes = load_data_from_db()
    if colognes:
        first_id = colognes[0]['id']
        print(f"\nTesting search for: {colognes[0]['brand']} {colognes[0]['name']}")
        similar = search_similar(first_id, top_k=3)
        for s in similar:
            c = next(c for c in colognes if c['id'] == s['db_id'])
            print(f"- {c['brand']} {c['name']} (Distance: {s['distance']:.4f})")
