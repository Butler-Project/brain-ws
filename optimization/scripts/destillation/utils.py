"""
Shared configuration and utilities for the distillation pipeline.
"""

import json
from pathlib import Path

import yaml

# ============================================================
# PATHS
# ============================================================

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.yaml"
MODELFILE_PATH = SCRIPT_DIR.parents[2] / "docker" / "models" / "gpu" / "Modelfile"

with open(CONFIG_PATH) as f:
    CONFIG = yaml.safe_load(f)

DATASET_DIR = Path(CONFIG["paths"]["dataset_dir"])
MODELS_DIR = Path(CONFIG["paths"]["models_dir"])
SEED = CONFIG["dataset"].get("seed", 42)
STUDENT_MODEL_ID = CONFIG["student"]["model_id"]
TRAINING_CFG = CONFIG["training"]

RESULT_FILES = [
    DATASET_DIR / "explicit" / "explicit_results.jsonl",
    DATASET_DIR / "implicit" / "implicit_results.jsonl",
    DATASET_DIR / "natural_language" / "natural_language_results.jsonl",
    DATASET_DIR / "invalids" / "invalid_results.jsonl",
]

TRAINING_DIR = DATASET_DIR / "training"
TRAIN_FILE = TRAINING_DIR / "train.jsonl"
EVAL_FILE = TRAINING_DIR / "eval.jsonl"


# ============================================================
# HELPERS
# ============================================================

def model_output_dir(model_name):
    """Return the output directory for a given model name."""
    return MODELS_DIR / model_name


def extract_system_prompt():
    """Extract the SYSTEM prompt from the Ollama ModelFile."""
    text = MODELFILE_PATH.read_text()
    start = text.find('SYSTEM """')
    if start == -1:
        raise ValueError(f"Could not find SYSTEM prompt in {MODELFILE_PATH}")
    start += len('SYSTEM """')
    end = text.find('"""', start)
    if end == -1:
        raise ValueError(f"Could not find closing triple quotes in {MODELFILE_PATH}")
    return text[start:end].strip()


def load_jsonl(path):
    """Load a JSONL file into a list of dicts."""
    records = []
    with open(path) as f:
        for line in f:
            records.append(json.loads(line))
    return records
