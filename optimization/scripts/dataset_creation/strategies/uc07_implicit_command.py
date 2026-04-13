"""UC-7: Implicit command — user implies intent, robot proposes + confirms."""

from .base_strategy import BaseStrategy


class UC07ImplicitCommand(BaseStrategy):
    use_case = "UC-7"
    dataset = "implicit"

    IMPLICIT_MOVE_TEMPLATES = [
        # Truly implicit — user provides context/need, not a direct command
        "I need to find the {landmark}",
        "I have a meeting in the {landmark}",
        "I'm looking for the {landmark}",
        "Do you know where the {landmark} is?",
        "I think I need the {landmark}",
        "I need to be at the {landmark}",
        "Is the {landmark} far from here?",
        "My appointment is at the {landmark}",
        "Where can I find the {landmark}?",
        # Bad grammar (implicit)
        "where is the {landmark} at?",
    ]

    IMPLICIT_TOUR_PHRASES = [
        "I'm not familiar with this building",
        "I'm new here",
        "I don't know where anything is",
        "This is my first time here",
        "I've never been to this building before",
        "I don't know my way around",
        "Can someone show me the place?",
        "I feel lost in this building",
        "I just arrived and don't know the layout",
        "I'd like to get to know this place",
        "I have no idea where things are",
        "Everything looks the same to me here",
        "I could use some orientation",
        "Is there a way to see the whole building?",
        "I want to familiarize myself with this place",
        # Bad grammar
        "i dont know where noting is",
        "im new here dont know nothing",
        "first time here i dont know place",
        "i never been here before",
        "can somone show me arround?",
    ]

    IMPLICIT_CANCEL_PHRASES = [
        # Clearly implies wanting to stop/cancel (without saying "stop"/"cancel")
        "Forget it, I don't want to go anymore",
        "I don't need to go there anymore",
        "I don't want to go after all",
        "I'm not going anymore",
        # Bad grammar
        "forget it i dont wanna go no more",
    ]

    def generate(self):
        entries = []

        # Implicit move_to
        for lm in self.landmarks:
            for tpl in self.IMPLICIT_MOVE_TEMPLATES:
                msg = tpl.format(landmark=self.human_name(lm))
                entries.append(self.entry(
                    self.make_input(msg),
                    self.make_expected(
                        "interpreted_implicit_command",
                        command=self.make_command("move_to", [lm]),
                        follow_up=self.FOLLOW_UP_CONFIRMATION,
                    ),
                    "implicit_move_to",
                ))

        # Implicit show_me_around
        for msg in self.IMPLICIT_TOUR_PHRASES:
            entries.append(self.entry(
                self.make_input(msg),
                self.make_expected(
                    "interpreted_implicit_command",
                    command=self.make_command("show_me_around", ["ALL_LANDMARKS"]),
                    follow_up=self.FOLLOW_UP_CONFIRMATION,
                ),
                "implicit_show_me_around",
            ))

        # Implicit cancel
        for msg in self.IMPLICIT_CANCEL_PHRASES:
            entries.append(self.entry(
                self.make_input(msg),
                self.make_expected(
                    "interpreted_implicit_command",
                    command=self.make_command("Cancel"),
                    follow_up=self.FOLLOW_UP_CONFIRMATION,
                ),
                "implicit_cancel",
            ))

        return entries
