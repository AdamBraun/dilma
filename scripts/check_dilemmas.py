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
from typing import List

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


def parse_runner_output(results_file: pathlib.Path, all_dilemmas: dict) -> List[List[str]]:
    """Parses a single LLM results JSONL file and returns rows for CSV output."""
    rows_for_csv: List[List[str]] = []
    if not results_file.exists():
        print(f"⚠️ Results file not found: {results_file}. Skipping its processing.")
        return rows_for_csv

    with results_file.open("r", encoding="utf-8") as fh_results:
        for line_num, line in enumerate(fh_results, 1):
            if not line.strip():
                continue
            try:
                result_obj = json.loads(line)
            except json.JSONDecodeError as e:
                print(
                    f"Error parsing JSON from {results_file.name}:{line_num}: {e} in line: {line.strip()}"
                )
                continue

            dilemma_id = result_obj.get("id")
            answer = result_obj.get("answer", "").strip()
            model_name = result_obj.get("model", "unknown_model")
            dilemma_type = result_obj.get("dilemma_type", "unknown") # Extract dilemma_type

            if not dilemma_id or not answer:
                print(f"Skipping entry in {results_file.name}:{line_num} with missing id or answer: {result_obj}")
                continue

            parsed_choice_id = "UNPARSEABLE" # Default
            chosen_tags_str = "unparseable"
            
            first_token = answer.split(maxsplit=1)[0].upper().rstrip(".,:;")

            if first_token == "A":
                parsed_choice_id = "A"
            elif first_token == "B":
                parsed_choice_id = "B"
            elif first_token == "INVALID" or first_token == "I":
                parsed_choice_id = "INVALID"

            dilemma_data = all_dilemmas.get(dilemma_id)
            if not dilemma_data:
                print(f"Dilemma {dilemma_id} from {results_file.name}:{line_num} not found in source files. Marking as UNKNOWN_DILEMMA.")
                # chosen_tags_str remains "unparseable" or similar, choice is effectively unknown
                rows_for_csv.append([dilemma_id, "UNKNOWN_DILEMMA", "error", model_name, dilemma_type])
                continue

            if parsed_choice_id == "A":
                tags = next((
                    opt.get("tags", []) 
                    for opt in dilemma_data.get("options", []) 
                    if opt.get("id") == "A"
                ), None) # Default to None to distinguish from empty list
                chosen_tags_str = ",".join(tags) if tags is not None else "error_tag_not_found"
                if tags is not None and not tags: # Explicitly empty tags list
                    chosen_tags_str = "no_tags"
            elif parsed_choice_id == "B":
                tags = next((
                    opt.get("tags", []) 
                    for opt in dilemma_data.get("options", []) 
                    if opt.get("id") == "B"
                ), None)
                chosen_tags_str = ",".join(tags) if tags is not None else "error_tag_not_found"
                if tags is not None and not tags:
                    chosen_tags_str = "no_tags"
            elif parsed_choice_id == "INVALID":
                chosen_tags_str = "invalid"
            else: # UNPARSEABLE
                print(
                    f"Warning: Could not parse choice for {dilemma_id} from {results_file.name}:{line_num} answer: '{answer[:50]}...' (First token: '{first_token}')"
                )
                # chosen_tags_str is already "unparseable", parsed_choice_id is "UNPARSEABLE"
            
            rows_for_csv.append([dilemma_id, parsed_choice_id, chosen_tags_str, model_name, dilemma_type])
            
    return rows_for_csv


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Check Dilma dilemmas and optionally parse LLM results."
    )
    parser.add_argument(
        "--results",
        type=pathlib.Path,
        help="Optional path to an LLM results JSONL file or a directory containing "
        "LLM results JSONL files to parse for value-label distribution.",
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
        results_path: pathlib.Path = args.results

        result_files_to_process = []
        if not results_path.exists():
            print(f"⚠️ Results path not found: {results_path}. No CSV will be generated/updated.")
        elif results_path.is_file():
            if results_path.suffix == ".jsonl":
                result_files_to_process.append(results_path)
            else:
                print(
                    f"⚠️ Specified results file is not a .jsonl file: {results_path}. No CSV will be generated/updated."
                )
        elif results_path.is_dir():
            found_files = sorted(list(results_path.glob("*.jsonl")))
            if not found_files:
                print(
                    f"⚠️ No .jsonl files found in results directory: {results_path}. No CSV will be generated/updated."
                )
            else:
                result_files_to_process.extend(found_files)
        else:
            print(
                f"⚠️ Results path is not a valid file or directory: {results_path}. No CSV will be generated/updated."
            )

        if not result_files_to_process:
            print("No result files to process for CSV generation.")
        else:
            print(f"Found {len(result_files_to_process)} result file(s) to process for CSV.")
            
            output_csv_path = RESULTS_DIR / "value_label_distribution.csv"
            RESULTS_DIR.mkdir(parents=True, exist_ok=True)
            
            csv_header = ["dilemma_id", "choice_id", "chosen_value_labels", "model_name", "dilemma_type"]
            can_write_to_csv = True
            write_new_header_row = False

            if not output_csv_path.exists() or output_csv_path.stat().st_size == 0:
                write_new_header_row = True
            else:
                try:
                    with output_csv_path.open("r", newline="", encoding="utf-8") as fh_check:
                        reader = csv.reader(fh_check)
                        existing_header = next(reader)
                        if "dilemma_type" not in existing_header:
                            print(f"❌ ERROR: The existing CSV file \n  '{output_csv_path}' \nhas an outdated format (missing 'dilemma_type' column).")
                            print("To prevent data corruption, please backup/rename this file and re-run the script.")
                            print("No new data will be appended to this CSV file in this run.")
                            can_write_to_csv = False
                except StopIteration: # File exists but is empty
                    write_new_header_row = True
                except Exception as e:
                    print(f"Error reading existing CSV header: {e}. Assuming incompatible.")
                    can_write_to_csv = False

            master_csv_rows = []
            for res_file_path in result_files_to_process:
                print(f"Parsing results from: {res_file_path.name}")
                parsed_rows = parse_runner_output(res_file_path, all_dilemmas_data)
                master_csv_rows.extend(parsed_rows)

            if can_write_to_csv:
                if master_csv_rows:
                    try:
                        with output_csv_path.open(mode="a", newline="", encoding="utf-8") as fh_csv:
                            writer = csv.writer(fh_csv)
                            if write_new_header_row:
                                writer.writerow(csv_header)
                            writer.writerows(master_csv_rows)
                        print(f"📊 Successfully appended {len(master_csv_rows)} new records to {output_csv_path}")
                        if write_new_header_row:
                            print("(New CSV file created or header written to empty file.)")
                    except IOError as e:
                        print(f"❌ Error writing to CSV file '{output_csv_path}': {e}")
                else:
                    print("No new valid records found to add to the CSV.")
            elif master_csv_rows: # Can't write, but had rows
                 print(f"Parsed {len(master_csv_rows)} records, but CSV writing was skipped due to header incompatibility.")
            else: # Can't write and no rows, or can write but no rows
                if not can_write_to_csv:
                     print("CSV writing skipped due to header incompatibility and no new records were parsed.")
                # else: (can_write_to_csv is true, but no master_csv_rows - covered by "No new valid records...")

    if errors:  # Exit with error if dilemma files had issues
        sys.exit(1)
