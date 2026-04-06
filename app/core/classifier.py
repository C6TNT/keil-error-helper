import json
import sys
from pathlib import Path
from typing import Dict, List, Optional


def _get_rules_path() -> Path:
    candidates = []
    module_base = Path(__file__).resolve().parents[1]
    candidates.append(module_base / "data" / "keil_errors.json")

    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        meipass = Path(getattr(sys, "_MEIPASS"))
        candidates.append(meipass / "app" / "data" / "keil_errors.json")
        candidates.append(meipass / "data" / "keil_errors.json")

    for path in candidates:
        if path.exists():
            return path

    return candidates[0]


def load_rules() -> List[Dict]:
    data_path = _get_rules_path()
    return json.loads(data_path.read_text(encoding="utf-8"))


def classify_error(error: Dict[str, str], rules: List[Dict]) -> Optional[Dict]:
    raw = f"{error.get('raw', '')} {error.get('message', '')}".lower()

    for rule in rules:
        for token in rule.get("match", []):
            if token.lower() in raw:
                return rule

    return None
