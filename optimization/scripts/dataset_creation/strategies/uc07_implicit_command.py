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
        # Obligation/context — user was told or is expected to go somewhere
        "I was told to go to the {landmark}",
        "Someone told me to meet them at the {landmark}",
        "I'm supposed to be at the {landmark}",
        "I should go to the {landmark}",
        # Bad grammar (implicit)
        "where is the {landmark} at?",
        "how i find the {landmark}?",
        "i need find the {landmark}",
        "i looking for {landmark}",
        "how i get to {landmark}?",
    ]

    IMPLICIT_VISIT_TEMPLATES = [
        # "visit" is ambiguous — could be move_to or show_me_around; treat as implicit show_me_around
        "I'd like to visit the {landmark}",
        "I want to visit the {landmark}",
        "Can I visit the {landmark}?",
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
        # Lost / no destination — implies a tour
        "I'm lost",
        "I want to go but I don't know where",
        "I need go but don't know where",
        "Not sure where to go",
        # Bad grammar
        "i dont know where noting is",
        "im new here dont know nothing",
        "first time here i dont know place",
        "i never been here before",
        "can somone show me arround?",
        "me not know where anything at",
        "dont know this place at all",
        "i new here where everyting",
        "first time me here no clue",
        "somone show me this building plz",
        "help me im lost",
        "i need go but dont know where",
        "need go but not sure where",
    ]

    IMPLICIT_CANCEL_PHRASES = [
        # Clearly implies wanting to stop/cancel (without saying "stop"/"cancel")
        "Forget it, I don't want to go anymore",
        "I don't need to go there anymore",
        "I don't want to go after all",
        "I'm not going anymore",
        "I don't feel like going now",
        # Bad grammar
        "forget it i dont wanna go no more",
        "dont need go there no more",
        "i changed mind dont go",
        "me stay here dont go",
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

        # Explicit move_to — teacher consistently classifies "visit" as a direct request
        for lm in self.landmarks:
            for tpl in self.IMPLICIT_VISIT_TEMPLATES:
                msg = tpl.format(landmark=self.human_name(lm))
                entries.append(self.entry(
                    self.make_input(msg),
                    self.make_expected(
                        "interpreted_explicit_command",
                        command=self.make_command("move_to", [lm]),
                    ),
                    "implicit_visit",
                ))

        # Implicit show_me_around — general tour
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
