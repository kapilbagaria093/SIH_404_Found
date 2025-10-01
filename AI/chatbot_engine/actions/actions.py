# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions


# This is a simple example for a custom action which utters "Hello World!"

# from typing import Any, Text, Dict, List
#
# from rasa_sdk import Action, Tracker
# from rasa_sdk.executor import CollectingDispatcher
#
#
# class ActionHelloWorld(Action):
#
#     def name(self) -> Text:
#         return "action_hello_world"
#
#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
#
#         dispatcher.utter_message(text="Hello World!")
#
#         return []

from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

# A mock database of system statuses. In a real app, this would be an API call.
SYSTEM_STATUS = {
    "sap": "Online",
    "vpn": "Experiencing Intermittent Issues",
    "email": "Online",
    "glpi": "Under Maintenance"
}

class ActionCheckStatus(Action):

    def name(self) -> Text:
        return "action_check_status"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Get the 'application' entity from the user's message
        app_name = next(tracker.get_latest_entity_values("application"), None)

        if not app_name:
            dispatcher.utter_message(text="Which application's status would you like to check?")
            return []

        # Get the status from our mock database
        status = SYSTEM_STATUS.get(app_name.lower(), "Unknown System")

        # Send the response back to the user
        dispatcher.utter_message(text=f"The current status of {app_name} is: {status}.")

        return []