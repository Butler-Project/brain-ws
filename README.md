# HighLevel Reasonning

This component manages high level component that:
- Integrates LLM to translate intention from the user and it convert to specific commands
- State Machine to control internal state of several ROS2 Nodes to execute commands
- Specific Commands implmemnetation to reflect in code the intention from the user
- Nav2 Ros node
- AMCL ros node
- Slam node (Slam Toolbox)
- Sensors Experts , these controls the current state of the robot sensors

## General Description, responsabilities , componentes and protocol

### Summary

- The `LLM` should not know which `landmarks` really exist or whether they are currently available. Its job is only to extract intent and normalize parameters; real validation must happen outside the model.
- The ability to execute a command must not be decided by the `LLM`. A deterministic software component should evaluate the robot's operative state and, if needed, return a predefined message without calling the model.
- The model's responsibility is limited to interpreting explicit commands, interpreting implicit commands, requesting confirmation when needed, rejecting inputs that break the model rules, and never inventing commands or execution logic.
- Implicit commands introduce a conversational state machine. The communication protocol must support the cycle: detect implicit intent, return a proposal plus confirmation request, store a `pending_command`, and let the next user turn confirm, reject, or replace that proposal.
- Because of that, the protocol cannot be only free-form text and it cannot be only a final command payload. It must also represent intermediate dialogue states.

### Design Conclusions

- The `bridge` or `frontend` should own both the conversational state and the operative state. The `LLM` should act as an intent router, not as a planner or execution validator.
- Operative checks should happen outside the `LLM`, ideally before execution and, when the condition is already known, even before calling the model.
- If the system decides not to call the `LLM` because of a known operative condition, the response to the user should come from deterministic templates or predefined messages.

### Agreed Direction


- The protocol should represent at least these states explicitly: `no_command`, `explicit_command_ready`, `implicit_command_pending_confirmation`, `confirmation_accepted`, `confirmation_rejected`, `rejected_by_rule`, and `blocked_by_system`.

### Compiling ROS workspace

# Updating Submodules manually
```bash
git submodule update --remote --recursive
```
# Dependencies
1.- Install ROS2 Colcon for Building
```bash
sudo apt install -y python3-colcon-common-extensions python3-rosdep
```
2.- Compilation
```bash
source /opt/ros/jazzy/setup.bash && colcon build
```
### Running the optimization pipeline
# Install Dependencies ( Create first you virtual enviroment before runnign this command) for 
```bash
pip install -r requirements.txt
``` 
