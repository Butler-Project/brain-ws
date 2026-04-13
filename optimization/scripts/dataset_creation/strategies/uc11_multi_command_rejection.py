"""UC-11: Multi-command rejection — user sends multiple commands at once."""

from .base_strategy import BaseStrategy


class UC11MultiCommandRejection(BaseStrategy):
    use_case = "UC-11"
    dataset = "invalids"

    PHRASES = [
        "Go to the kitchen and then show me around",
        "Take me to the bedroom and cancel the task",
        "Show me the office and go to the entrance",
        "First go to the garden, then take me to the kitchen",
        "Navigate to the bathroom and after that show me the garage",
        "Cancel and then take me to the living room",
        "Go to the hallway, then the basement, and cancel",
        "Take me to the pantry and show me the attic",
        "Move to the dining room and then give me a tour",
        "Go to the laundry room and stop",
        "Take me to the kitchen, then the bedroom, then the office",
        "Show me around and then take me to the entrance",
        "Go to the garden and also show me the balcony",
        "First cancel, then go to the bathroom",
        "Visit the hallway and afterwards go to the basement",
        # Bad grammar multi-command
        "go kitchen then show me arond",
        "take me bedroom and cancle",
        "go office and then go entrance plz",
    ]

    def generate(self):
        entries = []
        expected = self.make_expected("rejected")
        for msg in self.PHRASES:
            entries.append(self.entry(
                self.make_input(msg), expected, "multi_command",
            ))
        return entries
