import httpx
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel
from typing import List, Optional

# --- Database Configuration ---
DATABASE_URL = "postgresql://postgres:root@localhost/powergrid_helpdesk"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- Microservice URLs ---
AI_MICROSERVICE_URL = "http://localhost:8001/predict"
RASA_SERVER_URL = "http://localhost:5005/webhooks/rest/webhook"

app = FastAPI(title="PowerGrid IT Helpdesk API", version="1.0")

# --- Pydantic Models (Data Schemas) ---
class TicketCreate(BaseModel):
    title: str
    description: str
    created_by_user_id: int
    priority: Optional[str] = 'Medium'

class Ticket(BaseModel):
    id: int
    title: str
    description: str
    status: str
    priority: str
    category: Optional[str] = None
    created_by_user_id: int
    assigned_to_user_id: Optional[int] = None

    class Config:
        from_attributes = True

class ChatMessage(BaseModel):
    sender: str
    message: str

# --- Database Dependency ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- API Endpoints ---

@app.get("/")
def read_root():
    return {"message": "Welcome to the PowerGrid IT Helpdesk API"}

@app.post("/api/tickets", response_model=Ticket)
async def create_ticket(ticket: TicketCreate, db: Session = Depends(get_db)):
    """
    Creates a new ticket, classifies it using the AI microservice,
    and intelligently assigns it to an agent.
    """
    try:
        # 1. Call AI Microservice to get the category
        async with httpx.AsyncClient() as client:
            response = await client.post(AI_MICROSERVICE_URL, json={"text": ticket.description})
            response.raise_for_status()
            category = response.json().get("category")

        # 2. Find the best agent for this category (experience-based routing)
        # This query finds an agent who has previously resolved a ticket of the same category.
        query = text("""
            SELECT assigned_to_user_id FROM tickets
            WHERE category = :cat AND status = 'Resolved' AND assigned_to_user_id IS NOT NULL
            GROUP BY assigned_to_user_id
            ORDER BY COUNT(*) DESC
            LIMIT 1;
        """)
        result = db.execute(query, {"cat": category}).fetchone()
        assigned_agent_id = result[0] if result else None
        
        # Fallback: If no experienced agent is found, assign to L1 Service Desk
        if not assigned_agent_id:
            query = text("SELECT id FROM users WHERE department_id = (SELECT id FROM departments WHERE name = 'L1 Service Desk') LIMIT 1;")
            result = db.execute(query).fetchone()
            assigned_agent_id = result[0] if result else 1 # Default to user 1 if no one is in L1

        # 3. Create the new ticket in the database
        insert_query = text("""
            INSERT INTO tickets (title, description, priority, category, created_by_user_id, assigned_to_user_id)
            VALUES (:title, :description, :priority, :category, :created_by_user_id, :assigned_to_user_id)
            RETURNING id, title, description, status, priority, category, created_by_user_id, assigned_to_user_id;
        """)
        new_ticket_data = db.execute(insert_query, {
            "title": ticket.title,
            "description": ticket.description,
            "priority": ticket.priority,
            "category": category,
            "created_by_user_id": ticket.created_by_user_id,
            "assigned_to_user_id": assigned_agent_id
        }).fetchone()

        db.commit()

        return new_ticket_data

    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="AI microservice is unavailable.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {e}")


@app.get("/api/tickets", response_model=List[Ticket])
def get_all_tickets(db: Session = Depends(get_db)):
    """
    Retrieves all tickets from the database.
    """
    result = db.execute(text("SELECT * FROM tickets;")).fetchall()
    return result

@app.post("/api/chatbot/message")
async def chat_with_bot(message: ChatMessage):
    """
    Forwards a user's message to the Rasa chatbot and returns its response.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                RASA_SERVER_URL,
                json={"sender": message.sender, "message": message.message},
                timeout=60
            )
            response.raise_for_status()
            return response.json()
            
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="The chatbot service is unavailable.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
