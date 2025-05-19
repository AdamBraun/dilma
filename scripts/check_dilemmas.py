#!/usr/bin/env python
"""
Quick integrity checks for Dilma dilemmas:
1. Every JSON object parses.
2. Required keys exist.
3. Option tags appear in value_labels.yaml.
"""
import argparse
import csv
import json
import pathlib
import sys
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
LABELS = ROOT / "data" / "annotations" / "value_labels.yaml"
DILEMMA_DIR = ROOT / "data" / "dilemmas"
RESULTS_DIR = ROOT / "results"

allowed = set(yaml.safe_load(LABELS.read_text())["tags"].keys())


# Function to load all dilemmas into a dictionary for easy lookup
def load_all_dilemmas(dilemma_dir: pathlib.Path) -> dict:
    all_dilemmas = {}
    for jf in dilemma_dir.rglob("*.jsonl"):
        for line in jf.read_text().splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            all_dilemmas[obj["id"]] = obj
    return all_dilemmas


def check_dilemma_files() -> int:
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
    return errors


def parse_runner_output(results_file: pathlib.Path, all_dilemmas: dict) -> list:
    parsed_results = []
    if not results_file.exists():
        print(f"⚠️ Results file not found: {results_file}. Skipping CSV generation.")
        return parsed_results

    output_csv_path = RESULTS_DIR / "value_label_distribution.csv"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    file_exists = output_csv_path.exists()

    with results_file.open("r", encoding="utf-8") as fh_results, output_csv_path.open(
        mode="a" if file_exists else "w", newline="", encoding="utf-8"
    ) as fh_csv:

        writer = csv.writer(fh_csv)
        if not file_exists:
            writer.writerow(
                ["dilemma_id", "choice_id", "chosen_value_labels", "model_name"]
            )

        for line in fh_results:
            if not line.strip():
                continue
            try:
                result_obj = json.loads(line)
            except json.JSONDecodeError as e:
                print(
                    f"Error parsing JSON from results file: {e} in line: {line.strip()}"
                )
                continue

            dilemma_id = result_obj.get("id")
            answer = result_obj.get("answer", "").strip()
            model_name = result_obj.get("model", "unknown_model")

            if not dilemma_id or not answer:
                print(f"Skipping entry with missing id or answer: {result_obj}")
                continue

            # Refined parsing logic:
            parsed_choice = ""
            first_token = answer.split(maxsplit=1)[
                0
            ].upper()  # Get the first word/token
            # Strip common trailing punctuation
            first_token = first_token.rstrip(".,:")

            if first_token == "A":
                parsed_choice = "A"
            elif first_token == "B":
                parsed_choice = "B"
            elif first_token == "INVALID" or first_token == "I":
                parsed_choice = "INVALID"

            dilemma_data = all_dilemmas.get(dilemma_id)
            if not dilemma_data:
                print(f"Dilemma {dilemma_id} not found in source files. Skipping.")
                writer.writerow([dilemma_id, "UNKNOWN_DILEMMA", "error", model_name])
                continue

            if parsed_choice == "A":
                option_id = "A"
                tags = next(
                    (
                        opt.get("tags", [])
                        for opt in dilemma_data.get("options", [])
                        if opt.get("id") == "A"
                    ),
                    ["error_tag_not_found"],
                )
                writer.writerow(
                    [
                        dilemma_id,
                        option_id,
                        ",".join(tags) if tags else "no_tags",
                        model_name,
                    ]
                )
                parsed_results.append(
                    {
                        "id": dilemma_id,
                        "choice": option_id,
                        "tags": tags,
                        "model": model_name,
                    }
                )
            elif parsed_choice == "B":
                option_id = "B"
                tags = next(
                    (
                        opt.get("tags", [])
                        for opt in dilemma_data.get("options", [])
                        if opt.get("id") == "B"
                    ),
                    ["error_tag_not_found"],
                )
                writer.writerow(
                    [
                        dilemma_id,
                        option_id,
                        ",".join(tags) if tags else "no_tags",
                        model_name,
                    ]
                )
                parsed_results.append(
                    {
                        "id": dilemma_id,
                        "choice": option_id,
                        "tags": tags,
                        "model": model_name,
                    }
                )
            elif parsed_choice == "INVALID":
                writer.writerow([dilemma_id, "INVALID", "invalid", model_name])
                parsed_results.append(
                    {
                        "id": dilemma_id,
                        "choice": "INVALID",
                        "tags": ["invalid"],
                        "model": model_name,
                    }
                )
            else:
                # Handle cases where the answer is not clearly A, B, or INVALID
                print(
                    f"Warning: Could not parse choice for {dilemma_id} from answer: '{answer[:50]}...' (First token: '{first_token}')"
                )
                writer.writerow([dilemma_id, "UNPARSEABLE", "unparseable", model_name])
                parsed_results.append(
                    {
                        "id": dilemma_id,
                        "choice": "UNPARSEABLE",
                        "tags": ["unparseable"],
                        "model": model_name,
                    }
                )

    print(f"📊 Value label distribution saved to {output_csv_path}")
    return parsed_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Check Dilma dilemmas and optionally parse LLM results."
    )
    parser.add_argument(
        "--results",
        type=pathlib.Path,
        help="Optional path to LLM results JSONL file to parse for value-label distribution.",
    )
    args = parser.parse_args()

    # Always check dilemma files
    errors = check_dilemma_files()
    if errors:
        print(f"❌ {errors} error(s) found in dilemma files.")
        # We still proceed to parse results if provided, as they might be independent
    else:
        print("✅ All dilemma files look good.")

    # Parse results if the argument is provided
    if args.results:
        all_dilemmas_data = load_all_dilemmas(DILEMMA_DIR)
        parse_runner_output(args.results, all_dilemmas_data)

    if errors:  # Exit with error if dilemma files had issues
        sys.exit(1)
