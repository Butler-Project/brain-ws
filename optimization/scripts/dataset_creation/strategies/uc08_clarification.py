"""UC-8: Ambiguous input — robot asks for clarification."""

from .base_strategy import BaseStrategy


class UC08Clarification(BaseStrategy):
    use_case = "UC-8"
    dataset = "natural_language"

    PHRASES = [
        # No destination specified — needs clarification
        "Take me there",
        "I want to go",
        "Go",
        "Can you take me?",
        "I need to go somewhere",
        "Show me that room",
        "The one on the left",
        "Over there",
        "I need help",
        "That place I mentioned",
        "You know where",
        "The usual place",
        "Somewhere nice",
        # Bad grammar — no destination
        "take me ther",
        "i wanna go somwhere",
        "where i go?",
        "take me some place plz",
        "i go where now?",
        "help me find somwhere",
        "dont know were to go",
        # ASR + VAD bad endpoint / incomplete sentence
        "take me to the",
        "go to the",
        "show me the",
        "can you take me to the",
        "i need to go to the",
        "i'm looking for the",
        "i need to find the",
        "show me the room and",
        "take me on a",
        "go back to the",
        "cancel the",
        # Ambiguous soft-cancel — unclear without context, no pending command
        "Actually, I changed my mind",
        "Never mind, I'll find it myself",
        "I think I'll just stay here",
        "You know what, forget about it",
        "Let me stay where I am",
        "nevermind i stay here",
        "nah i stay put now",
    ]

    def generate(self):
        entries = []
        expected = self.make_expected("model_response")
        for msg in self.PHRASES:
            entries.append(self.entry(
                self.make_input(msg), expected, "clarification",
            ))
        return entries
