"""
STT Noise Augmentation Strategy.

Not a UC — this is a cross-cutting augmenter that takes clean prompts
from other strategies and generates noisy variants simulating
Speech-to-Text errors.

Produces entries for the SAME dataset as the source strategy.
Covers: filler words, stuttering, homophones, phonetic typos,
        dropped words, word merging, truncation, caveman grammar.
"""

import random

from .base_strategy import BaseStrategy
from .stt_noise import (
    generate_noisy_variants,
    caveman_grammar,
)


class STTNoiseAugmenter(BaseStrategy):
    use_case = "STT"
    dataset = "explicit"  # overridden per-entry

    # Clean templates to augment (landmark placeholder = {landmark})
    MOVE_TO_CLEAN = [
        "Take me to the {landmark}",
        "Go to the {landmark}",
        "Navigate to the {landmark}",
        "Can you take me to the {landmark}?",
        "I want to go to the {landmark}",
        "Please take me to the {landmark}",
        "Bring me to the {landmark}",
        "Head to the {landmark}",
    ]

    TOUR_CLEAN = [
        "Show me around",
        "Give me a tour",
        "I want to see everything",
        "Take me on a tour",
    ]

    CANCEL_CLEAN = [
        "Stop",
        "Cancel",
        "Go back home",
        "Stop the task",
    ]

    IMPLICIT_MOVE_CLEAN = [
        "I need to find the {landmark}",
        "I'm looking for the {landmark}",
        "Do you know where the {landmark} is?",
        "I have a meeting in the {landmark}",
    ]

    IMPLICIT_TOUR_CLEAN = [
        "I'm not familiar with this building",
        "I'm new here",
        "I don't know where anything is",
    ]

    # How many noisy variants per clean template
    VARIANTS_PER_TEMPLATE = 2
    # How many caveman grammar entries per landmark
    CAVEMAN_PER_LANDMARK = 2

    def generate(self):
        entries = []

        # ----------------------------------------------------------
        # Explicit move_to — STT noise
        # ----------------------------------------------------------
        for lm in self.landmarks:
            lm_human = self.human_name(lm)

            # Noisy variants from augmenter
            for tpl in random.sample(self.MOVE_TO_CLEAN, min(3, len(self.MOVE_TO_CLEAN))):
                clean = tpl.format(landmark=lm_human)
                for noisy in generate_noisy_variants(clean, n_variants=self.VARIANTS_PER_TEMPLATE):
                    entries.append(self.entry(
                        self.make_input(noisy),
                        self.make_expected(
                            "interpreted_explicit_command",
                            command=self.make_command("move_to", [lm]),
                        ),
                        "stt_noise_move_to",
                    ))

            # Caveman grammar
            for _ in range(self.CAVEMAN_PER_LANDMARK):
                cave = caveman_grammar("", landmark_hint=lm_human)
                entries.append(self.entry(
                    self.make_input(cave),
                    self.make_expected(
                        "interpreted_explicit_command",
                        command=self.make_command("move_to", [lm]),
                    ),
                    "caveman_move_to",
                ))

        # ----------------------------------------------------------
        # Explicit tour — STT noise
        # ----------------------------------------------------------
        for tpl in self.TOUR_CLEAN:
            for noisy in generate_noisy_variants(tpl, n_variants=2):
                entries.append(self.entry(
                    self.make_input(noisy),
                    self.make_expected(
                        "interpreted_explicit_command",
                        command=self.make_command("show_me_around", ["ALL_LANDMARKS"]),
                    ),
                    "stt_noise_tour",
                ))

        # Caveman tour
        caveman_tours = [
            "me see all", "show all places", "tour me",
            "see everything me", "all rooms show", "go everywhere",
            "me want tour", "show places robot", "all room me see",
        ]
        for msg in caveman_tours:
            entries.append(self.entry(
                self.make_input(msg),
                self.make_expected(
                    "interpreted_explicit_command",
                    command=self.make_command("show_me_around", ["ALL_LANDMARKS"]),
                ),
                "caveman_tour",
            ))

        # ----------------------------------------------------------
        # Explicit cancel — STT noise
        # ----------------------------------------------------------
        for tpl in self.CANCEL_CLEAN:
            for noisy in generate_noisy_variants(tpl, n_variants=2):
                entries.append(self.entry(
                    self.make_input(noisy),
                    self.make_expected(
                        "interpreted_explicit_command",
                        command=self.make_command("Cancel"),
                    ),
                    "stt_noise_cancel",
                ))

        # Caveman cancel
        caveman_cancels = [
            "stop now", "no go", "back home", "stop robot",
            "no more go", "home now", "robot stop", "no want go",
            "enough stop", "me stay",
        ]
        for msg in caveman_cancels:
            entries.append(self.entry(
                self.make_input(msg),
                self.make_expected(
                    "interpreted_explicit_command",
                    command=self.make_command("Cancel"),
                ),
                "caveman_cancel",
            ))

        # ----------------------------------------------------------
        # Implicit move_to — STT noise
        # ----------------------------------------------------------
        for lm in random.sample(self.landmarks, min(8, len(self.landmarks))):
            lm_human = self.human_name(lm)
            for tpl in random.sample(self.IMPLICIT_MOVE_CLEAN, 2):
                clean = tpl.format(landmark=lm_human)
                for noisy in generate_noisy_variants(clean, n_variants=1):
                    e = self.entry(
                        self.make_input(noisy),
                        self.make_expected(
                            "interpreted_implicit_command",
                            command=self.make_command("move_to", [lm]),
                            follow_up=self.FOLLOW_UP_CONFIRMATION,
                        ),
                        "stt_noise_implicit_move_to",
                    )
                    e["_dataset_override"] = "implicit"
                    entries.append(e)

        # Caveman implicit
        caveman_implicit_move = [
            "me need find {landmark}",
            "where {landmark}?",
            "{landmark} where?",
            "me look for {landmark}",
            "need go {landmark} think",
        ]
        for lm in random.sample(self.landmarks, min(8, len(self.landmarks))):
            tpl = random.choice(caveman_implicit_move)
            msg = tpl.format(landmark=self.human_name(lm))
            e = self.entry(
                self.make_input(msg),
                self.make_expected(
                    "interpreted_implicit_command",
                    command=self.make_command("move_to", [lm]),
                    follow_up=self.FOLLOW_UP_CONFIRMATION,
                ),
                "caveman_implicit_move_to",
            )
            e["_dataset_override"] = "implicit"
            entries.append(e)

        # ----------------------------------------------------------
        # Implicit tour — STT noise
        # ----------------------------------------------------------
        for tpl in self.IMPLICIT_TOUR_CLEAN:
            for noisy in generate_noisy_variants(tpl, n_variants=2):
                e = self.entry(
                    self.make_input(noisy),
                    self.make_expected(
                        "interpreted_implicit_command",
                        command=self.make_command("show_me_around", ["ALL_LANDMARKS"]),
                        follow_up=self.FOLLOW_UP_CONFIRMATION,
                    ),
                    "stt_noise_implicit_tour",
                )
                e["_dataset_override"] = "implicit"
                entries.append(e)

        # Caveman implicit tour
        caveman_implicit_tours = [
            "me new here no know",
            "first time here lost",
            "no know building",
            "me lost show place",
            "where everything?",
        ]
        for msg in caveman_implicit_tours:
            e = self.entry(
                self.make_input(msg),
                self.make_expected(
                    "interpreted_implicit_command",
                    command=self.make_command("show_me_around", ["ALL_LANDMARKS"]),
                    follow_up=self.FOLLOW_UP_CONFIRMATION,
                ),
                "caveman_implicit_tour",
            )
            e["_dataset_override"] = "implicit"
            entries.append(e)

        return entries
