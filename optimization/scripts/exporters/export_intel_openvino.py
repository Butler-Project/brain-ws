"""
Export the fine-tuned student model to OpenVINO IR + NNCF INT4 quantization.

Input:  artifacts/models/<model-name>/merged/
Output: artifacts/models/<model-name>/openvino_int4/

Usage:
    python export_intel_openvino.py --model-name distilled-1b-robot-router
"""

import argparse
import shutil
import sys
from importlib import metadata
from pathlib import Path

# Resolve utils from destillation/ regardless of working directory
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "destillation"))
from utils import CONFIG, model_output_dir


def _package_version(name: str):
    """Return the installed package version, or None if it is missing."""
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def _load_openvino_stack():
    """Import the OpenVINO export stack with actionable compatibility errors."""
    try:
        from nncf import CompressWeightsMode, compress_weights
    except ImportError as exc:
        print("ERROR: Could not import NNCF, which is required for INT4 quantization.")
        print(f"  nncf: {_package_version('nncf') or 'not installed'}")
        print("Fix: install or upgrade `nncf` in the optimization virtualenv.")
        raise SystemExit(1) from exc

    try:
        from optimum.intel import OVModelForCausalLM
    except ImportError as exc:
        print("ERROR: Could not import `OVModelForCausalLM` from `optimum.intel`.")
        print(f"  optimum-intel: {_package_version('optimum-intel') or 'not installed'}")
        print(f"  openvino:      {_package_version('openvino') or 'not installed'}")
        print(f"  openvino-dev:  {_package_version('openvino-dev') or 'not installed'}")
        if "requires OpenVINO version" in str(exc):
            print("Cause: the installed `optimum-intel` requires a newer OpenVINO runtime.")
            print("Fix: upgrade `openvino` and `openvino-dev` to 2025.4.0 or newer")
            print("     in the same virtualenv, or use a separate env with matching versions.")
        else:
            print(f"Original import error: {exc}")
        raise SystemExit(1) from exc

    return OVModelForCausalLM, CompressWeightsMode, compress_weights


def export(model_name: str):
    OVModelForCausalLM, CompressWeightsMode, compress_weights = _load_openvino_stack()
    output_dir = model_output_dir(model_name)
    merged_dir = output_dir / "merged"
    openvino_dir = output_dir / "openvino_int4"
    ov_cfg = CONFIG["openvino"]

    if not merged_dir.exists():
        print(f"ERROR: {merged_dir} not found. Run train_student.py first.")
        return

    print("=" * 60)
    print("  EXPORT TO OPENVINO INT4")
    print("=" * 60)
    print(f"  Input:  {merged_dir}")
    print(f"  Output: {openvino_dir}")
    print(f"  Mode:   {ov_cfg['quantization_mode']}  group={ov_cfg['group_size']}  ratio={ov_cfg['ratio']}")
    print("=" * 60)

    print("\n[1/3] Convirtiendo a OpenVINO IR ...")
    model = OVModelForCausalLM.from_pretrained(str(merged_dir), export=True)

    print("[2/3] Cuantizando con NNCF INT4 AWQ ...")
    model.model = compress_weights(
        model.model,
        mode=CompressWeightsMode.INT4_ASYM,
        group_size=ov_cfg["group_size"],
        ratio=ov_cfg["ratio"],
    )

    print(f"[3/3] Guardando en {openvino_dir} ...")
    openvino_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(openvino_dir))

    for f in merged_dir.iterdir():
        if f.suffix in (".json", ".jinja") and f.name != "config.json":
            shutil.copy(f, openvino_dir / f.name)

    size_mb = sum(f.stat().st_size for f in openvino_dir.rglob("*") if f.is_file()) / 1e6
    print(f"\nListo. Modelo OpenVINO INT4 en: {openvino_dir}")
    print(f"Tamaño total: {size_mb:.0f} MB")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export student model to OpenVINO INT4")
    parser.add_argument("--model-name", required=True, help="Name of the model directory")
    args = parser.parse_args()
    export(args.model_name)
