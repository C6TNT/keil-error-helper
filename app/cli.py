try:
    from core.engine import analyze_text
except ModuleNotFoundError:
    from .core.engine import analyze_text


def main() -> None:
    print("请粘贴 Keil 编译输出，输入空行后按 Ctrl+Z 回车结束：")
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
