from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Union
import joblib
import spacy
from sentence_transformers import SentenceTransformer, util
import torch

# --- 1. SETUP ---
app = FastAPI(title="POWERGRID Helpdesk AI Engine")

# Load models only once at startup
try:
    classifier = joblib.load('model_artifacts/ticket_classifier.pkl')
    label_encoder = joblib.load('model_artifacts/label_encoder.pkl')
    nlp_ner = spacy.load('en_core_web_sm')
    similarity_model = SentenceTransformer('all-MiniLM-L6-v2')
    print("✅ All models loaded successfully.")
except FileNotFoundError:
    print("❌ Model files not found. Please run train.py first.")
    exit()

# In-memory cache for duplicate detection
RECENT_TICKETS_CACHE = []
RECENT_TICKETS_VECTORS = []
CACHE_SIZE = 50

# --- 2. Pydantic Models for Data Validation ---
class TicketText(BaseModel):
    description: str

class AnalysisResult(BaseModel):
    category: str
    entities: dict
    is_duplicate: bool
    duplicate_score: Optional[float] = None  # Fixed for Python 3.9

# --- 3. THE API ENDPOINT ---
@app.post("/ai/analyze-ticket", response_model=AnalysisResult)
async def analyze_ticket(ticket: TicketText):
    """
    Analyzes a ticket description to perform:
    1. Classification: Predicts the ticket category.
    2. Entity Recognition: Extracts key entities like products or locations.
    3. Duplicate Detection: Checks for similarity against recent tickets.
    """
    
    # --- Task 1: Classification ---
    predicted_idx = classifier.predict([ticket.description])[0]
    predicted_category = label_encoder.inverse_transform([predicted_idx])[0]

    # --- Task 2: Entity Recognition (NER) ---
    doc = nlp_ner(ticket.description)
    entities = {ent.label_: ent.text for ent in doc.ents}

    # --- Task 3: Duplicate Detection ---
    is_duplicate = False
    max_similarity = 0.0
    
    new_ticket_vector = similarity_model.encode(ticket.description, convert_to_tensor=True)

    if RECENT_TICKETS_VECTORS:
        similarities = util.pytorch_cos_sim(new_ticket_vector, torch.stack(RECENT_TICKETS_VECTORS))[0]
        max_similarity = round(torch.max(similarities).item(), 2)

        if max_similarity > 0.90:
            is_duplicate = True

    # Update the cache
    if not is_duplicate:
        RECENT_TICKETS_CACHE.append(ticket.description)
        RECENT_TICKETS_VECTORS.append(new_ticket_vector)
        if len(RECENT_TICKETS_CACHE) > CACHE_SIZE:
            RECENT_TICKETS_CACHE.pop(0)
            RECENT_TICKETS_VECTORS.pop(0)

    return AnalysisResult(
        category=predicted_category,
        entities=entities,
        is_duplicate=is_duplicate,
        duplicate_score=max_similarity if is_duplicate else None
    )

@app.get("/")
def read_root():
    return {"message": "POWERGRID AI Helpdesk Engine is running."}

@app.get("/health")
def health_check():
    return {"status": "healthy", "models_loaded": True}
