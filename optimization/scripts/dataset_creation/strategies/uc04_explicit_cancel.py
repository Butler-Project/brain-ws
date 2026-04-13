"""UC-4: Explicit Cancel — user gives a clear stop/cancel command."""

from .base_strategy import BaseStrategy


class UC04ExplicitCancel(BaseStrategy):
    use_case = "UC-4"
    dataset = "explicit"

    PHRASES = [
        "Stop",
        "Cancel",
        "Go back home",
        "Abort",
        "Stop the task",
        "Cancel the navigation",
        "End the tour",
        "Stop moving",
        "Return home",
        "Halt",
        "Cancel that",
        "Stop now",
        "Go home",
        "Come back",
        "Cancel everything",
        "Stop right there",
        "Bring me back home",
        "Take me home",
        "Go back",
        "Return",
        "Please stop",
        "Please cancel",
        "I changed my mind, stop",
        "Never mind, cancel",
        "That's enough, go home",
        # Bad grammar
        "stpo",
        "cancle",
        "go bak home",
        "plz stop",
        "stopp the task",
    ]

    def generate(self):
        entries = []
        for msg in self.PHRASES:
            entries.append(self.entry(
                self.make_input(msg),
                self.make_expected(
                    "interpreted_explicit_command",
                    command=self.make_command("Cancel"),
                ),
                "cancel",
            ))
        return entries
