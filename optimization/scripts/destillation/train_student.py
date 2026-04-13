"""
Step 2: Fine-tune student model using Knowledge Distillation.

Uses Unsloth + QLoRA + SFTTrainer to train the 1B student model
on the teacher's validated responses.

Input:  dataset/training/train.jsonl + eval.jsonl
Output: models/<model-name>/  (LoRA adapters + merged model)

Usage:
    python train_student.py --model-name distilled-1b-robot-router
    python train_student.py --model-name distilled-1b-robot-router --epochs 5
    python train_student.py --model-name distilled-1b-robot-router --dry-run
"""

import argparse

import torch
from datasets import Dataset
from unsloth import FastLanguageModel, is_bfloat16_supported
from trl import SFTConfig, SFTTrainer

from utils import (
    CONFIG,
    EVAL_FILE,
    SEED,
    STUDENT_MODEL_ID,
    TRAIN_FILE,
    TRAINING_CFG,
    load_jsonl,
    model_output_dir,
)


def __parse_args():
    parser = argparse.ArgumentParser(description="Fine-tune student model via distillation")
    parser.add_argument("--model-name", required=True, help="Name for the output model directory")
    parser.add_argument("--epochs", type=int, default=TRAINING_CFG.get("epochs", 3))
    parser.add_argument("--batch-size", type=int, default=TRAINING_CFG.get("batch_size", 4))
    parser.add_argument("--lr", type=float, default=TRAINING_CFG.get("learning_rate", 2e-5))
    parser.add_argument("--max-seq-length", type=int, default=TRAINING_CFG.get("max_seq_length", 512))
    parser.add_argument("--lora-r", type=int, default=TRAINING_CFG.get("lora_r", 16))
    parser.add_argument("--lora-alpha", type=int, default=TRAINING_CFG.get("lora_alpha", 32))
    parser.add_argument("--dry-run", action="store_true", help="Load data and model, skip training")
    return parser.parse_args()


def __load_model(args):
    """Load student model in 4-bit and attach LoRA adapters."""
    print("\n[1/4] Loading student model with Unsloth...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=STUDENT_MODEL_ID,
        max_seq_length=args.max_seq_length,
        dtype=None,
        load_in_4bit=True,
    )

    print("[2/4] Adding LoRA adapters...")
    model = FastLanguageModel.get_peft_model(
        model,
        r=args.lora_r,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
        lora_alpha=args.lora_alpha,
        lora_dropout=TRAINING_CFG.get("lora_dropout", 0.05),
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=SEED,
    )

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    print(f"  Trainable: {trainable:,} / {total:,} ({trainable/total*100:.2f}%)")

    # Debug: tokenizer state BEFORE fix
    print(f"  [DEBUG] eos_token BEFORE fix: {repr(tokenizer.eos_token)}")
    print(f"  [DEBUG] eos_token_id BEFORE fix: {repr(tokenizer.eos_token_id)}")
    print(f"  [DEBUG] pad_token BEFORE fix: {repr(tokenizer.pad_token)}")
    print(f"  [DEBUG] chat_template has <EOS_TOKEN>: {'<EOS_TOKEN>' in (tokenizer.chat_template or '')}")
    print(f"  [DEBUG] all special tokens: {tokenizer.all_special_tokens[:10]}")

    # Fix Unsloth's <EOS_TOKEN> placeholder — must be AFTER get_peft_model
    real_eos = tokenizer.convert_ids_to_tokens(tokenizer.eos_token_id) or "<|eot_id|>"
    if tokenizer.eos_token in (None, "<EOS_TOKEN>"):
        tokenizer.eos_token = real_eos
    if tokenizer.pad_token in (None, "<EOS_TOKEN>"):
        tokenizer.pad_token = tokenizer.eos_token
    if tokenizer.chat_template and "<EOS_TOKEN>" in tokenizer.chat_template:
        tokenizer.chat_template = tokenizer.chat_template.replace("<EOS_TOKEN>", tokenizer.eos_token)

    # Debug: tokenizer state AFTER fix
    print(f"  [DEBUG] eos_token AFTER fix: {repr(tokenizer.eos_token)}")
    print(f"  [DEBUG] eos_token_id AFTER fix: {repr(tokenizer.eos_token_id)}")
    print(f"  [DEBUG] pad_token AFTER fix: {repr(tokenizer.pad_token)}")
    print(f"  [DEBUG] chat_template has <EOS_TOKEN>: {'<EOS_TOKEN>' in (tokenizer.chat_template or '')}")

    return model, tokenizer


def __format_dataset(records, tokenizer):
    """Apply chat template to each record and return Dataset with 'text' column."""
    eos = tokenizer.eos_token or "</s>"
    formatted = []
    for record in records:
        text = tokenizer.apply_chat_template(
            record["messages"],
            tokenize=False,
            add_generation_prompt=False,
        )
        text = text.replace("<EOS_TOKEN>", eos)
        formatted.append({"text": text})
    return Dataset.from_list(formatted)


