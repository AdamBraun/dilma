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
    else:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY environment variable not set for OpenAI models. Needed unless --dry is used."
            )
        client = OpenAI(api_key=api_key)

    rsp = client.chat.completions.create(**params)
    return rsp.choices[0].message.content.strip()


def run(args: argparse.Namespace) -> None:
    input_path = pathlib.Path(args.dilemmas).resolve()
    if not input_path.exists():
        sys.exit(f"❌ Path not found: {input_path}")

    dilemma_files: List[pathlib.Path] = []
    if input_path.is_file():
        if input_path.suffix == ".jsonl":
            dilemma_files.append(input_path)
        else:
            sys.exit(f"❌ Input file is not a .jsonl file: {input_path}")
    elif input_path.is_dir():
        if args.recursive:
            dilemma_files.extend(sorted(input_path.rglob("*.jsonl")))
        else:
            dilemma_files.extend(sorted(input_path.glob("*.jsonl")))
        if not dilemma_files:
            sys.exit(f"❌ No *.jsonl files found in directory: {input_path}")
    else:
        sys.exit(f"❌ Input path is not a file or directory: {input_path}")

    out_rows: List[Dict[str, Any]] = []
    total_processed_dilemmas = 0
    total_skipped_dilemmas = 0

    # Define strength hierarchies
    strength_map = {
        "prime": {"prime"},
        "okay": {"prime", "okay"},
        "weak": {
            "prime",
            "okay",
            "weak",
        },  # "weak" also includes items without a strength property
    }
    allowed_strengths = strength_map.get(args.strength)

    for dilemmas_path in dilemma_files:
        print(f"Processing file: {dilemmas_path.relative_to(ROOT)}...")
        processed_in_file = 0
        skipped_in_file = 0
        for item in iter_jsonl(dilemmas_path):
            item_strength = item.get("strength")

            # Apply strength filter
            if args.strength != "weak":  # "weak" is the default and means process all
                if not item_strength or item_strength not in allowed_strengths:
                    total_skipped_dilemmas += 1
                    skipped_in_file += 1
                    continue  # Skip this item

            prompt = build_prompt(item)

            if args.dry:
                if total_processed_dilemmas > 0 or processed_in_file > 0:
                    print("\n" + "=" * 79)  # Separator for multiple dilemmas/files
                else:
                    print("=" * 79)
                print(prompt)
                print()
                answer = ""
            else:
                answer = call_llm(
                    prompt, args.model, args.temperature, args.reasoning_effort
                )
                print(f"{item['id']} → {answer[:80]}…")

            out_rows.append(
                {
                    "id": item["id"],
                    "model": args.model,
                    "timestamp": _dt.datetime.utcnow().isoformat() + "Z",
                    "prompt": prompt,
                    "answer": answer,
                    "source_file": str(
                        dilemmas_path.relative_to(ROOT)
                    ),  # Add source file
                }
            )
            processed_in_file += 1
            total_processed_dilemmas += 1
        print(
            f"Processed {processed_in_file} dilemmas from {dilemmas_path.relative_to(ROOT)}."
        )
        if skipped_in_file > 0:
            print(
                f"Skipped {skipped_in_file} dilemmas from {dilemmas_path.relative_to(ROOT)} due to strength filter."
            )

    if args.out:
        out_path = pathlib.Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as fh:
            for row in out_rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(
            f"Saved {len(out_rows)} total results from {len(dilemma_files)} file(s) → {out_path}"
        )
    elif not args.dry:
        print(
            f"Processed {total_processed_dilemmas} dilemmas from {len(dilemma_files)} file(s). No --out path specified, results not saved."
        )
    else:  # Dry run, no output file
        print(
            f"Dry run complete. Processed {total_processed_dilemmas} dilemmas from {len(dilemma_files)} file(s)."
        )
    if total_skipped_dilemmas > 0:
        print(
            f"Skipped a total of {total_skipped_dilemmas} dilemmas due to strength filter."
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Dilma dilemmas through an LLM")
    parser.add_argument(
        "--model",
        default="gpt-4o",
        help="Chat model to query (e.g., gpt-4o, grok-3-mini)",
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
