#!/usr/bin/env python
"""
Quick integrity checks for Dilma dilemmas:
1. Every JSON object parses.
2. Required keys exist.
3. Option tags appear in value_labels.yaml.
"""
import json
import pathlib
import sys
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
LABELS = ROOT / "data" / "annotations" / "value_labels.yaml"
DILEMMA_DIR = ROOT / "data" / "dilemmas"

allowed = set(yaml.safe_load(LABELS.read_text())["tags"].keys())

errors = 0
for jf in DILEMMA_DIR.rglob("*.jsonl"):
    for ln, line in enumerate(jf.read_text().splitlines(), 1):
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            print(f"{jf}:{ln} JSON error → {e}")
            errors += 1
            continue

        for key in ("id", "vignette", "options"):
            if key not in obj:
                print(f"{jf}:{ln} missing field: {key}")
                errors += 1

        for opt in obj.get("options", []):
            bad = [t for t in opt.get("tags", []) if t not in allowed]
            if bad:
                print(f"{jf}:{ln} unknown tags {bad} in option {opt['id']}")
                errors += 1

if errors:
    print(f"❌ {errors} error(s) found")
    sys.exit(1)
print("✅ All dilemma files look good")
