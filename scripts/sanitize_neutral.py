import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
NEUTRAL_DIR = ROOT / "data" / "dilemmas-neutral"

REPLACEMENTS = {
    r"\bShabbat\b": "rest day",
    r"\bshabbat\b": "rest day",
    r"\bShabbos\b": "rest day",
    r"\bGentile\b": "outsider",
    r"\bgentile\b": "outsider",
    r"\bJewish\b": "observant",
    r"\bsynagogue\b": "community center",
    r"\bRivka\b": "Robin",
    r"\bLeah\b": "Lena",
    r"\bYosef\b": "Alex",
    r"\bBeit Shammai\b": "School A",
    r"\bBeit Hillel\b": "School B",
    r"\bRabbi Meir\b": "Scholar M",
    r"\bSages\b": "experts",
    r"\bTorah\b": "core law",
    r"ye'ush": "despair",
    r"\bcircumcision\b": "infant procedure",
    r"\bcommandment\b": "obligation",
    r"Jerusalem-of-Gold": "ornate",
    r"\bJerusalem\b": "designated zone",
    r"\bIsrael\b": "head office",
    r"\bDiaspora\b": "remote region",
    r"\bHigh[- ]?Priest\b": "high official",
    r"\bPriest\b": "senior professional",
    r"\bkohen\b": "senior professional",
    r"\bTemple\b": "central complex",
    r"\bLevite\b": "junior professional",
    r"\bIsraelite\b": "mainstream group",
    r"\bmamzer\b": "stigmatized group member",
    r"\bchallah\b": "sample",
    r"am ha-aretz": "unaccredited vendor",
    r"\bshechita\b": "slaughter",
    r"\bmitzvah\b": "duty",
    r"non[- ]?kosher": "non-approved",
    r"kosher": "approved",
    r"Hekdesh": "dedicated",
    r"\baltar\b": "main platform",
    r"\bpriests\b": "senior professionals",
    r"\bpriesthood\b": "senior professional body",
    r"\bReuven\b": "Ronan",
    r"\bMoses\b": "Morgan",
    r"\bYevamot\b": "Levirate Cases",
    r"\byibbum\b": "levirate union",
    r"\bchalitzah\b": "release ceremony",
    r"\bKetubot\b": "Marriage Contracts",
    r"\bketubah\b": "marriage contract",
    r"\bNedarim\b": "Vows",
    r"\bNazir\b": "Abstainer",
    r"\bnazirite\b": "abstainer",
    r"\bSotah\b": "Suspected Infidelity",
    r"\bniddah\b": "cycle separation",
    r"\bmikveh\b": "immersion pool",
    r"\btevul[- ]?yom\b": "daytime immersant",
    r"\bzavim\b": "emission cases",
    r"\bzav\b": "emission case",
    r"Netilat Yadayim": "hand rinsing",
    r"\bterumah\b": "donated portion",
    r"\bshiva\b": "mourning period",
    r"\bhalakhic\b": "formal",
}

pattern = re.compile("|".join(REPLACEMENTS.keys()), flags=re.IGNORECASE)


def sanitize_text(text: str) -> str:
    def repl(match: re.Match) -> str:
        original = match.group(0)
        for key, val in REPLACEMENTS.items():
            if re.fullmatch(key, original, flags=re.IGNORECASE):
                return val
        return original

    return pattern.sub(repl, text)


def sanitize_file(path: pathlib.Path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    new_lines = []
    for line in lines:
        item = json.loads(line)
        item["title"] = sanitize_text(item["title"])
        item["vignette"] = sanitize_text(item["vignette"])
        for opt in item.get("options", []):
            opt["text"] = sanitize_text(opt["text"])
        new_lines.append(json.dumps(item, ensure_ascii=False, separators=(",", ":")))
    path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def main() -> None:
    for jf in NEUTRAL_DIR.rglob("*.jsonl"):
        sanitize_file(jf)


if __name__ == "__main__":
    main()
