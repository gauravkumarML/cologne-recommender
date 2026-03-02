from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import sqlite3
import os

from ml_pipeline import DB_PATH, get_model, get_collection, search_similar, search_raw_text

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("loading up models and index...")
    try:
        get_model()
        get_collection()
        print("api is up and running")
    except Exception as e:
        print(f"Error loading models or Chroma (index might need building): {e}")
    yield
    print("shutting down...")

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
        
    return [colognes[db_id] for db_id in db_ids if db_id in colognes]

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
    matched_db_ids, match_distances = search_similar(cologne_id, top_k, gender)
    if not matched_db_ids:
        raise HTTPException(status_code=404, detail="Cologne ID not found in embedding index")
        
    colognes_data = get_cologne_details(matched_db_ids)
    
    results = []
    db_to_data = {c["id"]: c for c in colognes_data}
    
    for db_id, dist in zip(matched_db_ids, match_distances):
        col = db_to_data.get(db_id)
        if col:
            # Cosine similarity ranges from -1 to 1. Map this to 0-100%
            match_pct = min(100, max(0, round(((dist + 1.0) / 2.0) * 100)))
            results.append({"cologne": col, "match": match_pct})
            
    return results

@app.post("/recommend/quiz")
def recommend_quiz(request: QuizRequest):
    # Format the query to seamlessly match the structure of the document vectors to eliminate hubness
    gender_phrase = f"{request.gender.lower()} " if request.gender != "All" else ""
    text_query = f"Name: Ideal {request.gender if request.gender != 'All' else ''} Fragrance. Brand: Any. Notes: {request.preferences}. Reviews: I love this {gender_phrase}fragrance because it is {request.preferences}."
    matched_db_ids, match_distances = search_raw_text(text_query, request.top_k, request.gender)
    
    if not matched_db_ids:
        return []
        
    colognes_data = get_cologne_details(matched_db_ids)
    
    results = []
    db_to_data = {c["id"]: c for c in colognes_data}
    
    for db_id, dist in zip(matched_db_ids, match_distances):
        col = db_to_data.get(db_id)
        if col:
            # Cosine similarity ranges from -1 to 1. Map this to 0-100%
            match_pct = min(100, max(0, round(((dist + 1.0) / 2.0) * 100)))
            results.append({"cologne": col, "match": match_pct})
            
    return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
