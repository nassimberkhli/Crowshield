def section(message: str) -> None:
    print()
    print("=" * 80)
    print(message)
    print("=" * 80)


def info(message: str) -> None:
    print(f"[INFO] {message}")


def success(message: str) -> None:
    print(f"[SUCCESS] {message}")
