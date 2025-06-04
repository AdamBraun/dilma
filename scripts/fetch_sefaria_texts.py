#!/usr/bin/env python3
"""
Script to fetch all Talmud texts (Bavli and Yerushalmi) from Sefaria API.
For Mishna tractates that don't have Talmud, fetches the Mishna text instead.
"""

import json
import re
import requests
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

# Base URL for Sefaria API
SEFARIA_API_BASE = "https://www.sefaria.org/api/v3/texts/"

# All Mishna tractates organized by Seder
MISHNA_TRACTATES = {
    "Zeraim": [
        "Berakhot",
        "Peah",
        "Demai",
        "Kilayim",
        "Sheviit",
        "Terumot",
        "Maasrot",
        "Maaser Sheni",
        "Challah",
        "Orlah",
        "Bikkurim",
    ],
    "Moed": [
        "Shabbat",
        "Eruvin",
        "Pesachim",
        "Shekalim",
        "Yoma",
        "Sukkah",
        "Beitzah",
        "Rosh Hashanah",
        "Taanit",
        "Megillah",
        "Moed Katan",
        "Chagigah",
    ],
    "Nashim": [
        "Yevamot",
        "Ketubot",
        "Nedarim",
        "Nazir",
        "Sotah",
        "Gittin",
        "Kiddushin",
    ],
    "Nezikin": [
        "Bava Kamma",
        "Bava Metzia",
        "Bava Batra",
        "Sanhedrin",
        "Makkot",
        "Shevuot",
        "Eduyot",
        "Avodah Zarah",
        "Avot",
        "Horayot",
    ],
    "Kodashim": [
        "Zevachim",
        "Menachot",
        "Chullin",
        "Bekhorot",
        "Arakhin",
        "Temurah",
        "Keritot",
        "Meilah",
        "Tamid",
        "Middot",
        "Kinnim",
    ],
    "Taharot": [
        "Kelim",
        "Oholot",
        "Negaim",
        "Parah",
        "Taharot",
        "Mikvaot",
        "Niddah",
        "Makhshirin",
        "Zavim",
        "Tevul Yom",
        "Yadayim",
        "Oktzin",
    ],
}

# Tractates that have Bavli Talmud (verified from Sefaria index)
BAVLI_TRACTATES = [
    "Berakhot",
    "Shabbat",
    "Eruvin",
    "Pesachim",
    "Rosh Hashanah",
    "Yoma",
    "Sukkah",
    "Beitzah",
    "Taanit",
    "Megillah",
    "Moed Katan",
    "Chagigah",
    "Yevamot",
    "Ketubot",
    "Nedarim",
    "Nazir",
    "Sotah",
    "Gittin",
    "Kiddushin",
    "Bava Kamma",
    "Bava Metzia",
    "Bava Batra",
    "Sanhedrin",
    "Makkot",
    "Shevuot",
    "Avodah Zarah",
    "Horayot",
    "Zevachim",
    "Menachot",
    "Chullin",
    "Bekhorot",
    "Arakhin",
    "Temurah",
    "Keritot",
    "Meilah",
    "Niddah",
    "Tamid",
]

# Tractates that have Yerushalmi Talmud (verified from Sefaria index)
YERUSHALMI_TRACTATES = [
    "Berakhot",
    "Peah",
    "Demai",
    "Kilayim",
    "Sheviit",
    "Terumot",
    "Maasrot",
    "Maaser Sheni",
    "Challah",
    "Orlah",
    "Bikkurim",
    "Shabbat",
    "Eruvin",
    "Pesachim",
    "Shekalim",
    "Yoma",
    "Sukkah",
    "Beitzah",
    "Rosh Hashanah",
    "Taanit",
    "Megillah",
    "Chagigah",
    "Moed Katan",
    "Yevamot",
    "Ketubot",
    "Nedarim",
    "Nazir",
    "Sotah",
    "Gittin",
    "Kiddushin",
    "Bava Kamma",
    "Bava Metzia",
    "Bava Batra",
    "Sanhedrin",
    "Makkot",
    "Shevuot",
    "Avodah Zarah",
    "Horayot",
    "Niddah",
]


def sanitize_filename(name: str) -> str:
    """Sanitize a string to be used as a filename."""
    # Replace spaces and slashes with underscores
    sanitized = re.sub(r"[/\s]+", "_", name)
    # Remove other problematic characters
    sanitized = re.sub(r'[<>:"|?*]', "", sanitized)
    return sanitized


def fetch_text_from_sefaria(
    text_name: str, max_retries: int = 3
) -> Optional[Dict[str, Any]]:
    """
    Fetch text from Sefaria API with retry logic.

    Args:
        text_name: Name of the text to fetch
        max_retries: Maximum number of retry attempts

    Returns:
        JSON response as dictionary, or None if failed
    """
    url = f"{SEFARIA_API_BASE}{text_name}"
    headers = {"accept": "application/json"}

    for attempt in range(max_retries):
        try:
            print(f"  Fetching {text_name} (attempt {attempt + 1}/{max_retries})...")
            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                print(f"  Text '{text_name}' not found (404)")
                return None
            else:
                print(f"  HTTP {response.status_code} for {text_name}")
                if attempt < max_retries - 1:
                    time.sleep(2**attempt)  # Exponential backoff

        except requests.exceptions.RequestException as e:
            print(f"  Request failed for {text_name}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2**attempt)

    print(f"  Failed to fetch {text_name} after {max_retries} attempts")
    return None


def save_json_response(data: Dict[str, Any], filepath: Path) -> bool:
    """Save JSON response to file."""
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"  Error saving JSON to {filepath}: {e}")
        return False


