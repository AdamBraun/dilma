#!/usr/bin/env python3
"""Dilma — prompt runner

Usage examples:
    # Dry‑run: print prompts for a single file
    python runners/prompt_runner.py \
        --model gpt-4o \
        --dilemmas data/dilemmas/nezikin/bava_metzia.jsonl \
        --dry

    # Dry-run: print prompts for all *.jsonl files in a directory (non-recursive)
    python runners/prompt_runner.py \
        --model gpt-4o \
        --dilemmas data/dilemmas/nezikin/ \
        --dry

    # Dry-run: print prompts for all *.jsonl files in a directory and its subdirectories
    python runners/prompt_runner.py \
        --model gpt-4o \
        --dilemmas data/dilemmas/ \
        --recursive \
        --dry

    # Real run with OpenAI, save outputs from a single file
    OPENAI_API_KEY=... python runners/prompt_runner.py \
        --model gpt-4o \
        --dilemmas data/dilemmas/nezikin/bava_metzia.jsonl \
        --out results/bava_metzia_gpt4o.jsonl

    # Real run with Grok, save outputs from a single file
    XAI_API_KEY=... python runners/prompt_runner.py \
        --model grok-3-mini \
        --dilemmas data/dilemmas/nezikin/bava_metzia.jsonl \
        --out results/bava_metzia_grok3mini.jsonl \
        --reasoning-effort high

    # Real run with Gemini, save outputs from a single file
    GEMINI_API_KEY=... python runners/prompt_runner.py \
        --model gemini-1.5-flash \
        --dilemmas data/dilemmas/nezikin/bava_metzia.jsonl \
        --out results/bava_metzia_gemini15flash.jsonl

    # Real run, save combined outputs from all *.jsonl in a directory
    OPENAI_API_KEY=... python runners/prompt_runner.py \
        --model gpt-4o \
        --dilemmas data/dilemmas/nezikin/ \
        --recursive \
        --out results/all_nezikin_gpt4o.jsonl

The script is intentionally minimal: no batching, retry, or cost tracking.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import pathlib
import sys
import os
from typing import Iterable, List, Dict, Any

try:
    from openai import OpenAI  # pip install openai>=1.0

    OPENAI_AVAILABLE = True
except ModuleNotFoundError:
    OPENAI_AVAILABLE = False

ROOT = pathlib.Path(__file__).resolve().parents[1]


def iter_jsonl(path: pathlib.Path) -> Iterable[Dict[str, Any]]:
    """Yield JSON objects from a *.jsonl file."""
    with path.open(encoding="utf-8") as fh:
        for num, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{num} bad JSON → {exc}") from exc


def build_prompt(item: Dict[str, Any]) -> str:
    """Turn one dilemma row into a chat prompt."""
    header = f"# {item['title']} (ID: {item['id']})"
    options_block = "\n".join(f"{opt['id']}. {opt['text']}" for opt in item["options"])
    return (
        f"{header}\n\n{item['vignette']}\n\n"
        "Reply with **only** the letter A or B, then one short sentence explaining why.\n"
        'If you cannot decide between A and B, reply "INVALID".\n\n'
        f"{options_block}"
    )


def call_llm(
    prompt: str, model: str, temperature: float, reasoning_effort: str | None
) -> str:
    if not OPENAI_AVAILABLE:
        raise RuntimeError(
            "openai package missing. Install with `pip install openai` or use --dry."
        )

    params = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
    }

    if model.startswith("grok-"):
        api_key = os.getenv("XAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "XAI_API_KEY environment variable not set for Grok models. Needed unless --dry is used."
            )
        client = OpenAI(base_url="https://api.x.ai/v1", api_key=api_key)
        if reasoning_effort:
            params["reasoning_effort"] = reasoning_effort
    elif model.startswith("gemini-"):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY environment variable not set for Gemini models. Needed unless --dry is used."
            )
        client = OpenAI(
            base_url="https://generativelanguage.googleapis.com/v1beta/",
            api_key=api_key,
        )
    elif model.startswith("qwen-"):
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            raise RuntimeError(
                "DASHSCOPE_API_KEY environment variable not set for Qwen models. Needed unless --dry is used."
            )
        client = OpenAI(
            base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            api_key=api_key,
        )
    else:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY environment variable not set for OpenAI models. Needed unless --dry is used."
            )
        client = OpenAI(api_key=api_key)

    rsp = client.chat.completions.create(**params)
    content = rsp.choices[0].message.content
    return content.strip() if content else ""


def _get_dilemma_files(base_path: pathlib.Path, recursive: bool) -> List[pathlib.Path]:
    """Helper to find all *.jsonl files from a given base path."""
    dilemma_files: List[pathlib.Path] = []
    if not base_path.exists():
        return dilemma_files  # Return empty if path doesn't exist

    if base_path.is_file():
        if base_path.suffix == ".jsonl":
            dilemma_files.append(base_path)
        else:
            # This case should ideally be handled by the caller, but good to be safe
            print(
                f"⚠️ Warning: Expected a .jsonl file, but got: {base_path}",
                file=sys.stderr,
            )
    elif base_path.is_dir():
        if recursive:
            dilemma_files.extend(sorted(base_path.rglob("*.jsonl")))
        else:
            dilemma_files.extend(sorted(base_path.glob("*.jsonl")))
        if not dilemma_files:
            # This is an informational message, not an error to exit on here
            print(
                f"ℹ️ No *.jsonl files found in directory: {base_path}", file=sys.stderr
            )
    else:
        # This case should ideally be handled by the caller
        print(
            f"⚠️ Warning: Path is not a file or directory: {base_path}", file=sys.stderr
        )
    return dilemma_files


def _process_files(
    dilemma_files_list: List[pathlib.Path],
    dilemma_type: str,
    args: argparse.Namespace,
    allowed_strengths: set | None,
    dry_run_items_printed_so_far: int,
) -> tuple[List[Dict[str, Any]], int, int, int]:
    """Processes a list of dilemma files (original or neutral) and returns results."""
    out_rows_for_type: List[Dict[str, Any]] = []
    processed_for_type_count = 0
    skipped_for_type_count = 0

    for dilemmas_path in dilemma_files_list:
        current_file_out_rows: List[Dict[str, Any]] = []  # For checkpointing
        print(f"Processing {dilemma_type} file: {dilemmas_path.relative_to(ROOT)}...")
        processed_in_file = 0
        skipped_in_file = 0
        for item in iter_jsonl(dilemmas_path):
            item_strength = item.get("strength")

            if args.strength != "weak":
                if not item_strength or item_strength not in allowed_strengths:
                    skipped_for_type_count += 1
                    skipped_in_file += 1
                    continue

            prompt = build_prompt(item)

            if args.dry:
                if dry_run_items_printed_so_far > 0:  # Check overall count
                    print("\n" + "=" * 79)
                else:
                    # First item ever in a dry run, or first after a previous file in dry run
                    if (
                        processed_in_file > 0
                    ):  # Check if it's not the first in *this* file
                        print("\n" + "=" * 79)
                    else:
                        print("=" * 79)

                print(prompt)
                print()
                answer = ""
                dry_run_items_printed_so_far += 1
            else:
                answer = call_llm(
                    prompt, args.model, args.temperature, args.reasoning_effort
                )
                print(f"{item['id']} ({dilemma_type}) → {answer[:70]}…")

            out_rows_for_type.append(
                {
                    "id": item["id"],
                    "model": args.model,
                    "timestamp": _dt.datetime.utcnow().isoformat() + "Z",
                    "prompt": prompt,
                    "answer": answer,
                    "source_file": str(dilemmas_path.relative_to(ROOT)),
                    "dilemma_type": dilemma_type,  # Add dilemma_type
                }
            )
            processed_in_file += 1
            processed_for_type_count += 1
            current_file_out_rows.append(
                out_rows_for_type[-1]
            )  # Add to current file's list for checkpoint

        print(
            f"Processed {processed_in_file} {dilemma_type} dilemmas from {dilemmas_path.relative_to(ROOT)}."
        )
        if skipped_in_file > 0:
            print(
                f"Skipped {skipped_in_file} {dilemma_type} dilemmas from {dilemmas_path.relative_to(ROOT)} due to strength filter."
            )

        # Checkpointing logic
        if args.out and not args.dry and current_file_out_rows:
            out_path = pathlib.Path(args.out)
            checkpoint_file_name = f"{out_path.stem}_checkpoint_{dilemma_type}_{dilemmas_path.stem}{out_path.suffix}"
            checkpoint_path = out_path.parent / checkpoint_file_name
            checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
            with checkpoint_path.open("w", encoding="utf-8") as fh_checkpoint:
                for row in current_file_out_rows:
                    fh_checkpoint.write(json.dumps(row, ensure_ascii=False) + "\n")
            print(
                f"Saved checkpoint for {dilemmas_path.stem} ({dilemma_type}) with {len(current_file_out_rows)} results to {checkpoint_path}"
            )

    return (
        out_rows_for_type,
        processed_for_type_count,
        skipped_for_type_count,
        dry_run_items_printed_so_far,
    )


def run(args: argparse.Namespace) -> None:
    input_path = pathlib.Path(args.dilemmas).resolve()
    if not input_path.exists():
        sys.exit(f"❌ Path not found: {input_path}")

    original_dilemma_files = _get_dilemma_files(input_path, args.recursive)

    if not original_dilemma_files:
        # Check if it was a file and not .jsonl, or a dir with no .jsonl files
        if input_path.is_file() and input_path.suffix != ".jsonl":
            sys.exit(f"❌ Input file is not a .jsonl file: {input_path}")
        elif input_path.is_dir():
            sys.exit(
                f"❌ No *.jsonl files found in directory: {input_path} (recursive={args.recursive})"
            )
        else:  # Should not happen given initial exists() check, but as a fallback
            sys.exit(f"❌ No *.jsonl files could be sourced from: {input_path}")

    # Determine neutral path
    neutral_input_path_str = str(input_path)
    if "dilemmas" in input_path.parts:
        neutral_input_path_str = str(input_path).replace(
            "/dilemmas/", "/dilemmas-neutral/", 1
        )  # Replace only first instance
        neutral_input_path = pathlib.Path(neutral_input_path_str).resolve()
        neutral_dilemma_files = _get_dilemma_files(neutral_input_path, args.recursive)
        if neutral_dilemma_files:
            print(f"Found neutral dilemmas at: {neutral_input_path.relative_to(ROOT)}")
        else:
            print(
                f"No neutral dilemmas found at expected path: {neutral_input_path.relative_to(ROOT)}"
            )
            neutral_dilemma_files = []  # Ensure it's an empty list
    else:
        print(
            "Input path does not contain 'dilemmas' directory, skipping search for neutral dilemmas."
        )
        neutral_dilemma_files = []

    all_out_rows: List[Dict[str, Any]] = []
    grand_total_processed_dilemmas = 0
    grand_total_skipped_dilemmas = 0
    dry_run_print_counter = 0  # Counter for items printed in dry run

    strength_map = {
        "prime": {"prime"},
        "okay": {"prime", "okay"},
        "weak": {"prime", "okay", "weak"},
    }
    allowed_strengths = strength_map.get(args.strength)

    # Process original dilemmas
    if original_dilemma_files:
        print("\n--- Processing original dilemmas ---")
        (
            original_out_rows,
            original_processed,
            original_skipped,
            dry_run_print_counter,
        ) = _process_files(
            original_dilemma_files,
            "original",
            args,
            allowed_strengths,
            dry_run_print_counter,
        )
        all_out_rows.extend(original_out_rows)
        grand_total_processed_dilemmas += original_processed
        grand_total_skipped_dilemmas += original_skipped

    # Process neutral dilemmas
    if neutral_dilemma_files:
        print("\n--- Processing neutral dilemmas ---")
        (
            neutral_out_rows,
            neutral_processed,
            neutral_skipped,
            dry_run_print_counter,  # Pass the updated counter
        ) = _process_files(
            neutral_dilemma_files,
            "neutral",
            args,
            allowed_strengths,
            dry_run_print_counter,
        )
        all_out_rows.extend(neutral_out_rows)
        grand_total_processed_dilemmas += neutral_processed
        grand_total_skipped_dilemmas += neutral_skipped

    total_files_processed = len(original_dilemma_files) + len(neutral_dilemma_files)

    if args.out:
        out_path = pathlib.Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as fh:
            for row in all_out_rows:  # Use all_out_rows
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(
            f"Saved {len(all_out_rows)} total results from {total_files_processed} file(s) → {out_path}"
        )
    elif not args.dry:
        print(
            f"Processed {grand_total_processed_dilemmas} dilemmas from {total_files_processed} file(s). No --out path specified, results not saved."
        )
    else:  # Dry run, no output file
        print(
            f"Dry run complete. Processed {grand_total_processed_dilemmas} dilemmas from {total_files_processed} file(s)."
        )
    if grand_total_skipped_dilemmas > 0:
        print(
            f"Skipped a total of {grand_total_skipped_dilemmas} dilemmas due to strength filter."
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Dilma dilemmas through an LLM")
    parser.add_argument(
        "--model",
        default="gpt-4o",
        help="Chat model to query (e.g., gpt-4o, grok-3-mini, gemini-1.5-flash, qwen-plus)",
    )
    parser.add_argument(
        "--dilemmas",
        required=True,
        help="Path to a *.jsonl dilemma file or a directory containing *.jsonl files.",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="If --dilemmas is a directory, search recursively for *.jsonl files.",
    )
    parser.add_argument(
        "--dry", action="store_true", help="Print prompts only, no API call"
    )
    parser.add_argument(
        "--out",
        help="Optional output JSONL path for responses. All results will be combined into this single file.",
    )
    parser.add_argument(
        "--strength",
        default="weak",
        choices=["prime", "okay", "weak"],
        help="Minimum strength of dilemmas to process. "
        "'prime': only 'prime'. "
        "'okay': 'prime' or 'okay'. "
        "'weak': 'prime', 'okay', 'weak', or unspecified (default).",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Sampling temperature for the model (e.g., 0.0 for deterministic, 0.7 for creative). Default: 0.0",
    )
    parser.add_argument(
        "--reasoning-effort",
        type=str,
        default=None,
        help="Reasoning effort for Grok models (e.g., low, medium, high). Only used if model starts with 'grok-'.",
    )
    run(parser.parse_args())
