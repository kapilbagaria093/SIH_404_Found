# In /main_api_server/main.py
import httpx
from fastapi import FastAPI
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

app = FastAPI(title="POWERGRID Main API")

DATABASE_URL = "postgresql://postgres:kapilpostgres@localhost/powergrid_helpdesk"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

AI_MICROSERVICE_URL = "http://localhost:8001/ai/analyze-ticket"
RASA_SERVER_URL = "http://localhost:5005/webhooks/rest/webhook"

# This endpoint receives the new ticket from the frontend
# In /main_api_server/main.py

@app.post("/api/tickets")
async def create_ticket(ticket_data: dict):
    description = ticket_data.get("description")

    # Step 1: Get the specific category from the AI
    async with httpx.AsyncClient() as client:
        ai_response = await client.post(AI_MICROSERVICE_URL, json={"description": description})
        ai_analysis = ai_response.json()
    
    specific_category = ai_analysis.get("category")

    db = SessionLocal()
    try:
        # Step 2: Search for an agent who has solved a similar ticket
        expert_agent_query = text("""
            SELECT assigned_to_user_id FROM tickets
            WHERE category = :category AND status = 'Resolved'
            ORDER BY resolved_at DESC
            LIMIT 1;
        """)
        result = db.execute(expert_agent_query, {"category": specific_category})
        expert_agent_id = result.scalar_one_or_none()

        assigned_agent = None
        assigned_dept = None

        if expert_agent_id:
            # Step 3a: Expert found, assign directly to them
            assigned_agent = expert_agent_id
        else:
            # Step 3b: No expert, fall back to department routing
            # (This mapping would be stored in a config or another table)
            department_map = {
                "software_outlook": "Enterprise Applications",
                "network_vpn": "Network Operations",
                "hardware_printer": "Desktop Support"
            }
            dept_name = department_map.get(specific_category, "L1 Service Desk")
            dept_query = text("SELECT id FROM departments WHERE name = :name")
            result = db.execute(dept_query, {"name": dept_name})
            assigned_dept = result.scalar_one()

        # Step 4: Create the new ticket with the determined assignment
        ticket_query = text("""
            INSERT INTO tickets (title, description, category, status, created_by_user_id, assigned_to_user_id, assigned_department_id)
            VALUES (:title, :description, :category, 'Open', :user_id, :agent_id, :dept_id)
            RETURNING id;
        """)
        
        result = db.execute(
            ticket_query,
            {
                "title": ticket_data.get("title"),
                "description": description,
                "category": specific_category,
                "user_id": 5, # Placeholder for logged-in user
                "agent_id": assigned_agent,
                "dept_id": assigned_dept,
            },
        )
        new_ticket_id = result.scalar_one()
        db.commit()

        return {"message": "Ticket created and intelligently routed", "ticket_id": new_ticket_id}
    finally:
        db.close()


# Add this endpoint to /main_api_server/main.py

# This endpoint receives a chat message from the frontend
@app.post("/api/chatbot/message")
async def chat_with_bot(message_data: dict):
    # Forward the message directly to the Rasa server's webhook [cite: 44, 46]
    async with httpx.AsyncClient() as client:
        rasa_response = await client.post(RASA_SERVER_URL, json=message_data)
        bot_response = rasa_response.json()

    # Return Rasa's response directly to the frontend [cite: 51, 53]
    return bot_response