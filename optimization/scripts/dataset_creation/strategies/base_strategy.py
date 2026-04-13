"""
Base class for all dataset generation strategies.

Each strategy generates entries for a specific Use Case (UC).
Every strategy declares:
  - use_case:  the UC identifier (e.g. "UC-1")
  - dataset:   which output file it belongs to
               ("explicit", "implicit", "natural_language", "invalids")
  - generate(): returns a list of dataset entries
"""

from abc import ABC, abstractmethod


class BaseStrategy(ABC):
    """Abstract base for dataset generation strategies."""

    use_case: str = ""
    dataset: str = ""

    def __init__(self, landmarks, all_landmarks):
        self.landmarks = landmarks
        self.all_landmarks = all_landmarks

    @abstractmethod
    def generate(self):
        """Return a list of dataset entries."""
        ...

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    @staticmethod
    def make_input(user_message, conversation_state=None):
        obj = {
            "version": "1.0",
            "request_type": "from_user",
            "user_message": user_message,
        }
        if conversation_state:
            obj["conversation_state"] = conversation_state
        return obj

    @staticmethod
    def make_expected(result_type, command=None, follow_up=None):
        return {
            "version": "1.0",
            "result_type": result_type,
            "command": command,
            "follow_up": follow_up,
        }

    @staticmethod
    def make_command(name, landmarks=None):
        if name == "Cancel":
            return {"name": "Cancel", "parameters": {}}
        return {
            "name": name,
            "parameters": {"landmarks_to_visit": landmarks or []},
        }

    @staticmethod
    def make_conversation_state(command_name, landmarks=None):
        cmd = BaseStrategy.make_command(command_name, landmarks)
        return {
            "mode": "awaiting_confirmation",
            "pending_command": cmd,
        }

    FOLLOW_UP_CONFIRMATION = {
        "required": True,
        "type": "confirmation",
        "expires_in_sec": 30,
    }

    @staticmethod
    def human_name(landmark):
        return landmark.replace("_", " ")

    def entry(self, input_obj, expected_output, subcategory):
        return {
            "input": input_obj,
            "expected_output": expected_output,
            "use_case": self.use_case,
            "subcategory": subcategory,
        }
