import re
from typing import Dict, List, Optional


ERROR_PATTERNS = [
    re.compile(
        r"^(?P<file>.+?)\((?P<line>\d+)\):\s+error\s+(?P<code>[A-Z]\d+):\s+(?P<message>.+)$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^\*\*\*\s+ERROR\s+(?P<code>[A-Z]\d+):\s+(?P<message>.+)$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^C51\s+FATAL-ERROR\s+-\s*$",
        re.IGNORECASE,
    ),
]


def split_lines(text: str) -> List[str]:
    return [line.rstrip() for line in text.splitlines() if line.strip()]


def extract_first_error(text: str) -> Optional[Dict[str, str]]:
    lines = split_lines(text)

    for index, line in enumerate(lines):
        for pattern in ERROR_PATTERNS:
            match = pattern.match(line)
            if not match:
                continue

            groups = match.groupdict()
            if "FATAL-ERROR" in line.upper():
                message = ""
                for follow in lines[index + 1 : index + 6]:
                    if "ERROR:" in follow.upper():
                        message = follow.strip()
                        break
                return {
                    "raw": line if not message else f"{line} {message}",
                    "file": "",
                    "line": "",
                    "code": "FATAL",
                    "message": message or "Fatal error",
                }

            return {
                "raw": line,
                "file": groups.get("file", "").strip(),
                "line": groups.get("line", "").strip(),
                "code": groups.get("code", "").strip(),
                "message": groups.get("message", "").strip(),
            }

    return None
