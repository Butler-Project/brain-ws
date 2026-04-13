# User to LLM Communication Protocol

This document defines the JSON protocol used between the `FrontEnd` node and the `LLM`.

## Scope

- The protocol between `FrontEnd` and `LLM` is JSON.
- The `LLM` does not know which landmarks are really available.
- The `LLM` does not decide whether the robot is able to execute a command.
- Operative checks are handled by a deterministic software component outside the model.
- The `LLM` is responsible only for interpreting user input according to the command-routing rules.

## FrontEnd to LLM

Required fields:

```json
{
  "version": "1.0",
  "request_type": "from_user",
  "user_message": "<string>"
}
```

Optional field, only when there is pending conversational context (Implicit Commands):

```json
{
  "conversation_state": {
    "mode": "awaiting_confirmation",
    "pending_command": {
      "name": "<move_to|show_me_around|Cancel>",
      "parameters": {
        "landmarks_to_visit": ["<landmark>"]
      }
    }
  }
}
```


Allowed `result_type` values:

- `model_response`
- `interpreted_implicit_command`
- `interpreted_implicit_command_confirmation`
- `interpreted_explicit_command`
- `pre-emptive_system_command`
- `rejected`

Response rules:

- If no command is detected, use `result_type = "model_response"` and `command = null`.
- If an implicit command is detected, use `result_type = "interpreted_implicit_command"`, include the interpreted command, and require confirmation.
- If the user confirms a previously pending implicit command, use `result_type = "interpreted_implicit_command_confirmation"` and include the command.
- If an explicit command is detected, use `result_type = "interpreted_explicit_command"` and include the command.
- If the input violates router rules, use `result_type = "rejected"` and `command = null`.

## Command Format

Standard command payload:
(From LLM Model response)
```json
{
  "name": "<move_to|show_me_around|Cancel>",
  "parameters": {
    "landmarks_to_visit": ["<landmark>"]
  }
}
```
(From user model response)

For `Cancel`:

```json
{
  "name": "Cancel",
  "parameters": {}
}
```

## Follow-up Format (Implicit Commands)

When confirmation is required:

```json
{
  "required": true,
  "type": "confirmation",
  "expires_in_sec": 30
}
```

## Timeout Ownership

- A timeout for pending implicit commands should exist.
- The timeout must be enforced by the `FrontEnd`, not by the `LLM`.
- The `LLM` may include `follow_up.expires_in_sec` as protocol metadata.
- The `FrontEnd` remains the source of truth for starting the timer, clearing the pending command, and deciding whether a late reply is still valid.
- If the timeout expires before the user confirms, the `FrontEnd` should discard the pending command and reply with a predefined deterministic message without calling the `LLM`.

## Example 1: Conversational Only

User message:

```text
Hi, Good Morning
```

`FrontEnd -> LLM`

```json
{
  "version": "1.0",
  "request_type": "from_user",
  "user_message": "Hi, Good Morning"
}
```

`LLM -> FrontEnd`

```json
{
  "version": "1.0",
  "result_type": "model_response",
  "assistant_message": "Hi, Good Morning. I'm a navigation assistant. How can I help you?",
  "command": null,
  "follow_up": null
}
```

## Example 2: Implicit Command Detected

User message:

```text
I need to find the HR room
```

`FrontEnd -> LLM`

```json
{
  "version": "1.0",
  "request_type": "from_user",
  "user_message": "I need to find the HR room"
}
```

`LLM -> FrontEnd`

```json
{
  "version": "1.0",
  "result_type": "interpreted_implicit_command",
  "assistant_message": "I can take you to the HR room. Would you like me to guide you there?",
  "command": {
    "name": "move_to",
    "parameters": {
      "landmarks_to_visit": ["hr_room"]
    }
  },
  "follow_up": {
    "required": true,
    "type": "confirmation",
    "expires_in_sec": 30
  }
}
```

The `FrontEnd` should store the `pending_command`, start the timeout, and wait for the next user response.

## Example 3: Implicit Command Confirmed Within the Timeout Window

User message:

```text
yes
```

`FrontEnd -> LLM`

```json
{
  "version": "1.0",
  "request_type": "from_user",
  "user_message": "yes",
  "conversation_state": {
    "mode": "awaiting_confirmation",
    "pending_command": {
      "name": "move_to",
      "parameters": {
        "landmarks_to_visit": ["hr_room"]
      }
    }
  }
}
```

`LLM -> FrontEnd`

```json
{
  "version": "1.0",
  "result_type": "interpreted_implicit_command_confirmation",
  "assistant_message": "Ok, I will take you to the HR room.",
  "command": {
    "name": "move_to",
    "parameters": {
      "landmarks_to_visit": ["hr_room"]
    }
  },
  "follow_up": null
}
```

After this response, the `FrontEnd` should clear the pending confirmation state and continue with the execution pipeline.

## Example 4: Implicit Command Timeout Expired

Previous state held by the `FrontEnd`:

```json
{
  "mode": "awaiting_confirmation",
  "pending_command": {
    "name": "move_to",
    "parameters": {
      "landmarks_to_visit": ["hr_room"]
    }
  }
}
```

If no user confirmation is received before the timeout expires:

- The `FrontEnd` clears the pending command.
- The `FrontEnd` returns to `idle`.
- The `FrontEnd` replies with a predefined message without calling the `LLM`.

Deterministic timeout message to the user:

```text
The previous navigation request expired. Please ask again if you still want me to guide you.
```

This timeout-expiration branch is intentionally handled outside the `LLM` so that the confirmation window remains deterministic and easy to test.
