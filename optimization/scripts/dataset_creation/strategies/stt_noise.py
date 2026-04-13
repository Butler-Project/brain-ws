"""
STT (Speech-to-Text) noise augmentation.

Models the types of errors produced by automatic speech recognition systems
when converting audio to text. Used to generate noisy variants of clean
prompts so the student model learns to handle real-world STT input.

Noise types modeled:
  1. Filler words      — "uh", "um", "like" inserted
  2. Stuttering        — word repetition ("take take me")
  3. Dropped words     — articles/prepositions removed ("take me kitchen")
  4. Homophones        — sound-alike substitution ("to" → "too"/"two")
  5. Phonetic typos    — character-level errors ("kitchen" → "kichen")
  6. Caveman grammar   — broken word order, no function words
  7. Word boundary     — words merged ("takeme to")
  8. Truncation        — message cut short ("take me to the kitch")
"""

import random
import re

# ============================================================
# NOISE FUNCTIONS
# ============================================================

FILLERS = ["uh", "um", "like", "you know", "well", "so", "er", "hmm"]

HOMOPHONES = {
    "to": ["too", "two"],
    "there": ["their", "they're"],
    "your": ["you're", "ur"],
    "right": ["rite", "write"],
    "know": ["no"],
    "here": ["hear"],
    "where": ["wear"],
    "would": ["wood"],
    "see": ["sea"],
    "for": ["four", "4"],
    "are": ["r"],
    "you": ["u"],
    "the": ["da", "teh"],
    "please": ["plz", "pls"],
}

DROP_WORDS = {"the", "a", "an", "to", "me", "you", "can", "could", "would", "please"}


def add_fillers(message, n_fillers=1):
    """Insert filler words at random positions."""
    words = message.split()
    if len(words) < 2:
        return message
    for _ in range(n_fillers):
        pos = random.randint(1, len(words) - 1)
        words.insert(pos, random.choice(FILLERS))
    return " ".join(words)


def add_stutter(message):
    """Repeat a random word (stuttering)."""
    words = message.split()
    if len(words) < 2:
        return message
    idx = random.randint(0, min(2, len(words) - 1))
    words.insert(idx, words[idx])
    return " ".join(words)


def drop_function_words(message):
    """Remove articles, prepositions, pronouns."""
    words = message.split()
    result = [w for w in words if w.lower() not in DROP_WORDS]
    return " ".join(result) if result else message


def apply_homophones(message):
    """Replace one word with a homophone."""
    words = message.split()
    candidates = [(i, w) for i, w in enumerate(words) if w.lower() in HOMOPHONES]
    if not candidates:
        return message
    idx, word = random.choice(candidates)
    replacement = random.choice(HOMOPHONES[word.lower()])
    words[idx] = replacement
    return " ".join(words)


def phonetic_typo(message):
    """Introduce character-level phonetic errors in one word."""
    words = message.split()
    if len(words) < 2:
        return message

    # Pick a content word (skip short words)
    long_words = [(i, w) for i, w in enumerate(words) if len(w) > 3]
    if not long_words:
        return message

    idx, word = random.choice(long_words)
    typo_type = random.choice(["swap", "drop", "double", "replace"])

    chars = list(word.lower())
    if typo_type == "swap" and len(chars) > 2:
        p = random.randint(1, len(chars) - 2)
        chars[p], chars[p + 1] = chars[p + 1], chars[p]
    elif typo_type == "drop" and len(chars) > 3:
        p = random.randint(1, len(chars) - 2)
        chars.pop(p)
    elif typo_type == "double" and len(chars) > 2:
        p = random.randint(0, len(chars) - 1)
        chars.insert(p, chars[p])
    elif typo_type == "replace":
        replacements = {"i": "e", "e": "i", "o": "u", "u": "o", "a": "e",
                        "s": "z", "c": "k", "k": "c", "t": "d", "d": "t"}
        p = random.randint(0, len(chars) - 1)
        if chars[p] in replacements:
            chars[p] = replacements[chars[p]]

    words[idx] = "".join(chars)
    return " ".join(words)


def merge_words(message):
    """Merge two adjacent words (word boundary error)."""
    words = message.split()
    if len(words) < 3:
        return message
    idx = random.randint(0, len(words) - 2)
    merged = words[idx] + words[idx + 1]
    return " ".join(words[:idx] + [merged] + words[idx + 2:])


def truncate_message(message):
    """Cut the message short (simulating audio cutoff)."""
    words = message.split()
    if len(words) <= 2:
        return message
    cut_at = random.randint(max(2, len(words) - 2), len(words) - 1)
    last_word = words[cut_at - 1]
    # Optionally truncate the last word too
    if len(last_word) > 4 and random.random() < 0.5:
        cut_chars = random.randint(2, len(last_word) - 1)
        words[cut_at - 1] = last_word[:cut_chars]
    return " ".join(words[:cut_at])


def caveman_grammar(message, landmark_hint=None):
    """Rewrite as broken grammar with minimal function words.

    Examples:
        "Take me to the kitchen" → "me go kitchen"
        "Show me around" → "show around me"
        "Can you navigate to the office?" → "go office"
    """
    templates_move = [
        "me go {landmark}",
        "{landmark} go now",
        "robot {landmark}",
        "go {landmark} me",
        "want {landmark}",
        "need {landmark} now",
        "{landmark} please",
        "me need {landmark}",
        "bring {landmark}",
        "{landmark} take",
    ]

    templates_tour = [
        "me see all",
        "show all places",
        "tour me",
        "see everything me",
        "all rooms show",
        "go everywhere",
    ]

    templates_cancel = [
        "stop now",
        "no go",
        "back home",
        "stop robot",
        "no more go",
        "home now",
    ]

    if landmark_hint:
        tpl = random.choice(templates_move)
        return tpl.format(landmark=landmark_hint)

    # Try to detect intent from message
    msg_lower = message.lower()
    if any(w in msg_lower for w in ["show me around", "tour", "everything", "all"]):
        return random.choice(templates_tour)
    if any(w in msg_lower for w in ["stop", "cancel", "home", "abort"]):
        return random.choice(templates_cancel)

    return drop_function_words(message.lower())


# ============================================================
# AUGMENTATION ENGINE
# ============================================================

# Available noise functions and their weights (higher = more likely to be picked)
NOISE_FUNCTIONS = [
    (add_fillers, 2),
    (add_stutter, 2),
    (drop_function_words, 2),
    (apply_homophones, 2),
    (phonetic_typo, 3),
    (merge_words, 1),
    (truncate_message, 1),
]


def augment_message(message, n_transforms=1):
    """Apply N random noise transforms to a clean message.

    Returns the noisy message.
    """
    funcs = [f for f, _ in NOISE_FUNCTIONS]
    weights = [w for _, w in NOISE_FUNCTIONS]

    result = message
    selected = random.choices(funcs, weights=weights, k=n_transforms)
    for func in selected:
        result = func(result)
    return result


def generate_noisy_variants(message, n_variants=3, max_transforms=2):
    """Generate multiple noisy variants of a clean message.

    Returns a list of unique noisy messages (excludes the original).
    """
    variants = set()
    attempts = 0
    max_attempts = n_variants * 5

    while len(variants) < n_variants and attempts < max_attempts:
        n_t = random.randint(1, max_transforms)
        noisy = augment_message(message, n_transforms=n_t)
        if noisy.lower() != message.lower():
            variants.add(noisy)
        attempts += 1

    return list(variants)
