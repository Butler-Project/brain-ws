"""UC-11: Multi-command rejection — user sends multiple commands at once."""

import itertools

from .base_strategy import BaseStrategy


class UC11MultiCommandRejection(BaseStrategy):
    use_case = "UC-11"
    dataset = "invalids"

    # Static multi-command phrases (explicit, well-formed)
    STATIC_PHRASES = [
        # move_to + show_me_around
        "Go to the kitchen and then show me around",
        "Take me to the bedroom and then give me a tour",
        "Navigate to the bathroom and after that show me the building",
        "First go to the garden, then show me everything",
        "Go to the office, and also give me a tour",
        # move_to + cancel
        "Take me to the bedroom and cancel the task",
        "Go to the kitchen and then stop",
        "First go to the garden, then cancel",
        "Navigate to the bathroom and abort",
        "Take me to the hallway and then cancel the trip",
        # cancel + move_to
        "Cancel and then take me to the living room",
        "Stop and go to the kitchen",
        "Abort and then navigate to the bedroom",
        "First cancel, then go to the bathroom",
        "Stop everything and take me to the office",
        # show_me_around + move_to
        "Show me around and then take me to the entrance",
        "Give me a tour and after that go to the kitchen",
        "First show me around, then go to the office",
        "Show me the building and then navigate to the garage",
        # show_me_around + cancel
        "Show me around and then stop",
        "Give me a tour and cancel afterwards",
        "First show me around, then cancel",
        # move_to + move_to
        "Go to the kitchen and then take me to the bedroom",
        "Take me to the entrance and after that go to the kitchen",
        "First go to the garden, then take me to the kitchen",
        "Navigate to the bathroom, then go to the office",
        "Take me to the kitchen, then the bedroom, then the office",
        "Go to the hallway, then the basement, and cancel",
        # Three commands
        "Go to the kitchen, then show me around, then cancel",
        "First cancel, then go to the office, then show me around",
        # Bad grammar multi-command
        "go kitchen then show me arond",
        "take me bedroom and cancle",
        "go office and then go entrance plz",
        "show me kitchen and then go office plz",
        "go bathroom then cancle it",
        "take me pantry and show attic too",
        "go kitchen also stop",
        "take me bedroom then cancel plz",
        "navigate office and after go kitchen",
        "show me around then take me entrance",
        "go garden and also show me balcony",
        "first go hallway then basement",
        "take me kitchen and bedroom",
    ]

    # Templates for programmatic generation
    MOVE_TOUR_TEMPLATES = [
        "Go to the {lm1} and then show me around",
        "Take me to the {lm1} and after that give me a tour",
        "First go to the {lm1}, then show me the whole building",
        "Navigate to the {lm1} and also give me a full tour",
    ]

    MOVE_CANCEL_TEMPLATES = [
        "Go to the {lm1} and then stop",
        "Take me to the {lm1} and cancel",
        "Navigate to {lm1} and after that abort",
        "First go to the {lm1}, then cancel the task",
    ]

    CANCEL_MOVE_TEMPLATES = [
        "Cancel and then take me to the {lm1}",
        "Stop and go to the {lm1}",
        "Abort and then navigate to the {lm1}",
        "First cancel, then take me to the {lm1}",
    ]

    MOVE_MOVE_TEMPLATES = [
        "Go to the {lm1} and then take me to the {lm2}",
        "First go to the {lm1}, then go to the {lm2}",
        "Take me to {lm1} and after that to {lm2}",
        "Navigate to {lm1} then {lm2}",
    ]

    def generate(self):
        entries = []
        expected = self.make_expected("rejected")

        # Static phrases
        for msg in self.STATIC_PHRASES:
            entries.append(self.entry(
                self.make_input(msg), expected, "multi_command",
            ))

        # Programmatic: move_to + show_me_around (subset of landmarks)
        for lm in self.landmarks[:8]:
            for tpl in self.MOVE_TOUR_TEMPLATES:
                msg = tpl.format(lm1=self.human_name(lm))
                entries.append(self.entry(
                    self.make_input(msg), expected, "multi_command",
                ))

        # Programmatic: move_to + cancel (subset)
        for lm in self.landmarks[:8]:
            for tpl in self.MOVE_CANCEL_TEMPLATES:
                msg = tpl.format(lm1=self.human_name(lm))
                entries.append(self.entry(
                    self.make_input(msg), expected, "multi_command",
                ))

        # Programmatic: cancel + move_to (subset)
        for lm in self.landmarks[:8]:
            for tpl in self.CANCEL_MOVE_TEMPLATES:
                msg = tpl.format(lm1=self.human_name(lm))
                entries.append(self.entry(
                    self.make_input(msg), expected, "multi_command",
                ))

        # Programmatic: move_to + move_to (landmark pairs, subset)
        pairs = list(itertools.combinations(self.landmarks, 2))[:10]
        for lm1, lm2 in pairs:
            for tpl in self.MOVE_MOVE_TEMPLATES:
                msg = tpl.format(lm1=self.human_name(lm1), lm2=self.human_name(lm2))
                entries.append(self.entry(
                    self.make_input(msg), expected, "multi_command",
                ))

        return entries
