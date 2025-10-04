from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
import psycopg2

# --- Database Connection Details ---
DB_HOST = "localhost"
DB_NAME = "powergrid_helpdesk"
DB_USER = "postgres"
DB_PASS = "kapilpostgres"

# Mock system statuses
SYSTEM_STATUS = {"sap": "Online", "vpn": "Intermittent Issues", "email": "Online"}

def connect_to_db():
    try:
        return psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
    except psycopg2.OperationalError as e:
        print(f"Error connecting to database: {e}")
        return None

class ValidateTicketForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_ticket_form"

    async def validate_urgency(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate the urgency value."""
        if slot_value.lower() in ["low", "medium", "high"]:
            return {"urgency": slot_value.lower()}
        else:
            dispatcher.utter_message(response="utter_ask_urgency_invalid")
            return {"urgency": None}

    # This function is automatically called when the form is submitted
    # We are not using it here, but it's where you would add the final
    # API call to the main_api_server to create the ticket.

class ActionSubmitTicketForm(Action):
    def name(self) -> Text:
        # Note: This is not a real action in the domain, but a placeholder
        # for what would happen after the form is filled.
        # The form's submission is handled by Rasa Core.
        return "action_submit_ticket_form"
    
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        urgency = tracker.get_slot("urgency")
        issue_description = tracker.get_slot("issue_description")
        
        dispatcher.utter_message(
            response="utter_submit_ticket",
            urgency=urgency,
            issue_description=issue_description
        )
        return []

# class ActionSearchKb(Action):
#     def name(self) -> Text:
#         return "action_search_kb"

#     def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
#         search_topic = next(tracker.get_latest_entity_values("search_topic"), None)
#         if not search_topic:
#             dispatcher.utter_message(text="What topic can I help you find a solution for?")
#             return []

#         conn = connect_to_db()
#         if not conn:
#             dispatcher.utter_message(text="I'm having trouble connecting to our knowledge base right now.")
#             return []
            
#         try:
#             cursor = conn.cursor()
#             query = "SELECT content FROM knowledge_base WHERE keywords ILIKE %s;"
#             cursor.execute(query, (f"%{search_topic}%",))
#             result = cursor.fetchone()
            
#             if result:
#                 dispatcher.utter_message(response="utter_solution_found", solution_text=result[0])
#             else:
#                 dispatcher.utter_message(response="utter_no_solution_found")
#         finally:
#             if conn:
#                 conn.close()
#         return []

class ActionSearchKb(Action):
    def name(self) -> Text:
        return "action_search_kb"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        search_topic = next(tracker.get_latest_entity_values("search_topic"), None)
        if not search_topic:
            dispatcher.utter_message(text="What topic can I help you find a solution for?")
            return []

        conn = connect_to_db()
        if not conn:
            dispatcher.utter_message(text="I'm having trouble connecting to our knowledge base right now.")
            return []
            
        try:
            cursor = conn.cursor()
            query = "SELECT content FROM knowledge_base WHERE keywords ILIKE %s;"
            cursor.execute(query, (f"%{search_topic}%",))
            result = cursor.fetchone()
            
            if result:
                # First, provide the solution
                dispatcher.utter_message(response="utter_solution_found", solution_text=result[0])
                # THEN, proactively ask if it helped
                dispatcher.utter_message(response="utter_ask_if_solution_helped")
            else:
                dispatcher.utter_message(response="utter_no_solution_found")
        finally:
            if conn:
                conn.close()
        return []

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