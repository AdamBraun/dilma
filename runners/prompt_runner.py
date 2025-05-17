#!/usr/bin/env python3
"""Dilma — prompt runner

Usage examples:
    # Dry‑run: print prompts only
    python runners/prompt_runner.py \
        --model gpt-4o \
        --dilemmas data/dilemmas/nezikin/bava_metzia.jsonl \
        --dry

    # Real run, save outputs
    OPENAI_API_KEY=... python runners/prompt_runner.py \
        --model gpt-4o \
        --dilemmas data/dilemmas/nezikin/bava_metzia.jsonl \
        --out results/bava_metzia_gpt4o.jsonl

The script is intentionally minimal: no batching, retry, or cost tracking.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import pathlib
import sys
from typing import Iterable, List, Dict, Any

try:
    import openai  # Optional; only needed if --dry is *not* passed
except ModuleNotFoundError:
    openai = None  # Allows dry‑run without the package

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
        "What should be done? Choose one option and explain briefly.\n\n"
        f"{options_block}"
    )


def call_openai(prompt: str, model: str) -> str:
    if openai is None:
        raise RuntimeError(
            "openai package missing. Install with `pip install openai` or use --dry."
        )
    rsp = openai.ChatCompletion.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return rsp.choices[0].message.content.strip()


def run(args: argparse.Namespace) -> None:
    dilemmas_path = pathlib.Path(args.dilemmas).resolve()
    if not dilemmas_path.exists():
        sys.exit(f"❌ File not found: {dilemmas_path}")

    out_rows: List[Dict[str, Any]] = []

    for item in iter_jsonl(dilemmas_path):
        prompt = build_prompt(item)

        if args.dry:
            print("=" * 79)
            print(prompt)
            print()
            answer = ""
        else:
            answer = call_openai(prompt, args.model)
            print(f"{item['id']} → {answer[:80]}…")

        out_rows.append(
            {
                "id": item["id"],
                "model": args.model,
                "timestamp": _dt.datetime.utcnow().isoformat() + "Z",
                "prompt": prompt,
                "answer": answer,
            }
        )

    if args.out:
        out_path = pathlib.Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as fh:
            for row in out_rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"Saved {len(out_rows)} results → {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Dilma dilemmas through an LLM")
    parser.add_argument("--model", default="gpt-4o", help="Chat model to query")
    parser.add_argument(
        "--dilemmas", required=True, help="Path to *.jsonl dilemma file"
    )
    parser.add_argument(
        "--dry", action="store_true", help="Print prompts only, no API call"
    )
    parser.add_argument("--out", help="Optional output JSONL path for responses")
    run(parser.parse_args())
