#!/bin/bash

# First, change to the script's directory
cd "$(dirname "$0")"

source .venv/bin/activate
python src/brain_launch/glados.py