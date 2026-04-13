"""UC-8: Ambiguous input — robot asks for clarification."""

from .base_strategy import BaseStrategy


class UC08Clarification(BaseStrategy):
    use_case = "UC-8"
    dataset = "natural_language"

    PHRASES = [
        "Take me there",
        "I want to go",
        "Go",
        "Can you take me?",
        "I need to go somewhere",
        "Show me that room",
        "The one on the left",
        "Over there",
        "I'm lost",
        "I need help",
        "That place I mentioned",
        "You know where",
        "The usual place",
        "Somewhere nice",
        "I want to go but I don't know where",
        # Bad grammar
        "take me ther",
        "i wanna go somwhere",
        "help me im lost",
        "where i go?",
        "i need go but dont know where",
        # Ambiguous intent — could be cancel but unclear without context
        "Actually, I changed my mind",
        "Never mind, I'll find it myself",
        "I think I'll just stay here",
        "You know what, forget about it",
        "Let me stay where I am",
        "I don't feel like going now",
        # Bad grammar ambiguous
        "nevermind i stay here",
        "i changed mind dont go",
    ]

    def generate(self):
        entries = []
        expected = self.make_expected("model_response")
        for msg in self.PHRASES:
            entries.append(self.entry(
                self.make_input(msg), expected, "clarification",
            ))
        return entries
