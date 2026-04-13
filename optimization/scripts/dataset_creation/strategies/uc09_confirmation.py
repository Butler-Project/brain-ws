"""UC-9: Confirmation flows — accept, decline, or decline with new command.

This strategy produces entries for TWO datasets:
  - "implicit"         → acceptance and decline-with-new-command
  - "natural_language"  → plain decline (no new command)
"""

import random

from .base_strategy import BaseStrategy


class UC09Confirmation(BaseStrategy):
    use_case = "UC-9"
    dataset = "implicit"  # primary; decline entries override to natural_language

    CONFIRM_PHRASES = [
        "Yes", "Sure", "Ok", "Please", "Yes please", "Go ahead",
        "Absolutely", "Of course", "Yeah", "Yep", "Do it",
        "Yes, take me there", "Sure thing", "Alright", "Let's go",
    ]

    DECLINE_PHRASES = [
        "No", "No thanks", "Never mind", "Nope", "Not now",
        "I don't want that", "No, that's not what I meant",
        "Forget it", "Not really", "I'll pass",
        "No, I'm fine", "No thank you", "Not right now",
    ]

    DECLINE_NEW_TEMPLATES = [
        "No, take me to the {landmark} instead",
        "Actually, go to the {landmark}",
        "No, I want to go to the {landmark}",
        "Forget that, take me to the {landmark}",
        "No, bring me to the {landmark} please",
    ]

    def generate(self):
        entries = []

        # --- Accept move_to (all landmarks x varied phrases) ---
        for lm in self.landmarks:
            for phrase in random.sample(self.CONFIRM_PHRASES, min(4, len(self.CONFIRM_PHRASES))):
                entries.append(self.entry(
                    self.make_input(
                        phrase,
                        conversation_state=self.make_conversation_state("move_to", [lm]),
                    ),
                    self.make_expected(
                        "interpreted_implicit_command_confirmation",
                        command=self.make_command("move_to", [lm]),
                    ),
                    "confirmation_accept_move_to",
                ))

        # --- Accept show_me_around ---
        for phrase in self.CONFIRM_PHRASES[:8]:
            entries.append(self.entry(
                self.make_input(
                    phrase,
                    conversation_state=self.make_conversation_state(
                        "show_me_around", self.all_landmarks
                    ),
                ),
                self.make_expected(
                    "interpreted_implicit_command_confirmation",
                    command=self.make_command("show_me_around", self.all_landmarks),
                ),
                "confirmation_accept_show_me_around",
            ))

        # --- Accept Cancel ---
        for phrase in self.CONFIRM_PHRASES[:8]:
            entries.append(self.entry(
                self.make_input(
                    phrase,
                    conversation_state=self.make_conversation_state("Cancel"),
                ),
                self.make_expected(
                    "interpreted_implicit_command_confirmation",
                    command=self.make_command("Cancel"),
                ),
                "confirmation_accept_cancel",
            ))

        # --- Decline + new command ---
        for lm in self.landmarks[:10]:
            other = random.choice([l for l in self.landmarks if l != lm])
            tpl = random.choice(self.DECLINE_NEW_TEMPLATES)
            msg = tpl.format(landmark=self.human_name(other))
            entries.append(self.entry(
                self.make_input(
                    msg,
                    conversation_state=self.make_conversation_state("move_to", [lm]),
                ),
                self.make_expected(
                    "interpreted_explicit_command",
                    command=self.make_command("move_to", [other]),
                ),
                "confirmation_decline_new_command",
            ))

        # --- Plain decline (no new command) → goes to natural_language ---
        expected_decline = self.make_expected("model_response")

        # Decline move_to
        for lm in self.landmarks[:8]:
            for phrase in random.sample(self.DECLINE_PHRASES, 3):
                e = self.entry(
                    self.make_input(
                        phrase,
                        conversation_state=self.make_conversation_state("move_to", [lm]),
                    ),
                    expected_decline,
                    "confirmation_decline",
                )
                e["_dataset_override"] = "natural_language"
                entries.append(e)

        # Decline show_me_around
        for phrase in self.DECLINE_PHRASES[:5]:
            e = self.entry(
                self.make_input(
                    phrase,
                    conversation_state=self.make_conversation_state(
                        "show_me_around", self.all_landmarks
                    ),
                ),
                expected_decline,
                "confirmation_decline_tour",
            )
            e["_dataset_override"] = "natural_language"
            entries.append(e)

        # Decline Cancel
        for phrase in self.DECLINE_PHRASES[:5]:
            e = self.entry(
                self.make_input(
                    phrase,
                    conversation_state=self.make_conversation_state("Cancel"),
                ),
                expected_decline,
                "confirmation_decline_cancel",
            )
            e["_dataset_override"] = "natural_language"
            entries.append(e)

        return entries
