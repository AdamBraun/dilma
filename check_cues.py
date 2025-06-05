#!/usr/bin/env python3
import json
import re

jewish_patterns = [
    r"\bberakhot\b",
    r"\bpeah\b",
    r"\bdemai\b",
    r"\bkilayim\b",
    r"\bsheviit\b",
    r"\bterumot\b",
    r"\bmaaserot\b",
    r"\bmaaser\b",
    r"\bchalah\b",
    r"\borlah\b",
    r"\bbikurim\b",
    r"\bzeraim\b",
    r"R\.\s*Shimon",
    r"R\.\s*Yehudah",
    r"Tanna Kamma",
    r"rabbi",
    r"rabbinic",
    r"\bprozbul\b",
    r"\bbi\'ur\b",
    r"\bmamzer\b",
    r"\bIsraelite\b",
    r"\bkosher\b",
    r"\btreif\b",
    r"\bhalakha\b",
    r"\bhalitzah\b",
    r"\bmitzvah\b",
    r"\bchesed\b",
    r"\bsiyum\b",
    r"\bget\b",
    r"\bbeit din\b",
    r"\bkorban\b",
    r"\bchatat\b",
    r"\bchelev\b",
    r"\bshekalim\b",
    r"\bsukkah\b",
    r"\bhachnasat orchim\b",
    r"\bshofar\b",
    r"\bMegillah\b",
    r"\bPurim\b",
    r"\bYom Kippur\b",
    r"\bRosh Hashanah\b",
    r"\bShabbat\b",
    r"\bYom Tov\b",
    r"\bPaschal\b",
    r"\bkashrut\b",
    r"\bTemple\b",
    r"\bJerusalem\b",
    r"\bTorah\b",
    r"\bTalmud\b",
    r"\bTalmudic\b",
    r"\bJewish\b",
    r"\bHebrew\b",
    r"\bIsrael\b",
    r"\bEretz-Yisrael\b",
    r"\bmikveh\b",
    r"\bimpurity\b",
    r"\bpurity\b",
    r"\britual\b.*\b(bath|impurity|purity)\b",
    r"\bHigh Priest\b",
    r"\bpriest\b",
    r"\boffering\b",
    r"\bsacrifice\b",
    r"zeraim/",
    r"moed/",
    r"nashim/",
    r"nezikin/",
    r"kodashim/",
    r"taharot/",
]


def contains_jewish_cues(text):
    text_lower = text.lower()
    for pattern in jewish_patterns:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True
    return False


jewish_entries = []

with open(
    "results/all_dilemmas_claude-sonnet-4-20250514.jsonl", "r", encoding="utf-8"
) as f:
    for line_num, line in enumerate(f, 1):
        try:
            entry = json.loads(line.strip())
            text_to_check = " ".join(
                [
                    str(entry.get("id", "")),
                    str(entry.get("prompt", "")),
                    str(entry.get("answer", "")),
                    str(entry.get("source_file", "")),
                    str(entry.get("dilemma_type", "")),
                ]
            )
            if contains_jewish_cues(text_to_check):
                jewish_entries.append(entry)
                print(
                    f"Found Jewish cues in entry {line_num}: {entry.get('id', 'unknown')}"
                )
        except json.JSONDecodeError as e:
            print(f"Error parsing line {line_num}: {e}")
            continue

print(f"\nFound {len(jewish_entries)} entries with Jewish cues")

output_file = "jewish_cues_entries.jsonl"
with open(output_file, "w", encoding="utf-8") as f:
    for entry in jewish_entries:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
print(f"Saved {len(jewish_entries)} entries to {output_file}")

cue_counts = {}
for entry in jewish_entries:
    text_to_check = " ".join(
        [
            str(entry.get("id", "")),
            str(entry.get("prompt", "")),
            str(entry.get("answer", "")),
            str(entry.get("source_file", "")),
            str(entry.get("dilemma_type", "")),
        ]
    )
    for pattern in jewish_patterns:
        matches = re.findall(pattern, text_to_check, re.IGNORECASE)
        if matches:
            pattern_key = pattern.replace("\\b", "").replace("\\", "")
            cue_counts[pattern_key] = cue_counts.get(pattern_key, 0) + len(matches)

print("\nSummary of Jewish cues found:")
for cue, count in sorted(cue_counts.items(), key=lambda x: x[1], reverse=True):
    print(f"  {cue}: {count} occurrences")
