import sys
from pathlib import Path


CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from core.engine import analyze_text


def main() -> None:
    print("请粘贴 Keil 编译输出，输入空行后按 Ctrl+Z 再回车结束：")
    lines = []
    try:
        while True:
            lines.append(input())
    except EOFError:
        pass

    text = "\n".join(lines).strip()
    result = analyze_text(text)
    print("\n" + "=" * 60)
    print(result["report"])
    print("=" * 60)


if __name__ == "__main__":
    main()