def __load_datasets(tokenizer):
    """Load train and eval datasets, apply chat template."""
    print("[3/4] Loading and formatting datasets...")
    train_records = load_jsonl(TRAIN_FILE)
    train_dataset = __format_dataset(train_records, tokenizer)
    print(f"  Train: {len(train_dataset)} examples")

    eval_dataset = None
    if EVAL_FILE.exists():
        eval_records = load_jsonl(EVAL_FILE)
        eval_dataset = __format_dataset(eval_records, tokenizer)
        print(f"  Eval:  {len(eval_dataset)} examples")

    return train_dataset, eval_dataset


def __dry_run(train_dataset):
    """Show a sample and exit without training."""
    print("\n--- DRY RUN: skipping training ---")
    sample = train_dataset[0]
    print("\nFormatted sample (first 500 chars):")
    print(sample["text"][:500])
    print("...")


def __train(model, tokenizer, train_dataset, eval_dataset, args, output_dir):
    """Run SFTTrainer and return training stats."""
    print("[4/4] Starting training...")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Debug: verify tokenizer state right before SFTTrainer
    print(f"  [DEBUG] tokenizer.eos_token at SFTTrainer init: {repr(tokenizer.eos_token)}")
    print(f"  [DEBUG] tokenizer.eos_token_id at SFTTrainer init: {repr(tokenizer.eos_token_id)}")
    print(f"  [DEBUG] tokenizer.pad_token at SFTTrainer init: {repr(tokenizer.pad_token)}")

    sft_eos_token = tokenizer.eos_token
    sft_pad_token = tokenizer.pad_token or tokenizer.eos_token

    sft_config = SFTConfig(
        output_dir=str(output_dir / "checkpoints"),
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=4,
        warmup_steps=10,
        num_train_epochs=args.epochs,
        learning_rate=args.lr,
        fp16=not is_bfloat16_supported(),
        bf16=is_bfloat16_supported(),
        logging_steps=10,
        eval_strategy="epoch" if eval_dataset else "no",
        save_strategy="epoch",
        save_total_limit=2,
        optim="adamw_8bit",
        seed=SEED,
        report_to="none",
        dataset_num_proc=1,
        max_length=args.max_seq_length,
        eos_token=sft_eos_token,
        pad_token=sft_pad_token,
    )

    print(f"  [DEBUG] sft_config.eos_token: {repr(sft_config.eos_token)}")
    print(f"  [DEBUG] sft_config.pad_token: {repr(sft_config.pad_token)}")

    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        args=sft_config,
    )

    if torch.cuda.is_available():
        mem = torch.cuda.memory_allocated() / 1024**3
        print(f"  GPU memory before training: {mem:.2f} GB")

    trainer_stats = trainer.train()

    print(f"\n  Training complete!")
    print(f"  Train loss: {trainer_stats.training_loss:.4f}")
    print(f"  Train time: {trainer_stats.metrics['train_runtime']:.1f}s")

    return trainer_stats


def __save_model(model, tokenizer, output_dir, model_name):
    """Save LoRA adapters and merged FP16 model."""
    lora_dir = output_dir / "lora"
    print("\nSaving LoRA adapters...")
    model.save_pretrained(str(lora_dir))
    tokenizer.save_pretrained(str(lora_dir))
    print(f"  Saved to: {lora_dir}")

    merged_dir = output_dir / "merged"
    print("\nMerging LoRA into base model (FP16)...")
    model.save_pretrained_merged(
        str(merged_dir),
        tokenizer,
        save_method="merged_16bit",
    )
    print(f"  Merged model saved to: {merged_dir}")

    print("\n" + "=" * 60)
    print("  TRAINING COMPLETE")
    print(f"  LoRA adapters: {lora_dir}")
    print(f"  Merged model:  {merged_dir}")
    print("=" * 60)
    print(f"\nNext step: python export_gguf.py --model-name {model_name}")


def main():
    args = __parse_args()
    output_dir = model_output_dir(args.model_name)

    if not TRAIN_FILE.exists():
        print(f"ERROR: {TRAIN_FILE} not found. Run prepare_training_data.py first.")
        return

    print("=" * 60)
    print("  KNOWLEDGE DISTILLATION — STUDENT TRAINING")
    print("=" * 60)
    print(f"  Student model: {STUDENT_MODEL_ID}")
    print(f"  Output dir:    {output_dir}")
    print(f"  Epochs: {args.epochs}  Batch: {args.batch_size}  LR: {args.lr}")
    print(f"  LoRA r={args.lora_r}  alpha={args.lora_alpha}")
    print("=" * 60)

    model, tokenizer = __load_model(args)
    train_dataset, eval_dataset = __load_datasets(tokenizer)

    if args.dry_run:
        __dry_run(train_dataset)
        return

    __train(model, tokenizer, train_dataset, eval_dataset, args, output_dir)
    __save_model(model, tokenizer, output_dir, args.model_name)


if __name__ == "__main__":
    main()
