"""UC-2: Explicit show_me_around (generic) — tour all landmarks."""

from .base_strategy import BaseStrategy


class UC02ExplicitShowAroundGeneric(BaseStrategy):
    use_case = "UC-2"
    dataset = "explicit"

    PHRASES = [
        "Show me around",
        "Give me a tour",
        "I want a tour of the building",
        "Show me everything",
        "Take me on a tour",
        "I'd like to see the whole place",
        "Can you show me all the rooms?",
        "Tour the building please",
        "Show me the whole place",
        "Take me around",
        "Walk me through the place",
        "Guide me around",
        "I want to see all landmarks",
        "Visit all rooms",
        "Let's do a tour",
        "Please show me around",
        "I want to explore the building",
        "Let's visit everything",
        "Give me the grand tour",
        "Show me what's around",
        # Bad grammar
        "show me arond",
        "give me a toor",
        "i want see everthing",
        "take me on toor plz",
        "can u show me arround?",
        "show all place plz",
        "i wanna tour the building",
        "lets do toor",
        "show me every room pls",
        "u can show me all?",
    ]

    def generate(self):
        entries = []
        for msg in self.PHRASES:
            entries.append(self.entry(
                self.make_input(msg),
                self.make_expected(
                    "interpreted_explicit_command",
                    command=self.make_command("show_me_around", ["ALL_LANDMARKS"]),
                ),
                "show_me_around_generic",
            ))
        return entries
