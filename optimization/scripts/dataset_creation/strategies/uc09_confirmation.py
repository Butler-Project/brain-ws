"""UC-9: Confirmation flows — accept, decline, or decline with new command.

This strategy produces entries for TWO datasets:
  - "implicit"         → acceptance and decline-with-new-command
  - "natural_language"  → plain decline (no new command)
"""

import itertools

from .base_strategy import BaseStrategy


class UC09Confirmation(BaseStrategy):
    use_case = "UC-9"
    dataset = "implicit"  # primary; decline entries override to natural_language

    CONFIRM_PHRASES = [
        # Clear positive — unambiguous to the teacher
        "Yes", "Sure", "Ok", "Please", "Yes please", "Go ahead",
        "Absolutely", "Of course", "Yeah", "Yep", "Do it",
        "Yes, take me there", "Sure thing", "Alright", "Let's go",
        "Let's do it", "Go for it", "Sounds good", "That works",
        "I'm ready", "Go on", "Please do",
        "Yeah go ahead", "Yep go ahead", "Alright then",
        "Let's go then", "Yes I'm ready", "Ok let's do this",
        "Yeah that's fine", "Do it please",
        # Bad grammar / short — clear positive intent
        "yep yep", "ya sure", "ok ok", "yup", "yup do it",
        "yeah yeah", "ok pls", "yes pls",
        "sure sure", "yea",
    ]

    DECLINE_PHRASES = [
        # Clear negative — unambiguous to the teacher
        "No", "No thanks", "Never mind", "Nope", "Not now",
        "I don't want that", "No, that's not what I meant",
        "Forget it", "Not really", "I'll pass",
        "No, I'm fine", "No thank you", "Not right now",
        "Actually no", "Hmm no", "No actually", "Wait no",
        "Hold on no", "Nah", "No way",
        # Bad grammar
        "nah dont", "no no no", "wait dont", "hmm nope",
        "nah im good", "nope nope",
    ]

    DECLINE_NEW_MOVE_TEMPLATES = [
        "No, take me to the {landmark} instead",
        "Actually, go to the {landmark}",
        "No, I want to go to the {landmark}",
        "Forget that, take me to the {landmark}",
        "No, bring me to the {landmark} please",
        "Wait, I want to go to the {landmark} instead",
        "Change that to the {landmark}",
        "Never mind, take me to the {landmark}",
    ]

    DECLINE_NEW_TOUR_TEMPLATES = [
        "Actually, just show me around",
        "No, give me a tour instead",
        "Forget that, show me everything",
        "Never mind, I want a full tour",
        "No, show me around the whole building",
    ]

    def generate(self):
        entries = []

        # --- Accept move_to: ALL landmarks × ALL confirm phrases ---
        for lm in self.landmarks:
            for phrase in self.CONFIRM_PHRASES:
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

        # --- Accept show_me_around (generic ALL_LANDMARKS) × ALL confirm ---
        for phrase in self.CONFIRM_PHRASES:
            entries.append(self.entry(
                self.make_input(
                    phrase,
                    conversation_state=self.make_conversation_state(
                        "show_me_around", ["ALL_LANDMARKS"]
                    ),
                ),
                self.make_expected(
                    "interpreted_implicit_command_confirmation",
                    command=self.make_command("show_me_around", ["ALL_LANDMARKS"]),
                ),
                "confirmation_accept_show_me_around",
            ))

        # --- Accept show_me_around (specific landmark pairs) × subset of confirms ---
        confirm_subset = self.CONFIRM_PHRASES[:10]
        pairs = list(itertools.combinations(self.landmarks, 2))[:8]
        for lm1, lm2 in pairs:
            for phrase in confirm_subset:
                entries.append(self.entry(
                    self.make_input(
                        phrase,
                        conversation_state=self.make_conversation_state(
                            "show_me_around", [lm1, lm2]
                        ),
                    ),
                    self.make_expected(
                        "interpreted_implicit_command_confirmation",
                        command=self.make_command("show_me_around", [lm1, lm2]),
                    ),
                    "confirmation_accept_show_me_around_specific",
                ))

        # --- Accept Cancel × ALL confirm ---
        for phrase in self.CONFIRM_PHRASES:
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

        # --- Decline + new move_to command: ALL landmarks × ALL decline+move templates ---
        for lm in self.landmarks:
            for tpl in self.DECLINE_NEW_MOVE_TEMPLATES:
                other = [l for l in self.landmarks if l != lm][0]
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

        # --- Decline + new show_me_around command ---
        for lm in self.landmarks[:8]:
            for tpl in self.DECLINE_NEW_TOUR_TEMPLATES:
                entries.append(self.entry(
                    self.make_input(
                        tpl,
                        conversation_state=self.make_conversation_state("move_to", [lm]),
                    ),
                    self.make_expected(
                        "interpreted_explicit_command",
                        command=self.make_command("show_me_around", ["ALL_LANDMARKS"]),
                    ),
                    "confirmation_decline_new_tour",
                ))

        # --- Plain decline (no new command) → goes to natural_language ---
        expected_decline = self.make_expected("model_response")

        # Decline move_to: ALL landmarks × ALL decline phrases
        for lm in self.landmarks:
            for phrase in self.DECLINE_PHRASES:
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

        # Decline show_me_around (ALL_LANDMARKS): ALL decline phrases
        for phrase in self.DECLINE_PHRASES:
            e = self.entry(
                self.make_input(
                    phrase,
                    conversation_state=self.make_conversation_state(
                        "show_me_around", ["ALL_LANDMARKS"]
                    ),
                ),
                expected_decline,
                "confirmation_decline_tour",
            )
            e["_dataset_override"] = "natural_language"
            entries.append(e)

        # Decline show_me_around (specific pairs): subset of decline phrases
        decline_subset = self.DECLINE_PHRASES[:10]
        for lm1, lm2 in pairs[:4]:
            for phrase in decline_subset:
                e = self.entry(
                    self.make_input(
                        phrase,
                        conversation_state=self.make_conversation_state(
                            "show_me_around", [lm1, lm2]
                        ),
                    ),
                    expected_decline,
                    "confirmation_decline_specific_tour",
                )
                e["_dataset_override"] = "natural_language"
                entries.append(e)

        # Decline Cancel: ALL decline phrases
        for phrase in self.DECLINE_PHRASES:
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
