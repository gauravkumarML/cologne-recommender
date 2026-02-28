from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import sqlite3
import json
import os
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

from ml_pipeline import DB_PATH, INDEX_PATH, MAPPING_PATH, MODEL_NAME

from contextlib import asynccontextmanager

# Global variables for the ML model and index
model = None
index = None
id_mapping = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, index, id_mapping
    print("Loading ML models and FAISS index...")
    
    if not os.path.exists(INDEX_PATH) or not os.path.exists(MAPPING_PATH):
        raise RuntimeError("FAISS index or mapping not found. Run ml_pipeline.py first.")
        
    index = faiss.read_index(INDEX_PATH)
    
    with open(MAPPING_PATH, 'r') as f:
        # Convert string keys back to int
        id_mapping = {int(k): v for k, v in json.load(f).items()}
        
    model = SentenceTransformer(MODEL_NAME)
    print("API is ready to serve recommendations.")
    yield
    print("Shutting down API...")

app = FastAPI(lifespan=lifespan, title="Cologne Recommender API")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_root():
    return FileResponse("static/index.html")

class QuizRequest(BaseModel):
    preferences: str
    top_k: int = 5
    gender: str = "All"

def get_cologne_details(db_ids):
    if not db_ids:
        return []
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    placeholders = ','.join('?' * len(db_ids))
    query = f'''
    SELECT c.id, c.name, c.brand, c.url, c.gender, GROUP_CONCAT(n.name, ', ')
    FROM colognes c
    LEFT JOIN cologne_notes cn ON c.id = cn.cologne_id
    LEFT JOIN notes n ON cn.note_id = n.id
    WHERE c.id IN ({placeholders})
    GROUP BY c.id
    '''
    
    cursor.execute(query, db_ids)
    results = cursor.fetchall()
    conn.close()
    
    colognes = {}
    for row in results:
        notes = row[5].split(', ') if row[5] else []
        colognes[row[0]] = {
            "id": row[0],
            "name": row[1],
            "brand": row[2],
            "url": row[3],
            "gender": row[4],
            "notes": notes
        }
        
    # Return in the order of db_ids
    return [colognes[db_id] for db_id in db_ids if db_id in colognes]

@app.get("/")
def read_root():
    return {"message": "Welcome to the Scent Matcher API."}

@app.get("/colognes")
def list_colognes(limit: int = 50):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, brand FROM colognes LIMIT ?", (limit,))
    results = [{"id": r[0], "name": r[1], "brand": r[2]} for r in cursor.fetchall()]
    conn.close()
    return results

@app.get("/recommend/similar/{cologne_id}")
def recommend_similar(cologne_id: int, top_k: int = 5, gender: str = "All"):
    """Pathway 1: Direct match based on a known cologne ID."""
    reverse_mapping = {v: k for k, v in id_mapping.items()}
    if cologne_id not in reverse_mapping:
        raise HTTPException(status_code=404, detail="Cologne ID not found in embedding index")
        
    faiss_id = reverse_mapping[cologne_id]
    
    try:
        vector = index.reconstruct(faiss_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reconstructing vector: {e}")
        
    query_vector = np.array([vector]).astype('float32')
    
    # Pre-fetch more candidates to account for potential filtering
    fetch_k = top_k * 5 if gender != "All" else top_k
    distances, indices = index.search(query_vector, fetch_k + 1)
    
    matched_db_ids = []
    match_distances = []
    
    for i in range(1, len(indices[0])):
        idx = indices[0][i]
        db_id = id_mapping.get(idx)
        if db_id:
            matched_db_ids.append(db_id)
            match_distances.append(float(distances[0][i]))
            
    colognes_data = get_cologne_details(matched_db_ids)
    
    results = []
    for col, dist in zip(colognes_data, match_distances):
        if gender != "All" and col.get("gender") != gender:
            continue
        # Convert Inner Product to generic Match % (0-100)
        match_pct = round(max(0, dist) * 100)
        results.append({"cologne": col, "match": match_pct})
        if len(results) >= top_k:
            break
            
    return results

@app.post("/recommend/quiz")
def recommend_quiz(request: QuizRequest):
    """Pathway 2: General text/preferences search using search_raw_text."""
    from ml_pipeline import search_raw_text
    
    text_query = f"Looking for a fragrance with these qualities: {request.preferences}"
    fetch_k = request.top_k * 5 if request.gender != "All" else request.top_k
    distances, indices = search_raw_text(text_query, index, model, fetch_k)
    
    matched_db_ids = []
    match_distances = []
    for i in range(len(indices[0])):
        idx = indices[0][i]
        db_id = id_mapping.get(idx)
        if db_id:
            matched_db_ids.append(db_id)
            match_distances.append(float(distances[0][i]))
            
    colognes_data = get_cologne_details(matched_db_ids)
    
    results = []
    for col, dist in zip(colognes_data, match_distances):
        if request.gender != "All" and col.get("gender") != request.gender:
            continue
        match_pct = round(max(0, dist) * 100)
        results.append({"cologne": col, "match": match_pct})
        if len(results) >= request.top_k:
            break
            
    return results

