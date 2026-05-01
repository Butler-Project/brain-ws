"""UC-1b: Explicit move_to with unknown landmarks.

The ModelFile says: "Do not reject a landmark because you do not know
whether it exists." The LLM must accept unknown landmarks and emit
move_to — the deterministic layer validates existence.
"""

from .base_strategy import BaseStrategy


class UC01bExplicitMoveToUnknownLandmark(BaseStrategy):
    use_case = "UC-1"
    dataset = "explicit"

    # Landmarks that do NOT exist in config.yaml
    UNKNOWN_LANDMARKS = [
        "pool", "gym", "rooftop", "cafeteria", "lobby",
        "reception", "server_room", "parking_lot", "terrace",
        "library", "meeting_room", "break_room", "storage",
        "elevator", "stairs",
    ]

    TEMPLATES = [
        "Take me to the {landmark}",
        "Go to the {landmark}",
        "Navigate to the {landmark}",
        "I want to go to the {landmark}",
        "Can you take me to the {landmark}?",
        "Bring me to the {landmark}",
        "Head to the {landmark}",
        "Lead me to the {landmark}",
        # Bad grammar
        "tak me to the {landmark}",
        "go too {landmark}",
        "i wanna go {landmark}",
        "take me {landmark} plz",
        "need go {landmark}",
        "u take me to {landmark}",
    ]

    def generate(self):
        entries = []
        for lm in self.UNKNOWN_LANDMARKS:
            for tpl in self.TEMPLATES:
                msg = tpl.format(landmark=self.human_name(lm))
                entries.append(self.entry(
                    self.make_input(msg),
                    self.make_expected(
                        "interpreted_explicit_command",
                        command=self.make_command("move_to", [lm]),
                    ),
                    "move_to_unknown_landmark",
                ))
        return entries
