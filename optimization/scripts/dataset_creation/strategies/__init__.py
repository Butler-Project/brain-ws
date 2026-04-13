from .uc01_explicit_move_to import UC01ExplicitMoveTo
from .uc01b_explicit_move_to_unknown_landmark import UC01bExplicitMoveToUnknownLandmark
from .uc02_explicit_show_around_generic import UC02ExplicitShowAroundGeneric
from .uc03_explicit_show_around_specific import UC03ExplicitShowAroundSpecific
from .uc04_explicit_cancel import UC04ExplicitCancel
from .uc05_conversation import UC05Conversation
from .uc06_landmark_query import UC06LandmarkQuery
from .uc07_implicit_command import UC07ImplicitCommand
from .uc08_clarification import UC08Clarification
from .uc09_confirmation import UC09Confirmation
from .uc11_multi_command_rejection import UC11MultiCommandRejection
from .uc13_prompt_injection import UC13PromptInjection
from .uc14_protocol_violation import UC14ProtocolViolation
from .stt_noise_augmenter import STTNoiseAugmenter

# Each strategy declares which dataset it belongs to
STRATEGY_REGISTRY = [
    UC01ExplicitMoveTo,
    UC01bExplicitMoveToUnknownLandmark,
    UC02ExplicitShowAroundGeneric,
    UC03ExplicitShowAroundSpecific,
    UC04ExplicitCancel,
    UC05Conversation,
    UC06LandmarkQuery,
    UC07ImplicitCommand,
    UC08Clarification,
    UC09Confirmation,
    UC11MultiCommandRejection,
    UC13PromptInjection,
    UC14ProtocolViolation,
    STTNoiseAugmenter,  # cross-cutting: generates noisy variants for all categories
]
