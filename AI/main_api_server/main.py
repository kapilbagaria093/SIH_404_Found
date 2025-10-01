# In /main_api_server/main.py
import httpx
from fastapi import FastAPI

app = FastAPI(title="POWERGRID Main API")

AI_MICROSERVICE_URL = "http://localhost:8001/ai/analyze-ticket"
RASA_SERVER_URL = "http://localhost:5005/webhooks/rest/webhook"

# This endpoint receives the new ticket from the frontend
@app.post("/api/tickets")
async def create_ticket(ticket_data: dict):
    # Get the description from the frontend's request [cite: 23, 27]
    description = ticket_data.get("description")

    # Make an internal call to the AI Microservice for analysis [cite: 29]
    async with httpx.AsyncClient() as client:
        ai_response = await client.post(AI_MICROSERVICE_URL, json={"description": description})
        ai_analysis = ai_response.json()

    # Combine original data with AI analysis [cite: 36]
    # In a real app, you would save this to a database
    final_ticket_data = {**ticket_data, **ai_analysis}

    # Return the complete ticket object to the frontend [cite: 37]
    return final_ticket_data

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