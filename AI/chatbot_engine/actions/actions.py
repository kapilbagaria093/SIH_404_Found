from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
import psycopg2

# --- Database Connection Details ---
# IMPORTANT: Replace with your actual password and database name
DB_HOST = "localhost"
DB_NAME = "powergrid_helpdesk"
DB_USER = "postgres"
DB_PASS = "YOUR_DATABASE_PASSWORD"

# A mock database of system statuses.
SYSTEM_STATUS = {
    "sap": "Online",
    "vpn": "Experiencing Intermittent Issues",
    "email": "Online",
    "glpi": "Under Maintenance"
}

def connect_to_db():
    """Establishes a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
        return conn
    except psycopg2.OperationalError as e:
        print(f"Error connecting to database: {e}")
        return None

class ActionCheckStatus(Action):
    def name(self) -> Text:
        return "action_check_status"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        app_name = next(tracker.get_latest_entity_values("application"), None)
        if not app_name:
            dispatcher.utter_message(text="Which application's status would you like to check?")
            return []
        status = SYSTEM_STATUS.get(app_name.lower(), "Unknown System")
        dispatcher.utter_message(text=f"The current status of {app_name} is: {status}.")
        return []

class ActionSearchKb(Action):
    def name(self) -> Text:
        return "action_search_kb"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        search_topic = next(tracker.get_latest_entity_values("search_topic"), None)
        
        if not search_topic:
            dispatcher.utter_message(text="What topic are you looking for help with?")
            return []

        conn = connect_to_db()
        if not conn:
            dispatcher.utter_message(text="I'm having trouble connecting to our knowledge base right now. Please try again later.")
            return []
            
        try:
            cursor = conn.cursor()
            query = "SELECT content FROM knowledge_base WHERE keywords ILIKE %s;"
            cursor.execute(query, (f"%{search_topic}%",))
            result = cursor.fetchone()
            
            if result:
                solution = result[0]
                dispatcher.utter_message(response="utter_solution_found", solution_text=solution)
            else:
                dispatcher.utter_message(response="utter_no_solution_found")

        except Exception as e:
            print(f"Database query failed: {e}")
            dispatcher.utter_message(text="I encountered an error while searching. Please ask an agent for help.")
        finally:
            if conn:
                conn.close()

        return []

class ActionCreateTicket(Action):
    def name(self) -> Text:
        return "action_create_ticket"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        issue_description = next(tracker.get_latest_entity_values("issue_description"), None)
        
        if not issue_description:
            # If the user just says "create a ticket" without describing the issue
            dispatcher.utter_message(response="utter_ask_for_issue_details")
            return []

        # In a real application, you would make an API call here to your Main API Server
        # to create a real ticket in the database.
        # For the hackathon, we will just confirm it to the user.
        dispatcher.utter_message(response="utter_ticket_created", issue_description=issue_description)
        return []