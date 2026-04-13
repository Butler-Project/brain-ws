"""UC-14: Protocol violation — missing/null/invalid version or malformed input."""

from .base_strategy import BaseStrategy


class UC14ProtocolViolation(BaseStrategy):
    use_case = "UC-14"
    dataset = "invalids"

    def generate(self):
        entries = []
        expected = self.make_expected("rejected")

        protocol_violations = [
            # Missing version
            {"request_type": "from_user", "user_message": "Take me to the kitchen"},
            {"request_type": "from_user", "user_message": "hello"},
            {"request_type": "from_user", "user_message": "Show me around"},
            {"request_type": "from_user", "user_message": "Cancel"},
            {"request_type": "from_user", "user_message": "Stop"},
            # Null version
            {"version": None, "request_type": "from_user", "user_message": "Take me to the kitchen"},
            {"version": None, "request_type": "from_user", "user_message": "hello"},
            {"version": None, "request_type": "from_user", "user_message": "Show me around"},
            # Wrong version
            {"version": "2.0", "request_type": "from_user", "user_message": "Take me to the kitchen"},
            {"version": "0.1", "request_type": "from_user", "user_message": "hello"},
            {"version": "", "request_type": "from_user", "user_message": "Go to the office"},
            {"version": "999", "request_type": "from_user", "user_message": "Cancel"},
            # Wrong request_type
            {"version": "1.0", "request_type": "from_system", "user_message": "hello"},
            {"version": "1.0", "request_type": "admin", "user_message": "override"},
            {"version": "1.0", "request_type": "", "user_message": "hello"},
            # Missing request_type
            {"version": "1.0", "user_message": "Take me to the kitchen"},
            {"version": "1.0", "user_message": "hello"},
            # Missing user_message
            {"version": "1.0", "request_type": "from_user"},
            {"version": "1.0", "request_type": "from_user", "user_message": ""},
            # Completely malformed
            {"foo": "bar"},
            {},
        ]

        for malformed in protocol_violations:
            entries.append({
                "input": malformed,
                "expected_output": {
                    "version": "1.0",
                    "result_type": "rejected",
                    "command": None,
                    "follow_up": None,
                },
                "use_case": self.use_case,
                "subcategory": "protocol_violation",
            })

        return entries