def extract_text_content(data: Dict[str, Any]) -> str:
    """
    Extract readable text content from Sefaria JSON response.
    Handles various text structures and removes HTML tags.
    """

    def clean_html(text: str) -> str:
        """Remove HTML tags from text."""
        if not isinstance(text, str):
            return str(text)
        # Remove HTML tags
        clean = re.sub(r"<[^>]+>", "", text)
        # Clean up extra whitespace
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean

    def extract_from_structure(obj: Any, level: int = 0) -> List[str]:
        """Recursively extract text from nested structures."""
        texts = []

        if isinstance(obj, str):
            cleaned = clean_html(obj)
            if cleaned:
                texts.append(cleaned)
        elif isinstance(obj, list):
            for item in obj:
                texts.extend(extract_from_structure(item, level + 1))
        elif isinstance(obj, dict):
            # Look for common text fields
            text_fields = ["text", "he", "en", "content", "body"]
            for field in text_fields:
                if field in obj:
                    texts.extend(extract_from_structure(obj[field], level + 1))

            # If no text fields found, recurse through all values
            if not texts and level < 3:  # Limit recursion depth
                for value in obj.values():
                    texts.extend(extract_from_structure(value, level + 1))

        return texts

    # Extract all text content
    all_texts = extract_from_structure(data)

    # Join with appropriate separators
    if all_texts:
        return "\n\n".join(all_texts)
    else:
        return "No text content found"


def save_text_content(content: str, filepath: Path) -> bool:
    """Save text content to file."""
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"  Error saving text to {filepath}: {e}")
        return False


def main():
    """Main function to fetch all Talmud texts."""
    print("Starting Sefaria text fetching process...")
    print("Using verified Sefaria naming conventions:")
    print("  - Bavli: Simple tractate names (e.g., 'Berakhot')")
    print("  - Yerushalmi: 'Jerusalem Talmud [Tractate]'")
    print("  - Mishna: 'Mishnah [Tractate]'")

    # Create base directories
    sources_dir = Path("data/sources")
    texts_dir = Path("data/texts")
    sources_dir.mkdir(parents=True, exist_ok=True)
    texts_dir.mkdir(parents=True, exist_ok=True)

    # Get all unique tractate names
    all_tractates = set()
    for seder_tractates in MISHNA_TRACTATES.values():
        all_tractates.update(seder_tractates)

    total_tractates = len(all_tractates)
    processed = 0
    successful_fetches = 0

    print(f"\nProcessing {total_tractates} tractates...")

    for tractate in sorted(all_tractates):
        processed += 1
        print(f"\n[{processed}/{total_tractates}] Processing {tractate}...")

        # Try to fetch Bavli Talmud first
        if tractate in BAVLI_TRACTATES:
            bavli_name = tractate  # Sefaria uses simple names for Bavli
            bavli_data = fetch_text_from_sefaria(bavli_name)

            if bavli_data:
                # Save JSON
                json_filename = f"{sanitize_filename(tractate)}_bavli.json"
                json_path = sources_dir / json_filename
                if save_json_response(bavli_data, json_path):
                    print(f"  ✓ Saved Bavli JSON: {json_filename}")

                # Extract and save text
                text_content = extract_text_content(bavli_data)
                text_filename = f"{sanitize_filename(tractate)}_bavli.txt"
                text_path = texts_dir / text_filename
                if save_text_content(text_content, text_path):
                    print(f"  ✓ Saved Bavli text: {text_filename}")
                    successful_fetches += 1

        # Try to fetch Yerushalmi Talmud
        if tractate in YERUSHALMI_TRACTATES:
            yerushalmi_name = f"Jerusalem Talmud {tractate}"
            yerushalmi_data = fetch_text_from_sefaria(yerushalmi_name)

            if yerushalmi_data:
                # Save JSON
                json_filename = f"{sanitize_filename(tractate)}_yerushalmi.json"
                json_path = sources_dir / json_filename
                if save_json_response(yerushalmi_data, json_path):
                    print(f"  ✓ Saved Yerushalmi JSON: {json_filename}")

                # Extract and save text
                text_content = extract_text_content(yerushalmi_data)
                text_filename = f"{sanitize_filename(tractate)}_yerushalmi.txt"
                text_path = texts_dir / text_filename
                if save_text_content(text_content, text_path):
                    print(f"  ✓ Saved Yerushalmi text: {text_filename}")
                    successful_fetches += 1

        # Always try to fetch Mishna text as well
        mishna_name = f"Mishnah {tractate}"
        mishna_data = fetch_text_from_sefaria(mishna_name)

        if mishna_data:
            # Save JSON
            json_filename = f"{sanitize_filename(tractate)}_mishna.json"
            json_path = sources_dir / json_filename
            if save_json_response(mishna_data, json_path):
                print(f"  ✓ Saved Mishna JSON: {json_filename}")

            # Extract and save text
            text_content = extract_text_content(mishna_data)
            text_filename = f"{sanitize_filename(tractate)}_mishna.txt"
            text_path = texts_dir / text_filename
            if save_text_content(text_content, text_path):
                print(f"  ✓ Saved Mishna text: {text_filename}")
                successful_fetches += 1

        # Be respectful to the API - add a small delay
        time.sleep(1)

    print(f"\n✅ Completed processing all {total_tractates} tractates!")
    print(f"📊 Successfully fetched {successful_fetches} texts")
    print(f"📁 JSON files saved to: {sources_dir}")
    print(f"📄 Text files saved to: {texts_dir}")


if __name__ == "__main__":
    main()
