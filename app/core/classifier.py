import json
from pathlib import Path
from typing import Dict, List, Optional


def load_rules() -> List[Dict]:
    data_path = Path(__file__).resolve().parents[1] / "data" / "keil_errors.json"
    return json.loads(data_path.read_text(encoding="utf-8"))


def classify_error(error: Dict[str, str], rules: List[Dict]) -> Optional[Dict]:
    raw = f"{error.get('raw', '')} {error.get('message', '')}".lower()

    for rule in rules:
        for token in rule.get("match", []):
            if token.lower() in raw:
                return rule

    return None
