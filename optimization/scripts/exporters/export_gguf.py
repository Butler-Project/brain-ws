"""
Step 3: Export the fine-tuned student model to GGUF format.

Converts the merged FP16 model to GGUF Q4_K_M for deployment
on the N100 with Ollama or llama.cpp.

Input:  artifacts/models/<model-name>/merged/
Output: artifacts/models/<model-name>/gguf/

Usage:
    python export_gguf.py --model-name distilled-1b-robot-router
    python export_gguf.py --model-name distilled-1b-robot-router -q q8_0
"""

import argparse

from unsloth import FastLanguageModel

from utils import TRAINING_CFG, model_output_dir


def main():
    parser = argparse.ArgumentParser(description="Export student model to GGUF")
    parser.add_argument("--model-name", required=True, help="Name of the model directory")
    parser.add_argument(
        "--quantization", "-q",
        default="q4_k_m",
        help="GGUF quantization type (default: q4_k_m)",
    )
    args = parser.parse_args()

    output_dir = model_output_dir(args.model_name)
    merged_dir = output_dir / "merged"
    gguf_dir = output_dir / "gguf"

    if not merged_dir.exists():
        print(f"ERROR: {merged_dir} not found. Run train_student.py first.")
        return

    print("=" * 60)
    print("  EXPORT TO GGUF")
    print("=" * 60)
    print(f"  Input:        {merged_dir}")
    print(f"  Output:       {gguf_dir}")
    print(f"  Quantization: {args.quantization}")
    print("=" * 60)

    print("\n[1/2] Loading merged model...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=str(merged_dir),
        max_seq_length=TRAINING_CFG.get("max_seq_length", 512),
        dtype=None,
        load_in_4bit=False,
    )

    print("[2/2] Exporting to GGUF...")
    gguf_dir.mkdir(parents=True, exist_ok=True)

    model.save_pretrained_gguf(
        str(gguf_dir),
        tokenizer,
        quantization_method=args.quantization,
    )

    gguf_files = list(gguf_dir.glob("*.gguf"))
    if gguf_files:
        for f in gguf_files:
            size_mb = f.stat().st_size / 1024 / 1024
            print(f"  {f.name}: {size_mb:.1f} MB")

    print("\n" + "=" * 60)
    print("  GGUF EXPORT COMPLETE")
    print(f"  Files in: {gguf_dir}")
    print("=" * 60)
    


if __name__ == "__main__":
    main()
