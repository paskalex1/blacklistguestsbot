import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
COUNTRIES_FILE = DATA_DIR / "countries.json"


def load_countries() -> list[str]:
    if not COUNTRIES_FILE.exists():
        return ["Россия", "Казахстан", "Беларусь", "Абхазия"]
    with COUNTRIES_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_countries(countries: list[str]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with COUNTRIES_FILE.open("w", encoding="utf-8") as f:
        json.dump(countries, f, ensure_ascii=False, indent=2)
