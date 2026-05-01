# GPU Ollama Image

This image builds the `robot-router` Ollama model from the shared source at
`model/system_prompt/MODELFILE`.

Run from the repo root:

```bash
cd /home/operador/Documents/brain-ws &&
docker compose -f docker/models/gpu/docker-compose.yaml build --no-cache &&
docker compose -f docker/models/gpu/docker-compose.yaml up -d &&
cd /home/operador/Documents/brain-ws/optimization/scripts/destillation &&
python3 optimization/scripts/dataset_creation/sintetic_dataset_generator.py &&
python3 scripts/dataset_creation/teacher_dataset_evaluator.py -c all
```

The compose file uses the repo root as build context so the Docker build can read
`model/system_prompt/MODELFILE` and generate the final Ollama `Modelfile` with
the selected base model from `MODEL`.
