"""UC-6: Ask for available landmarks — user queries what places exist."""

from .base_strategy import BaseStrategy


class UC06LandmarkQuery(BaseStrategy):
    use_case = "UC-6"
    dataset = "natural_language"

    PHRASES = [
        "What places can you take me to?",
        "What landmarks do you know?",
        "Where can you take me?",
        "What rooms are available?",
        "Show me the list of places",
        "What locations do you know about?",
        "Which places can I visit?",
        "Tell me what places are here",
        "What do you know about this building?",
        "List all available rooms",
        "What are the landmarks here?",
        "What places exist in this building?",
        # Bad grammar
        "wat places u know?",
        "where can u take me?",
        "wat rooms is here?",
        "which place u got?",
        "tell me wat rooms here",
        "what location u know?",
    ]

    def generate(self):
        entries = []
        expected = self.make_expected("model_response")
        for msg in self.PHRASES:
            entries.append(self.entry(
                self.make_input(msg), expected, "landmark_query",
            ))
        return entries
