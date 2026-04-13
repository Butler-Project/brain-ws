"""UC-1: Explicit move_to — user gives a clear, direct navigation command."""

from .base_strategy import BaseStrategy


class UC01ExplicitMoveTo(BaseStrategy):
    use_case = "UC-1"
    dataset = "explicit"

    TEMPLATES = [
        # Direct commands
        "Take me to the {landmark}",
        "Go to the {landmark}",
        "Navigate to the {landmark}",
        "Bring me to the {landmark}",
        "Lead me to the {landmark}",
        "I want to go to the {landmark}",
        "Can you take me to the {landmark}?",
        "Please go to the {landmark}",
        "Head to the {landmark}",
        "Walk me to the {landmark}",
        "Move to the {landmark}",
        "Drive to the {landmark}",
        "Go towards the {landmark}",
        "Please take me to the {landmark}",
        "Could you take me to the {landmark}?",
        "Would you take me to the {landmark}?",
        "Let's go to the {landmark}",
        "I need to go to the {landmark}",
        "I'd like to go to the {landmark}",
        "Hey, take me to the {landmark}",
        "Go ahead and move to the {landmark}",
        "Get me to the {landmark}",
        # Moved from UC-7 (too direct to be implicit)
        "I was told to go to the {landmark}",
        "Someone told me to meet them at the {landmark}",
        "I'm supposed to be at the {landmark}",
        "I'm trying to get to the {landmark}",
        "I'd like to visit the {landmark}",
        "I should go to the {landmark}",
        # Bad grammar / misspellings
        "tak me to the {landmark}",
        "go too the {landmark}",
        "i wanna go to {landmark}",
        "plese take me to {landmark}",
        "can u bring me to the {landmark}",
        "move me too {landmark}",
        "take me too the {landmark} pls",
        "go to {landmark} plz",
        "i want go {landmark}",
        "bring me {landmark}",
        # Bad grammar — moved from UC-7
        "i must go {landmark}",
        "i need find the {landmark}",
        "i looking for {landmark}",
        "how i get to {landmark}?",
    ]

    def generate(self):
        entries = []
        for lm in self.landmarks:
            for tpl in self.TEMPLATES:
                msg = tpl.format(landmark=self.human_name(lm))
                entries.append(self.entry(
                    self.make_input(msg),
                    self.make_expected(
                        "interpreted_explicit_command",
                        command=self.make_command("move_to", [lm]),
                    ),
                    "move_to",
                ))
        return entries
