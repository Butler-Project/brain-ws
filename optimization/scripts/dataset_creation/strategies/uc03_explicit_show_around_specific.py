"""UC-3: Explicit show_me_around (specific) — tour selected landmarks."""

import itertools
import random

from .base_strategy import BaseStrategy


class UC03ExplicitShowAroundSpecific(BaseStrategy):
    use_case = "UC-3"
    dataset = "explicit"

    TEMPLATES = [
        "Show me the {landmarks_text}",
        "Give me a tour of the {landmarks_text}",
        "I want to see the {landmarks_text}",
        "Take me to see the {landmarks_text}",
        "Can you show me the {landmarks_text}?",
        "Guide me through the {landmarks_text}",
        # Bad grammar
        "show me {landmarks_text} plz",
        "i wanna see the {landmarks_text}",
        "take me see {landmarks_text}",
        "can u show {landmarks_text} pls",
    ]

    def generate(self):
        entries = []

        # Pairs
        pairs = list(itertools.combinations(self.landmarks, 2))
        random.shuffle(pairs)
        selected_pairs = pairs[:30]

        # Triples
        triples = list(itertools.combinations(self.landmarks, 3))
        random.shuffle(triples)
        selected_triples = triples[:15]

        for combo in selected_pairs + selected_triples:
            names = [self.human_name(lm) for lm in combo]
            if len(names) == 2:
                landmarks_text = f"{names[0]} and the {names[1]}"
            else:
                landmarks_text = f"{names[0]}, the {names[1]}, and the {names[2]}"

            tpl = random.choice(self.TEMPLATES)
            msg = tpl.format(landmarks_text=landmarks_text)
            entries.append(self.entry(
                self.make_input(msg),
                self.make_expected(
                    "interpreted_explicit_command",
                    command=self.make_command("show_me_around", list(combo)),
                ),
                "show_me_around_specific",
            ))

        return entries
