import csv
import sys
import os
import chromadb
from sentence_transformers import SentenceTransformer

csv.field_size_limit(sys.maxsize)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(BASE_DIR, "src", "cleaned_data.csv")
CHROMA_DB_PATH = os.path.join(BASE_DIR, "data", "chroma_db")
DB_PATH = os.path.join(BASE_DIR, "data", "colognes_basenotes.db")
MODEL_NAME = 'all-MiniLM-L6-v2'

_model = None
_chroma_client = None
_collection = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model

def get_collection():
    global _chroma_client, _collection
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    if _collection is None:
        _collection = _chroma_client.get_collection(name="colognes")
    return _collection

def load_data_from_csv():
    colognes = []
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                popularity = float(row['popularity']) if row['popularity'] else 0.0
            except:
                popularity = 0.0
            
            try:
                positive_reviews = float(row.get('positive_reviews', 0.0)) if row.get('positive_reviews') else 0.0
            except:
                positive_reviews = 0.0

            colognes.append({
                "id": str(row['id']),
                "name": row['name'],
                "brand": row['brand'],
                "gender": row['gender'],
                "popularity": popularity,
                "positive_reviews": positive_reviews,
                "review_texts": row.get('review_texts', ''),
                "notes": row.get('cleaned_notes', '')
            })
    return colognes

def build_index():
    print("Pulling data from CSV...")
    if not os.path.exists(CSV_PATH):
        print(f"CSV not found at {CSV_PATH}")
        return
        
    colognes = load_data_from_csv()
    if not colognes:
        print("Data is empty, stopping.")
        return
        
    print(f"Found {len(colognes)} items, prepping texts and metadata...")
    
    docs = []
    metadatas = []
    ids = []
    
    for item in colognes:
        notes_text = item['notes']
        words = item['review_texts'].split()
        truncated_reviews = " ".join(words[:150]) # Truncate to ~150 words
        text = f"Name: {item['name']}. Brand: {item['brand']}. Notes: {notes_text}. Reviews: {truncated_reviews}"
        docs.append(text)
        # Store metadata for hard-filtering
        metadatas.append({
            "name": item['name'],
            "brand": item['brand'],
            "gender": item['gender'],
            "popularity": item['popularity'],
            "positive_reviews": item['positive_reviews']
        })
        ids.append(item['id'])
        
    print(f"Firing up model {MODEL_NAME}...")
    model = get_model()
    
    print("Crunching text into vectors... This might take a while.")
    embeddings = model.encode(docs, show_progress_bar=True)
    
    print(f"Storing into ChromaDB at {CHROMA_DB_PATH}...")
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    
    try:
        client.delete_collection(name="colognes")
    except:
        pass
        
    collection = client.create_collection(
        name="colognes",
        metadata={"hnsw:space": "cosine"}
    )
    
    batch_size = 1000
    for i in range(0, len(ids), batch_size):
        end = min(i + batch_size, len(ids))
        collection.add(
            ids=ids[i:end],
            embeddings=embeddings[i:end].tolist(),
            metadatas=metadatas[i:end],
            documents=docs[i:end]
        )
        print(f"Added batch {i} to {end}...")
        
    print("All done building ChromaDB index!")

def _format_results(search_results, exclude_id, top_k):
    if not search_results['ids'] or not search_results['ids'][0]:
        return [], []
        
    ids = search_results['ids'][0]
    distances = search_results['distances'][0]
    
    matched_db_ids = []
    match_distances = []
    
    for i in range(len(ids)):
        if exclude_id and ids[i] == exclude_id:
            continue
            
        # ChromaDB cosine distance: 0 is identical, 1 is orthogonal, 2 is opposite
        # Similarity = 1 - distance
        dist = distances[i]
        sim = 1.0 - dist
        
        matched_db_ids.append(int(ids[i]))
        match_distances.append(float(sim))
        
        if len(matched_db_ids) >= top_k:
            break
            
    return matched_db_ids, match_distances

def search_similar(cologne_id: int, top_k: int = 5, gender: str = "All"):
    collection = get_collection()
    
    # Get the embedding for this specific ID
    result = collection.get(
        ids=[str(cologne_id)],
        include=["embeddings"]
    )
    
    embeddings_result = result.get('embeddings')
    if embeddings_result is None or len(embeddings_result) == 0 or embeddings_result[0] is None:
        print(f"ID {cologne_id} missing from the index")
        return [], []
        
    query_embedding = embeddings_result[0]
    
    search_results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k + 1
    )
    
    return _format_results(search_results, exclude_id=str(cologne_id), top_k=top_k)

def search_raw_text(query: str, top_k: int = 5, gender: str = "All"):
    model = get_model()
    collection = get_collection()
    
    query_embedding = model.encode([query])[0]
    
    search_results = collection.query(
        query_embeddings=[query_embedding.tolist()],
        n_results=top_k
    )
    
    return _format_results(search_results, exclude_id=None, top_k=top_k)

if __name__ == "__main__":
    build_index()
    print("\nTesting a search for ID 1")
    # Warm up globals
    get_model()
    get_collection()
    ids, dists = search_similar(1, top_k=5)
    for i, d in zip(ids, dists):
        print(f"Matched ID: {i} Distance: {d:.4f}")
